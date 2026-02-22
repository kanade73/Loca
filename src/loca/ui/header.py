from rich.panel import Panel
from rich.text import Text
from rich.align import Align
from loca.ui.display import console

# スラッシュやバックスラッシュが崩れないよう raw文字列 (r"...") を使用
ASCII_ART = r"""
██╗      ██████╗  ██████╗ █████╗ 
██║     ██╔═══██╗██╔════╝██╔══██╗
██║     ██║   ██║██║     ███████║
██║     ██║   ██║██║     ██╔══██║
███████╗╚██████╔╝╚██████╗██║  ██║
╚══════╝ ╚═════╝  ╚═════╝╚═╝  ╚═╝
   LOCAL AI  ·  FREE  ·  YOURS
"""

def print_header(model_name="unknown"):
    # アスキーアート部分（シアン色で発光）
    title = Text(ASCII_ART, style="bold cyan")
    
    subtitle = Text.from_markup(f"\nSystems Online. Connected to local brain: [bold green]{model_name}[/]")
    subtitle.stylize("dim white") 
    
    header_content = Text.assemble(title, subtitle)

    panel = Panel(
        Align.center(header_content),
        border_style="blue",
        padding=(1, 2),
        title="[bold magenta]Initializing...[/]",
        subtitle="[dim]Type 'exit' to quit[/]",
    )

    console.print(panel)
    console.print("\n")

# テスト実行用
if __name__ == "__main__":
    print_header(model_name="qwen2.5-coder:32b")