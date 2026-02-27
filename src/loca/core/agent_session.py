"""
AgentSession: メインループとフラグ管理をカプセル化したクラス。
以前の main.py に散在していた状態を一元管理し、テスト容易性を高める。
"""
import json
import time

from loca.core.llm_client import (
    chat_with_tools,
    chat_with_llm,
    stream_chat_with_llm,
    extract_json_from_text,
    estimate_tokens,
)
from loca.core.prompts import get_system_prompt, get_agent_system_prompt
from loca.core.memory import MemoryManager
from loca.core.router import route_command
from loca.core.executor import create_default_registry, backup_manager
from loca.core.tool_registry import ToolRegistry
from loca.tools.web_search import search_web
from loca.ui.header import print_header
from loca.ui.display import console, print_thought, print_error, get_user_input
from rich.live import Live
from rich.markdown import Markdown

MAX_EXCHANGES = 30
MAX_MESSAGES = 60


def _trim_messages(messages: list) -> list:
    """コンテキストウィンドウのオーバーフローを防ぐ安全装置。"""
    if len(messages) <= MAX_MESSAGES:
        return messages
    trimmed = [messages[0]] + messages[-(MAX_MESSAGES - 1):]
    console.print(
        f"[dim]📎 コンテキスト整理: 古いメッセージを切り捨てました ({len(messages)} → {len(trimmed)})[/dim]"
    )
    return trimmed


