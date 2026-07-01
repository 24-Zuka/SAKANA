import { useEffect, useState } from "react";
import { api } from "../../lib/api";
import type { QuotaStatus } from "../../types/cockpit";
import type { HealthStatus } from "../../types/taskcard";

// Quota & Cost（コスト管制）— spec §7.2/§8.4。
// 「クレジット購入」はUIに存在させない（無効固定）。APIキー検出時は赤旗。

export function QuotaCost() {
  const [quota, setQuota] = useState<QuotaStatus | null>(null);
  const [health, setHealth] = useState<HealthStatus | null>(null);

  useEffect(() => {
    api.getQuotaStatus().then(setQuota).catch(() => undefined);
    api.health().then(setHealth).catch(() => undefined);
  }, []);

  const redFlags = health?.api_key_red_flag ?? [];

  return (
    <div className="flex flex-col gap-4">
      <h1 className="text-lg font-semibold">Quota & Cost（コスト管制）</h1>

      {redFlags.length > 0 && (
        <div className="rounded-lg border border-jarvis-danger/40 bg-jarvis-danger/10 p-4 text-sm text-jarvis-danger">
          🚩 赤旗: APIキー環境変数が検出されました（{redFlags.join(", ")}）。従量課金が発生する可能性があります。
          サブスクログインに切り替えてください。
        </div>
      )}
      {redFlags.length === 0 && health && (
        <div className="rounded-lg border border-jarvis-success/40 bg-jarvis-success/10 p-4 text-sm text-jarvis-success">
          APIキー環境変数は検出されていません（課金ゼロ規律を維持）。
        </div>
      )}

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <section className="rounded-lg border border-jarvis-border bg-jarvis-surface p-4">
          <h2 className="text-sm font-semibold text-jarvis-text-muted">5hウィンドウ使用率（Codex）</h2>
          <p className="mt-2 font-mono text-2xl text-jarvis-text-muted">
            {quota?.codexWindowUsedPct ?? "不明"}
          </p>
        </section>
        <section className="rounded-lg border border-jarvis-border bg-jarvis-surface p-4">
          <h2 className="text-sm font-semibold text-jarvis-text-muted">5hウィンドウ使用率（Gemini）</h2>
          <p className="mt-2 font-mono text-2xl text-jarvis-text-muted">
            {quota?.geminiWindowUsedPct ?? "不明"}
          </p>
        </section>
      </div>

      <section className="rounded-lg border border-jarvis-border bg-jarvis-surface p-4">
        <h2 className="text-sm font-semibold text-jarvis-text-muted">認証経路</h2>
        <p className="mt-2 text-sm">
          ChatGPT: {quota?.authOk ? "✓ ログイン済み" : "未確認"} ／ 退避モード:{" "}
          {quota?.fallbackModeActive ? "ON（LM Studioへダウングレード中）" : "OFF"}
        </p>
      </section>

      <section className="rounded-lg border border-jarvis-border bg-jarvis-surface p-4">
        <h2 className="text-sm font-semibold text-jarvis-text-muted">クレジット購入</h2>
        <button
          type="button"
          disabled
          className="mt-2 cursor-not-allowed rounded border border-jarvis-border px-3 py-1.5 text-sm text-jarvis-text-muted opacity-50"
        >
          無効（このアプリはサブスク＋ローカルのみ。課金導線は意図的に存在しません）
        </button>
      </section>
    </div>
  );
}
