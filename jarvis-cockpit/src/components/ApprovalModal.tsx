// 承認モーダル — spec §8.3。risk_score>=3.0 または要承認操作で必須表示。
// Approve / Feedback(差し戻し) / Reject の3択。

import { useAppStore } from "../store/useAppStore";

export function ApprovalModal() {
  const approvalRequest = useAppStore((s) => s.approvalRequest);
  const resolveApproval = useAppStore((s) => s.resolveApproval);

  if (!approvalRequest) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="approval-modal-title"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4"
    >
      <div className="w-full max-w-md rounded-lg border border-jarvis-border bg-jarvis-surface p-6 shadow-xl">
        <h2 id="approval-modal-title" className="text-base font-semibold text-jarvis-text">
          承認が必要です
        </h2>
        <p className="mt-2 text-sm text-jarvis-text">{approvalRequest.title}</p>
        <p className="mt-1 text-sm text-jarvis-text-muted">{approvalRequest.description}</p>
        {approvalRequest.riskScore !== undefined && (
          <p className="mt-2 font-mono text-xs text-jarvis-warning">
            risk_score: {approvalRequest.riskScore.toFixed(1)}
          </p>
        )}
        <div className="mt-6 flex justify-end gap-2">
          <button
            type="button"
            onClick={() => resolveApproval(false)}
            className="rounded border border-jarvis-border px-3 py-1.5 text-sm text-jarvis-text-muted hover:bg-jarvis-surface-raised"
          >
            Reject
          </button>
          <button
            type="button"
            onClick={() => resolveApproval(false)}
            className="rounded border border-jarvis-warning/40 px-3 py-1.5 text-sm text-jarvis-warning hover:bg-jarvis-warning/10"
          >
            Feedback
          </button>
          <button
            type="button"
            onClick={() => resolveApproval(true)}
            autoFocus
            className="rounded bg-jarvis-accent px-3 py-1.5 text-sm font-medium text-jarvis-bg hover:opacity-90"
          >
            Approve
          </button>
        </div>
      </div>
    </div>
  );
}
