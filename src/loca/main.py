import time
import argparse
from rich.panel import Panel

# --- Loca 初期化 ---
import loca.config as config
config.setup_environment()

# --- コア機能 ---
from loca.core.llm_client import chat_with_llm, extract_json_from_text
from loca.core.prompts import get_system_prompt
from loca.core.memory import MemoryManager
from loca.core.pro_agent import run_pro_mode

# --- ツール ---
from loca.tools.web_search import search_web
from loca.tools.commander import execute_command
from loca.tools.file_ops import read_file, write_file, read_directory
from loca.tools.git_ops import auto_commit

# --- UI ---
from loca.ui.header import print_header
from loca.ui.display import console, print_thought, print_command, print_error, get_user_input

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
        console.print("[bold cyan]🧠 Locaの記憶(loca_rules.md)をロードしました！[/bold cyan]\n")
        
    needs_user_input = True 
    auto_mode = False

    while True:
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

            is_ask_mode = False
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
        start_time = time.time()
        with console.status("[bold cyan]AI is thinking...", spinner="dots"):
            response_data = chat_with_llm(messages, model_name=model_name, provider=provider, is_ask_mode=is_ask_mode)
        
        if is_ask_mode:
            raw_text = response_data.get("raw_response", "")
            parsed_json = extract_json_from_text(raw_text)
            
            if parsed_json and parsed_json.get("action") == "search_web":
                query = parsed_json.get("query", "")
                console.print(f"\n[bold cyan]🔍 検索中:[/bold cyan] {query}")
                
                with console.status("[bold yellow]Webを検索し、回答を生成中...", spinner="dots"):
                    search_result = search_web(query)
                    messages.append({"role": "assistant", "content": raw_text})
                    messages.append({"role": "user", "content": f"検索結果:\n{search_result}\n\nこの結果を踏まえて、最初の質問にマークダウンで直接答えてください。"})
                    
                    final_response = chat_with_llm(messages, model_name=model_name, provider=provider, is_ask_mode=True)
                    raw_text = final_response.get("raw_response", "検索結果の解釈に失敗しました。")
                    elapsed_time = time.time() - start_time

            console.print(f"[dim]⏱️ Answered in {elapsed_time:.1f}s[/dim]")
            console.print(Panel(raw_text, title="[bold blue]Loca[/bold blue]", border_style="blue"))
            messages.append({"role": "assistant", "content": raw_text})
            needs_user_input = True
            continue

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
                confirm = input("編集を許可しますか？ [y/N]: ").strip().lower()
                
            if confirm == 'y':
                result_output = write_file(filepath, content)
                console.print(f"[dim]ファイルに書き込みました。[/dim]")
            else:
                result_output = "キャンセルされました。"
                console.print(f"[dim]書き込みをキャンセルしました。[/dim]")
        
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