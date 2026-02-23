import os
from loca.ui.display import console


class BackupManager:
    """ファイル変更のバックアップを管理し、/undo による取り消しを実現するクラス"""

    def __init__(self):
        # スタック: [(filepath, old_content_or_None), ...]
        # old_content が None → 新規作成されたファイル（undoで削除する）
        self._stack: list[tuple[str, str | None]] = []

    def save(self, filepath: str):
        """ファイル変更前の状態を保存する"""
        abs_path = os.path.abspath(filepath)
        if os.path.exists(abs_path):
            try:
                with open(abs_path, "r", encoding="utf-8") as f:
                    content = f.read()
                self._stack.append((abs_path, content))
            except Exception:
                # バイナリファイル等で読めない場合はスキップ
                pass
        else:
            # 新規作成されるファイル → undo時に削除
            self._stack.append((abs_path, None))

    def undo(self) -> tuple[str, bool]:
        """直前の変更を元に戻す。(メッセージ, 成功したか) を返す"""
        if not self._stack:
            return "取り消せる変更がありません。", False

        filepath, old_content = self._stack.pop()

        try:
            if old_content is None:
                # 新規作成されたファイルを削除
                if os.path.exists(filepath):
                    os.remove(filepath)
                    return f"🗑️ 新規作成されたファイルを削除しました: {filepath}", True
                else:
                    return f"ファイルは既に存在しません: {filepath}", False
            else:
                # 元の内容に復元
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(old_content)
                return f"⏪ ファイルを元に戻しました: {filepath}", True
        except Exception as e:
            return f"Undo に失敗しました: {e}", False

    def has_backups(self) -> bool:
        return len(self._stack) > 0

    @property
    def count(self) -> int:
        return len(self._stack)
