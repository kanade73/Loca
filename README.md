# my-agent-cli ディレクトリ構成

my-agent-cli/
├── .env                  # 環境変数（APIキーなど）
├── pyproject.toml        # パッケージの依存関係と設定（uv用）
├── README.md             # プロジェクトの説明書
├── requirements.txt      # 依存パッケージ一覧
├── uv.lock               # ロックファイル（手動編集厳禁）
│
└── src/                  # ソースコードのルートディレクトリ
    ├── __init__.py
    ├── config.py         # 実行環境・ディレクトリパスなどの全体設定
    ├── shared_state.json # マルチエージェント間のプロセス間通信（IPC）用ファイル
    │
    ├── core/             # AIの「脳みそ」となるコア機能
    │   ├── llm_client.py # Qwen（Ollama）との通信クライアント
    │   └── prompts.py    # システムプロンプトの定義
    │
    ├── multi/            # マルチエージェント（合議制）用の起動スクリプト
    │   ├── agent_editor.py   # コードを書くエディターAI
    │   ├── agent_reviewer.py # コードを審査するレビュワーAI
    │   └── start_session.py  # お題を投下してセッションを開始する起点
    │
    ├── single/           # 単体エージェント用の起動スクリプト
    │   └── main.py       # ターミナルで対話しながらタスクをこなす汎用エージェント
    │
    ├── tools/            # エージェントが使う「手足」となるツール群
    │   ├── __init__.py
    │   ├── commander.py  # コマンド実行ツール
    │   ├── file_ops.py   # ファイル読み書きツール
    │   └── ipc_manager.py# IPC（プロセス間通信）の管理・安全なファイル書き込み
    │
    └── ui/               # コンソールの見た目や描画に関する機能
        ├── __init__.py
        ├── display.py    # パネルやログの表示（Rich）
        └── header.py     # アプリ起動時のヘッダーロゴ描画