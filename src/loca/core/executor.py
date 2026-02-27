import subprocess

from loca.ui.display import console, print_command
from loca.tools.commander import execute_command
from loca.tools.file_ops import read_file, write_file, edit_file, read_directory
from loca.tools.web_search import search_web
from loca.tools.backup import BackupManager
from loca.tools.plugin_loader import load_plugins
from loca.core.tool_registry import Tool, ToolRegistry

# グローバルなバックアップマネージャー（/undo で使用）
backup_manager = BackupManager()


# ==========================================
# 共通ユーティリティ
# ==========================================

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
    try:
        result = subprocess.run(
            ["ruff", "check", filepath, "--output-format=concise"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode != 0 and result.stdout.strip():
            lint_errors = result.stdout.strip()
            console.print("[bold yellow]⚠️ Lint警告が検出されました:[/bold yellow]")
            console.print(f"[dim]{lint_errors}[/dim]")
            errors.append(f"⚠️ Lint Errors (ruff):\n{lint_errors}")
    except (FileNotFoundError, Exception):
        pass

    try:
        result = subprocess.run(
            ["python", "-c", f"import py_compile; py_compile.compile('{filepath}', doraise=True)"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode != 0:
            err_msg = result.stderr.strip().split('\n')[-1] if result.stderr.strip() else "Syntax error"
            console.print("[bold red]❌ 構文エラーが検出されました:[/bold red]")
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
    return "ユーザーに拒否されました。（※同じアクションを繰り返すのは禁止です。別のアプローチを提案するか、人間に質問してください）"


# ==========================================
# ツールハンドラー（各ツールの実装）
# ==========================================

def _handle_run_command(args: dict, auto_mode: bool) -> tuple[str, bool]:
    cmd = args.get("command", "")
    if not cmd:
        return "Error: command引数が指定されていません。", False
    print_command(cmd)
    return execute_command(cmd, auto_mode=auto_mode), False


def _handle_read_file(args: dict, auto_mode: bool) -> tuple[str, bool]:
    filepath = args.get("filepath", "")
    console.print(f"[bold blue]📄 Reading file:[/bold blue] {filepath}")
    result = read_file(filepath)
    console.print("[dim]内容をメモリに読み込みました。[/dim]")
    return result, False


def _handle_write_file(args: dict, auto_mode: bool) -> tuple[str, bool]:
    filepath = args.get("filepath", "")
    content = args.get("content", "")
    console.print(f"[bold green]📝 Writing file:[/bold green] {filepath}")
    print_command(content)

    confirm = confirm_action(auto_mode)

    if confirm.lower() == 'y':
        backup_manager.save(filepath)
        result = write_file(filepath, content)
        result += lint_python_file(filepath)
        console.print("[dim]ファイルに書き込みました。[/dim]")
        return result, False
    elif confirm.lower() == 'q':
        console.print("[bold red]🛑 タスクを強制終了(Kill)しました。[/bold red]")
        return "", True
    else:
        result = handle_rejection(confirm)
        console.print("[dim]書き込みをキャンセルし、AIに強い拒否のフィードバックを送りました。[/dim]")
        return result, False


def _handle_edit_file(args: dict, auto_mode: bool) -> tuple[str, bool]:
    filepath = args.get("filepath", "")
    old_text = args.get("old_text", "")
    new_text = args.get("new_text", "")
    console.print(f"[bold yellow]✏️ Editing file:[/bold yellow] {filepath}")
    console.print(f"[dim]old_text: {old_text[:100]}{'...' if len(old_text) > 100 else ''}[/dim]")
    console.print(f"[dim]new_text: {new_text[:100]}{'...' if len(new_text) > 100 else ''}[/dim]")

    confirm = confirm_action(auto_mode)

    if confirm.lower() == 'y':
        backup_manager.save(filepath)
        result = edit_file(filepath, old_text, new_text)
        result += lint_python_file(filepath)
        console.print("[dim]ファイルを編集しました。[/dim]")
        return result, False
    elif confirm.lower() == 'q':
        console.print("[bold red]🛑 タスクを強制終了(Kill)しました。[/bold red]")
        return "", True
    else:
        result = handle_rejection(confirm)
        console.print("[dim]編集をキャンセルし、AIに強い拒否のフィードバックを送りました。[/dim]")
        return result, False


def _handle_read_directory(args: dict, auto_mode: bool) -> tuple[str, bool]:
    dir_path = args.get("dir_path", ".")
    console.print(f"[bold blue]📂 Reading directory:[/bold blue] {dir_path}")
    result = read_directory(dir_path)
    console.print("[dim]ディレクトリ構造を読み込みました。[/dim]")
    return result, False


def _handle_web_search(args: dict, auto_mode: bool) -> tuple[str, bool]:
    query = args.get("query", "")
    console.print(f"[bold cyan]🔍 Web Searching:[/bold cyan] {query}")
    result = search_web(query)
    console.print("[dim]検索結果を取得しました。[/dim]")
    return result, False


def _handle_none(args: dict, auto_mode: bool) -> tuple[str, bool]:
    return "", False


# ==========================================
# ToolRegistry ファクトリー
# ==========================================

def create_default_registry() -> ToolRegistry:
    """組み込みツール＋プラグインを登録した ToolRegistry を作成して返す。"""
    registry = ToolRegistry()

    registry.register(Tool(
        name="run_command",
        description="Execute a shell command. Run ONE command at a time. Do NOT chain with && or ;.",
        args_schema={"command": {"type": "string", "description": "The shell command to run"}},
        required_args=["command"],
        handler=_handle_run_command,
    ))
    registry.register(Tool(
        name="read_file",
        description="Read the contents of an existing file.",
        args_schema={"filepath": {"type": "string", "description": "Path to the file"}},
        required_args=["filepath"],
        handler=_handle_read_file,
    ))
    registry.register(Tool(
        name="write_file",
        description="Write or overwrite the ENTIRE content of a file. Do not use for partial edits.",
        args_schema={
            "filepath": {"type": "string", "description": "Path to the file to write"},
            "content": {"type": "string", "description": "Complete new file content"},
        },
        required_args=["filepath", "content"],
        handler=_handle_write_file,
    ))
    registry.register(Tool(
        name="edit_file",
        description="Replace a specific part of an existing file. Use for small, targeted edits.",
        args_schema={
            "filepath": {"type": "string", "description": "Path to the file to edit"},
            "old_text": {"type": "string", "description": "Exact text to find and replace"},
            "new_text": {"type": "string", "description": "Replacement text"},
        },
        required_args=["filepath", "old_text", "new_text"],
        handler=_handle_edit_file,
    ))
    registry.register(Tool(
        name="read_directory",
        description="Get the tree structure of a directory. Use ONLY when explicitly asked to explore folders.",
        args_schema={"dir_path": {"type": "string", "description": "Path to directory (use '.' for current)"}},
        required_args=["dir_path"],
        handler=_handle_read_directory,
    ))
    registry.register(Tool(
        name="web_search",
        description="Search the web for up-to-date information, documentation, or error solutions.",
        args_schema={"query": {"type": "string", "description": "The search query string"}},
        required_args=["query"],
        handler=_handle_web_search,
    ))
    registry.register(Tool(
        name="none",
        description="Use when the task is fully complete and no further action is needed.",
        args_schema={},
        required_args=[],
        handler=_handle_none,
    ))

    # プラグインを登録
    for plugin in load_plugins():
        def _make_handler(run_fn):
            def handler(args: dict, auto_mode: bool) -> tuple[str, bool]:
                clean_args = {k: v for k, v in args.items() if k != "thought"}
                result = run_fn(clean_args)
                return str(result), False
            return handler

        registry.register(Tool(
            name=plugin["name"],
            description=plugin["description"],
            args_schema={},
            required_args=[],
            handler=_make_handler(plugin["run"]),
        ))

    return registry


# ==========================================
# 後方互換ラッパー（pro_agent.py 等が参照するため残す）
# ==========================================

_registry_cache: ToolRegistry | None = None


def _get_registry() -> ToolRegistry:
    global _registry_cache
    if _registry_cache is None:
        _registry_cache = create_default_registry()
    return _registry_cache


def execute_action(action: str, args: dict, auto_mode: bool) -> tuple[str, bool]:
    """後方互換性のためのラッパー。内部では ToolRegistry を使用する。"""
    return _get_registry().execute(action, args, auto_mode)
