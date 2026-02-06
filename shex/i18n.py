"""
Shex 多语言支持模块
"""

# 语言包
LANGUAGES = {
    "zh": {
        "name": "简体中文",
        # 配置向导
        "config_title": "Shex 首次配置向导",
        "config_no_api_key": "未检测到 API Key 配置",
        "config_step1": "【步骤 1/2】选择大模型：",
        "config_step2": "【步骤 2/2】输入 API Key：",
        "config_input_number": "请输入序号: ",
        "config_selected": "已选择",
        "config_custom": "【自定义配置】",
        "config_api_url": "API Base URL: ",
        "config_model_name": "模型名称: ",
        "config_get_key": "获取地址",
        "config_input_key": "请输入 API Key: ",
        "config_success": "✅ 配置完成！",
        "config_failed": "❌ 配置失败",
        "config_cancelled": "配置取消",
        "config_context_option": "是否开启上下文记忆？(默认：是)",
        "invalid_input": "无效输入",
        # 执行相关
        "confirm_execute": "确认执行? (y/n): ",
        "context_cleared": "✅ 上下文已清空",
        "context_empty": "⚠️ 上下文为空",
        "continue_retry": "已重试 {count} 次仍未成功，是否继续尝试? (y/n): ",
        "cancelled": "已取消",
        "init_failed": "❌ 初始化失败",
        "exec_failed": "执行失败，已重试 {count} 次",
        "timeout": "处理超时",
        "command_timeout": "命令执行超时（{timeout}秒）",
        "user_cancelled": "用户取消执行危险命令",
        "thinking": "思考中...",
        "analyzing": "分析执行结果...",
        "executing": "执行中...",
        # Agent prompt
        "agent_prompt": r"""你是一个命令行助手，直接执行用户请求的操作。

系统信息：
{system_info}

行为准则：
1. 直接执行，不要询问用户确认或提问
2. 错误处理：如果命令执行失败（如"command not found"或不支持的参数），**禁止**重复相同的命令！必须分析错误信息，尝试不同的命令、参数或工具来达成目标（例如 Windows 上 ls 失败尝试 dir，grep 失败尝试 findstr）。
3. Windows PowerShell 特别注意：在双引号字符串内部使用路径时，**严禁**在路径末尾加反斜杠 `\`（例如 `"$path\"` 是错误的），因为这会转义闭合引号导致语法错误！应写成 `"$path"` 或 `"$path\\"`。
4. 只有在确实无法完成时才告知用户原因
5. 成功后简洁报告结果即可结束

危险命令处理：
- 设置 is_dangerous=true，系统会自动向用户确认
- 直接调用工具，不要在回复中询问

【严格要求】
1. 严禁使用任何 markdown 格式！禁止：代码块(```)、标题(#)、列表(- *)、加粗(**)、斜体(*)、链接等。只能输出纯文本。
2. 必须使用中文回复用户。
3. 【绝对禁止】在回复末尾提出任何问题或询问！禁止说"还需要什么帮助吗"、"需要我做什么吗"、"有什么问题吗"等任何形式的提问。执行完毕后直接结束，不要追问！"""
    },
    "en": {
        "name": "English",
        # Config wizard
        "config_title": "Shex Setup Wizard",
        "config_no_api_key": "API Key not configured",
        "config_step1": "[Step 1/2] Select LLM Provider:",
        "config_step2": "[Step 2/2] Enter API Key:",
        "config_input_number": "Enter number: ",
        "config_selected": "Selected",
        "config_custom": "[Custom Configuration]",
        "config_api_url": "API Base URL: ",
        "config_model_name": "Model name: ",
        "config_get_key": "Get key at",
        "config_input_key": "Enter API Key: ",
        "config_success": "✅ Configuration complete!",
        "config_failed": "❌ Configuration failed",
        "config_cancelled": "Configuration cancelled",
        "config_context_option": "Enable context memory? (Default: Yes)",
        "invalid_input": "Invalid input",
        # Execution
        "confirm_execute": "Confirm execution? (y/n): ",
        "context_cleared": "✅ Context cleared",
        "context_empty": "⚠️ Context is empty",
        "continue_retry": "Failed after {count} retries, continue trying? (y/n): ",
        "cancelled": "Cancelled",
        "init_failed": "❌ Initialization failed",
        "exec_failed": "Execution failed after {count} retries",
        "timeout": "Processing timeout",
        "command_timeout": "Command execution timeout ({timeout}s)",
        "user_cancelled": "User cancelled dangerous command execution",
        "thinking": "Thinking...",
        "analyzing": "Analyzing execution results...",
        "executing": "Executing...",
        # Agent prompt
        "agent_prompt": """You are a command-line assistant that directly executes user requests.

System info:
{system_info}

Guidelines:
1. Execute directly, don't ask for confirmation or questions
2. Error Handling: If a command fails (e.g., "command not found" or invalid arguments), do **NOT** repeat the exact same command! Analyze the error, and try a DIFFERENT command, argument, or tool (e.g., on Windows try 'dir' if 'ls' fails, or 'findstr' if 'grep' fails).
3. Only report failure when truly unable to complete
4. Report results briefly after success and end

Dangerous commands:
- Set is_dangerous=true, system will auto-confirm with user
- Call tools directly, don't ask in response

[STRICT RULES]
1. Never use any markdown formatting! Forbidden: code blocks(```), headers(#), lists(- *), bold(**), italic(*), links, etc. Output plain text only.
2. You MUST respond in English only.
3. [ABSOLUTELY FORBIDDEN] Never ask any questions at the end of your response! Never say "need anything else?", "want me to do anything?", "any questions?", etc. Just finish after completing the task, do not follow up with questions!"""
    }
}

# 当前语言
_current_lang = "zh"


def set_language(lang: str):
    """设置当前语言"""
    global _current_lang
    if lang in LANGUAGES:
        _current_lang = lang


def get_language() -> str:
    """获取当前语言"""
    return _current_lang


def t(key: str, **kwargs) -> str:
    """获取翻译文本"""
    text = LANGUAGES.get(_current_lang, LANGUAGES["zh"]).get(key, key)
    if kwargs:
        text = text.format(**kwargs)
    return text


def get_available_languages() -> dict:
    """获取可用语言列表"""
    return {code: lang["name"] for code, lang in LANGUAGES.items()}
