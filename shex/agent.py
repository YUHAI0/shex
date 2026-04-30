"""
Shex Agent 核心模块
基于 Tool Calling 的命令行助手
"""

import json
import re
from typing import Callable, List, Optional, Tuple
from openai import OpenAI
from .config import AgentConfig
from .tools import TOOLS, execute_command, get_system_info
from .i18n import t


# 选项块标签：模型按提示词约定输出 [CHOICES]...[/CHOICES]
_CHOICES_OPEN = "[CHOICES]"
_CHOICES_CLOSE = "[/CHOICES]"

# 用于从完整内容中提取 [CHOICES] 块（懒匹配，DOTALL 跨行）
_CHOICES_BLOCK_RE = re.compile(r"\[CHOICES\](.*?)\[/CHOICES\]", re.DOTALL)
# 用于解析每行编号选项：1. xxx / 1) xxx / 1、xxx
_CHOICES_ITEM_RE = re.compile(r"^\s*(\d+)\s*[\.\)、]\s*(.+?)\s*$")


class _StreamTagFilter:
    """
    流式标签过滤器。

    把流式 chunk 投喂进来，原样返回应该展示给用户的字符，
    但会精确吃掉 [CHOICES] 与 [/CHOICES] 标签本身（以及紧随其后的一个换行符），
    让用户看到的内容更干净。能正确处理标签被切片到不同 chunk 之间的情况。
    """

    _TAGS = (_CHOICES_CLOSE, _CHOICES_OPEN)  # 较长的优先尝试匹配

    def __init__(self):
        self._buf = ""

    def feed(self, text: str) -> str:
        if not text:
            return ""
        self._buf += text
        out_parts: List[str] = []
        i = 0
        n = len(self._buf)
        while i < n:
            ch = self._buf[i]
            if ch == "[":
                # 1) 是否是某个标签的完整匹配
                matched_tag: Optional[str] = None
                for tag in self._TAGS:
                    if self._buf.startswith(tag, i):
                        matched_tag = tag
                        break
                if matched_tag is not None:
                    j = i + len(matched_tag)
                    # 吃掉标签后紧邻的一个换行（让上下文更紧凑）
                    if j < n and self._buf[j] == "\n":
                        j += 1
                    i = j
                    continue
                # 2) 是否为某个标签的前缀（数据未到齐），停下来等下一块
                rest = self._buf[i:]
                if any(tag.startswith(rest) for tag in self._TAGS):
                    break
            out_parts.append(ch)
            i += 1
        # 已消费的内容从 buffer 移除，未决定的尾部保留
        self._buf = self._buf[i:]
        return "".join(out_parts)

    def flush(self) -> str:
        """流结束时把 buffer 中残留的内容一次性吐出。"""
        rest = self._buf
        self._buf = ""
        return rest


def _parse_choices(text: str) -> Optional[Tuple[str, List[str]]]:
    """
    从完整内容里提取最后一个 [CHOICES] 块。
    返回 (question, options)；若不存在合法选项块则返回 None。
    """
    if not text or _CHOICES_OPEN not in text:
        return None
    matches = list(_CHOICES_BLOCK_RE.finditer(text))
    if not matches:
        return None
    block = matches[-1].group(1)

    question_lines: List[str] = []
    options: List[str] = []
    for line in block.splitlines():
        item_match = _CHOICES_ITEM_RE.match(line)
        if item_match:
            options.append(item_match.group(2).strip())
            continue
        stripped = line.strip()
        if stripped and not options:
            question_lines.append(stripped)

    if len(options) < 2:
        return None

    question = " ".join(question_lines).strip()
    # 去掉常见的"问题："前缀，让交互更整洁
    for prefix in ("问题：", "问题:", "Question:", "Question："):
        if question.startswith(prefix):
            question = question[len(prefix):].strip()
            break
    return question, options


