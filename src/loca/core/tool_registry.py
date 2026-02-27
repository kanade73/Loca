from dataclasses import dataclass, field
from typing import Callable


@dataclass
class Tool:
    """単一ツールの定義。ハンドラー・スキーマ・説明を1ファイルで完結させる。"""

    name: str
    description: str
    # JSON Schema の properties 相当（thought は自動付与するので含めない）
    args_schema: dict = field(default_factory=dict)
    # required に含めるキー一覧（thought は自動付与）
    required_args: list[str] = field(default_factory=list)
    # (args: dict, auto_mode: bool) -> (result_output: str, should_kill: bool)
    handler: Callable = None

    def to_openai_schema(self) -> dict:
        """OpenAI Function Calling 形式のスキーマを返す。thought は自動追加。"""
        props = {
            "thought": {
                "type": "string",
                "description": "Briefly explain why you chose this action (in English).",
            }
        }
        props.update(self.args_schema)
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": props,
                    "required": ["thought"] + self.required_args,
                },
            },
        }


class ToolRegistry:
    """全ツールを一元管理するレジストリ。ツール追加が1ファイルで完結する。"""

    def __init__(self):
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool | None:
        return self._tools.get(name)

    def all(self) -> list[Tool]:
        return list(self._tools.values())

    def openai_schemas(self) -> list[dict]:
        """Function Calling 用スキーマリストを返す。"""
        return [t.to_openai_schema() for t in self._tools.values()]

    def execute(self, name: str, args: dict, auto_mode: bool) -> tuple[str, bool]:
        """ツールを名前で実行する。未知の名前はエラー文字列を返す。"""
        tool = self.get(name)
        if tool is None:
            return f"Error: 未知のアクション '{name}'", False
        return tool.handler(args, auto_mode)
