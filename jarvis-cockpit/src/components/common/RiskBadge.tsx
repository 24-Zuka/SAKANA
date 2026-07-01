import { RISK_APPROVAL_THRESHOLD } from "../../types/taskcard";

// デザイン仕様書 §04/§06: risk_score >= 3.0 Red(HIGH・承認必須) / 1.5-2.9 Yellow(MED) / <1.5 Green(LOW)。
function tierStyles(score: number): string {
  if (score >= RISK_APPROVAL_THRESHOLD) return "text-jarvis-red bg-jarvis-red/12";
  if (score >= 1.5) return "text-jarvis-yellow bg-jarvis-yellow/12";
  return "text-jarvis-green bg-jarvis-green/12";
}

export function RiskBadge({ score }: { score: number }) {
  const requiresApproval = score >= RISK_APPROVAL_THRESHOLD;
  return (
    <span
      className={`inline-flex items-center rounded-[5px] px-2 py-0.5 font-mono text-[11px] font-semibold ${tierStyles(score)}`}
      title={requiresApproval ? "承認モーダル必須（risk_score >= 3.0）" : "エージェント単独実行可"}
    >
      {score.toFixed(1)}
    </span>
  );
}