class AgentSession:
    """
    1セッション分のエージェント状態を保持し、メインループを実行するクラス。

    Attributes:
        model_name: 使用するLLMモデル名
        provider: LLMプロバイダー（ollama/openai/anthropic/gemini）
        messages: 会話履歴
        auto_mode: True のとき確認プロンプトをスキップ
        exchange_count: 現セッションのLLM呼び出し回数
        needs_user_input: True のとき次のループでユーザー入力を待つ
        is_ask_mode: /ask コマンドによる会話モードか否か
    """

    def __init__(self, model_name: str, provider: str):
        self.model_name = model_name
        self.provider = provider
        self.memory = MemoryManager()
        self.registry: ToolRegistry = create_default_registry()
        self.messages: list = []
        self.auto_mode: bool = False
        self.exchange_count: int = 0
        self.needs_user_input: bool = True
        self.is_ask_mode: bool = False
        self._reset_messages()

    # ------------------------------------------------------------------
    # パブリック API
    # ------------------------------------------------------------------

    def run(self) -> None:
        """メインループを開始する。"""
        print_header(model_name=f"{self.model_name} ({self.provider.upper()})")

        if "<project_guidelines>" in self.messages[0]["content"]:
            console.print("[bold cyan]🧠 Locaの記憶(Loca.md)をロードしました！[/bold cyan]\n")

        while True:
            self.messages = _trim_messages(self.messages)

            if self.needs_user_input:
                should_continue = self._handle_user_input()
                if not should_continue:
                    break
                if self.needs_user_input:
                    # コマンドとして処理済み → 次のユーザー入力を待つ
                    continue

            self._run_ai_step()

    # ------------------------------------------------------------------
    # プライベートメソッド
    # ------------------------------------------------------------------

    def _reset_messages(self) -> None:
        """会話履歴とカウンターをリセットする。"""
        self.messages = [get_agent_system_prompt()]
        self.exchange_count = 0

    def _handle_user_input(self) -> bool:
        """
        ユーザー入力を受け取り、ルーティングする。
        False を返すとメインループを終了する。
        """
        try:
            user_input = get_user_input()
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]Shutting down agent...[/dim]")
            return False

        route_result, self.auto_mode, self.exchange_count = route_command(
            user_input, self.messages, self.memory,
            model_name=self.model_name, provider=self.provider,
            auto_mode=self.auto_mode, exchange_count=self.exchange_count,
        )

        if route_result.should_exit:
            return False

        if route_result.handled:
            # /clear 等でメッセージが書き換わった場合、FC用プロンプトを確実に復元する
            if self.messages:
                self.messages[0] = get_agent_system_prompt()
            self.needs_user_input = True
            return True

        self.is_ask_mode = route_result.is_ask_mode
        self.needs_user_input = False
        return True

    def _run_ai_step(self) -> None:
        """AI思考フェーズを実行し、needs_user_input を更新する。"""
        self.exchange_count += 1
        if self.exchange_count > MAX_EXCHANGES:
            console.print(
                f"\n[bold yellow]⚠️ セッションの上限 ({MAX_EXCHANGES}回) に達しました。"
                "コンテキストをリセットします。[/bold yellow]"
            )
            console.print("[dim]新しいタスクを入力してください。[/dim]\n")
            self._reset_messages()
            self.needs_user_input = True
            return

        token_count = estimate_tokens(self.messages)
        console.print(
            f"[dim]📊 Tokens: ~{token_count} | Exchange: {self.exchange_count}/{MAX_EXCHANGES}[/dim]"
        )

        start_time = time.time()

        if self.is_ask_mode:
            self._run_ask_step(start_time)
        else:
            self._run_agent_step(start_time)

    def _run_ask_step(self, start_time: float) -> None:
        """
        /ask モード: 1回のストリーミング呼び出しで回答する。

        【2重呼び出し解消】
        旧実装: chat_with_llm() (非ストリーミング) → search_web判定 → stream_chat_with_llm() (再度呼び出し)
        新実装: stream_chat_with_llm() で一度だけバッファに収集 → search_web判定 → 必要なら2回目
        """
        # ask モード用プロンプトは router.py が messages[0] に設定済み
        raw_text = ""

        # 1回のストリーミングでバッファに収集（spinner を表示しながら）
        with console.status("[bold cyan]AI is thinking...", spinner="dots"):
            for chunk in stream_chat_with_llm(
                self.messages, model_name=self.model_name, provider=self.provider
            ):
                raw_text += chunk

        parsed_json = extract_json_from_text(raw_text)

        if parsed_json and parsed_json.get("action") == "search_web":
            # Web検索が必要な場合のみ2回目の呼び出しを行う
            query = parsed_json.get("query", "")
            console.print(f"\n[bold cyan]🔍 検索中:[/bold cyan] {query}")

            with console.status("[bold yellow]Webを検索し、回答を生成中...", spinner="dots"):
                search_result = search_web(query)
                self.messages.append({"role": "assistant", "content": raw_text})
                self.messages.append({
                    "role": "user",
                    "content": (
                        f"検索結果:\n{search_result}\n\n"
                        "この結果を踏まえて、最初の質問にマークダウンで直接答えてください。"
                    ),
                })

            raw_text = ""
            console.print()
            with Live("", console=console, refresh_per_second=8) as live:
                for chunk in stream_chat_with_llm(
                    self.messages, model_name=self.model_name, provider=self.provider
                ):
                    raw_text += chunk
                    live.update(Markdown(raw_text))
        else:
            # 通常の回答: バッファ済みテキストを Markdown でレンダリング
            console.print()
            console.print(Markdown(raw_text))

        elapsed_time = time.time() - start_time
        console.print(f"\n[dim]⏱️ Answered in {elapsed_time:.1f}s[/dim]")
        self.messages.append({"role": "assistant", "content": raw_text})
        self.needs_user_input = True
        self.is_ask_mode = False
        # ask モード終了後、エージェントモード用プロンプトを復元
        self.messages[0] = get_agent_system_prompt()

    def _run_agent_step(self, start_time: float) -> None:
        """
        通常エージェントモード: Function Calling でアクションを決定・実行する。
        Function Calling 非対応モデルの場合は JSON フォールバックを使用。
        """
        # エージェントモード用プロンプトを確実にセット
        self.messages[0] = get_agent_system_prompt()

        tools = self.registry.openai_schemas()

        with console.status("[bold cyan]AI is thinking...", spinner="dots"):
            response_data = chat_with_tools(
                self.messages, tools,
                model_name=self.model_name, provider=self.provider,
            )

        # Function Calling 非対応モデルへのフォールバック
        if response_data.get("error") == "NO_TOOL_CALL":
            console.print(
                "[dim]⚠️ Function Callingが利用できません。JSONモードにフォールバックします。[/dim]"
            )
            response_data = self._fallback_json_call()

        if "error" in response_data:
            print_error("うまく解釈できませんでした。")
            console.print(f"[dim]詳細: {response_data.get('raw_response', response_data)}[/dim]")
            self.needs_user_input = True
            return

        thought = response_data.get("thought", "")
        action = response_data.get("action", "none")
        args = response_data.get("args", {})
        elapsed_time = time.time() - start_time

        console.print(f"[dim]⏱️ Thought completed in {elapsed_time:.1f}s[/dim]")
        print_thought(thought)

        result_output, should_kill = self.registry.execute(action, args, self.auto_mode)

        if should_kill:
            self.messages.append({
                "role": "user",
                "content": (
                    "ユーザーがこの処理を強制終了しました。"
                    "絶対にこれ以上何もせず、すぐに none ツールを呼び出して待機状態に戻ってください。"
                ),
            })
            self.needs_user_input = True
            return

        if action != "none":
            # 会話履歴はテキスト形式で保存（FC/JSONモード両方で再利用できる）
            self.messages.append({
                "role": "assistant",
                "content": f"```json\n{{\"action\": \"{action}\", \"args\": {json.dumps(args, ensure_ascii=False)}}}\n```",
            })
            self.messages.append({
                "role": "user",
                "content": (
                    f"実行結果:\n```\n{result_output}\n```\n"
                    "次のアクションを実行してください。完全に達成された場合のみ none ツールを呼び出してください。"
                ),
            })
            if result_output:
                console.print(f"\n[bold]Action Result:[/bold]\n[dim]{result_output}[/dim]\n")
            self.needs_user_input = False
        else:
            self.messages.append({
                "role": "assistant",
                "content": f"Thought: {thought}\n(Action: none)",
            })
            console.print("[bold green]✅ タスク完了[/bold green]\n")
            self.needs_user_input = True

    def _fallback_json_call(self) -> dict:
        """
        Function Calling 非対応モデル用の JSON フォールバック。
        旧来の chat_with_llm() を使用し、JSONパースを試みる。
        """
        # JSON モード用プロンプトに一時的に切り替え
        fc_prompt = self.messages[0]
        self.messages[0] = get_system_prompt()

        with console.status("[bold cyan]AI is retrying (JSON mode)...", spinner="dots"):
            response_data = chat_with_llm(
                self.messages, model_name=self.model_name, provider=self.provider, is_ask_mode=False
            )

        # JSONパース失敗時はもう1回リトライ
        if response_data.get("error") == "JSON_PARSE_ERROR":
            console.print("[dim]🔄 JSONパースに失敗しました。自動リトライ中...[/dim]")
            self.messages.append({"role": "assistant", "content": response_data.get("raw_response", "")})
            self.messages.append({
                "role": "user",
                "content": "あなたの前の応答はJSONとしてパースできませんでした。指定されたJSONフォーマットで再度出力してください。",
            })
            with console.status("[bold cyan]AI is retrying...", spinner="dots"):
                response_data = chat_with_llm(
                    self.messages, model_name=self.model_name, provider=self.provider, is_ask_mode=False
                )

        # FC プロンプトを復元
        self.messages[0] = fc_prompt
        return response_data
