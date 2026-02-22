import subprocess
from loca.ui.display import console
from loca.core.llm_client import chat_with_llm
import loca.config as config

def auto_commit(model_name: str = None, provider: str = None):
    model_name = model_name or config.DEFAULT_MODEL
    provider = provider or config.DEFAULT_PROVIDER
    """Gitの変更を解析し、自動でコミットメッセージを生成してコミットする"""
    console.print(f"\n[bold cyan]🐙 Git Auto Commit を開始します...[/bold cyan]")
    
    status_res = subprocess.run("git status --porcelain", shell=True, capture_output=True, text=True)
    
    if status_res.returncode != 0:
        console.print(f"[bold red]❌ Gitエラーが発生しました！[/bold red]")
        console.print(f"[dim]{status_res.stderr.strip()}[/dim]")
        console.print("[yellow]💡 ヒント: まだ `git init` を実行していない可能性があります。[/yellow]\n")
        return
        
    status = status_res.stdout.strip()
    if not status:
        console.print("[yellow]変更されたファイルがありません。[/yellow]\n")
        return
    
    # 変更されたファイルを一覧表示して確認を求める
    console.print(f"\n[bold]📋 変更されたファイル:[/bold]")
    console.print(f"[dim]{status}[/dim]\n")
    
    stage_choice = console.input("[bold]これらのファイルを全てステージングしますか？ [Y/n]: [/bold]").strip().lower()
    if stage_choice == 'n':
        console.print("[dim]コミットをキャンセルしました。[/dim]\n")
        return
    
    subprocess.run("git add -A", shell=True)
    
    diff = subprocess.run("git diff --staged", shell=True, capture_output=True, text=True).stdout.strip()
    if not diff:
        console.print("[yellow]コミットする差分がありません。[/yellow]\n")
        return
        
    console.print("[dim]差分を解析してコミットメッセージを生成中...[/dim]")
    messages = [
        {"role": "system", "content": "You are an expert software engineer. Generate a concise, clear Git commit message in Japanese based on the provided git diff. Output ONLY the commit message without any quotes or markdown formatting."},
        {"role": "user", "content": f"以下のdiffから変更の意図を汲み取り、適切なコミットメッセージを1行で生成してください:\n\n```diff\n{diff[:3000]}\n```"}
    ]
    
    # 抽象化されたchat_with_llmを使用
    res = chat_with_llm(messages, model_name=model_name, provider=provider, is_ask_mode=True)
    commit_msg = res.get("raw_response", "Update files").strip()
    
    console.print(f"\n[bold green]✨ 提案されたメッセージ:[/bold green] {commit_msg}")
    choice = console.input("[bold]このメッセージでコミットしますか？ [Y/n/e (編集)]: [/bold]").strip().lower()
    
    if choice == 'e':
        commit_msg = console.input("[bold]新しいコミットメッセージを入力: [/bold]").strip()
    elif choice == 'n':
        console.print("[dim]コミットをキャンセルしました。(git addは維持されています)[/dim]\n")
        return
        
    if not commit_msg:
        console.print("[red]メッセージが空のためキャンセルしました。[/red]\n")
        return
        
    safe_msg = commit_msg.replace('"', '\\"') 
    commit_res = subprocess.run(f'git commit -m "{safe_msg}"', shell=True, capture_output=True, text=True)
    console.print(f"[dim]{commit_res.stdout.strip()}[/dim]")
    console.print("[bold green]✅ コミットが完了しました！[/bold green]\n")