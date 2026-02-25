import os
import re
import json
import subprocess
from rich.panel import Panel
from rich.syntax import Syntax
from rich.live import Live
from rich.text import Text as RichText
from loca.ui.display import console, print_error
from loca.core.llm_client import chat_with_llm, stream_chat_with_llm, extract_json_from_text
from loca.core.prompts import get_editor_prompt, get_reviewer_prompt
from loca.tools.file_ops import write_file
import loca.config as config


def _extract_thought(partial_text: str) -> str:
    """ストリーミング途中のJSONからthoughtフィールドを取り出す"""
    match = re.search(r'"thought"\s*:\s*"((?:[^"\\]|\\.)*)', partial_text, re.DOTALL)
    if match:
        raw = match.group(1)
        return raw.replace('\\n', '\n').replace('\\"', '"').replace('\\\\', '\\')
    return ""


def _stream_with_thought(messages, model_name, provider, title, border_style="cyan"):
    """ストリーミングしながらthoughtをリアルタイム表示し、完成したdictを返す"""
    full_text = ""
    with Live(
        Panel("[dim]考え中...[/dim]", title=title, border_style=border_style),
        refresh_per_second=10,
        console=console,
    ) as live:
        for chunk in stream_chat_with_llm(messages, model_name=model_name, provider=provider):
            full_text += chunk
            thought = _extract_thought(full_text)
            if thought:
                live.update(Panel(
                    RichText(thought, style="italic dim"),
                    title=title,
                    border_style=border_style,
                ))
    parsed = extract_json_from_text(full_text)
    if parsed:
        return parsed
    return {"error": "JSON_PARSE_ERROR", "raw_response": full_text}


