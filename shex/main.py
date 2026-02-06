"""
Shex 主入口
自然语言驱动的命令行助手

使用方式:
    shex "你想做的事情"
    shex list files in current directory
"""

import sys
import os
import argparse
import logging
from datetime import datetime

from .paths import ensure_log_dir, get_env_path, ensure_app_dir, get_history_path, get_context_path
from .config import AgentConfig, LLMConfig, needs_language_setup, save_config, load_config, get_config_value


# 设置日志
def setup_logger():
    """设置日志"""
    log_dir = ensure_log_dir()
    log_file = log_dir / f"shex_{datetime.now().strftime('%Y%m%d')}.log"
    
    logger = logging.getLogger("shex")
    logger.setLevel(logging.DEBUG)
    
    if not logger.handlers:
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        ))
        logger.addHandler(file_handler)
    
    return logger


logger = setup_logger()


def save_history(query: str):
    """保存命令历史"""
    try:
        history_path = get_history_path()
        # 避免重复记录最后一条
        if history_path.exists():
            try:
                # 读取最后一行
                import collections
                with open(history_path, 'r', encoding='utf-8') as f:
                    try:
                        last_line = collections.deque(f, 1)[0].strip()
                        if last_line == query:
                            return
                    except IndexError:
                        pass # 文件为空
            except Exception:
                pass

        with open(history_path, "a", encoding="utf-8") as f:
            f.write(f"{query}\n")
    except Exception as e:
        # 历史记录失败不应影响主程序
        logger.warning(f"Failed to save history: {e}")


def colorize(text: str, color: str) -> str:
    """为文本添加颜色"""
    colors = {
        "red": "\033[91m",
        "green": "\033[92m",
        "yellow": "\033[93m",
        "blue": "\033[94m",
        "magenta": "\033[95m",
        "cyan": "\033[96m",
        "reset": "\033[0m"
    }
    return f"{colors.get(color, '')}{text}{colors['reset']}"


def setup_language() -> str:
    """语言选择向导"""
    from .i18n import set_language, get_available_languages
    languages = get_available_languages()
    lang_list = list(languages.items())
    
    print()
    print(colorize("=" * 40, "cyan"))
    print(colorize("  Select Language / 选择语言", "cyan"))
    print(colorize("=" * 40, "cyan"))
    print()
    
    for i, (code, name) in enumerate(lang_list, 1):
        print(f"  {colorize(str(i), 'green')}. {name}")
    print()
    
    while True:
        choice = input(colorize("Enter number / 请输入序号: ", "yellow")).strip()
        if choice.isdigit() and 1 <= int(choice) <= len(lang_list):
            selected_code = lang_list[int(choice) - 1][0]
            
            # 保存语言配置
            config = load_config()
            config["language"] = selected_code
            save_config(config)
            
            # 设置当前语言
            set_language(selected_code)
            
            print(colorize(f"\n✅ {languages[selected_code]}\n", "green"))
            return selected_code
        
        print(colorize("Invalid / 无效", "red"))


