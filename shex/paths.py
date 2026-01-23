"""
Shex 路径管理模块
管理程序数据目录、配置文件和日志文件的路径
"""

import os
import platform
from pathlib import Path


def get_app_dir() -> Path:
    """
    获取程序数据目录
    
    Windows: %LOCALAPPDATA%\\shex
    Linux/Mac: ~/.config/shex
    
    Returns:
        程序数据目录路径
    """
    system = platform.system()
    
    if system == "Windows":
        # Windows: C:\Users\<user>\AppData\Local\shex
        base = os.environ.get("LOCALAPPDATA")
        if not base:
            base = os.path.expanduser("~\\AppData\\Local")
        app_dir = Path(base) / "shex"
    else:
        # Linux/Mac: ~/.config/shex
        config_home = os.environ.get("XDG_CONFIG_HOME")
        if config_home:
            app_dir = Path(config_home) / "shex"
        else:
            app_dir = Path.home() / ".config" / "shex"
    
    return app_dir


def get_env_path() -> Path:
    """获取 .env 配置文件路径（大模型API配置）"""
    return get_app_dir() / ".env"


def get_config_path() -> Path:
    """获取 config.json 配置文件路径（程序配置）"""
    return get_app_dir() / "config.json"


def get_log_dir() -> Path:
    """获取日志目录路径"""
    return get_app_dir() / "logs"


def get_history_path() -> Path:
    """获取历史记录文件路径"""
    return Path.home() / ".shex_history"


def get_context_path() -> Path:
    """获取上下文文件路径"""
    return get_app_dir() / "context.json"


def ensure_app_dir() -> Path:
    """
    确保程序数据目录存在
    
    Returns:
        程序数据目录路径
    """
    app_dir = get_app_dir()
    app_dir.mkdir(parents=True, exist_ok=True)
    return app_dir


def ensure_log_dir() -> Path:
    """
    确保日志目录存在
    
    Returns:
        日志目录路径
    """
    log_dir = get_log_dir()
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir


def init_env_file() -> Path:
    """
    获取 .env 文件路径（不自动创建模板，由配置向导处理）
    
    Returns:
        .env 文件路径
    """
    ensure_app_dir()
    return get_env_path()


def print_paths():
    """打印所有路径信息（调试用）"""
    print(f"程序数据目录: {get_app_dir()}")
    print(f"配置文件路径: {get_env_path()}")
    print(f"日志目录路径: {get_log_dir()}")


if __name__ == "__main__":
    print_paths()
