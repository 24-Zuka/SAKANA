# jarvis-cockpit

AirFlow のUI層「JARVIS Cockpit」。React + TypeScript + Vite +
Tailwind CSS v4 + Zustand。仕様書 §7 に基づく8画面すべてを実装しているが、
画面ごとの深度は異なる（下記参照）。

macOS実機を前提にした仕様書（Tauriデスクトップ化・Rust製ブリッジ等）との
差分は `../docs/DEVIATIONS.md` を参照。

## セットアップ・起動

```bash
npm install
npm run dev       # http://localhost:5173、既定でMockトランスポート
```

## トランスポート（3経路・優先順位 Tauri → Bridge → Mock）

- **Mock（既定）**: `src/lib/browserMock.ts`。実依存不要、常に動作する。
- **Bridge**: `../airflow/` のFastAPI dev bridge（`uvicorn airflow.bridge:app --port 8787`）に接続し、
  `AirflowApi` の全メソッドをBearer認証付きで実処理する。接続先はビルド時の
  `VITE_BRIDGE_URL` 環境変数、または実行時にSettings画面へ入力した
  bridgeUrl/bridgeToken（`localStorage`永続化）のどちらでも設定できる —
  後者は**リビルド・リロード不要**で反映されるため、GitHub Pages公開版から
  ローカルのbridgeへ接続することもできる。トークンは
  `.venv/bin/airflowctl show-bridge-token` で確認する。
- **Tauri**: 型のみのスタブ（`src/lib/tauriTransport.ts`）。デスクトップ化は未着手。

## 画面の実装深度（§7.2の8画面）

Dashboard・Build はフル実装（Dashboardはstatus遷移・実行ボタンを含む）、
Memory は読取専用、Agents/Schedule/Research/Quota&Cost は軽量実装。
詳細は `../docs/DEVIATIONS.md` を参照。

## テスト

```bash
npx tsc -b        # 型チェック
npm run build     # ビルド確認
npx playwright test   # 8画面のスモークテスト・Build承認フロー・⌘Kパレット
```
