# 仕様書からの逸脱・見送り項目

本実装は「AirFlow AI自動化タスクボード 完全版仕様書 v1.0」を、macOS実機ではなく
Linuxクラウドコンテナ上で実装したもの。この文書は、仕様書との差分・見送った項目を
正直に記録する（P7「静かに壊れない」）。

このリポジトリには cargo/rustc が使えるため、§8.2の安全ゲート dcg は
**Rustで本実装**し、`cargo test` で受け入れ基準（§15.3）を検証している。
Codex/Gemini CLI・LM Studio・Obsidian Local REST API・macOS launchd/Keychainは
この環境に実体が無いため、**統合コードは完全に書き上げた上で**、フェイクバイナリ・
httpxモック・環境変数によるパス差し替えでテスト可能な範囲を検証している
（下表参照）。

## 環境差分

| 項目 | 仕様書 | 本実装 |
|---|---|---|
| 実データパス（§4.2） | `~/Library/Application Support/AirFlow/`（macOS） | `~/.airflow`（`AIRFLOW_HOME`で上書き可）。`airflow/src/airflow/config.py`参照 |
| デスクトップUI（§7.1/§12.2） | Tauri 2（Rustコア＋WebView）による`.app`/`.dmg` | 未実装。`jarvis-cockpit/`はVite開発サーバー/静的ビルドで動作するWebアプリとして実装。`src-tauri/`は未着手 |
| ブリッジ（§7.1/§12.2） | Rust + axum + tokio-stream（SSE）、`127.0.0.1`専用 | FastAPI製 `airflow/src/airflow/bridge.py`。Bearer認証・`AirflowApi`全メソッドを実装済みだが、SSEでのプッシュ配信は無い（ポーリング相当）。**Rust/axum化はFastAPI版が既にフル機能で稼働しているため優先度低** |
| 安全ゲート dcg（§8.2） | Rust製・同梱の破壊的コマンド改札 | `dcg/`（Rust, cargo test 13件）＋ `airflow/src/airflow/guard.py`（Python統合・dcgバイナリが無い場合の内蔵ルールへのP7縮退）。エンジン/ブリッジの全subprocess起動はこれ経由（allowlist: codex/gemini/git/launchctl/security） |
| Codex/Gemini CLI連携（§6.1/§6.3） | `codex exec` / `gemini` をsubprocess起動、ログイン認証必須 | 統合コード（JSONL逐次パース・timeout/retry・APIキー検出時の実行拒否）は完成。この環境に実CLIが無いため、PATH上のフェイクスクリプトによる統合テスト（`test_codex_cli.py`/`test_gemini_cli.py`）で検証。**実機での`codex login`/`gemini`ログイン後の最終確認は未検証** |
| LM Studio連携（§6.2） | `http://localhost:1234/v1`（OpenAI互換）へHTTP | 実装済み（classify/summarize/verify/list_models/run）。この環境にLM Studio実体が無いため、実サーバーへの疎通は未検証（`AdapterUnavailable`フォールバック経路はテスト済み） |
| launchd自動化（§10） | `~/Library/LaunchAgents/`にユーザー領域登録・`launchctl load/unload` | plist生成・登録・有効/無効切替・ブリッジ経由の手動実行・ログ管理まで実装。`launchctl load/unload`自体は`sys.platform=="darwin"`でゲートしており、非macOSでは実行しない（正直に「未対応」と表示）。**実機でのlaunchctl動作確認は未検証** |
| macOS Keychain（§8.4） | トークンはKeychainのみ・平文非表示 | `airflow/src/airflow/secrets.py`: darwinでは`security`コマンド経由（フェイクバイナリでラッパーをテスト）、非macOSでは`<home>/secrets.json`（0600・平文である旨をコード上明記）に縮退。ブリッジのBearerトークンもこの経路で保存し、値は標準出力・ログに一切出力しない |
| Obsidian連携（§7.3/§9.3/§4.7） | Local REST API `:27123`（Bearer）でvault読み書き | `obsidian.py`: read/write/heading単位PATCH/削除（ゴミ箱経由）/検索、`AI_HANDOFF_ANCHOR`非破壊追記、朝礼のマーカー付き書き出し（§9.3）まで実装。httpx MockTransportで契約を検証。この環境に実サーバーが無いため実接続は未検証 |
| SQLite索引（§4.5） | 検索高速化用の任意派生索引 | `store/index.py`で実装済み。`groom`実行時に`tickets/*.md`から再構築される |
| olmOCRアダプタ（§6.4） | ローカルVLM OCRでPDF/画像読取 | 未実装（対象外のまま） |
| Apache Airflow 3.0 + MCP（§17） | 将来オプション（20台超運用時のみ） | 未着手（意図的に対象外） |

