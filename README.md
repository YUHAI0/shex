# Shex

[![PyPI version](https://img.shields.io/pypi/v/shex.svg)](https://pypi.org/project/shex/)
[![Python](https://img.shields.io/pypi/pyversions/shex.svg)](https://pypi.org/project/shex/)
[![Downloads](https://static.pepy.tech/badge/shex)](https://pepy.tech/project/shex)
[![License](https://img.shields.io/pypi/l/shex.svg)](https://github.com/meyuh/shex/blob/main/LICENSE)

**Natural language command-line assistant powered by LLM**

Execute system commands using natural language. No need to remember complex command syntax.

## Features

- 🗣️ **Natural Language** - Describe what you want in plain language
- 🤖 **Multi-LLM Support** - DeepSeek, OpenAI, Claude, Gemini, Mistral, Groq, Qwen, and more
- 🔄 **Auto Retry** - Automatically tries alternative approaches on failure
- ⚠️ **Safety First** - Confirms before executing dangerous commands
- 🌍 **Multi-language** - English and Chinese interface
- 💻 **Cross-platform** - Windows, macOS, and Linux

## Installation

```bash
pip install shex
```

## Quick Start

```bash
# First run will guide you through configuration
shex list all files in current directory

# More examples
shex show disk usage
shex find all python files
shex what is my IP address
shex compress the logs folder
```

## Configuration

### First Run

On first run, Shex will guide you to:
1. Select your language (English/Chinese)
2. Choose an LLM provider
3. Enter your API key

### Reconfigure

```bash
# Change LLM provider
shex --config

# Change language
shex --lang
```

### Supported LLM Providers

| Provider | Model |
|----------|-------|
| OpenAI | GPT-4o |
| Anthropic | Claude 3.5 |
| Google | Gemini Pro |
| Mistral | Mistral Large |
| Groq | Llama 3 |
| Cohere | Command R+ |
| DeepSeek | DeepSeek Chat |
| Qwen | Qwen Plus |
| Moonshot | Kimi |
| Zhipu AI | GLM-4 |

You can also configure any OpenAI-compatible API.

## Usage

```bash
# Basic usage
shex <your request in natural language>

# Options
shex --version          # Show version
shex --config           # Reconfigure LLM
shex --lang             # Change language
shex --max-retries N    # Set max retry attempts (default: 3)
```

## How It Works

1. You describe what you want to do in natural language
2. Shex sends your request to the configured LLM
3. The LLM generates the appropriate system command
4. Shex executes the command and shows the output
5. If the command fails, Shex automatically tries alternative approaches

## Safety

- Dangerous commands (delete, format, etc.) require user confirmation
- The LLM analyzes each command for potential risks
- You always have the final say before execution

## Configuration Files

Configuration is stored in:
- **Windows**: `%LOCALAPPDATA%\shex\`
- **macOS/Linux**: `~/.config/shex/`

Files:
- `.env` - API keys and LLM settings
- `config.json` - Language and other preferences
- `logs/` - Execution logs

## License

MIT

## Contributing

Issues and pull requests are welcome!
