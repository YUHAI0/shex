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
from typing import Callable


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
                "error": "用户取消执行危险命令",
                "return_code": -1
            }
    
    try:
        # 获取系统编码
        if platform.system() == "Windows":
            encoding = locale.getpreferredencoding(False)
        else:
            encoding = 'utf-8'
        
        # 使用 Popen 实时输出
        if platform.system() == "Windows":
            process = subprocess.Popen(
                command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                encoding=encoding,
                errors='replace'
            )
        else:
            process = subprocess.Popen(
                command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                encoding=encoding,
                errors='replace',
                executable='/bin/bash'
            )
        
        stdout_data = []
        stderr_data = []
        
        def read_stdout():
            while True:
                char = process.stdout.read(1)
                if not char:
                    break
                stdout_data.append(char)
                print(char, end='', flush=True)
        
        def read_stderr():
            while True:
                char = process.stderr.read(1)
                if not char:
                    break
                stderr_data.append(char)
                print(char, end='', file=sys.stderr, flush=True)
        
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
                "output": ''.join(stdout_data),
                "error": f"命令执行超时（{timeout}秒）",
                "return_code": -2
            }
        
        stdout_thread.join()
        stderr_thread.join()
        
        return {
            "success": process.returncode == 0,
            "output": ''.join(stdout_data),
            "error": ''.join(stderr_data),
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
