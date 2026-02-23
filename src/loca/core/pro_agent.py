import os
import json
from rich.panel import Panel
from rich.syntax import Syntax
from loca.ui.display import console, print_error
from loca.core.llm_client import chat_with_llm
from loca.core.prompts import get_editor_prompt, get_reviewer_prompt
from loca.tools.file_ops import write_file
import loca.config as config

def run_pro_mode(task: str, model_name: str = None, provider: str = None, auto_mode: bool = False):
    """EditorとReviewerの2つのAIエージェントを戦わせて高品質なコードを生成するモード"""
    model_name = model_name or config.DEFAULT_MODEL
    provider = provider or config.DEFAULT_PROVIDER
    console.print(f"\n[bold magenta]🚀 起動: Pro Agent (Deep Thinking Mode)[/bold magenta]")
    console.print(f"[dim]Task: {task}[/dim]\n")
    
    editor_messages = [get_editor_prompt(), {"role": "user", "content": task}]
    reviewer_messages = [get_reviewer_prompt()]
    
    max_attempts = 3
    final_files = [] 
    
    for attempt in range(1, max_attempts + 1):
        with console.status(f"[bold cyan]Pro Editor is architecting & coding... (Attempt {attempt}/{max_attempts})[/bold cyan]", spinner="dots"):
            editor_res = chat_with_llm(editor_messages, model_name=model_name, provider=provider)
        
        if "error" in editor_res:
            print_error("Editorがエラーを起こしました。")
            break
            
        files = editor_res.get("files", [])
        final_files = files 
        console.print(f"[dim]✍️  Editor (Attempt {attempt}): {len(files)}個のファイルからなるプロジェクト原案を作成しました。[/dim]")
        
        code_for_review = ""
        for f in files:
            code_for_review += f"\n--- {f.get('filepath')} ---\n```python\n{f.get('content')}\n```\n"
        
        review_prompt = f"Original Task: {task}\n\nProject Code to review:\n{code_for_review}"
        reviewer_messages.append({"role": "user", "content": review_prompt})
        
        with console.status(f"[bold yellow]Pro Reviewer is reviewing... (Attempt {attempt}/{max_attempts})[/bold yellow]", spinner="dots"):
            reviewer_res = chat_with_llm(reviewer_messages, model_name=model_name, provider=provider)
        
        if "error" in reviewer_res:
            print_error("Reviewerがエラーを起こしました。")
            break
            
        decision = reviewer_res.get("decision", "reject")
        feedback = reviewer_res.get("feedback", "")
        reviewer_messages.append({"role": "assistant", "content": json.dumps(reviewer_res, ensure_ascii=False)})
        
        if decision == "approve":
            console.print(f"[bold green]✅ Reviewer Approved! 完璧なプロジェクト構成です。 (Attempt {attempt})[/bold green]")
            break
        else:
            console.print(f"[bold red]❌ Reviewer Rejected (差し戻し)[/bold red]\n[dim]Feedback: {feedback}[/dim]\n")
            if attempt < max_attempts:
                editor_messages.append({"role": "assistant", "content": json.dumps(editor_res, ensure_ascii=False)})
                editor_messages.append({"role": "user", "content": f"Reviewer feedback: {feedback}\nPlease fix the project according to this feedback."})
            else:
                console.print("[bold yellow]⚠️ 最大試行回数に到達しました。現在の最新コードを出力します。[/bold yellow]")

    # 最終結果の表示と保存
    if final_files:
        console.print("\n[bold magenta]✨ Pro Mode Final Project ✨[/bold magenta]")
        for f in final_files:
            filepath = f.get("filepath", "unknown.py")
            console.print(f"\n[bold blue]📄 {filepath}[/bold blue]")
            # ファイル拡張子からシンタックスハイライトの言語を推定
            ext = filepath.rsplit(".", 1)[-1] if "." in filepath else "text"
            lang_map = {"py": "python", "js": "javascript", "ts": "typescript", "html": "html", "css": "css", "json": "json", "md": "markdown", "yml": "yaml", "yaml": "yaml", "sh": "bash", "toml": "toml"}
            syntax_lang = lang_map.get(ext, ext)
            syntax = Syntax(f.get("content", ""), syntax_lang, theme="monokai", line_numbers=True)
            console.print(Panel(syntax, border_style="magenta"))
        
        if auto_mode:
            save_ans = 'y'
            console.print("\n[bold yellow]🤖 Auto Mode: 全ファイルを自動生成します...[/bold yellow]")
        else:
            save_ans = console.input(f"\nこれら {len(final_files)} 個のファイルを提案されたパスに自動生成しますか？ [y/N]: ").strip().lower()
            
        if save_ans == 'y':
            for f in final_files:
                filepath = f.get("filepath", "unknown.py")
                content = f.get("content", "")
                os.makedirs(os.path.dirname(filepath) or ".", exist_ok=True)
                write_file(filepath, content)
                console.print(f"[bold green]✔ Saved to {filepath}[/bold green]")
            console.print("")
    return final_files