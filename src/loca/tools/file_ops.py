import os
from pathlib import Path

# 書き込みを禁止する危険なディレクトリ
DANGEROUS_PATHS = [
    "/etc", "/usr", "/bin", "/sbin", "/var", "/boot", "/dev", "/proc", "/sys",
    "/System", "/Library",  # macOS系
    os.path.expanduser("~/.ssh"),
    os.path.expanduser("~/.gnupg"),
    os.path.expanduser("~/.config"),
    os.path.expanduser("~/.aws"),
]

def is_safe_path(filepath: str) -> tuple[bool, str]:
    """書き込み先のパスが安全かどうかを検証する"""
    abs_path = os.path.abspath(filepath)
    for danger in DANGEROUS_PATHS:
        if abs_path.startswith(danger):
            return False, f"安全装置: '{abs_path}' はシステムディレクトリ ({danger}) 内のため書き込みを拒否しました。"
    return True, ""

def read_file(filepath: str) -> str:
    """指定されたファイルを読み込む"""
    if not os.path.exists(filepath):
        return f"Error: ファイル '{filepath}' が見つかりません。"
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        return f"--- {filepath} の中身 ---\n{content}\n--- EOF ---"
    except Exception as e:
        return f"Error: ファイルの読み込みに失敗しました: {e}"

def edit_file(filepath: str, old_text: str, new_text: str) -> str:
    """ファイル内の特定の文字列を、新しい文字列に置換する"""
    if not os.path.exists(filepath):
        return f"Error: ファイル '{filepath}' が見つかりません。"
    safe, msg = is_safe_path(filepath)
    if not safe:
        return msg
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # LLMがインデントなどを間違えて対象テキストが見つからない場合のエラーハンドリング
        if old_text not in content:
            return "Error: 置換対象の `old_text` がファイル内に完全一致で見つかりませんでした。インデントや改行が完全に一致しているか確認するか、一度 `read_file` で中身を確認してください。"
        
        # 置換を実行（最初の1箇所だけ）
        new_content = content.replace(old_text, new_text, 1)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
            
        return f"Success: '{filepath}' の編集が完了しました。"
    except Exception as e:
        return f"Error: ファイルの編集に失敗しました: {e}"

def write_file(filepath: str, content: str) -> str:
    """ファイル全体を新しい内容で上書き（または新規作成）する"""
    safe, msg = is_safe_path(filepath)
    if not safe:
        return msg
    try:
        # ディレクトリが存在しない場合は作成する
        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
            
        return f"Success: ファイル '{filepath}' を上書き保存しました。"
    except Exception as e:
        return f"Error: ファイルの保存に失敗しました: {e}"

def read_directory(dir_path: str = ".", max_depth: int = 2) -> str:
    """
    指定されたディレクトリのツリー構造を文字列として返す。
    AIがプロジェクトの全体像を把握するために使用する。
    """
    # 読み込まなくていいフォルダを追加（build や egg-info など）
    ignore_dirs = {'.git', '__pycache__', 'venv', '.venv', 'node_modules', '.pytest_cache', 'build'}
    
    try:
        base_path = Path(dir_path)
        if not base_path.exists() or not base_path.is_dir():
            return f"Error: ディレクトリ '{dir_path}' が見つかりません。"

        tree_str = f"Directory structure of '{base_path.absolute()}' (max_depth={max_depth}):\n"
        
        for root, dirs, files in os.walk(base_path):
            # 現在の深さを計算
            rel_path = Path(root).relative_to(base_path)
            level = len(rel_path.parts)
            
            # ★ 1. 深さ制限: 指定した階層に達したら、それ以上下には潜らない
            if level >= max_depth:
                dirs[:] = [] 
                
            # 無視するディレクトリや隠しフォルダ(.vscode等)を除外
            dirs[:] = [d for d in dirs if d not in ignore_dirs and not d.startswith('.') and not d.endswith('.egg-info')]
            
            if root == str(base_path):
                indent = ""
            else:
                indent = "  " * level + "├── "
                tree_str += f"{indent}[DIR] {Path(root).name}/\n"
                
            sub_indent = "  " * (level + 1) + "├── " if root != str(base_path) else "├── "
            
            # ★ 2. ファイル数制限: 1つのフォルダ内にファイルが多すぎる場合は省略する
            valid_files = [f for f in files if not f.startswith('.')]
            for i, f in enumerate(valid_files):
                if i >= 30: # 30ファイルを超えたら省略
                    tree_str += f"{sub_indent}... (and {len(valid_files) - 30} more files)\n"
                    break
                tree_str += f"{sub_indent}{f}\n"

        return tree_str.strip()
        
    except Exception as e:
        return f"Error: ディレクトリの読み込みに失敗しました: {e}"
        