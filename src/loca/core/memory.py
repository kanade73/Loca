from rich.panel import Panel
from rich.table import Table
from loca.ui.display import console
import loca.config as config

class MemoryManager:
    """Locaの掟（Loca.md）を管理するクラス"""
    
    def __init__(self):
        self.rules_path = config.get_rules_path()

    def remember(self, rule: str):
        try:
            with open(self.rules_path, "a", encoding="utf-8") as f:
                f.write(f"- {rule}\n")
            console.print(f"[bold green]✅ 記憶しました:[/bold green] {rule}")
        except Exception as e:
            console.print(f"[bold red]❌ 記憶の保存に失敗しました: {e}[/bold red]")

    def show_rules(self):
        if not self.rules_path.exists():
            console.print("[yellow]まだ記憶（Loca.md）がありません。[/yellow]")
            return
            
        try:
            lines = self.rules_path.read_text(encoding="utf-8").strip().splitlines()
            if not lines:
                console.print("[yellow]記憶は空っぽです。[/yellow]")
                return
                
            table = Table(title="🧠 Locaの記憶 (Project Rules)", border_style="cyan")
            table.add_column("No.", style="dim", width=4)
            table.add_column("Rule", style="white")
            
            for i, line in enumerate(lines, 1):
                table.add_row(str(i), line)
                
            console.print(table)
            console.print("[dim]※特定のルールを消すには `/forget <番号>` を実行してください。[/dim]")
        except Exception as e:
            console.print(f"[bold red]❌ 記憶の読み込みに失敗しました: {e}[/bold red]")

    def forget(self, line_number_str: str):
        if not self.rules_path.exists():
            console.print("[yellow]削除する記憶がありません。[/yellow]")
            return
            
        try:
            line_number = int(line_number_str)
            lines = self.rules_path.read_text(encoding="utf-8").strip().splitlines()
            
            if 1 <= line_number <= len(lines):
                removed_rule = lines.pop(line_number - 1)
                self.rules_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
                console.print(f"[bold red]🗑️ 忘れました:[/bold red] {removed_rule}")
            else:
                console.print(f"[bold yellow]指定された番号 ({line_number}) の記憶はありません。[/bold yellow]")
        except ValueError:
            console.print("[bold red]エラー: 行番号を数字で指定してください。(例: /forget 2)[/bold red]")
        except Exception as e:
            console.print(f"[bold red]❌ 記憶の削除に失敗しました: {e}[/bold red]")