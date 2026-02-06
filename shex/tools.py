"""
Shex 工具定义
定义大模型可调用的工具
"""

import subprocess
import platform
import os
import sys
import locale
import threading
import select
from typing import Callable
from .i18n import t
from .spinner import Spinner

# Linux/Unix 上使用 pty 模块
if platform.system() != "Windows":
    import pty
    import fcntl
    import struct
    import termios


def process_carriage_return(text: str) -> str:
    """
    处理包含 \\r (回车) 的文本，模拟终端对进度条的显示行为
    
    进度条通常使用 \\r 回到行首覆盖之前的内容，本函数将：
    - 同一行内的多次 \\r 覆盖合并为最终显示内容
    - 保留正常的换行符 \\n
    
    Args:
        text: 包含 \\r 的原始文本
        
    Returns:
        处理后的文本，只保留最终显示内容
    """
    if '\r' not in text:
        return text
    
    lines = []
    current_line = ""
    
    i = 0
    while i < len(text):
        char = text[i]
        
        if char == '\n':
            # 换行：保存当前行并开始新行
            lines.append(current_line)
            current_line = ""
        elif char == '\r':
            # 检查是否是 \r\n (Windows 换行)
            if i + 1 < len(text) and text[i + 1] == '\n':
                lines.append(current_line)
                current_line = ""
                i += 1  # 跳过 \n
            else:
                # 单独的 \r：回到行首（清空当前行以准备覆盖）
                current_line = ""
        else:
            current_line += char
        
        i += 1
    
    # 添加最后一行（如果有）
    if current_line:
        lines.append(current_line)
    
    return '\n'.join(lines)


def _execute_with_pty(command: str, encoding: str, timeout: int, spinner: Spinner = None) -> dict:
    """
    使用 PTY（伪终端）执行命令，支持进度条等交互式输出
    仅在 Linux/Unix 上使用
    """
    import time
    import re
    import tty  # 新增
    
    master_fd, slave_fd = pty.openpty()
    
    # 设置终端大小（可选，某些程序需要）
    try:
        winsize = struct.pack('HHHH', 24, 80, 0, 0)  # rows, cols, xpixel, ypixel
        fcntl.ioctl(slave_fd, termios.TIOCSWINSZ, winsize)
    except Exception:
        pass
    
    # 尝试将 stdin 设置为 raw 模式，以便转发所有按键（包括方向键等）
    old_tty_attrs = None
    try:
        old_tty_attrs = termios.tcgetattr(sys.stdin)
        tty.setraw(sys.stdin.fileno())
    except Exception:
        pass

    process = subprocess.Popen(
        command,
        shell=True,
        stdin=slave_fd,
        stdout=slave_fd,
        stderr=slave_fd,
        close_fds=True,
        executable='/bin/bash'
    )
    
    os.close(slave_fd)
    
    # 设置非阻塞读取
    flags = fcntl.fcntl(master_fd, fcntl.F_GETFL)
    fcntl.fcntl(master_fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)
    
    output_data = []
    start_time = time.time()
    
    try:
        while True:
            # 检查超时
            if time.time() - start_time > timeout:
                process.kill()
                return {
                    "success": False,
                    "output": process_carriage_return(''.join(output_data)),
                    "error": t("command_timeout", timeout=timeout),
                    "return_code": -2
                }
            
            # 监听 master_fd (子进程输出) 和 stdin (用户输入)
            rlist = [master_fd]
            if old_tty_attrs: # 只有在成功设置 raw 模式后才监听 stdin
                 rlist.append(sys.stdin)
            
            ready, _, _ = select.select(rlist, [], [], 0.1)
            
            if master_fd in ready:
                try:
                    data = os.read(master_fd, 4096)
                    if data:
                        # 只要有输出，就永久停止 Spinner，避免破坏 TUI 界面
                        if spinner and spinner.running:
                            spinner.stop()
                        
                        # 在 Raw 模式下，直接写入 stdout（不使用 Spinner.write，避免二次处理）
                        # 注意：Raw 模式下需要手动处理 \n -> \r\n，但子进程输出通常已经是处理好的
                        if old_tty_attrs:
                             # 尝试添加颜色，增强用户体验
                             # 注意：这可能会在极其罕见的情况下破坏被截断的 ANSI 序列
                             # 但为了满足用户对颜色的需求，这是一个折衷方案
                             cyan = b'\x1b[96m'
                             reset = b'\x1b[0m'
                             os.write(sys.stdout.fileno(), cyan + data + reset)
                        else:
                             # 如果没进入 Raw 模式，使用 spinner.write 打印彩色输出
                             text = data.decode(encoding, errors='replace')
                             spinner.write(text, color="\033[96m")
                        
                        # 保存输出用于给 LLM
                        output_data.append(data.decode(encoding, errors='replace'))
                    else:
                        break # EOF
                except OSError:
                    break
            
            if sys.stdin in ready:
                try:
                    # 读取用户输入直接写入 master_fd
                    input_data = os.read(sys.stdin.fileno(), 1024)
                    os.write(master_fd, input_data)
                except OSError:
                    pass
            
            # 检查进程是否结束
            if process.poll() is not None:
                # 读取剩余输出
                while True:
                    ready, _, _ = select.select([master_fd], [], [], 0.1)
                    if ready:
                        try:
                            data = os.read(master_fd, 4096)
                            if data:
                                if spinner and spinner.running:
                                    spinner.stop()
                                    
                                if old_tty_attrs:
                                     cyan = b'\x1b[96m'
                                     reset = b'\x1b[0m'
                                     os.write(sys.stdout.fileno(), cyan + data + reset)
                                else:
                                     text = data.decode(encoding, errors='replace')
                                     spinner.write(text, color="\033[96m")
                                output_data.append(data.decode(encoding, errors='replace'))
                            else:
                                break
                        except OSError:
                            break
                    else:
                        break
                break
    finally:
        # 恢复终端设置
        if old_tty_attrs:
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_tty_attrs)
        
        try:
            os.close(master_fd)
        except OSError:
            pass
    
    output_text = process_carriage_return(''.join(output_data))
    
    return {
        "success": process.returncode == 0,
        "output": output_text,
        "error": "",  # PTY 模式下 stderr 合并到 stdout
        "return_code": process.returncode
    }


