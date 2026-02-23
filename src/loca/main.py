import time
import argparse

# --- コア機能 ---
from loca.core.llm_client import chat_with_llm, stream_chat_with_llm, extract_json_from_text, estimate_tokens
from loca.core.prompts import get_system_prompt
from loca.core.memory import MemoryManager
from loca.core.router import route_command
from loca.core.executor import execute_action

# --- ツール ---
from loca.tools.web_search import search_web

# --- UI ---
from loca.ui.header import print_header
from loca.ui.display import console, print_thought, print_error, get_user_input
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

            # コマンドルーティング
            route_result, auto_mode, exchange_count = route_command(
                user_input, messages, memory,
                model_name=model_name, provider=provider,
                auto_mode=auto_mode, exchange_count=exchange_count,
            )
            
            if route_result.should_exit:
                break
            if route_result.handled:
                needs_user_input = True
                continue
            
            is_ask_mode = route_result.is_ask_mode
                
        # --- AI思考フェーズ ---
        # 交換回数チェック
        exchange_count += 1
        if exchange_count > MAX_EXCHANGES:
            console.print(f"\n[bold yellow]⚠️ セッションの上限 ({MAX_EXCHANGES}回) に達しました。コンテキストをリセットします。[/bold yellow]")
            console.print("[dim]新しいタスクを入力してください。[/dim]\n")
            messages.clear()
            messages.append(get_system_prompt())
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

        # --- アクション実行フェーズ ---
        result_output, should_kill = execute_action(action, args, auto_mode)
        
        if should_kill:
            messages.append({"role": "user", "content": "ユーザーがこの処理を強制終了しました。絶対にこれ以上何もせず、すぐに Action: none を返して待機状態に戻ってください。"})
            needs_user_input = True
            continue

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
    import loca.config as config
    parser = argparse.ArgumentParser(description="Loca - Autonomous AI Coding Assistant")
    parser.add_argument("-p", "--provider", type=str, default=config.DEFAULT_PROVIDER, choices=["ollama", "openai", "anthropic", "gemini"], help="LLMのプロバイダー")
    parser.add_argument("-m", "--model", type=str, default=config.DEFAULT_MODEL, help="使用するモデル名")
    
    args = parser.parse_args()
    main(model_name=args.model, provider=args.provider)

if __name__ == "__main__":
    cli()