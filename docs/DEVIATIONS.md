# 仕様書からの逸脱・見送り項目

本実装は「AirFlow AI自動化タスクボード 完全版仕様書 v1.0」のMVPスコープ
（§14）を、macOS実機ではなくLinuxクラウドコンテナ上で実装したもの。
この文書は、仕様書との差分・見送った項目を正直に記録する（P7「静かに壊れない」）。

## 環境差分

| 項目 | 仕様書 | 本実装 |
|---|---|---|
| 実データパス（§4.2） | `~/Library/Application Support/AirFlow/`（macOS） | `~/.airflow`（`AIRFLOW_HOME`で上書き可）。`airflow/src/airflow/config.py`参照 |
| デスクトップUI（§7.1/§12.2） | Tauri 2（Rustコア＋WebView）による`.app`/`.dmg` | 未実装。`jarvis-cockpit/`はVite開発サーバーで動作するWebアプリとして実装 |
| ブリッジ（§7.1/§12.2） | Rust + axum + tokio-stream（SSE）、`127.0.0.1`専用 | 一時的な FastAPI dev bridge（`airflow/src/airflow/bridge.py`）。認証なし・SSEなし。**本番/公開環境では使用不可** |
| 安全ゲート dcg（§8.2） | Rust製・同梱の破壊的コマンド改札 | 未実装。dcgに相当する保護は本実装のどのコマンド実行経路にも存在しない |
| Codex/Gemini CLI連携（§6.1/§6.3） | `codex exec` / `gemini` をsubprocess起動、ログイン認証必須 | スタブのみ（`airflow/src/airflow/adapters/codex_cli.py` / `gemini_cli.py`）。CLI不在時に`AdapterUnavailable`を返すのみで実処理は未検証 |
| launchd自動化（§10） | `~/Library/LaunchAgents/`にユーザー領域登録 | 未実装。`airflowctl install-launchd`/`uninstall-launchd`は「未対応」と表示するのみのスタブ |
| macOS Keychain（§8.4） | トークンはKeychainのみ・平文非表示 | 未実装。Settings画面のブリッジトークン等は現状フロントエンドのメモリ内state止まり（永続化・暗号化なし）。実装時はOS依存の安全なストレージに置き換えること |
| Obsidian連携（§7.3/§9.3） | Local REST API `:27123`（Bearer）でvault読み書き | 未実装。`obsidian_connected`は常に`false`を返す |
| olmOCRアダプタ（§6.4） | ローカルVLM OCRでPDF/画像読取 | 未実装 |
| SQLite索引（§4.5） | 検索高速化用の任意派生索引 | 未実装（正データのMarkdownのみで運用） |
| Apache Airflow 3.0 + MCP（§17） | 将来オプション（20台超運用時のみ） | 未着手（意図的に対象外） |

## 実装したもの（MVPスコープ、§14準拠）

- `airflow/` Pythonパッケージ: TaskCard CRUD（Markdown+YAML）、risk_score算出（§4.6を正確に実装）、
  AirFlow⇔JARVIS status/priority対応表（§4.4）、LM Studioアダプタ＋ローカル規則フォールバック分類、
  朝礼生成（§9）、`airflowctl` CLI（status/brief/add/import-inbox/list、他はスタブ）。
- `jarvis-cockpit/` フロントエンド: React+TS+Vite+Tailwind v4+Zustand。3トランスポート
  （Tauriスタブ→Bridge→Mockの優先順位、既定はMock）。8画面すべてを実装（深度は画面ごとに異なる。
  Dashboard/Buildはフル、Memoryは読取専用、Agents/Schedule/Research/Quota&Costは軽量実装）。
  ApprovalModal・⌘Kコマンドパレットは横断機能として実装。

## デザイン準拠について

初回実装時は claude.ai/design のURLが本環境から取得不能だったため、仕様書 §7.4 の文章記述のみを
根拠にUIを実装した。その後、ユーザーから正式なデザイン仕様書HTML（AirFlow Design Spec v1.0）が
アップロードされ、そこに明記された正確なカラートークン（#0E1116/#141922/#4EA1FF等）・タイポグラフィ
（Space Grotesk/IBM Plex Sans/IBM Plex Mono）・コンポーネント寸法（ヘルスピル30px・バッジradius5px・
トグル38×22px等）・レイアウト（サイドバー236px・管制/運用2グループ・ウィンドウ幅1280px）に
正確に準拠するようリスタイルした。`jarvis-cockpit/src/index.css` の `@theme` と
`components/common/{Card,Button,CategoryBadge,Toggle}.tsx` がその実装。
なお本環境はGoogle Fontsサーバーに到達できないため、指定フォントは読み込み失敗時に
システムフォントへ自動フォールバックする（`<link>`タグ自体は正しく設置済み）。

## 続行作業（macOS実機セッション向け）

1. `src-tauri/`（Rust + Tauri 2）を追加し、`jarvis-cockpit`のフロントエンドをネイティブ化する。
2. `jarvis-bridge`をRust/axumで実装し、`bridge.py`を置き換える（tokio-stream SSEでイベント配信）。
3. dcg（Destructive Command Guard）をRustで実装し、Codex/git/launchctl等の起動前段に挟む。
4. `adapters/codex_cli.py` / `gemini_cli.py` を実際のCLIに対して検証する。
5. launchd plist生成・登録処理を実装し、`airflowctl install-launchd`を実処理化する。
6. macOS Keychainへのトークン保存（`security`コマンド経由）を実装する。
7. Obsidian Local REST APIとの連携（vault_read/write/delete、heading単位PATCH）を実装する。