# 模型配置信息
MODEL_OPTIONS = [
    # 国外模型
    {"name": "openai", "display": "OpenAI (GPT-4o)", "base_url": "https://api.openai.com/v1", "model": "gpt-4o", "key_name": "LLM_API_KEY", "get_key_url": "https://platform.openai.com/api-keys"},
    {"name": "claude", "display": "Anthropic (Claude 3.5)", "base_url": "https://api.anthropic.com/v1", "model": "claude-3-5-sonnet-20241022", "key_name": "LLM_API_KEY", "get_key_url": "https://console.anthropic.com/settings/keys"},
    {"name": "gemini", "display": "Google (Gemini Pro)", "base_url": "https://generativelanguage.googleapis.com/v1beta/openai", "model": "gemini-2.0-flash", "key_name": "LLM_API_KEY", "get_key_url": "https://aistudio.google.com/apikey"},
    {"name": "mistral", "display": "Mistral AI", "base_url": "https://api.mistral.ai/v1", "model": "mistral-large-latest", "key_name": "LLM_API_KEY", "get_key_url": "https://console.mistral.ai/api-keys"},
    {"name": "groq", "display": "Groq (Llama 3)", "base_url": "https://api.groq.com/openai/v1", "model": "llama-3.3-70b-versatile", "key_name": "LLM_API_KEY", "get_key_url": "https://console.groq.com/keys"},
    {"name": "cohere", "display": "Cohere (Command R+)", "base_url": "https://api.cohere.ai/v1", "model": "command-r-plus", "key_name": "LLM_API_KEY", "get_key_url": "https://dashboard.cohere.com/api-keys"},
    # 国内模型
    {"name": "deepseek", "display": "DeepSeek", "base_url": "https://api.deepseek.com", "model": "deepseek-chat", "key_name": "DEEPSEEK_API_KEY", "get_key_url": "https://platform.deepseek.com/api_keys"},
    {"name": "qwen", "display": "Qwen (通义千问)", "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1", "model": "qwen-plus", "key_name": "LLM_API_KEY", "get_key_url": "https://dashscope.console.aliyun.com/apiKey"},
    {"name": "moonshot", "display": "Moonshot (Kimi)", "base_url": "https://api.moonshot.cn/v1", "model": "moonshot-v1-8k", "key_name": "LLM_API_KEY", "get_key_url": "https://platform.moonshot.cn/console/api-keys"},
    {"name": "zhipu", "display": "Zhipu AI (GLM-4)", "base_url": "https://open.bigmodel.cn/api/paas/v4", "model": "glm-4", "key_name": "LLM_API_KEY", "get_key_url": "https://open.bigmodel.cn/usercenter/apikeys"},
    # 自定义
    {"name": "custom", "display": "Custom (OpenAI Compatible)", "base_url": "", "model": "", "key_name": "LLM_API_KEY", "get_key_url": ""},
]


def setup_config_wizard() -> bool:
    """配置向导"""
    from .i18n import t
    print()
    print(colorize("=" * 50, "cyan"))
    print(colorize(f"  {t('config_title')}", "cyan"))
    print(colorize("=" * 50, "cyan"))
    print()
    
    # 选择模型
    print(colorize(t('config_step1'), "yellow"))
    for i, opt in enumerate(MODEL_OPTIONS, 1):
        print(f"  {colorize(str(i), 'green')}. {opt['display']}")
    print()
    
    while True:
        choice = input(colorize(t('config_input_number'), "yellow")).strip()
        if choice.isdigit() and 1 <= int(choice) <= len(MODEL_OPTIONS):
            selected = MODEL_OPTIONS[int(choice) - 1]
            break
        print(colorize(t('invalid_input'), "red"))
    
    print(f"\n{t('config_selected')}: {colorize(selected['display'], 'green')}")
    
    # 配置上下文选项
    print(colorize(f"\n{t('config_context_option') if t('config_context_option') != 'config_context_option' else 'Enable Context Memory? (Default: Yes)'}", "yellow"))
    context_choice = input(colorize("Enable context? [Y/n]: ", "yellow")).strip().lower()
    enable_context = context_choice not in ['n', 'no', '否']
    
    if selected["name"] == "custom":
        print(colorize(f"\n{t('config_custom')}", "yellow"))
        selected["base_url"] = input(t('config_api_url')).strip()
        selected["model"] = input(t('config_model_name')).strip()
        if not selected["base_url"] or not selected["model"]:
            print(colorize(t('config_cancelled'), "red"))
            return False
    
    # 输入 API Key
    print(colorize(f"\n{t('config_step2')}", "yellow"))
    if selected["get_key_url"]:
        print(f"  {t('config_get_key')}: {colorize(selected['get_key_url'], 'blue')}")
    
    api_key = input(colorize(f"\n{t('config_input_key')}", "yellow")).strip()
    if not api_key:
        print(colorize(t('config_cancelled'), "red"))
        return False
    
    # 保存配置
    ensure_app_dir()
    env_path = get_env_path()
    
    # 保存 config.json
    save_config({"enable_context": enable_context})

    lines = [
        "# Shex Config",
        f"# Model: {selected['display']}",
        "",
    ]
    
    if selected["name"] == "deepseek":
        lines.append(f"DEEPSEEK_API_KEY={api_key}")
    else:
        lines.append(f"LLM_API_KEY={api_key}")
        lines.append(f"LLM_BASE_URL={selected['base_url']}")
        lines.append(f"LLM_MODEL={selected['model']}")
    
    env_path.write_text("\n".join(lines), encoding="utf-8")
    
    print(colorize(f"\n{t('config_success')}", "green"))
    
    from dotenv import load_dotenv
    load_dotenv(env_path, override=True)
    
    return True


