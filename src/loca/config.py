import os
from pathlib import Path

# Locaリポジトリのルートディレクトリ (src/loca/ → src/ → Loca/)
PROJECT_ROOT = str(Path(__file__).resolve().parent.parent.parent)

# デフォルトのLLM設定
DEFAULT_MODEL = "qwen2.5-coder:32b"
DEFAULT_PROVIDER = "ollama"

def get_rules_path() -> Path:
    """Loca.md のパスを一元管理して返す。cwdのLoca.mdを優先し、なければリポジトリルートにフォールバック。"""
    cwd_rules = Path(os.getcwd()) / "Loca.md"
    if cwd_rules.exists():
        return cwd_rules
    return Path(PROJECT_ROOT) / "Loca.md"