class ShexAgent:
    """
    Shex Agent - 基于 Tool Calling 的命令行助手
    """
    
    def __init__(self, config: AgentConfig = None):
        self.config = config or AgentConfig()
        self.client = OpenAI(
            api_key=self.config.llm.api_key,
            base_url=self.config.llm.base_url
        )
        self.system_info = get_system_info()
        self.messages = []
        self.confirm_fn = None  # 危险命令确认函数
        self.stream_fn = None   # 流式输出函数
        self.continue_fn = None # 询问是否继续重试函数
        self.choice_fn = None   # 让用户做编号选择的函数
        self.start_spinner = None # 启动加载动画函数
        self.stop_spinner = None  # 停止加载动画函数
        self.next_spinner_message = None # 下一次加载动画的消息
        self._init_system_message()
    
    def _init_system_message(self):
        """初始化系统消息"""
        self.messages = [{
            "role": "system",
            "content": t("agent_prompt", system_info=self.system_info, max_retries=self.config.max_retries)
        }]
    
    def set_confirm_fn(self, fn: Callable[[str], bool]):
        """设置危险命令确认函数"""
        self.confirm_fn = fn
    
    def set_stream_fn(self, fn: Callable[[str], None]):
        """设置流式输出函数"""
        self.stream_fn = fn
    
    def set_continue_fn(self, fn: Callable[[int], bool]):
        """设置询问是否继续重试函数"""
        self.continue_fn = fn

    def set_choice_fn(self, fn: Callable[[str, List[str]], Optional[str]]):
        """
        设置“让用户做编号选择”回调。

        回调签名：(question: str, options: List[str]) -> Optional[str]
            - 返回拼接好的字符串将作为下一轮的 user 消息发回给大模型
            - 返回 None 表示用户取消，本次对话直接结束
        """
        self.choice_fn = fn

    def set_spinner(self, start_fn: Callable[[str], None], stop_fn: Callable[[], None]):
        """设置加载动画函数"""
        self.start_spinner = start_fn
        self.stop_spinner = stop_fn
    
    def _call_llm(self, stream: bool = False):
        """调用大模型"""
        return self.client.chat.completions.create(
            model=self.config.llm.model,
            messages=self.messages,
            tools=TOOLS,
            tool_choice="auto",
            temperature=self.config.llm.temperature,
            max_tokens=self.config.llm.max_tokens,
            stream=stream
        )
    
    def _handle_choices(self, content: str) -> Optional[str]:
        """
        若模型在 content 中给出了 [CHOICES] 块，则唤起 choice_fn 让用户选择。

        返回值：
            - None：没有选项块、未注册回调，或用户取消选择 —— 调用方应正常结束
            - str：用户选择后要回传给模型的下一轮 user 消息文本
        """
        if not self.choice_fn:
            return None
        parsed = _parse_choices(content)
        if parsed is None:
            return None
        question, options = parsed
        try:
            return self.choice_fn(question, options)
        except KeyboardInterrupt:
            return None

    def _handle_tool_call(self, tool_call) -> dict:
        """处理工具调用"""
        if tool_call.function.name == "execute_command":
            args = json.loads(tool_call.function.arguments)
            command = args.get("command", "")
            is_dangerous = args.get("is_dangerous", False)
            
            # 打印命令（前面加换行，与思考内容分开）
            if self.stream_fn:
                self.stream_fn(f"\n\033[96m$ {command}\033[0m\n")
            
            # 执行命令
            result = execute_command(
                command=command,
                is_dangerous=is_dangerous,
                timeout=self.config.command_timeout,
                confirm_fn=self.confirm_fn if is_dangerous else None
            )
            
            return {
                "tool_call_id": tool_call.id,
                "output": json.dumps({
                    "success": result["success"],
                    "output": result["output"][:2000],
                    "error": result["error"][:500] if result["error"] else "",
                    "return_code": result["return_code"]
                }, ensure_ascii=False)
            }
        
        return {
            "tool_call_id": tool_call.id,
            "output": json.dumps({"error": "未知工具"})
        }
    
    def run(self, user_input: str) -> str:
        """
        运行 Agent
        
        Args:
            user_input: 用户输入
            
        Returns:
            最终响应
        """
        # 添加用户消息
        self.messages.append({
            "role": "user",
            "content": user_input
        })
        
        retry_count = 0
        total_retries = 0  # 总重试次数
        
        while True:
            # 调用大模型
            if self.stream_fn:
                # 流式输出
                stream_filter = _StreamTagFilter()
                try:
                    if self.start_spinner:
                        msg = self.next_spinner_message or (t("thinking") if t else "Thinking...")
                        self.start_spinner(msg)
                        self.next_spinner_message = None # 重置消息
                        
                    response = self._call_llm(stream=True)
                    
                    full_content = ""
                    tool_calls = []
                    
                    first_chunk = True
                    
                    for chunk in response:
                        if first_chunk:
                            if self.stop_spinner:
                                self.stop_spinner()
                            first_chunk = False

                        delta = chunk.choices[0].delta
                        
                        if delta.content:
                            full_content += delta.content
                            visible = stream_filter.feed(delta.content)
                            if visible:
                                self.stream_fn(visible)
                        
                        if delta.tool_calls:
                            for tc in delta.tool_calls:
                                if tc.index is not None:
                                    while len(tool_calls) <= tc.index:
                                        tool_calls.append({
                                            "id": "",
                                            "function": {"name": "", "arguments": ""}
                                        })
                                    if tc.id:
                                        tool_calls[tc.index]["id"] = tc.id
                                    if tc.function:
                                        if tc.function.name:
                                            tool_calls[tc.index]["function"]["name"] = tc.function.name
                                        if tc.function.arguments:
                                            tool_calls[tc.index]["function"]["arguments"] += tc.function.arguments
                    
                    # 确保 spinner 停止（如果 response 为空）
                    if first_chunk and self.stop_spinner:
                        self.stop_spinner()

                except Exception:
                    if self.stop_spinner:
                        self.stop_spinner()
                    raise

                # 把过滤器残余字符吐出（流式输出收尾）
                tail = stream_filter.flush()
                if tail:
                    self.stream_fn(tail)

                # 构建 assistant 消息
                assistant_message = {"role": "assistant", "content": full_content or None}
                if tool_calls:
                    assistant_message["tool_calls"] = [
                        {
                            "id": tc["id"],
                            "type": "function",
                            "function": {
                                "name": tc["function"]["name"],
                                "arguments": tc["function"]["arguments"]
                            }
                        }
                        for tc in tool_calls if tc["id"]
                    ]
                
                self.messages.append(assistant_message)
                
                if not tool_calls or not any(tc["id"] for tc in tool_calls):
                    if full_content:
                        self.stream_fn("\n")
                    # 检查模型是否给出了 [CHOICES] 块，等待用户做选择
                    follow_up = self._handle_choices(full_content)
                    if follow_up is None:
                        return full_content
                    # 用户已选择，作为新的 user 消息继续与模型对话
                    self.messages.append({"role": "user", "content": follow_up})
                    retry_count = 0
                    self.next_spinner_message = t("thinking")
                    continue
                
                # 处理工具调用
                class ToolCall:
                    def __init__(self, data):
                        self.id = data["id"]
                        self.function = type('obj', (object,), {
                            'name': data["function"]["name"],
                            'arguments': data["function"]["arguments"]
                        })()
                
                for tc_data in tool_calls:
                    if tc_data["id"]:
                        tc = ToolCall(tc_data)
                        result = self._handle_tool_call(tc)
                        self.messages.append({
                            "role": "tool",
                            "tool_call_id": result["tool_call_id"],
                            "content": result["output"]
                        })

                        # 设置下一次思考的消息状态
                        self.next_spinner_message = t("analyzing")
                        
                        output = json.loads(result["output"])
                        if not output.get("success", True):
                            retry_count += 1
                            total_retries += 1
                            if retry_count >= self.config.max_retries:
                                if self.continue_fn and self.continue_fn(total_retries):
                                    retry_count = 0  # 重置计数器，继续尝试
                                else:
                                    return t("exec_failed", count=total_retries)
            else:
                # 非流式
                try:
                    if self.start_spinner:
                        msg = self.next_spinner_message or (t("thinking") if t else "Thinking...")
                        self.start_spinner(msg)
                        self.next_spinner_message = None # 重置消息
                    
                    response = self._call_llm(stream=False)
                finally:
                    if self.stop_spinner:
                        self.stop_spinner()
                        
                message = response.choices[0].message
                
                self.messages.append({
                    "role": "assistant",
                    "content": message.content,
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function", 
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments
                            }
                        }
                        for tc in (message.tool_calls or [])
                    ] if message.tool_calls else None
                })
                
                if not message.tool_calls:
                    follow_up = self._handle_choices(message.content or "")
                    if follow_up is None:
                        return message.content or ""
                    self.messages.append({"role": "user", "content": follow_up})
                    retry_count = 0
                    self.next_spinner_message = t("thinking")
                    continue
                
                for tool_call in message.tool_calls:
                    result = self._handle_tool_call(tool_call)
                    self.messages.append({
                        "role": "tool",
                        "tool_call_id": result["tool_call_id"],
                        "content": result["output"]
                    })

                    # 设置下一次思考的消息状态
                    self.next_spinner_message = t("analyzing")
                    
                    output = json.loads(result["output"])
                    if not output.get("success", True):
                        retry_count += 1
                        total_retries += 1
                        if retry_count >= self.config.max_retries:
                            if self.continue_fn and self.continue_fn(total_retries):
                                retry_count = 0  # 重置计数器，继续尝试
                            else:
                                return t("exec_failed", count=total_retries)
    
    def clear_history(self):
        """清空对话历史"""
        self._init_system_message()

    def save_context(self, path):
        """保存上下文到文件"""
        try:
            # 只保存非 system 消息
            context_messages = [m for m in self.messages if m.get("role") != "system"]
            
            # 根据配置的轮数限制上下文
            # 一轮对话通常包括 User 提问及后续的 Assistant 回复/Tool calls
            # 简单起见，我们假设每轮平均产生 2-4 条消息（视 Tool calls 而定）
            # 这里我们尝试从后往前查找 User 消息，保留最近 N 个 User 消息之后的所有内容
            
            max_turns = self.config.max_context_turns
            user_msg_indices = [i for i, m in enumerate(context_messages) if m.get("role") == "user"]
            
            if len(user_msg_indices) > max_turns:
                # 找到倒数第 N 个 User 消息的索引
                # 注意：如果 max_turns 为 0，-0 会被当作 0，导致切片错误
                if max_turns > 0:
                    start_index = user_msg_indices[-max_turns]
                    context_messages = context_messages[start_index:]
                else:
                    context_messages = []
            elif max_turns <= 0:
                context_messages = []
            
            # 兜底策略：防止单轮对话过长导致 Context 无限膨胀
            # 强制限制最大消息数量（例如 50 条），但必须保证切片后的第一条是 User 消息
            if len(context_messages) > 50:
                # 先截取最后 50 条
                candidate_messages = context_messages[-50:]
                
                # 找到第一条 User 消息
                start_index = -1
                for i, msg in enumerate(candidate_messages):
                    if msg.get("role") == "user":
                        start_index = i
                        break
                
                if start_index != -1:
                    context_messages = candidate_messages[start_index:]
                else:
                    # 如果最后 50 条里没有 user 消息，说明上下文结构异常或单轮过长
                    # 为了安全（避免 orphaned tool calls），清空或仅保留最近几条（如果不含 tool）
                    # 这里选择清空，让模型重新开始
                    context_messages = []
                
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(context_messages, f, ensure_ascii=False, indent=2)
        except Exception as e:
            # 上下文保存失败不应影响主流程
            pass

    def load_context(self, path):
        """从文件加载上下文"""
        try:
            if not path.exists():
                return
                
            with open(path, 'r', encoding='utf-8') as f:
                context_messages = json.load(f)
            
            if isinstance(context_messages, list):
                # 过滤掉可能的 system 消息（以防万一）
                valid_messages = [m for m in context_messages if m.get("role") != "system"]
                
                # 修复：确保上下文以 User 消息开始
                # 这可以防止加载因切片错误而产生的孤立 tool/assistant 消息
                while valid_messages and valid_messages[0].get("role") != "user":
                    valid_messages.pop(0)
                
                self.messages.extend(valid_messages)
        except Exception:
            pass
