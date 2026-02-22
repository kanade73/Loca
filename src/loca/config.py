import os
import sys

# Loca本体のソースコードが置かれているディレクトリ
SRC_DIR = os.path.dirname(os.path.abspath(__file__))

def setup_environment():
    """実行環境の初期化（OSS・グローバルCLI対応版）"""
    
    # Pythonが 'core' や 'tools' などの内部モジュールをどこからでも見つけられるようにパスを通す
    if SRC_DIR not in sys.path:
        sys.path.insert(0, SRC_DIR)