from dataclasses import dataclass
from loca.core.prompts import get_system_prompt
from loca.core.memory import MemoryManager
from loca.core.pro_agent import run_pro_mode
from loca.core.executor import backup_manager
from loca.tools.git_ops import auto_commit
from loca.ui.display import console


@dataclass
class RouteResult:
    """コマンドルーティングの結果を保持するデータクラス"""
    handled: bool = False        # コマンドとして処理されたか（Trueなら main loop で continue）
    should_exit: bool = False    # プログラムを終了するか
    is_ask_mode: bool = False    # /ask モードか


def route_command(
    user_input: str,
    messages: list,
    memory: MemoryManager,
    model_name: str,
    provider: str,
    auto_mode: bool,
    exchange_count: int,
) -> tuple[RouteResult, bool, int]:
    """
    ユーザー入力をコマンドとしてルーティングする。
    
    戻り値: (RouteResult, auto_mode, exchange_count)
    auto_mode と exchange_count は変更される可能性があるため戻り値に含める。
    """
    result = RouteResult()
    stripped = user_input.strip()
    lower = stripped.lower()
    
    # --- 終了 ---
    if lower in ['exit', 'quit']:
        console.print("[dim]Shutting down agent...[/dim]")
        result.should_exit = True
        result.handled = True
        return result, auto_mode, exchange_count
    
    # --- 空入力 ---
    if not stripped:
        result.handled = True
        return result, auto_mode, exchange_count
    
    # --- /auto ---
    if lower == "/auto":
        auto_mode = not auto_mode
        status = "ON (全自動・承認スキップ)" if auto_mode else "OFF (都度確認)"
        console.print(f"\n[bold yellow]🤖 Auto Mode: {status}[/bold yellow]\n")
        result.handled = True
        return result, auto_mode, exchange_count
    
    # --- /clear ---
    if lower == "/clear":
        messages.clear()
        messages.append(get_system_prompt())
        exchange_count = 0
        console.print("\n[bold cyan]🔄 会話をリセットしました。新しいタスクを入力してください。[/bold cyan]\n")
        result.handled = True
        return result, auto_mode, exchange_count
    
    # --- /undo ---
    if lower == "/undo":
        if backup_manager.has_backups():
            msg, success = backup_manager.undo()
            style = "[bold green]" if success else "[bold yellow]"
            console.print(f"\n{style}{msg}[/{style[1:]}\n")
            remaining = backup_manager.count
            if remaining > 0:
                console.print(f"[dim]残りの取り消し可能な変更: {remaining}件[/dim]\n")
        else:
            console.print("\n[bold yellow]⏪ 取り消せる変更がありません。[/bold yellow]\n")
        result.handled = True
        return result, auto_mode, exchange_count
    
    # --- /ask ---
    # /ask 後にプロンプトが戻らないバグ防止: 毎回通常モードに復元する
    messages[0] = get_system_prompt()
    
    if user_input.startswith("/ask"):
        result.is_ask_mode = True
        question = user_input[4:].strip()
        messages[0] = get_system_prompt(is_ask_mode=True)
        enforced_question = f"{question}\n\n(※必ずシステムプロンプト内の <project_guidelines> に指定された掟やトーンを厳格に守って回答してください)"
        messages.append({"role": "user", "content": enforced_question})
        return result, auto_mode, exchange_count
    
    # --- /remember ---
    if user_input.startswith("/remember "):
        rule = user_input[len("/remember "):].strip()
        if rule:
            memory.remember(rule)
            messages[0] = get_system_prompt()
        result.handled = True
        return result, auto_mode, exchange_count
    
    # --- /rules ---
    if stripped == "/rules":
        memory.show_rules()
        result.handled = True
        return result, auto_mode, exchange_count
    
    # --- /forget ---
    if user_input.startswith("/forget "):
        target = user_input[len("/forget "):].strip()
        if target:
            memory.forget(target)
            messages[0] = get_system_prompt()
        result.handled = True
        return result, auto_mode, exchange_count
    
    # --- /commit ---
    if user_input.startswith("/commit"):
        auto_commit(model_name=model_name, provider=provider)
        result.handled = True
        return result, auto_mode, exchange_count
    
    # --- /pro ---
    if user_input.startswith("/pro"):
        task = user_input[4:].strip()
        if not task:
            console.print("[dim]タスクの内容を入力してください。(例: /pro テトリスを作って)[/dim]")
        else:
            final_files = run_pro_mode(task, model_name=model_name, provider=provider, auto_mode=auto_mode)
            if final_files:
                messages.append({"role": "user", "content": f"(Proモード実行: {task})"})
                messages.append({"role": "assistant", "content": f"({len(final_files)}個のファイルを生成しました。)"})
        result.handled = True
        return result, auto_mode, exchange_count
    
    # --- 通常テキスト（コマンドでない） ---
    messages.append({"role": "user", "content": user_input})
    return result, auto_mode, exchange_count
