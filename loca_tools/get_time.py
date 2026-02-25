"""
サンプルプラグイン: 現在の日時を返す

プラグインの作り方:
  1. このファイルを loca_tools/ にコピーして編集する
  2. TOOL_NAME, TOOL_DESCRIPTION, ARGS_FORMAT を設定する
  3. run(args: dict) -> str を実装する
  4. Loca を起動すると自動的にロードされる
"""

from datetime import datetime

TOOL_NAME = "get_time"
TOOL_DESCRIPTION = "Get the current date and time. Use this when you need to know today's date."
ARGS_FORMAT = '{}'


def run(args: dict) -> str:
    now = datetime.now()
    return f"現在日時: {now.strftime('%Y年%m月%d日（%A）%H:%M:%S')}"
