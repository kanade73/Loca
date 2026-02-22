import time
import argparse
from rich.panel import Panel


# --- コア機能 ---
from loca.core.llm_client import chat_with_llm, stream_chat_with_llm, extract_json_from_text, estimate_tokens
from loca.core.prompts import get_system_prompt
from loca.core.memory import MemoryManager
from loca.core.pro_agent import run_pro_mode

# --- ツール ---
from loca.tools.web_search import search_web
from loca.tools.commander import execute_command
from loca.tools.file_ops import read_file, write_file, edit_file, read_directory
from loca.tools.git_ops import auto_commit

# --- UI ---
from loca.ui.header import print_header
from loca.ui.display import console, print_thought, print_command, print_error, get_user_input
from rich.live import Live
from rich.markdown import Markdown

# ==========================================
# メッセージ管理（コンテキストウィンドウ溢れ防止）
# ==========================================
MAX_EXCHANGES = 30       # 1セッション中の最大やりとり回数
MAX_MESSAGES = 60        # messagesリストの上限（これを超えたら古いものを捨てる）

def trim_messages(messages: list) -> list:
    """コンテキストウィンドウのオーバーフローを防ぐだけの安全装置。"""
    if len(messages) <= MAX_MESSAGES:
        return messages
    
    # system_prompt (messages[0]) + 直近のやりとりだけ残す
    trimmed = [messages[0]] + messages[-(MAX_MESSAGES - 1):]
    console.print(f"[dim]📎 コンテキスト整理: 古いメッセージを切り捨てました ({len(messages)} → {len(trimmed)})[/dim]")
    return trimmed

