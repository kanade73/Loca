from loca.ui.display import console, print_command
from loca.tools.commander import execute_command
from loca.tools.file_ops import read_file, write_file, edit_file, read_directory
from loca.tools.web_search import search_web
from loca.tools.backup import BackupManager
import subprocess

# グローバルなバックアップマネージャー（/undo で使用）
backup_manager = BackupManager()


def confirm_action(auto_mode: bool) -> str:
    """write_file / edit_file 共通の確認フロー。ユーザーの入力文字列を返す。"""
    if auto_mode:
        console.print("[dim]🤖 Auto Mode: 自動で編集を許可しました。[/dim]")
        return "y"
    
    console.print("[dim]💡 ヒント: 'n 理由' でAIに指示を出せます。'q' でタスクを強制終了できます。[/dim]")
    return console.input("[bold]編集を許可しますか？ [y/N/q]: [/bold]").strip()


def lint_python_file(filepath: str) -> str:
    """Pythonファイルに対してruffを実行し、エラーがあればメッセージを返す。"""
    if not filepath.endswith('.py'):
        return ""
    errors = []
    # 1. ruff 静的チェック
    try:
        result = subprocess.run(
            ["ruff", "check", filepath, "--output-format=concise"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode != 0 and result.stdout.strip():
            lint_errors = result.stdout.strip()
            console.print(f"[bold yellow]⚠️ Lint警告が検出されました:[/bold yellow]")
            console.print(f"[dim]{lint_errors}[/dim]")
            errors.append(f"⚠️ Lint Errors (ruff):\n{lint_errors}")
    except FileNotFoundError:
        pass
    except Exception:
        pass
    
    # 2. Python 構文・import チェック
    try:
        result = subprocess.run(
            ["python", "-c", f"import py_compile; py_compile.compile('{filepath}', doraise=True)"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode != 0:
            err_msg = result.stderr.strip().split('\n')[-1] if result.stderr.strip() else "Syntax error"
            console.print(f"[bold red]❌ 構文エラーが検出されました:[/bold red]")
            console.print(f"[dim]{err_msg}[/dim]")
            errors.append(f"❌ Syntax Error:\n{err_msg}")
    except Exception:
        pass
    
    if errors:
        combined = "\n\n".join(errors)
        return f"\n\n{combined}\nこれらのエラーを修正してください。特にimportの漏れや存在しないAPIの使用に注意してください。"
    return ""


def handle_rejection(confirm: str) -> str:
    """拒否時のフィードバックメッセージを生成する共通関数"""
    reason = confirm[1:].strip() if confirm.lower().startswith('n') and len(confirm) > 1 else ""
    
    if reason:
        return f"ユーザーに拒否されました。理由: {reason} （※指示に従い、同じ変更は絶対に繰り返さないでください）"
    else:
        return "ユーザーに拒否されました。（※同じアクションを繰り返すのは禁止です。別のアプローチを提案するか、人間に質問してください）"


def execute_action(action: str, args: dict, auto_mode: bool) -> tuple[str, bool]:
    """
    AIが選択したアクションを実行する。
    戻り値: (result_output, should_kill)
    should_kill が True の場合、タスクを強制終了してユーザー入力に戻る。
    """
    result_output = ""
    should_kill = False
    
    if action == "run_command":
        cmd = args.get("command", "")
        if not cmd:
            result_output = "Error: command引数が指定されていません。"
        else:
            print_command(cmd)
            result_output = execute_command(cmd, auto_mode=auto_mode)
    
    elif action == "read_file":
        filepath = args.get("filepath", "")
        console.print(f"[bold blue]📄 Reading file:[/bold blue] {filepath}")
        result_output = read_file(filepath)
        console.print("[dim]内容をメモリに読み込みました。[/dim]")
    
    elif action == "write_file":
        filepath = args.get("filepath", "")
        content = args.get("content", "")
        console.print(f"[bold green]📝 Writing file:[/bold green] {filepath}")
        print_command(content)
        
        confirm = confirm_action(auto_mode)
        
        if confirm.lower() == 'y':
            backup_manager.save(filepath)
            result_output = write_file(filepath, content)
            lint_msg = lint_python_file(filepath)
            result_output += lint_msg
            console.print("[dim]ファイルに書き込みました。[/dim]")
        elif confirm.lower() == 'q':
            console.print("[bold red]🛑 タスクを強制終了(Kill)しました。[/bold red]")
            should_kill = True
        else:
            result_output = handle_rejection(confirm)
            console.print("[dim]書き込みをキャンセルし、AIに強い拒否のフィードバックを送りました。[/dim]")
    
    elif action == "edit_file":
        filepath = args.get("filepath", "")
        old_text = args.get("old_text", "")
        new_text = args.get("new_text", "")
        console.print(f"[bold yellow]✏️ Editing file:[/bold yellow] {filepath}")
        console.print(f"[dim]old_text: {old_text[:100]}{'...' if len(old_text) > 100 else ''}[/dim]")
        console.print(f"[dim]new_text: {new_text[:100]}{'...' if len(new_text) > 100 else ''}[/dim]")
        
        confirm = confirm_action(auto_mode)
        
        if confirm.lower() == 'y':
            backup_manager.save(filepath)
            result_output = edit_file(filepath, old_text, new_text)
            lint_msg = lint_python_file(filepath)
            result_output += lint_msg
            console.print("[dim]ファイルを編集しました。[/dim]")
        elif confirm.lower() == 'q':
            console.print("[bold red]🛑 タスクを強制終了(Kill)しました。[/bold red]")
            should_kill = True
        else:
            result_output = handle_rejection(confirm)
            console.print("[dim]編集をキャンセルし、AIに強い拒否のフィードバックを送りました。[/dim]")
    
    elif action == "read_directory":
        dir_path = args.get("dir_path", ".")
        console.print(f"[bold blue]📂 Reading directory:[/bold blue] {dir_path}")
        result_output = read_directory(dir_path)
        console.print("[dim]ディレクトリ構造を読み込みました。[/dim]")
    
    elif action == "web_search":
        query = args.get("query", "")
        console.print(f"[bold cyan]🔍 Web Searching:[/bold cyan] {query}")
        result_output = search_web(query)
        console.print("[dim]検索結果を取得しました。[/dim]")
    
    elif action == "none":
        pass
    
    else:
        result_output = f"Error: 未知のアクション '{action}'"
    
    return result_output, should_kill
