# 🧠 Loca - Autonomous AI Coding Assistant

[![Python](https://img.shields.io/badge/Python-3.12%2B-blue)](https://python.org)
[![uv](https://img.shields.io/badge/Package_Manager-uv-purple)](https://github.com/astral-sh/uv)
[![Ollama](https://img.shields.io/badge/Local_AI-Ollama-black)](https://ollama.com)
[![LiteLLM](https://img.shields.io/badge/Multi_Provider-LiteLLM-green)](https://github.com/BerriAI/litellm)

**LOCAL AI · FREE · YOURS**

> I couldn't afford Claude Code. So I built my own.

<img width="867" height="502" alt="スクリーンショット 2026-02-22 11 26 13" src="https://github.com/user-attachments/assets/debf4f8a-107d-465a-af38-19e93208ffc1" />

Loca（ロカ）は、ローカルLLMを使って自律的に思考し、コードを書き、使えば使うほどあなた専用に育っていくCLI型のAIコーディングエージェントです。APIキー不要、課金不要。`uv sync` と `loca` だけで動きます。

---

## 🛠️ インストール

```bash
git clone https://github.com/kanade73/Loca.git
cd Loca
uv sync
loca
```

これだけです。

---

## 💻 コマンド一覧

| コマンド | 説明 |
| --- | --- |
| 自然言語 | AIが自律的に思考し、ファイル操作やコマンド実行などのアクションを起こします |
| `/ask <質問>` | アクションを伴わず、AIの知識を引き出すモード。必要に応じて自律的にWeb検索を行います |
| `/pro <タスク>` | EditorとReviewerの2つのAIによる合議制で、高品質なコードを生成します |
| `/auto` | AIの行動に対するユーザーの承認をスキップし、完全自律モードに切り替えます |
| `/commit` | Gitの差分を解析し、コミットメッセージを自動生成してコミットします |
| `/remember <ルール>` | Locaにルールやあなたの好みを記憶させます |
| `/rules` | 現在記憶しているルールを一覧表示します |
| `/forget <番号>` | 特定のルールを削除します |

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

### 🤝 透明な記憶システム

クラウドのブラックボックスな「メモリ機能」と違い、Locaの記憶は `Loca.md` というマークダウンファイルとして手元に存在します。何を覚えているか、何を忘れさせるかを完全にコントロールできます。使えば使うほど、あなた専用の相棒へと育っていきます。

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

### 🔌 ローカルファースト、でもクラウドにも対応

デフォルトはローカルの `Ollama` で完全無料・完全プライベートに動作します。必要なときだけ引数一つでクラウドAPIに切り替えられます。

```bash
# ローカルで実行（デフォルト・無料）
loca

# モデルを指定して実行
loca -m qwen2.5-coder:32b

# クラウドAPIで実行
export OPENAI_API_KEY="sk-..."
loca -p openai -m gpt-4o
```

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
│   ├── config.py      # プロジェクトルートの解決、Loca.mdのパス管理
│   ├── main.py        # エントリーポイント、コマンドルーティング、メッセージ管理
│   ├── core/
│   │   ├── llm_client.py   # LiteLLM経由のLLM通信・JSONパース
│   │   ├── prompts.py      # システムプロンプト・ツール定義
│   │   ├── memory.py       # Loca.mdの読み書き（記憶システム）
│   │   └── pro_agent.py    # /pro モードのEditor/Reviewerロジック
│   ├── tools/
│   │   ├── commander.py    # シェルコマンドの安全な実行
│   │   ├── file_ops.py     # ファイル読み書き・パス安全検証
│   │   ├── git_ops.py      # Gitコミット・差分解析
│   │   └── web_search.py   # DuckDuckGo検索
│   └── ui/
│       ├── display.py      # Rich UIコンポーネント・入力処理
│       └── header.py       # 起動時ヘッダー表示
├── pyproject.toml     # 依存関係とCLIコマンド定義
└── Loca.md      # Locaの記憶（あなたが育てるマークダウン）
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