def _lint_files(files: list[dict]) -> str:
    """生成されたPythonファイルに対してruff + 構文チェックを実行し、エラーをまとめて返す。"""
    all_errors = []
    for f in files:
        filepath = f.get("filepath", "")
        if not filepath.endswith('.py'):
            continue
        if not os.path.exists(filepath):
            continue
        # 1. ruff 静的チェック
        try:
            result = subprocess.run(
                ["ruff", "check", filepath, "--output-format=concise"],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode != 0 and result.stdout.strip():
                all_errors.append(result.stdout.strip())
        except Exception:
            pass
        # 2. Python 構文チェック（py_compile）
        try:
            result = subprocess.run(
                ["python", "-c", f"import py_compile; py_compile.compile('{filepath}', doraise=True)"],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode != 0 and result.stderr.strip():
                err_msg = result.stderr.strip().split('\n')[-1]
                all_errors.append(f"Syntax/Import Error in {filepath}: {err_msg}")
        except Exception:
            pass
    return "\n".join(all_errors)


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
        # Editor フェーズ（JSONパースエラー時は最大2回リトライ）
        editor_res = None
        for json_retry in range(3):
            editor_res = _stream_with_thought(
                editor_messages, model_name, provider,
                title=f"[bold cyan]💭 Pro Editor (Attempt {attempt}/{max_attempts})[/bold cyan]",
                border_style="cyan",
            )
            
            if "error" not in editor_res:
                break  # 正常にパース成功
            
            if editor_res.get("error") == "JSON_PARSE_ERROR":
                console.print(f"[bold yellow]⚠️ EditorのJSON出力が不正です。リトライ中... ({json_retry + 1}/3)[/bold yellow]")
                raw = editor_res.get("raw_response", "")
                editor_messages.append({"role": "assistant", "content": raw})
                editor_messages.append({"role": "user", "content": "Your previous response was not valid JSON. Please output ONLY a valid JSON object with 'thought' and 'files' keys. Do not include any text outside the JSON."})
            else:
                # 接続エラー等 → リトライしても無意味
                break
        
        if "error" in editor_res:
            print_error(f"Editorがエラーを起こしました: {editor_res.get('error')}")
            break
            
        files = editor_res.get("files", [])
        final_files = files 
        console.print(f"[dim]✍️  Editor (Attempt {attempt}): {len(files)}個のファイルからなるプロジェクト原案を作成しました。[/dim]")
        
        code_for_review = ""
        for f in files:
            code_for_review += f"\n--- {f.get('filepath')} ---\n```python\n{f.get('content')}\n```\n"
        
        review_prompt = f"Original Task: {task}\n\nProject Code to review:\n{code_for_review}"
        reviewer_messages.append({"role": "user", "content": review_prompt})
        
        # Reviewer フェーズ（JSONパースエラー時は最大2回リトライ）
        reviewer_res = None
        for json_retry in range(3):
            reviewer_res = _stream_with_thought(
                reviewer_messages, model_name, provider,
                title=f"[bold yellow]💭 Pro Reviewer (Attempt {attempt}/{max_attempts})[/bold yellow]",
                border_style="yellow",
            )
            
            if "error" not in reviewer_res:
                break
            
            if reviewer_res.get("error") == "JSON_PARSE_ERROR":
                console.print(f"[bold yellow]⚠️ ReviewerのJSON出力が不正です。リトライ中... ({json_retry + 1}/3)[/bold yellow]")
                raw = reviewer_res.get("raw_response", "")
                reviewer_messages.append({"role": "assistant", "content": raw})
                reviewer_messages.append({"role": "user", "content": "Your previous response was not valid JSON. Please output ONLY a valid JSON object with 'thought', 'decision', and 'feedback' keys."})
            else:
                break
        
        if "error" in reviewer_res:
            print_error(f"Reviewerがエラーを起こしました: {reviewer_res.get('error')}")
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
            
            # === 実行検証フェーズ ===
            console.print(f"\n[bold cyan]🔍 実行検証フェーズ: 生成されたコードをチェック中...[/bold cyan]")
            lint_errors = _lint_files(final_files)
            
            if lint_errors:
                console.print(f"[bold yellow]⚠️ Lint警告が検出されました:[/bold yellow]")
                console.print(f"[dim]{lint_errors}[/dim]")
                console.print(f"\n[bold cyan]🔧 自動修正を試みます...[/bold cyan]")
                
                # Editorにlintエラーを渡して修正させる
                fix_prompt = (
                    f"The following lint errors were found in the generated code:\n\n{lint_errors}\n\n"
                    f"Please fix ALL these errors (especially missing imports) and return the corrected files. "
                    f"Return the COMPLETE corrected files, not just the changes."
                )
                editor_messages.append({"role": "user", "content": fix_prompt})
                
                fix_res = _stream_with_thought(
                    editor_messages, model_name, provider,
                    title="[bold cyan]💭 Pro Editor (Lint Fix)[/bold cyan]",
                    border_style="cyan",
                )
                
                if "error" not in fix_res:
                    fixed_files = fix_res.get("files", [])
                    if fixed_files:
                        for f in fixed_files:
                            filepath = f.get("filepath", "unknown.py")
                            content = f.get("content", "")
                            os.makedirs(os.path.dirname(filepath) or ".", exist_ok=True)
                            write_file(filepath, content)
                            console.print(f"[bold green]✔ Fixed: {filepath}[/bold green]")
                        
                        # 修正後に再度lint
                        remaining_errors = _lint_files(fixed_files)
                        if remaining_errors:
                            console.print(f"[bold yellow]⚠️ まだ一部の警告が残っています:[/bold yellow]")
                            console.print(f"[dim]{remaining_errors}[/dim]")
                        else:
                            console.print(f"[bold green]✅ 全てのLintエラーが修正されました！[/bold green]")
                        final_files = fixed_files
                else:
                    console.print("[dim]自動修正に失敗しました。手動で修正してください。[/dim]")
            else:
                console.print(f"[bold green]✅ Lintチェック通過: エラーなし[/bold green]")
            
            console.print("")
    return final_files