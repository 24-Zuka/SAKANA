# airflow

AirFlow のオーケストレーション＆データ層（MVP実装）。仕様書「AirFlow AI自動化タスクボード
完全版仕様書 v1.0」に基づく。デスクトップUI層は `../jarvis-cockpit/` を参照。

macOS実機を前提にした仕様書との差分は `../docs/DEVIATIONS.md` を参照。

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
.venv/bin/airflowctl brief --show
.venv/bin/airflowctl list --category Business
```

`AIRFLOW_HOME` 環境変数で実データ格納場所を指定できる（既定 `~/.airflow`）。
仕様書はmacOSの `~/Library/Application Support/AirFlow/` を前提にしているが、
本実装はLinux含むクロスプラットフォーム動作のためこのパスに変更している。

## 開発用ブリッジ（一時的・非公式）

`jarvis-cockpit` フロントエンドから実データに接続して動作確認するための、
最小限・一時的なFastAPI製ブリッジ。**spec §12.2 の本来のRust/axum製
`jarvis-bridge` ではない。** 認証なし・localhost開発専用。

```bash
AIRFLOW_HOME=~/.airflow .venv/bin/uvicorn airflow.bridge:app --port 8787
```
