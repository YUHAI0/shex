# Shex

[English](README.md)

[![PyPI version](https://img.shields.io/pypi/v/shex.svg)](https://pypi.org/project/shex/)
[![Python](https://img.shields.io/pypi/pyversions/shex.svg)](https://pypi.org/project/shex/)
[![Downloads](https://static.pepy.tech/badge/shex)](https://pepy.tech/project/shex)
[![License](https://img.shields.io/pypi/l/shex.svg)](https://github.com/YUHAI0/shex/blob/master/LICENSE)
[![GitHub issues](https://img.shields.io/github/issues/YUHAI0/shex)](https://github.com/YUHAI0/shex/issues)
[![GitHub last commit](https://img.shields.io/github/last-commit/YUHAI0/shex)](https://github.com/YUHAI0/shex/commits)
[![GitHub stars](https://img.shields.io/github/stars/YUHAI0/shex?style=social)](https://github.com/YUHAI0/shex/stargazers)

**基于大模型的自然语言命令行助手**

用自然语言执行系统命令，无需记忆复杂的命令语法。

## 特性

- 🗣️ **自然语言** - 用日常语言描述你想做的事
- 🤖 **多模型支持** - DeepSeek、OpenAI、Claude、Gemini、Mistral、Groq、通义千问等
- 🔄 **自动重试** - 失败时自动尝试其他方法
- ⚠️ **安全优先** - 执行危险命令前需确认
- 🌍 **多语言** - 支持中英文界面
- 💻 **跨平台** - Windows、macOS、Linux

## 安装

你可以使用一条命令安装或更新 Shex。这将直接从 GitHub 下载并安装最新版本。

**Windows (PowerShell):**
```powershell
iwr -useb https://raw.githubusercontent.com/YUHAI0/shex/master/scripts/install.ps1 | iex
```

**Linux/macOS:**
```bash
curl -fsSL https://raw.githubusercontent.com/YUHAI0/shex/master/scripts/install.sh | bash
```

## 快速开始

```bash
# 首次运行会引导你完成配置
shex 列出当前目录所有文件

# 更多示例
shex 查看磁盘使用情况
shex 找出所有 python 文件
shex 我的 IP 地址是多少
shex 压缩 logs 文件夹
```

## 配置

### 首次运行

首次运行时，Shex 会引导你：
1. 选择语言（中文/英文）
2. 选择大模型提供商
3. 输入 API Key

### 重新配置

```bash
# 更换大模型
shex --config

# 更换语言
shex --lang
```

### 支持的大模型

| 提供商 | 模型 |
|--------|------|
| OpenAI | GPT-4o |
| Anthropic | Claude 3.5 |
| Google | Gemini Pro |
| Mistral | Mistral Large |
| Groq | Llama 3 |
| Cohere | Command R+ |
| DeepSeek | DeepSeek Chat |
| 通义千问 | Qwen Plus |
| 月之暗面 | Kimi |
| 智谱 AI | GLM-4 |

也支持配置任何兼容 OpenAI 接口的 API。

## 使用方法

```bash
# 基本用法
shex <用自然语言描述你想做的事>

# 选项
shex --version          # 显示版本
shex --config           # 重新配置大模型
shex --lang             # 更换语言
shex --max-retries N    # 设置最大重试次数（默认：3）
```

## 工作原理

1. 你用自然语言描述想做的事
2. Shex 将请求发送给配置的大模型
3. 大模型生成相应的系统命令
4. Shex 执行命令并显示输出
5. 如果命令失败，Shex 会自动尝试其他方法

## 安全性

- 危险命令（删除、格式化等）需要用户确认
- 大模型会分析每个命令的潜在风险
- 执行前你始终拥有最终决定权

## 配置文件

配置存储在：
- **Windows**: `%LOCALAPPDATA%\shex\`
- **macOS/Linux**: `~/.config/shex/`

文件说明：
- `.env` - API Key 和大模型设置
- `config.json` - 语言和其他偏好
- `logs/` - 执行日志

## 许可证

MIT

## 贡献

欢迎提交 Issue 和 Pull Request！

---

<p align="center">
  如果您觉得这个项目对您有帮助，请给一个 ⭐️ 以示支持！
</p>