# ==========================================
# メインループ
# ==========================================
def main(model_name: str, provider: str):
    # ヘッダー表示
    print_header(model_name=f"{model_name} ({provider.upper()})")
    
    # 記憶管理クラスの初期化
    memory = MemoryManager()
    
    sys_prompt = get_system_prompt()
    messages = [sys_prompt]
    
    if "<project_guidelines>" in sys_prompt["content"]:
        console.print("[bold cyan]🧠 Locaの記憶(Loca.md)をロードしました！[/bold cyan]\n")
        
    needs_user_input = True 
    auto_mode = False
    is_ask_mode = False
    exchange_count = 0  # LLM呼び出し回数カウンター

    while True:
        # --- メッセージ管理 ---
        messages = trim_messages(messages)
        
        # --- ユーザー入力フェーズ ---
        if needs_user_input:
            try:
                user_input = get_user_input()
            except (KeyboardInterrupt, EOFError):
                console.print("\n[dim]Shutting down agent...[/dim]")
                break
                
            if user_input.lower() in ['exit', 'quit']:
                console.print("[dim]Shutting down agent...[/dim]")
                break
                
            if not user_input:
                continue

            # コマンドのルーティング
            if user_input.lower().strip() == "/auto":
                auto_mode = not auto_mode
                status = "ON (全自動・承認スキップ)" if auto_mode else "OFF (都度確認)"
                console.print(f"\n[bold yellow]🤖 Auto Mode: {status}[/bold yellow]\n")
                needs_user_input = True
                continue

            if user_input.lower().strip() == "/clear":
                sys_prompt = get_system_prompt()
                messages = [sys_prompt]
                exchange_count = 0
                console.print("\n[bold cyan]🔄 会話をリセットしました。新しいタスクを入力してください。[/bold cyan]\n")
                needs_user_input = True
                continue

            is_ask_mode = False
            # /ask 後にプロンプトが戻らないバグ防止: 毎回通常モードに復元する
            messages[0] = get_system_prompt()
            
            if user_input.startswith("/ask"):
                is_ask_mode = True
                question = user_input[4:].strip()
                messages[0] = get_system_prompt(is_ask_mode=True)
                enforced_question = f"{question}\n\n(※必ずシステムプロンプト内の <project_guidelines> に指定された掟やトーンを厳格に守って回答してください)"
                messages.append({"role": "user", "content": enforced_question})

            elif user_input.startswith("/remember "):
                rule = user_input[len("/remember "):].strip()
                if rule:
                    memory.remember(rule)
                    sys_prompt = get_system_prompt()
                    messages[0] = sys_prompt
                needs_user_input = True
                continue
                
            elif user_input.strip() == "/rules":
                memory.show_rules()
                needs_user_input = True
                continue
                
            elif user_input.startswith("/forget "):
                target = user_input[len("/forget "):].strip()
                if target:
                    memory.forget(target)
                    sys_prompt = get_system_prompt()
                    messages[0] = sys_prompt
                needs_user_input = True
                continue

            elif user_input.startswith("/commit"):
                auto_commit(model_name=model_name, provider=provider)
                needs_user_input = True
                continue
                
            elif user_input.startswith("/pro"):
                task = user_input[4:].strip()
                if not task:
                    console.print("[dim]タスクの内容を入力してください。(例: /pro テトリスを作って)[/dim]")
                    needs_user_input = True
                    continue
                
                final_files = run_pro_mode(task, model_name=model_name, provider=provider, auto_mode=auto_mode)
                if final_files:
                    messages.append({"role": "user", "content": f"(Proモード実行: {task})"})
                    messages.append({"role": "assistant", "content": f"({len(final_files)}個のファイルを生成しました。)"})
                needs_user_input = True
                continue
                
        # --- AI思考フェーズ ---
        # 交換回数チェック
        exchange_count += 1
        if exchange_count > MAX_EXCHANGES:
            console.print(f"\n[bold yellow]⚠️ セッションの上限 ({MAX_EXCHANGES}回) に達しました。コンテキストをリセットします。[/bold yellow]")
            console.print("[dim]新しいタスクを入力してください。[/dim]\n")
            sys_prompt = get_system_prompt()
            messages = [sys_prompt]
            exchange_count = 0
            needs_user_input = True
            continue
        
        # トークン数の概算表示
        token_count = estimate_tokens(messages)
        console.print(f"[dim]📊 Tokens: ~{token_count} | Exchange: {exchange_count}/{MAX_EXCHANGES}[/dim]")
        
        start_time = time.time()
        
        # /ask モード: ストリーミング表示
        if is_ask_mode:
            raw_text = ""
            parsed_json = None
            
            # まず通常のレスポンスを取得（web_searchアクションの判定のため）
            with console.status("[bold cyan]AI is thinking...", spinner="dots"):
                response_data = chat_with_llm(messages, model_name=model_name, provider=provider, is_ask_mode=True)
            
            raw_text = response_data.get("raw_response", "")
            parsed_json = extract_json_from_text(raw_text)
            
            if parsed_json and parsed_json.get("action") == "search_web":
                query = parsed_json.get("query", "")
                console.print(f"\n[bold cyan]🔍 検索中:[/bold cyan] {query}")
                
                with console.status("[bold yellow]Webを検索し、回答を生成中...", spinner="dots"):
                    search_result = search_web(query)
                    messages.append({"role": "assistant", "content": raw_text})
                    messages.append({"role": "user", "content": f"検索結果:\n{search_result}\n\nこの結果を踏まえて、最初の質問にマークダウンで直接答えてください。"})
                
                # 検索結果を踏まえた回答をストリーミングで表示
                raw_text = ""
                console.print()
                with Live("", console=console, refresh_per_second=8) as live:
                    for chunk in stream_chat_with_llm(messages, model_name=model_name, provider=provider):
                        raw_text += chunk
                        live.update(Markdown(raw_text))
            else:
                # 通常の/ask回答: ストリーミングで再度生成
                raw_text = ""
                console.print()
                with Live("", console=console, refresh_per_second=8) as live:
                    for chunk in stream_chat_with_llm(messages, model_name=model_name, provider=provider):
                        raw_text += chunk
                        live.update(Markdown(raw_text))

            elapsed_time = time.time() - start_time
            console.print(f"\n[dim]⏱️ Answered in {elapsed_time:.1f}s[/dim]")
            messages.append({"role": "assistant", "content": raw_text})
            needs_user_input = True
            continue

        # 通常モード: JSONレスポンス（非ストリーミング）
        with console.status("[bold cyan]AI is thinking...", spinner="dots"):
            response_data = chat_with_llm(messages, model_name=model_name, provider=provider, is_ask_mode=False)
        
        # JSONパース失敗時の自動リトライ（1回まで）
        if "error" in response_data and response_data.get("error") == "JSON_PARSE_ERROR":
            console.print("[dim]🔄 JSONパースに失敗しました。自動リトライ中...[/dim]")
            messages.append({"role": "assistant", "content": response_data.get("raw_response", "")})
            messages.append({"role": "user", "content": "あなたの前の応答はJSONとしてパースできませんでした。指定されたJSONフォーマットで再度出力してください。"})
            with console.status("[bold cyan]AI is retrying...", spinner="dots"):
                response_data = chat_with_llm(messages, model_name=model_name, provider=provider, is_ask_mode=False)

        if "error" in response_data:
            print_error("うまく解釈できませんでした。")
            console.print(f"[dim]詳細: {response_data.get('raw_response', response_data)}[/dim]")
            needs_user_input = True
            continue

        thought = response_data.get("thought", "思考プロセスなし")
        action = response_data.get("action", "none")
        args = response_data.get("args", {})
        elapsed_time = time.time() - start_time

        console.print(f"[dim]⏱️ Thought completed in {elapsed_time:.1f}s[/dim]")
        print_thought(thought)

        result_output = ""
        
        # --- アクション実行フェーズ ---
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
            console.print(f"[dim]内容をメモリに読み込みました。[/dim]")

        elif action == "write_file":
            filepath = args.get("filepath", "")
            content = args.get("content", "")
            console.print(f"[bold green]📝 Writing file:[/bold green] {filepath}")
            print_command(content)
            
            if auto_mode:
                confirm = 'y'
                console.print("[dim]🤖 Auto Mode: 自動で書き込みを許可しました。[/dim]")
            else:
                confirm = console.input("[bold]編集を許可しますか？ [y/N]: [/bold]").strip().lower()
                
            if confirm == 'y':
                result_output = write_file(filepath, content)
                console.print(f"[dim]ファイルに書き込みました。[/dim]")
            else:
                result_output = "キャンセルされました。"
                console.print(f"[dim]書き込みをキャンセルしました。[/dim]")

        elif action == "edit_file":
            filepath = args.get("filepath", "")
            old_text = args.get("old_text", "")
            new_text = args.get("new_text", "")
            console.print(f"[bold yellow]✏️ Editing file:[/bold yellow] {filepath}")
            console.print(f"[dim]old_text: {old_text[:100]}{'...' if len(old_text) > 100 else ''}[/dim]")
            console.print(f"[dim]new_text: {new_text[:100]}{'...' if len(new_text) > 100 else ''}[/dim]")
            
            if auto_mode:
                confirm = 'y'
                console.print("[dim]🤖 Auto Mode: 自動で編集を許可しました。[/dim]")
            else:
                confirm = console.input("[bold]編集を許可しますか？ [y/N]: [/bold]").strip().lower()
            
            if confirm == 'y':
                result_output = edit_file(filepath, old_text, new_text)
                console.print(f"[dim]ファイルを編集しました。[/dim]")
            else:
                result_output = "キャンセルされました。"
                console.print(f"[dim]編集をキャンセルしました。[/dim]")

        elif action == "read_directory":
            dir_path = args.get("dir_path", ".")
            console.print(f"[bold blue]📂 Reading directory:[/bold blue] {dir_path}")
            result_output = read_directory(dir_path)
            console.print(f"[dim]ディレクトリ構造を読み込みました。[/dim]")

        elif action == "web_search":
            query = args.get("query", "")
            console.print(f"[bold cyan]🔍 Web Searching:[/bold cyan] {query}")
            result_output = search_web(query)
            console.print("[dim]検索結果を取得しました。[/dim]")
        
        elif action == "none":
            pass
        else:
            result_output = f"Error: 未知のアクション '{action}'"

        if action != "none":
            messages.append({"role": "assistant", "content": f"```json\n{{\"action\": \"{action}\", \"args\": {args}}}\n```"})
            messages.append({"role": "user", "content": f"実行結果:\n```\n{result_output}\n```\n次のアクションを実行してください。完全に達成された場合のみ action: none にしてください。"})
            if result_output:
                console.print(f"\n[bold]Action Result:[/bold]\n[dim]{result_output}[/dim]\n")
            needs_user_input = False 
        else:
            messages.append({"role": "assistant", "content": f"Thought: {thought}\n(Action: none)"})
            console.print("[bold green]✅ タスク完了[/bold green]\n")
            needs_user_input = True 

def cli():
    parser = argparse.ArgumentParser(description="Loca - Autonomous AI Coding Assistant")
    parser.add_argument("-p", "--provider", type=str, default="ollama", choices=["ollama", "openai", "anthropic", "gemini"], help="LLMのプロバイダー")
    parser.add_argument("-m", "--model", type=str, default="qwen2.5-coder:32b", help="使用するモデル名")
    
    args = parser.parse_args()
    main(model_name=args.model, provider=args.provider)

if __name__ == "__main__":
    cli()