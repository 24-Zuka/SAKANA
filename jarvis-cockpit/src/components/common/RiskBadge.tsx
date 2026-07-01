import { RISK_APPROVAL_THRESHOLD } from "../../types/taskcard";

export function RiskBadge({ score }: { score: number }) {
  const requiresApproval = score >= RISK_APPROVAL_THRESHOLD;
  return (
    <span
      className={`inline-flex items-center gap-1 rounded border px-2 py-0.5 text-xs font-mono ${
        requiresApproval
          ? "border-jarvis-danger/40 bg-jarvis-danger/15 text-jarvis-danger"
          : "border-jarvis-border bg-jarvis-surface-raised text-jarvis-text-muted"
      }`}
      title={requiresApproval ? "承認モーダル必須（risk_score >= 3.0）" : "エージェント単独実行可"}
    >
      risk {score.toFixed(1)}
      {requiresApproval && <span aria-hidden>⚠</span>}
    </span>
  );
}
