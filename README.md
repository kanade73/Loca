# 🧠 Loca - 自律型AIコーディングアシスタント

[![Python](https://img.shields.io/badge/Python-3.12%2B-blue)](https://python.org)
[![uv](https://img.shields.io/badge/Package_Manager-uv-purple)](https://github.com/astral-sh/uv)
[![Ollama](https://img.shields.io/badge/Local_AI-Ollama-black)](https://ollama.com)
[![LiteLLM](https://img.shields.io/badge/Multi_Provider-LiteLLM-green)](https://github.com/BerriAI/litellm)

**🌐 [English](../README.md)**

> 🇺🇸 **Looking for the English version?** This page is in Japanese. [Click here for the English README.](../README.md)

**LOCAL AI · FREE · YOURS**

<img width="867" height="502" alt="スクリーンショット" src="https://github.com/user-attachments/assets/debf4f8a-107d-465a-af38-19e93208ffc1" />

Loca（ロカ）は、ローカルLLMを使って自律的に思考し、コードを書き、使えば使うほどあなた専用に育っていくCLI型のAIコーディングエージェントです。APIキー不要、課金不要。`uv sync` と `loca` だけで動きます。

---

## 🛠️ インストール

### 1. Ollamaのセットアップ

[Ollama](https://ollama.com) をインストールし、デフォルトモデルをダウンロードしてください。

```bash
# Ollamaのインストール（macOS）
brew install ollama

# デフォルトモデルのダウンロード（約4.7GB）
ollama pull qwen2.5-coder:7b
```

### 2. Locaのセットアップ

```bash
git clone https://github.com/kanade73/Loca.git
cd Loca
uv sync
loca
```

これだけで動きます。

### モデルの変更

デフォルトのモデルは `src/loca/config.py` で一元管理されています。

```python
# src/loca/config.py
DEFAULT_MODEL = "qwen2.5-coder:7b"   # ← ここを変更
DEFAULT_PROVIDER = "ollama"
```

別のモデルを使いたい場合は、**pullしてからconfig.pyを書き換える**だけです。

```bash
# 例: より高精度なモデルに変更（VRAM 20GB以上推奨）
ollama pull qwen2.5-coder:32b
# → config.py の DEFAULT_MODEL を "qwen2.5-coder:32b" に変更
```

コマンドラインで一時的に指定することもできます。

```bash
loca -m qwen2.5-coder:32b
```

### クラウドAPIを使う場合

```bash
export OPENAI_API_KEY="sk-..."
loca -p openai -m gpt-4o
```

---

## 💻 コマンド一覧

| コマンド | 説明 |
| --- | --- |
| 自然言語 | AIが自律的に思考し、ファイル操作やコマンド実行などのアクションを起こします |
| `/ask <質問>` | アクションを伴わず、AIの知識を引き出すモード。必要に応じて自律的にWeb検索を行います |
| `/pro <タスク>` | EditorとReviewerの2つのAIによる合議制で、高品質なコードを生成します |
| `/auto` | AIの行動に対するユーザーの承認をスキップし、完全自律モードに切り替えます |
| `/clear` | 会話履歴をリセットし、新しいタスクを開始します |
| `/commit` | Gitの差分を解析し、コミットメッセージを自動生成してコミットします |
| `/remember <ルール>` | Locaにルールやあなたの好みを記憶させます |
| `/rules` | 現在記憶しているルールを一覧表示します |
| `/forget <番号>` | 特定のルールを削除します |
| `/undo` | Locaが行った直前のファイル変更を元に戻します |

---

## ✨ コア機能

### 🛠️ 7つのツール

Locaは以下のツールを自律的に選択し、タスクを遂行します。

| ツール | 説明 |
| --- | --- |
| `run_command` | シェルコマンドの実行（ユーザー確認あり） |
| `read_file` | ファイルの読み込み |
| `write_file` | ファイルの新規作成・全体上書き |
| `edit_file` | ファイルの部分編集（差分置換） |
| `read_directory` | ディレクトリ構造の取得 |
| `web_search` | DuckDuckGoによるWeb検索 |
| `none` | タスク完了の宣言 |

### 🔌 プラグイン

プロジェクトルートに `loca_tools/` ディレクトリを作り、Pythonファイルを置くだけでLocaにカスタムツールを追加できます。起動時に自動でロードされ、AIが使えるアクションとして登録されます。設定ファイルは不要です。

```python
# loca_tools/my_tool.py
TOOL_NAME        = "my_tool"
TOOL_DESCRIPTION = "このツールが何をするか（AIに伝える説明）"
ARGS_FORMAT      = '{"key": "value"}'  # 省略可 — 省略時は {}

def run(args: dict) -> str:
    # 処理を書く
    return "結果の文字列"
```

サンプルとして `loca_tools/get_time.py`（現在日時を返すツール）が同梱されています。

### 🤝 透明な記憶システム

クラウドのブラックボックスな「メモリ機能」と違い、Locaの記憶は `Loca.md` というマークダウンファイルとして手元に存在します。何を覚えているか、何を忘れさせるかをコントロールできます。使えば使うほど、あなた専用の相棒へと育っていきます。

```bash
> /remember Djangoのビューは常にクラスベースで書くこと
🧠 了解。Loca.md に追記しました。

> /rules
> /forget 3
```

### ⚖️ Pro Mode：AI同士の合議制

`/pro` モードでは「コードを生成するEditor AI」と「それを審査するReviewer AI」が内部で議論し、Reviewerが承認するまで自律的に修正を繰り返します。同じモデルでも、役割を分けることで単体より高い精度を引き出します。

### 🔒 安全設計

- **コマンド実行前の確認**: `run_command` や `write_file` は実行前にユーザーの承認を求めます（`/auto` で解除可能）
- **パスの安全装置**: `/etc`, `~/.ssh` 等のシステムディレクトリへの書き込みを自動でブロックします
- **セッション管理**: 1セッション30回のやりとり上限で、コンテキストウィンドウの溢れを防ぎます
- **自動lintチェック**: `write_file` や `edit_file` でPythonファイルを書き込むたびに `ruff` と `py_compile` を自動実行します。エラーが検出された場合は結果をAIに返し、自動修正を促します。

---

## 🌱 Locaを育てる

`Loca.md` に好みやルールを書いておくと、どんなタスクでも最初からその前提で動いてくれます。

```markdown
# Loca.md の例
- パッケージ管理は必ず uv を使うこと
- UIはシンプルでモダンなデザインにすること
- コミットメッセージは日本語で書くこと
```

---

## 📁 フォルダ構成

```
Loca/
├── src/loca/
│   ├── config.py      # デフォルトモデル・プロバイダー、パス管理
│   ├── main.py        # エントリーポイント、メインループ、メッセージ管理
│   ├── core/
│   │   ├── llm_client.py   # LiteLLM経由のLLM通信・JSONパース
│   │   ├── prompts.py      # システムプロンプト・ツール定義
│   │   ├── memory.py       # Loca.mdの読み書き（記憶システム）
│   │   ├── pro_agent.py    # /pro モードのEditor/Reviewerロジック
│   │   ├── router.py       # コマンドルーティング（/ask, /pro, /undo 等）
│   │   └── executor.py     # アクション実行・ユーザー確認フロー
│   ├── tools/
│   │   ├── commander.py    # シェルコマンドの安全な実行
│   │   ├── file_ops.py     # ファイル読み書き・パス安全検証
│   │   ├── git_ops.py      # Gitコミット・差分解析
│   │   ├── web_search.py   # DuckDuckGo検索
│   │   ├── backup.py       # ファイルバックアップ・取り消しシステム
│   │   └── plugin_loader.py # プラグインの動的ロード（loca_tools/）
│   └── ui/
│       ├── display.py      # Rich UIコンポーネント・入力処理
│       └── header.py       # 起動時ヘッダー表示
├── loca_tools/        # カスタムプラグイン置き場（任意）
│   └── get_time.py    # サンプルプラグイン：現在日時を返す
├── pyproject.toml     # 依存関係とCLIコマンド定義
└── Loca.md            # Locaの記憶（あなたが育てるマークダウン）
```

---

## 🔧 技術スタック

| 技術 | 用途 |
| --- | --- |
| [LiteLLM](https://github.com/BerriAI/litellm) | LLM APIの抽象化（Ollama / OpenAI / Anthropic / Gemini を統一的に扱う） |
| [Ollama](https://ollama.com) | ローカルLLMの実行基盤（デフォルト） |
| [Rich](https://github.com/Textualize/rich) | ターミナルUIの描画 |
| [prompt-toolkit](https://github.com/prompt-toolkit/python-prompt-toolkit) | 入力補完・履歴・複数行入力 |
| [ddgs](https://github.com/deedy5/duckduckgo_search) | DuckDuckGo Web検索 |
| [uv](https://github.com/astral-sh/uv) | パッケージ管理 |

---

## ライセンス

MIT