## 実装したもの

- `airflow/` Pythonパッケージ: TaskCard CRUD（Markdown+YAML）、risk_score算出（§4.6）、
  ステータス遷移図バリデーション（§4.4）、Budget Guard（§5.3・5時間ローリングウィンドウ）、
  Router（§5.2・コスト優先ルーティング）、Plan→Route→Execute→Verifyのクローズドループ
  （§5.1、`airflowctl run`/ブリッジ`/tickets/{id}/run`）、朝礼生成（§9）・夜間グルーミング
  （§10）、`airflowctl` CLI（status/brief/add/import-inbox/watch-inbox/list/run/groom/
  configure-obsidian/install-launchd/uninstall-launchd/show-bridge-token）。
- `dcg/`（Rust）+ `guard.py`（Python統合）: 3段解析の破壊的コマンド改札。
- `bridge.py`: Bearer認証付きFastAPI。ticket CRUD/状態遷移（承認ゲート含む）/実行ループ起動/
  agents/worktrees（isolated demo-repo経由）/build・review・diff・merge/launchd管理/quota/
  settings/Obsidian vaultパススルー。
- `jarvis-cockpit/` フロントエンド: React+TS+Vite+Tailwind v4+Zustand。3トランスポート
  （Tauriスタブ→Bridge→Mock、既定Mock、bridgeUrl/tokenはSettings画面から実行時切替可能）。
  8画面すべて実装。DashboardはチケットのステータスUI操作・実行ボタン（bridge接続時のみ活性）を
  持つ。ApprovalModal（risk_score>=3.0で必須）・⌘Kコマンドパレットは横断機能。
- テスト: pytest 190件、cargo test 13件、tsc型チェック、Playwright 16件
  （8画面スモーク・承認フロー・ステータス遷移・設定永続化を含む）。

## デザイン準拠について

claude.ai/design のURLに加えてユーザーから正式なデザイン仕様書HTML（AirFlow Design
Spec v1.0）が提供され、そこに明記された正確なカラートークン（#0E1116/#141922/#4EA1FF等）・
タイポグラフィ（Space Grotesk/IBM Plex Sans/IBM Plex Mono）・コンポーネント寸法
（ヘルスピル30px・バッジradius5px・トグル38×22px等）・レイアウト（サイドバー236px・
管制/運用2グループ・ウィンドウ幅1280px）に準拠してリスタイルした。
`jarvis-cockpit/src/index.css` の `@theme` と
`components/common/{Card,Button,CategoryBadge,Toggle}.tsx` がその実装。
本環境はGoogle Fontsサーバーに到達できないため、指定フォントは読み込み失敗時に
システムフォントへ自動フォールバックする（`<link>`タグ自体は正しく設置済み）。

## 続行作業（macOS実機セッション向け）

1. `src-tauri/`（Rust + Tauri 2）を追加し、`jarvis-cockpit`のフロントエンドをネイティブ化する。
2. 実機で `codex login` / `gemini` ログインを済ませ、`adapters/codex_cli.py` /
   `gemini_cli.py` の実CLI連携を最終確認する。
3. LM Studioを起動し、`LMStudioAdapter` の実サーバー疎通を確認する。
4. Obsidian Local REST APIプラグインを有効化し、`ObsidianClient` の実接続・
   `AI_HANDOFF_ANCHOR`追記・朝礼書き出しを確認する。
5. `airflowctl install-launchd` を実行し、`launchctl load` 後の実ジョブ発火を確認する。
6. Bearerトークン等のKeychain保存（`security`コマンド経由）を実機で確認する。
7. （優先度低）`jarvis-bridge`をRust/axum + tokio-stream SSEで実装し、`bridge.py`を置き換える。
