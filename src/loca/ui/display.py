# src/ui/display.py
from rich.console import Console
from rich.panel import Panel
from rich.theme import Theme
from rich.syntax import Syntax
# src/ui/display.py の上の方に追加
from prompt_toolkit import PromptSession
from prompt_toolkit.styles import Style
from prompt_toolkit.key_binding import KeyBindings

# グローバルにセッションを持たせる（これで上矢印キーで過去の入力履歴を呼び出せます！）
prompt_session = PromptSession()

# カスタムテーマの定義（お好みの色に変更できます）
custom_theme = Theme({
    "user": "bold cyan",
    "ai_thought": "dim magenta",
    "ai_command": "bold green",
    "error": "bold red",
    "success": "bold blue"
})

# アプリ全体で使い回すコンソールインスタンス
console = Console(theme=custom_theme)

def print_thought(thought: str):
    """AIの思考プロセスを枠で囲ってカッコよく表示する"""
    if not thought or thought == "思考プロセスなし":
        return
        
    panel = Panel(
        thought,
        title="[ai_thought]AI Thought[/ai_thought]",
        border_style="magenta",
        padding=(0, 1)
    )
    console.print(panel)

def print_command(command: str):
    """提案されたコマンドをシンタックスハイライトして表示する"""
    if not command or command.lower() == "null":
        return

    # Bashスクリプトとして色付け
    syntax = Syntax(command, "bash", theme="monokai", line_numbers=False)
    panel = Panel(
        syntax,
        title="[ai_command]Proposed Command[/ai_command]",
        border_style="green",
        padding=(0, 1)
    )
    console.print(panel)

def print_error(msg: str):
    """エラーメッセージの表示"""
    console.print(f"[error]✖ Error:[/error] {msg}")

def print_success(msg: str):
    """成功メッセージの表示"""
    console.print(f"[success]✔ Success:[/success] {msg}")

def get_user_input():
    """
    ユーザーからの入力を受け取る（Enter送信、Alt+Enter改行）
    """
    bindings = KeyBindings()

    # ① 通常の「Enter」は送信（確定）にする
    @bindings.add('enter')
    def _(event):
        event.current_buffer.validate_and_handle()

    # ② 「Escを押してEnter」または「Alt+Enter」で改行にする
    @bindings.add('escape', 'enter')
    def _(event):
        event.current_buffer.insert_text('\n')

    style = Style.from_dict({
        'prompt': 'ansicyan bold',
    })
    
    console.print("\n[dim]💡 [Enter] 送信 / [Alt+Enter] または [Esc]→[Enter] で改行[/dim]")
    
    # multiline=Trueにしつつ、自作のキーバインドを適用
    text = prompt_session.prompt('> ', multiline=True, key_bindings=bindings, style=style)
    
    return text.strip()