import importlib.util
import os
from pathlib import Path

from loca.ui.display import console

_plugins: list[dict] | None = None


def load_plugins() -> list[dict]:
    """
    カレントディレクトリの ./loca_tools/*.py をプラグインとして動的にロードする。
    結果はキャッシュされ、2回目以降は即座に返す。

    各プラグインファイルに必要なもの:
        TOOL_NAME        (str): アクション名（英小文字・アンダースコア推奨）
        TOOL_DESCRIPTION (str): LLMに伝えるツールの説明
        ARGS_FORMAT      (str): args の JSON フォーマット例（省略可、省略時は "{}"）
        run(args: dict) -> str: 実行関数
    """
    global _plugins
    if _plugins is not None:
        return _plugins

    _plugins = []
    tools_dir = Path(os.getcwd()) / "loca_tools"
    if not tools_dir.exists():
        return _plugins

    for py_file in sorted(tools_dir.glob("*.py")):
        if py_file.name.startswith("_"):
            continue
        try:
            spec = importlib.util.spec_from_file_location(py_file.stem, py_file)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)

            name = getattr(mod, "TOOL_NAME", None)
            description = getattr(mod, "TOOL_DESCRIPTION", None)
            args_format = getattr(mod, "ARGS_FORMAT", "{}")
            run_fn = getattr(mod, "run", None)

            if not (name and description and callable(run_fn)):
                console.print(
                    f"[dim yellow]⚠️ Plugin skipped ({py_file.name}): "
                    f"TOOL_NAME, TOOL_DESCRIPTION, run() が必要です。[/dim yellow]"
                )
                continue

            _plugins.append({
                "name": name,
                "description": description,
                "args_format": args_format,
                "run": run_fn,
                "filepath": str(py_file),
            })
            console.print(f"[dim]🔌 Plugin loaded: [bold]{name}[/bold] ({py_file.name})[/dim]")

        except Exception as e:
            console.print(f"[dim red]⚠️ Plugin load error ({py_file.name}): {e}[/dim red]")

    return _plugins


def get_plugin(action_name: str) -> dict | None:
    """アクション名からプラグインを返す。見つからなければ None。"""
    for plugin in load_plugins():
        if plugin["name"] == action_name:
            return plugin
    return None
