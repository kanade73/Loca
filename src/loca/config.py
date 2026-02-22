import os
from pathlib import Path

# Locaリポジトリのルートディレクトリ (src/loca/ → src/ → Loca/)
PROJECT_ROOT = str(Path(__file__).resolve().parent.parent.parent)

def get_rules_path() -> Path:
    """Loca.md のパスを一元管理して返す"""
    return Path(PROJECT_ROOT) / "Loca.md"