def confirm_dangerous(command: str) -> bool:
    """确认危险命令"""
    from .i18n import t
    while True:
        response = input(colorize(t('confirm_execute'), "yellow")).strip().lower()
        if response in ['y', 'yes', '是']:
            return True
        elif response in ['n', 'no', '否']:
            return False


def confirm_continue(retry_count: int) -> bool:
    """询问是否继续重试"""
    from .i18n import t
    while True:
        response = input(colorize(f"\n{t('continue_retry', count=retry_count)}", "yellow")).strip().lower()
        if response in ['y', 'yes', '是']:
            return True
        elif response in ['n', 'no', '否']:
            return False


def main():
    """主函数"""
    # 首次运行时选择语言
    if needs_language_setup():
        setup_language()
    
    # 延迟导入（需要在语言设置后）
    from .agent import ShexAgent
    from .i18n import t
    from .spinner import Spinner
    
    parser = argparse.ArgumentParser(
        description="Shex - Natural Language Command Line Assistant",
        epilog="Example: shex list files in current directory"
    )
    parser.add_argument("query", nargs="*", help="Natural language description of what you want to do")
    parser.add_argument("--config", action="store_true", help="Reconfigure")
    parser.add_argument("--lang", action="store_true", help="Change language")
    parser.add_argument("--max-retries", type=int, default=30, help="Max retries")
    parser.add_argument("--no-context", action="store_true", help="Disable context loading/saving")
    parser.add_argument("--clear-context", action="store_true", help="Clear context history")
    parser.add_argument("--version", action="store_true", help="Show version")
    
    args = parser.parse_args()
    
    if args.version:
        from . import __version__
        print(f"shex {__version__}")
        sys.exit(0)
    
    if args.lang:
        setup_language()
        sys.exit(0)
    
    if args.config:
        setup_config_wizard()
        sys.exit(0)

    # 处理上下文清理
    if args.clear_context:
        context_path = get_context_path()
        if context_path.exists():
            try:
                os.remove(context_path)
                print(colorize(f"{t('context_cleared') if 't' in locals() else 'Context cleared'}", "green"))
            except Exception as e:
                print(colorize(f"Failed to clear context: {e}", "red"))
        else:
            print(colorize(f"{t('context_empty') if 't' in locals() else 'Context is empty'}", "yellow"))
        sys.exit(0)
    
    # 合并所有参数为一个查询字符串
    query = " ".join(args.query).strip()
    
    if not query:
        parser.print_help()
        sys.exit(0)
    
    logger.info(f"User input: {query}")
    
    # 保存历史
    save_history(query)
    
    # 加载配置
    llm_config = LLMConfig.from_env()
    
    if not llm_config.api_key:
        print(colorize(f"⚠️  {t('config_no_api_key')}", "yellow"))
        if not setup_config_wizard():
            sys.exit(1)
        llm_config = LLMConfig.from_env()
        if not llm_config.api_key:
            print(colorize(t('config_failed'), "red"))
            sys.exit(1)
    
    # 创建 Agent
    config = AgentConfig(llm=llm_config, max_retries=args.max_retries)
    
    try:
        agent = ShexAgent(config=config)
        agent.set_confirm_fn(confirm_dangerous)
        agent.set_stream_fn(lambda x: print(x, end='', flush=True))
        agent.set_continue_fn(confirm_continue)

        spinner = Spinner()
        agent.set_spinner(spinner.start, spinner.stop)

        # 加载上下文
        enable_context = get_config_value("enable_context", True)
        if enable_context and not args.no_context:
            context_path = get_context_path()
            agent.load_context(context_path)

    except Exception as e:
        logger.error(f"Init failed: {e}")
        print(colorize(f"{t('init_failed')}: {e}", "red"))
        sys.exit(1)
    
    # 运行
    try:
        result = agent.run(query)
        logger.info(f"Execution completed")

        # 保存上下文
        if enable_context and not args.no_context:
            context_path = get_context_path()
            agent.save_context(context_path)

    except KeyboardInterrupt:
        print(colorize(f"\n{t('cancelled')}", "yellow"))
        sys.exit(0)
    except Exception as e:
        logger.error(f"Execution failed: {e}")
        print(colorize(f"\n❌ {e}", "red"))
        sys.exit(1)


if __name__ == "__main__":
    main()
