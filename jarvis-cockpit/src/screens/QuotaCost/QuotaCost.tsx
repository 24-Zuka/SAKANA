import { useEffect, useState } from "react";
import { api } from "../../lib/api";
import type { QuotaStatus } from "../../types/cockpit";
import type { HealthStatus } from "../../types/taskcard";
import { Card, CardHeading } from "../../components/common/Card";

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
      <h1 className="font-display text-2xl font-bold">Quota &amp; Cost コスト管制</h1>

      {redFlags.length > 0 && (
        <div className="rounded-[13px] border border-jarvis-red/40 bg-jarvis-red/10 p-4 text-sm text-jarvis-red">
          🚩 赤旗: APIキー環境変数が検出されました（{redFlags.join(", ")}）。従量課金が発生する可能性があります。
          サブスクログインに切り替えてください。
        </div>
      )}
      {redFlags.length === 0 && health && (
        <div className="rounded-[13px] border border-jarvis-green/40 bg-jarvis-green/10 p-4 text-sm text-jarvis-green">
          APIキー環境変数は検出されていません（課金ゼロ規律を維持）。
        </div>
      )}

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <Card>
          <CardHeading>5hウィンドウ使用率（Codex）</CardHeading>
          <p className="mt-2 font-display text-2xl font-bold text-jarvis-text2">
            {quota?.codexWindowUsedPct ?? "不明"}
          </p>
        </Card>
        <Card>
          <CardHeading>5hウィンドウ使用率（Gemini）</CardHeading>
          <p className="mt-2 font-display text-2xl font-bold text-jarvis-text2">
            {quota?.geminiWindowUsedPct ?? "不明"}
          </p>
        </Card>
      </div>

      <Card>
        <CardHeading>認証経路</CardHeading>
        <p className="mt-2 text-sm">
          ChatGPT: {quota?.authOk ? "✓ ログイン済み" : "未確認"} ／ 退避モード:{" "}
          {quota?.fallbackModeActive ? "ON（LM Studioへダウングレード中）" : "OFF"}
        </p>
      </Card>

      <Card>
        <CardHeading>クレジット購入</CardHeading>
        <button
          type="button"
          disabled
          className="mt-2 cursor-not-allowed rounded-lg border border-jarvis-line px-3 py-1.5 text-sm text-jarvis-text3 opacity-50"
        >
          無効（このアプリはサブスク＋ローカルのみ。課金導線は意図的に存在しません）
        </button>
      </Card>
    </div>
  );
}
