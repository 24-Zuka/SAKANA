# jarvis-cockpit

AirFlow のUI層「JARVIS Cockpit」（MVP実装）。React + TypeScript + Vite +
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
- **Bridge**: `../airflow/` の一時的なFastAPI dev bridge（`uvicorn airflow.bridge:app --port 8787`）
  に接続。有効化するには起動時に `VITE_BRIDGE_URL=http://127.0.0.1:8787 npm run dev` を指定。
  tickets/brief/health のみ実装済み。それ以外（Build/Agents/Schedule/Quota/Settings）は
  現状 `NotImplementedError` を返す（開発ブリッジのスコープ外）。
- **Tauri**: 型のみのスタブ（`src/lib/tauriTransport.ts`）。デスクトップ化は未着手。

## 画面の実装深度（§7.2の8画面）

Dashboard・Build はフル実装、Memory は読取専用、Agents/Schedule/Research/
Quota&Cost は軽量実装。詳細は `../docs/DEVIATIONS.md` を参照。

## テスト

```bash
npx tsc -b        # 型チェック
npm run build     # ビルド確認
npx playwright test   # 8画面のスモークテスト・Build承認フロー・⌘Kパレット
```
