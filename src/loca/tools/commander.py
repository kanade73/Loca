import subprocess
import os
from pathlib import Path
from loca.ui.display import console

def execute_command(command: str, auto_mode: bool = False) -> str:
    """
    LLMが提案したシェルコマンドを安全に実行し、結果のテキストを返す。
    """
    # ユーザーに分かりやすく提案されたコマンドを表示
    console.print(f"\n[bold yellow]\\[AI Proposal]: {command}[/bold yellow]")
    
    # 1. 安全装置: ユーザーに確認を求める (Autoモード対応)
    if auto_mode:
        console.print("[dim]🤖 [Auto Mode] コマンドを自動実行します...[/dim]")
    else:
        while True:
            choice = console.input("[bold]Execute? [y/N/e (edit)]: [/bold]").strip().lower()
            
            if choice == 'y':
                break
            elif choice == 'e':
                # ユーザーがコマンドを手動で修正できるようにする
                command = console.input("[bold]Edit command: [/bold]").strip()
                if not command:
                    return "キャンセルされました。"
                break
            elif choice == 'n' or choice == '':
                return "ユーザーによって実行がキャンセルされました。"
            else:
                console.print("[dim]y, n, e のいずれかを入力してください。[/dim]")

    # 2. ファイル作成コマンドの特別処理
    # 例: echo "内容" > ファイル名 など
    if ">" in command:
        parts = command.split(">", 1)
        left = parts[0].strip()
        right = parts[1].strip()
        # rightがパス指定でなければ generated_files/ に保存
        if not ("/" in right or right.startswith("~")):
            gen_dir = Path(__file__).parent.parent.parent / "generated_files"
            gen_dir.mkdir(exist_ok=True)
            right = str(gen_dir / right)
            command = f"{left} > {right}"

    # 3. 特殊なコマンドの処理 (`cd` の罠を回避)
    if command.startswith("cd "):
        # AIが `&&` や `;` でコマンドを繋げて横着するのを防ぐ安全装置
        if "&&" in command or ";" in command:
            return "Error: `cd`コマンドは `&&` や `;` で他のコマンドと繋がず、単独で実行してください。結果を確認してから次のコマンドを実行してください。"

        target_dir = command[3:].strip()
        try:
            # '~' (ホームディレクトリ) などを展開する
            target_dir = os.path.expanduser(target_dir)
            os.chdir(target_dir)
            return f"Success: カレントディレクトリを {os.getcwd()} に変更しました。"
        except Exception as e:
            return f"Error: ディレクトリの変更に失敗しました: {e}"

    # 4. 通常のコマンド実行
    try:
        # shell=True で実行。check=Falseにしてエラー時もPythonを止めないようにする
        result = subprocess.run(
            command,
            shell=True,
            check=False,
            capture_output=True, # 標準出力とエラー出力を捕まえる
            text=True            # 結果を文字列として受け取る
        )
        
        # 標準出力と標準エラーを結合
        output = result.stdout
        if result.stderr:
            output += f"\n[Error/Warning Output]:\n{result.stderr}"
            
        # 実行成功したが出力が無い場合（例: mkdir など）
        if not output.strip():
            output = f"Success: コマンド '{command}' は正常に実行されましたが出力はありません。"
            
        return output.strip()
        
    except Exception as e:
        # コマンドが存在しないなどの予期せぬエラー
        return f"Execution Error: コマンドの実行中に予期せぬエラーが発生しました: {e}"

# --- テスト用コード ---
if __name__ == "__main__":
    # テスト1: 普通のコマンド
    print(execute_command("echo 'Hello M5 Mac!'"))
    
    # テスト2: Autoモードのテスト
    print(execute_command("echo 'Auto mode test'", auto_mode=True))