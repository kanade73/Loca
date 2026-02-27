# 🧠 Loca - Autonomous AI Coding Assistant

[![Python](https://img.shields.io/badge/Python-3.12%2B-blue)](https://python.org)
[![uv](https://img.shields.io/badge/Package_Manager-uv-purple)](https://github.com/astral-sh/uv)
[![Ollama](https://img.shields.io/badge/Local_AI-Ollama-black)](https://ollama.com)
[![LiteLLM](https://img.shields.io/badge/Multi_Provider-LiteLLM-green)](https://github.com/BerriAI/litellm)

**🌐 [日本語](docs/README_ja.md)**

**LOCAL AI · FREE · YOURS**

> I couldn't afford Claude Code. So I built my own.

<img width="867" height="502" alt="screenshot" src="https://github.com/user-attachments/assets/debf4f8a-107d-465a-af38-19e93208ffc1" />

Loca is a CLI-based autonomous AI coding agent that runs entirely on local LLMs. It thinks, writes code, executes commands, and learns your preferences over time — all without API keys or subscriptions. Just `uv sync` and `loca`.

---

## 🛠️ Installation

### 1. Set up Ollama

Install [Ollama](https://ollama.com) and download the default model.

```bash
# Install Ollama (macOS)
brew install ollama

# Download the default model (~4.7GB)
ollama pull qwen2.5-coder:7b
```

### 2. Set up Loca

```bash
git clone https://github.com/kanade73/Loca.git
cd Loca
uv sync
loca
```

That's it. You're ready to go.

### Changing the Model

The default model is configured in `src/loca/config.py`:

```python
# src/loca/config.py
DEFAULT_MODEL = "qwen2.5-coder:7b"   # ← Change this
DEFAULT_PROVIDER = "ollama"
```

To use a different model, just **pull it and update config.py**:

```bash
# Example: Use a more powerful model (20GB+ VRAM recommended)
ollama pull qwen2.5-coder:32b
# → Change DEFAULT_MODEL to "qwen2.5-coder:32b" in config.py
```

You can also specify a model temporarily via CLI:

```bash
loca -m qwen2.5-coder:32b
```

### Using Cloud APIs

```bash
export OPENAI_API_KEY="sk-..."
loca -p openai -m gpt-4o
```

---

## 💻 Commands

| Command | Description |
| --- | --- |
| Natural language | The AI autonomously thinks and takes actions (file ops, commands, etc.) |
| `/ask <question>` | Knowledge-only mode — no file changes. Automatically searches the web if needed |
| `/pro <task>` | Dual-AI mode: an Editor AI writes code, a Reviewer AI critiques it, iterating until approved |
| `/auto` | Toggles full-auto mode — skips all user confirmations |
| `/clear` | Resets conversation history and starts a fresh task |
| `/commit` | Analyzes git diff, auto-generates a commit message, and commits |
| `/remember <rule>` | Teaches Loca a rule or preference |
| `/rules` | Lists all remembered rules |
| `/forget <number>` | Removes a specific rule |
| `/undo` | Reverts the last file change made by Loca |

---

## ✨ Core Features

### 🛠️ 7 Built-in Tools

Loca autonomously selects from these tools to complete your tasks. All tools — including plugins — are managed through a unified `ToolRegistry`, so adding a new tool requires changes to just one file.

| Tool | Description |
| --- | --- |
| `run_command` | Execute shell commands (with user confirmation) |
| `read_file` | Read file contents |
| `write_file` | Create or overwrite files |
| `edit_file` | Partial file edits (find & replace) |
| `read_directory` | Explore project structure |
| `web_search` | Search via DuckDuckGo |
| `none` | Signal task completion |

Tool selection uses the LLM's native Function Calling API, which means no JSON text parsing and no parse errors. Models that don't support Function Calling fall back to JSON mode automatically.

### 🔌 Plugin System

Drop Python files into a `loca_tools/` directory in your project root to give Loca custom tools. Each file is auto-loaded at startup and registered as an available action — no configuration needed.

```python
# loca_tools/my_tool.py
TOOL_NAME        = "my_tool"
TOOL_DESCRIPTION = "What this tool does (shown to the AI)"
ARGS_FORMAT      = '{"key": "value"}'  # Optional — defaults to {}

def run(args: dict) -> str:
    # Your logic here
    return "result string"
```

A sample plugin (`loca_tools/get_time.py`) is included as a starting point.

### 🤝 Transparent Memory System

Unlike cloud-based "memory" features hidden behind APIs, Loca's memory is a plain markdown file (`Loca.md`) sitting in your project root. You can read it, edit it, or delete it anytime. Full control, zero magic.

```bash
> /remember Always use class-based views in Django
🧠 Got it. Added to Loca.md.

> /rules
> /forget 3
```

### ⚖️ Pro Mode: Dual-AI Collaboration

In `/pro` mode, two AI agents debate internally — an **Editor** generates code, and a **Reviewer** critiques it. The cycle repeats until the Reviewer approves. Even with the same underlying model, role separation produces noticeably better output.

### 🔒 Safety by Design

- **Confirmation before execution**: `run_command` and `write_file` require user approval (toggle with `/auto`)
- **Path protection**: Writes to system directories (`/etc`, `~/.ssh`, etc.) are automatically blocked
- **Session limits**: 30 exchanges per session to prevent context window overflow
- **Auto-lint on write**: After every `write_file` or `edit_file`, Python files are automatically checked with `ruff` and `py_compile`. Any errors are fed back to the AI for self-correction.

---

## 🌱 Train Your Loca

Add rules and preferences to `Loca.md` and Loca will follow them in every task:

```markdown
# Loca.md example
- Always use uv for package management
- Keep UI minimal and modern
- Write commit messages in English
```

---

## 📁 Project Structure

```
Loca/
├── src/loca/
│   ├── config.py      # Default model/provider, path management
│   ├── main.py        # Entry point (delegates to AgentSession)
│   ├── core/
│   │   ├── agent_session.py # Session state & main loop encapsulated in a class
│   │   ├── tool_registry.py # Tool / ToolRegistry (unified tool management)
│   │   ├── llm_client.py   # LLM communication via LiteLLM (Function Calling support)
│   │   ├── prompts.py      # System prompts (FC mode & JSON fallback mode)
│   │   ├── memory.py       # Loca.md read/write (memory system)
│   │   ├── pro_agent.py    # /pro mode Editor/Reviewer logic
│   │   ├── router.py       # Command routing (/ask, /pro, /undo, etc.)
│   │   └── executor.py     # Tool handlers & ToolRegistry factory
│   ├── tools/
│   │   ├── commander.py    # Safe shell command execution
│   │   ├── file_ops.py     # File I/O with path validation
│   │   ├── git_ops.py      # Git commit & diff analysis
│   │   ├── web_search.py   # DuckDuckGo search
│   │   ├── backup.py       # File backup & undo system
│   │   └── plugin_loader.py # Dynamic plugin loader (loca_tools/)
│   └── ui/
│       ├── display.py      # Rich UI components
│       └── header.py       # Startup header
├── loca_tools/        # Your custom plugins (optional)
│   └── get_time.py    # Sample plugin: returns current datetime
├── pyproject.toml     # Dependencies & CLI entrypoint
└── Loca.md            # Loca's memory (your rules, your data)
```

---

## 🔧 Tech Stack

| Technology | Purpose |
| --- | --- |
| [LiteLLM](https://github.com/BerriAI/litellm) | Unified LLM API (Ollama / OpenAI / Anthropic / Gemini) |
| [Ollama](https://ollama.com) | Local LLM runtime (default) |
| [Rich](https://github.com/Textualize/rich) | Terminal UI rendering |
| [prompt-toolkit](https://github.com/prompt-toolkit/python-prompt-toolkit) | Input history, multi-line editing |
| [ddgs](https://github.com/deedy5/duckduckgo_search) | DuckDuckGo web search |
| [uv](https://github.com/astral-sh/uv) | Fast Python package management |

---

## License

MIT
