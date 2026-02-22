import json
import os

# src/tools/ipc_manager.py の上部
import os
import json
import loca.config as config

STATE_FILE = os.path.join(config.PROJECT_ROOT, "shared_state.json")

def init_state(task_description: str, max_iter: int = 3):
    """通信用の初期状態（まっさらな交換日記）を作成する"""
    initial_state = {
        "turn": "editor",       # 現在のターン ("editor" | "reviewer" | "completed")
        "task": task_description, # ユーザーからの初期指示
        "code_content": "",     # エディターが書いたコード（または結果）
        "feedback": "",         # レビュワーからのダメ出し
        "iteration": 0,         # 現在のやり取り回数
        "max_iterations": max_iter # 最大往復回数（無限ループでAPIが死ぬのを防ぐ）
    }
    write_state(initial_state)
    return initial_state

def read_state() -> dict | None:
    """共有状態を読み込む。ファイルが存在しない、またはアクセス中の場合はNoneを返す"""
    if not os.path.exists(STATE_FILE):
        return None
    try:
        with open(STATE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError:
        # 書き込み途中などでパースできない場合は、一瞬待つためにNoneを返す
        return None
    except Exception as e:
        print(f"[IPC Error] 読み込みエラー: {e}")
        return None

def write_state(state_dict: dict):
    """
    【重要】アトミック書き込みを使って状態を安全に保存する。
    直接ファイルを上書きせず、一時ファイル(.tmp)に書いてからOSの機能で一瞬でリネーム（すり替え）する。
    """
    temp_file = f"{STATE_FILE}.tmp"
    try:
        # 1. まずは一時ファイルに安全に書き込む
        with open(temp_file, 'w', encoding='utf-8') as f:
            json.dump(state_dict, f, ensure_ascii=False, indent=4)
        
        # 2. OSレベルのアトミック操作でファイルをすり替える（Mac/Linuxで有効）
        os.replace(temp_file, STATE_FILE)
    except Exception as e:
        print(f"[IPC Error] 書き込みエラー: {e}")