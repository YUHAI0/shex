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


def _execute_with_pty(command: str, encoding: str, timeout: int) -> dict:
    """
    使用 PTY（伪终端）执行命令，支持进度条等交互式输出
    仅在 Linux/Unix 上使用
    """
    import time
    import re
    
    master_fd, slave_fd = pty.openpty()
    
    # 设置终端大小（可选，某些程序需要）
    try:
        winsize = struct.pack('HHHH', 24, 80, 0, 0)  # rows, cols, xpixel, ypixel
        fcntl.ioctl(slave_fd, termios.TIOCSWINSZ, winsize)
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
    last_output_time = time.time()
    
    # 交互提示检测模式（需要精确匹配避免误触发）
    interactive_patterns = [
        r'\[Y/n\]\s*$',                    # apt: [Y/n]
        r'\[y/N\]\s*$',                    # [y/N]
        r'\[N/y\]\s*$',                    # [N/y]
        r'\[yes/no\]\s*$',                 # [yes/no]
        r'\(yes/no\)\s*$',                 # (yes/no)
        r'\[Y/n/\?\]\s*$',                 # pacman 等
        r'\(y/n\)\s*$',                    # (y/n)
        r'password\s*(for\s+\S+)?:\s*$',   # 密码提示
        r'passphrase.*:\s*$',              # SSH passphrase
        r'continue\?\s*',                  # continue?
        r'proceed\?\s*',                   # proceed?
        r'overwrite\?.*$',                 # overwrite?
        r'enter.*:\s*$',                   # Enter xxx:
        r'input.*:\s*$',                   # Input xxx:
    ]
    
    waiting_for_input = False
    skip_echo_bytes = 0  # 需要跳过的回显字节数
    
    def check_interactive_prompt(current_output: str) -> bool:
        """检查是否有交互提示"""
        recent_output = current_output[-500:] if len(current_output) > 500 else current_output
        for pattern in interactive_patterns:
            if re.search(pattern, recent_output, re.IGNORECASE):
                return True
        return False
    
    def read_user_input_and_send():
        """读取用户输入并发送到子进程"""
        nonlocal waiting_for_input, skip_echo_bytes
        try:
            user_input = input()
            data_to_send = user_input + '\n'
            os.write(master_fd, data_to_send.encode(encoding))
            # PTY 会回显输入，需要跳过这些字节
            skip_echo_bytes = len(data_to_send.encode(encoding))
            waiting_for_input = False
        except (EOFError, OSError):
            pass
    
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
            
            # 检查是否有数据可读
            ready, _, _ = select.select([master_fd], [], [], 0.1)
            if ready:
                try:
                    data = os.read(master_fd, 4096)
                    if data:
                        # 跳过用户输入的回显
                        if skip_echo_bytes > 0:
                            if len(data) <= skip_echo_bytes:
                                skip_echo_bytes -= len(data)
                                data = b''
                            else:
                                data = data[skip_echo_bytes:]
                                skip_echo_bytes = 0
                        
                        if data:
                            text = data.decode(encoding, errors='replace')
                            output_data.append(text)
                            # 直接输出到终端（保留原始格式，包括 \r）
                            sys.stdout.write(text)
                            sys.stdout.flush()
                        last_output_time = time.time()
                except OSError:
                    break
            else:
                # 没有新输出，检查是否在等待交互
                # 如果超过 0.5 秒没有新输出且进程还在运行，检查交互提示
                if (time.time() - last_output_time > 0.5 and 
                    process.poll() is None and 
                    output_data and
                    not waiting_for_input):
                    current_output = ''.join(output_data)
                    if check_interactive_prompt(current_output):
                        waiting_for_input = True
                        read_user_input_and_send()
                        last_output_time = time.time()  # 重置时间
            
            # 检查进程是否结束
            if process.poll() is not None:
                # 读取剩余输出
                while True:
                    ready, _, _ = select.select([master_fd], [], [], 0.1)
                    if ready:
                        try:
                            data = os.read(master_fd, 4096)
                            if data:
                                text = data.decode(encoding, errors='replace')
                                output_data.append(text)
                                sys.stdout.write(text)
                                sys.stdout.flush()
                            else:
                                break
                        except OSError:
                            break
                    else:
                        break
                break
    finally:
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
    
    try:
        # Linux/Unix 使用 PTY（伪终端）来支持进度条等交互式输出
        if platform.system() != "Windows":
            return _execute_with_pty(command, 'utf-8', timeout)
        
        # Windows：强制使用 UTF-8 编码 (chcp 65001)
        # 这样可以避免 GBK/CP936 编码问题
        wrapped_command = f'cmd /c "chcp 65001 >nul && {command}"'
        encoding = 'utf-8'
        
        process = subprocess.Popen(
            wrapped_command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            encoding=encoding,
            errors='replace'
        )
        
        stdout_data = []
        stderr_data = []
        
        # 在 Windows 上启用 ANSI 转义序列支持
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32
            kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
        except Exception:
            pass
        
        def read_stdout():
            while True:
                char = process.stdout.read(1)
                if not char:
                    break
                stdout_data.append(char)
                if char == '\r':
                    sys.stdout.write('\x1b[2K\r')
                    sys.stdout.flush()
                elif char == '\n':
                    sys.stdout.write('\n')
                    sys.stdout.flush()
                else:
                    sys.stdout.write(char)
                    sys.stdout.flush()
        
        def read_stderr():
            while True:
                char = process.stderr.read(1)
                if not char:
                    break
                stderr_data.append(char)
                if char == '\r':
                    sys.stderr.write('\x1b[2K\r')
                    sys.stderr.flush()
                elif char == '\n':
                    sys.stderr.write('\n')
                    sys.stderr.flush()
                else:
                    sys.stderr.write(char)
                    sys.stderr.flush()
        
        stdout_thread = threading.Thread(target=read_stdout)
        stderr_thread = threading.Thread(target=read_stderr)
        
        stdout_thread.start()
        stderr_thread.start()
        
        try:
            process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            process.kill()
            stdout_thread.join(timeout=1)
            stderr_thread.join(timeout=1)
            return {
                "success": False,
                "output": process_carriage_return(''.join(stdout_data)),
                "error": t("command_timeout", timeout=timeout),
                "return_code": -2
            }
        
        stdout_thread.join()
        stderr_thread.join()
        
        stdout_text = process_carriage_return(''.join(stdout_data))
        stderr_text = process_carriage_return(''.join(stderr_data))
        
        return {
            "success": process.returncode == 0,
            "output": stdout_text,
            "error": stderr_text,
            "return_code": process.returncode
        }
        
    except Exception as e:
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
