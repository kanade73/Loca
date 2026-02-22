# 🧠 Loca - Autonomous AI Coding Assistant

![Python](https://img.shields.io/badge/Python-3.12%2B-blue)
![uv](https://img.shields.io/badge/Package_Manager-uv-purple)
![Ollama](https://img.shields.io/badge/Local_AI-Ollama-black)
![LiteLLM](https://img.shields.io/badge/Multi_Provider-LiteLLM-green)

**LOCAL AI · FREE · YOURS**

Loca（ロカ）は、あなたのローカル環境で自律的に思考し、コードを書き、共に成長するCLI型のAIコーディングエージェントです。

---
## フォルダ構成
```
Loca/
├── src/loca/
│   ├── core/         # AIの脳 (LLMクライアント, プロンプト管理, 記憶システム, Proモード制御)
│   ├── tools/        # AIの手足 (ファイル操作, コマンド実行, Web検索, Git操作)
│   ├── ui/           # AIの顔 (ターミナル描画, ヘッダー表示)
│   └── main.py       # エントリーポイント・ルーティング
├── pyproject.toml    # 依存関係とCLIコマンド定義
└── loca_rules.md     # Locaの記憶（動的に更新されるマークダウン）
```


## 🛠️ インストール (Installation)
パッケージマネージャーuvを使用してダウンロードします。
```bash
# リポジトリのクローン
git clone [https://github.com/あなたのユーザー名/Loca.git](https://github.com/あなたのユーザー名/Loca.git)
cd Loca

# 依存関係のインストールとCLIコマンドの登録
uv pip install -e .

# 起動
loca
```

## 💻 コマンド一覧 (Commands)
Loca起動後、プロンプトに対して自然言語で指示を出すか、以下の専用コマンドを使用できます。

| コマンド           | 説明                                                                                       |
|--------------------|------------------------------------------------------------------------------------------|
| 自然言語           | AIが自律的に思考し、ファイル操作やコマンド実行などのアクションを起こします。               |
| /ask <質問>        | アクション（ファイル操作等）を伴わず、純粋にAIの知識のみを引き出して爆速で回答を得るモード。必要に応じて自律的にWeb検索を行います。 |
| /pro <タスク>      | EditorとReviewerの2つのAIによる合議制で、高品質なコードやプロジェクト構成を生成します。   |
| /auto              | AIの行動に対するユーザーの承認（y/N）をスキップし、完全自律モードに切り替えます。         |
| /commit            | Gitの差分を解析し、最適なコミットメッセージを自動生成してコミットします。                 |
| /remember <ルール>     | Locaにプロジェクトのルールやあなたの好みを記憶させます。                                   |
| /rules             | 現在記憶しているルールを一覧表示します。                                                     |
| /forget <番号>     | 特定のルールを削除します。                                                                   |

## ✨ 強みとコア機能 (Key Features)

### 1. 🤝 透過的で操作可能な記憶システム (Transparent Memory System)
クラウドAPIの不透明な「メモリ機能」に依存せず、記憶をローカルのマークダウンファイル（`loca_rules.md`）として管理します。
ユーザーはコマンド一つでAIに「掟」を教え込み、不要になったら忘れさせることができます。使えば使うほど、**「あなた専用の右腕」**へと育ちます。
- `/remember <掟>`: AIに新しいルールを学習させる
- `/rules`: 現在の脳内ルールを一覧表示
- `/forget <番号>`: 特定のルールを削除する

### 2. ⚖️ Pro Mode: AI同士の合議制アーキテクチャ (Multi-Agent Debate)
複雑なタスクには `/pro` モードが威力を発揮します。
「コードを生成するEditor AI」と「それを厳格に審査するReviewer AI」の2つのエージェントが内部で議論し、Reviewerが「承認（Approve）」を出すまで自律的に修正を繰り返すことで、高品質なプロジェクト構造を出力します。

### 3. 🔌 マルチプロバイダー＆ローカルファースト (Facade Pattern)
`LiteLLM`を活用したファサードパターンにより、プロバイダーごとのAPIの差異を完全に吸収しています。
デフォルトではローカルの `Ollama`（完全無料・セキュア）で動作し、必要に応じて引数一つで `OpenAI` や `Anthropic` に脳みそを切り替えることが可能です。
```bash
# ローカルで実行（デフォルト）
$ loca -m qwen2.5-coder:32b

# クラウドAPIで実行
$export OPENAI_API_KEY="sk-..."$ loca -p openai -m gpt-4o
```