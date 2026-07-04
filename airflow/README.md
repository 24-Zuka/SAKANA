# airflow

AirFlow のオーケストレーション＆データ層。仕様書「AirFlow AI自動化タスクボード
完全版仕様書 v1.0」に基づく。デスクトップUI層は `../jarvis-cockpit/` を参照。
安全ゲートは `../dcg/`（Rust）＋ `src/airflow/guard.py`（Python統合）。

macOS実機（Tauri/Keychain/launchctl等）を前提にした仕様書との残差分は
`../docs/DEVIATIONS.md` を参照。

## セットアップ

```bash
uv venv .venv
uv pip install -e ".[dev]" --python .venv/bin/python
```

## テスト

```bash
.venv/bin/pytest
```

## CLI（airflowctl）

```bash
AIRFLOW_HOME=~/.airflow .venv/bin/airflowctl status
.venv/bin/airflowctl add "A社との提携レート再交渉の方針を決めたい"
.venv/bin/airflowctl run TKT-20260628-001   # Plan→Route→Execute→Verifyのクローズドループ
.venv/bin/airflowctl brief --show
.venv/bin/airflowctl groom                  # 夜間グルーミング（期限切れ整理・Done圧縮・索引再構築）
.venv/bin/airflowctl list --category Business
.venv/bin/airflowctl install-launchd        # launchd登録（darwinのみlaunchctl loadまで実行）
.venv/bin/airflowctl show-bridge-token      # 開発ブリッジのBearerトークンを表示
```

`AIRFLOW_HOME` 環境変数で実データ格納場所を指定できる（既定 `~/.airflow`）。
仕様書はmacOSの `~/Library/Application Support/AirFlow/` を前提にしているが、
本実装はLinux含むクロスプラットフォーム動作のためこのパスに変更している。

## 開発用ブリッジ

`jarvis-cockpit` フロントエンドから実データに接続するためのFastAPI製ブリッジ。
**spec §12.2 の本来のRust/axum製 `jarvis-bridge`（SSE配信）ではない**が、
Bearer認証・`AirflowApi`の全メソッド・承認ゲート・isolated demo-repo経由の
git操作など、実運用に必要な機能は一通り実装している。

```bash
AIRFLOW_HOME=~/.airflow .venv/bin/uvicorn airflow.bridge:app --port 8787
```

初回起動時にBearerトークンを自動生成しKeychain（darwin）/`secrets.json`
（他OS）へ保存するが、値は標準出力・ログには一切出力しない
（Credential Materialization対策）。値を確認するには:

```bash
.venv/bin/airflowctl show-bridge-token
```

を自分の端末で実行し、Cockpitの設定画面（bridgeUrl/bridgeToken）に貼り付ける。
`/health` のみ無認証、他の全エンドポイントはBearerトークン必須。
