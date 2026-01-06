"""
Shex 配置模块
- 大模型配置：从 .env 文件加载
- 程序配置：从 config.json 文件加载
"""

import os
import json
from dataclasses import dataclass, field

from dotenv import load_dotenv
from .paths import get_env_path, get_config_path, ensure_app_dir


# 加载 .env 文件
_env_path = get_env_path()
if _env_path.exists():
    load_dotenv(_env_path)


# 默认程序配置（不包含 language，首次运行时让用户选择）
DEFAULT_CONFIG = {
    "command_timeout": 60,
    "max_retries": 3
}


def load_config() -> dict:
    """从 config.json 加载程序配置"""
    config_path = get_config_path()
    
    if config_path.exists():
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    
    return {}


def save_config(config: dict):
    """保存程序配置到 config.json"""
    ensure_app_dir()
    config_path = get_config_path()
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


def needs_language_setup() -> bool:
    """检查是否需要设置语言"""
    config = load_config()
    return "language" not in config


def get_config_value(key: str, default=None):
    """获取配置值"""
    config = load_config()
    if key in config:
        return config[key]
    return DEFAULT_CONFIG.get(key, default)


# 加载程序配置
_app_config = load_config()

# 初始化语言（如果已配置）
if "language" in _app_config:
    from .i18n import set_language
    set_language(_app_config["language"])


@dataclass
class LLMConfig:
    """大模型配置（从 .env 加载）"""
    api_key: str = ""
    base_url: str = "https://api.deepseek.com"
    model: str = "deepseek-chat"
    temperature: float = 0.7
    max_tokens: int = 2048
    
    @classmethod
    def from_env(cls) -> "LLMConfig":
        """从环境变量加载配置"""
        return cls(
            api_key=os.getenv("LLM_API_KEY", os.getenv("DEEPSEEK_API_KEY", "")),
            base_url=os.getenv("LLM_BASE_URL", "https://api.deepseek.com"),
            model=os.getenv("LLM_MODEL", "deepseek-chat"),
            temperature=float(os.getenv("LLM_TEMPERATURE", "0.7")),
            max_tokens=int(os.getenv("LLM_MAX_TOKENS", "2048")),
        )


@dataclass
class AgentConfig:
    """Agent 配置"""
    llm: LLMConfig = field(default_factory=LLMConfig)
    command_timeout: int = field(default_factory=lambda: get_config_value("command_timeout", 60))
    max_retries: int = field(default_factory=lambda: get_config_value("max_retries", 3))