def execute_command(
    command: str,
    is_dangerous: bool = False,
    timeout: int = 60,
    confirm_fn: Callable[[str], bool] = None
) -> dict:
    """
    执行系统命令
    
    Args:
        command: 要执行的命令
        is_dangerous: 是否为危险命令（由大模型判断）
        timeout: 超时时间（秒）
        confirm_fn: 危险命令确认函数，接收 command 返回是否执行
        
    Returns:
        执行结果字典
    """
    # 危险命令需要用户确认
    if is_dangerous and confirm_fn:
        if not confirm_fn(command):
            return {
                "success": False,
                "output": "",
                "error": t("user_cancelled"),
                "return_code": -1
            }
            
    # 初始化并启动 Spinner
    spinner = Spinner(t("executing"), delay=0.1)
    spinner.start()
    
    try:
        # Linux/Unix 使用 PTY（伪终端）来支持进度条等交互式输出
        if platform.system() != "Windows":
            result = _execute_with_pty(command, 'utf-8', timeout, spinner)
            if spinner:
                spinner.stop()
            return result
        
        # Windows：尝试设置编码并执行
        # 注意：不要使用 cmd /c "..." 包裹整个命令，因为内部的双引号会与命令中的双引号冲突
        # 导致管道符 | 等被外层 cmd 错误解释
        if is_dangerous:
            # 危险命令如果不包含 chcp 可能乱码，但为了安全性优先保证命令结构正确
            # 或者我们也可以用 chcp && command 的形式
            wrapped_command = f'chcp 65001 >nul && {command}'
        else:
            wrapped_command = f'chcp 65001 >nul && {command}'
            
        encoding = 'utf-8'
        
        process = subprocess.Popen(
            wrapped_command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, # 合并 stderr 到 stdout
            encoding=encoding,
            errors='replace'
        )
        
        stdout_data = []
        # stderr_data 不再需要，因为合并了
        
        # 在 Windows 上启用 ANSI 转义序列支持
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32
            kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
        except Exception:
            pass
        
        def read_stdout():
            while True:
                # 尝试读取较大的块，减少锁的竞争
                char = process.stdout.read(1)
                if not char:
                    break
                stdout_data.append(char)
                
                # 使用青色输出命令结果 (\033[96m)
                spinner.write(char, sys.stdout, color="\033[96m")
        
        # 不再需要 read_stderr 线程
        
        stdout_thread = threading.Thread(target=read_stdout)
        
        stdout_thread.start()
        
        try:
            process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            process.kill()
            # 停止 Spinner，这将阻止后续的输出写入 stdout
            if spinner:
                spinner.stop()
            
            # 即使线程还没结束，因为 spinner 已经停止，它们也不会再污染输出了
            stdout_thread.join(timeout=1)
            
            return {
                "success": False,
                "output": process_carriage_return(''.join(stdout_data)),
                "error": t("command_timeout", timeout=timeout),
                "return_code": -2
            }
        
        stdout_thread.join()

        # 停止 Spinner
        if spinner:
            spinner.stop()
        
        stdout_text = process_carriage_return(''.join(stdout_data))
        stderr_text = "" # stderr 已合并到 stdout
        
        return {
            "success": process.returncode == 0,
            "output": stdout_text,
            "error": stderr_text,
            "return_code": process.returncode
        }
        
    except Exception as e:
        if spinner:
            spinner.stop()
        return {
            "success": False,
            "output": "",
            "error": str(e),
            "return_code": -3
        }


def get_system_info() -> str:
    """获取系统信息"""
    info = {
        "os": platform.system(),
        "os_version": platform.version(),
        "architecture": platform.architecture()[0],
        "machine": platform.machine(),
        "cwd": os.getcwd(),
        "user": os.getenv("USERNAME") or os.getenv("USER", "unknown"),
        "shell": os.getenv("SHELL") or os.getenv("COMSPEC", "unknown")
    }
    return "\n".join([f"- {k}: {v}" for k, v in info.items()])


# Tool 定义（OpenAI Function Calling 格式）
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "execute_command",
            "description": "执行系统命令。用于完成用户请求的文件操作、系统查询、程序运行等任务。",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "要执行的系统命令"
                    },
                    "explanation": {
                        "type": "string", 
                        "description": "命令的作用说明"
                    },
                    "is_dangerous": {
                        "type": "boolean",
                        "description": "命令是否危险（可能导致数据丢失、系统损坏等），危险命令需要用户确认"
                    }
                },
                "required": ["command", "explanation", "is_dangerous"]
            }
        }
    }
]
