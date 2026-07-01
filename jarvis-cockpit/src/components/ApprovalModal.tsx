// 承認モーダル — デザイン仕様書 §07/spec §8.3。risk_score>=3.0 または要承認操作で必須表示。
// 対象・検証結果・レビュー件数を明示する。Approve / Feedback(差し戻し) / Reject の3択。

import { useAppStore } from "../store/useAppStore";
import { GhostButton, PrimaryButton } from "./common/Button";

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
      <div className="w-full max-w-md rounded-[13px] border border-jarvis-line bg-jarvis-panel p-6 shadow-xl">
        <span className="inline-flex items-center rounded-[5px] bg-jarvis-yellow/12 px-2 py-0.5 text-[11px] font-semibold text-jarvis-yellow">
          承認モーダル · HITL
        </span>
        <h2 id="approval-modal-title" className="mt-3 font-display text-base font-semibold text-jarvis-text">
          {approvalRequest.title}
        </h2>
        <p className="mt-1 text-sm text-jarvis-text2">{approvalRequest.description}</p>

        {(approvalRequest.riskScore !== undefined || approvalRequest.details) && (
          <dl className="mt-3 flex flex-col gap-1 border-t border-jarvis-linesoft pt-3">
            {approvalRequest.riskScore !== undefined && (
              <div className="flex justify-between text-xs">
                <dt className="text-jarvis-text3">risk_score</dt>
                <dd className="font-mono text-jarvis-yellow">{approvalRequest.riskScore.toFixed(1)}</dd>
              </div>
            )}
            {approvalRequest.details?.map((d) => (
              <div key={d.label} className="flex justify-between text-xs">
                <dt className="text-jarvis-text3">{d.label}</dt>
                <dd className="font-mono text-jarvis-text2">{d.value}</dd>
              </div>
            ))}
          </dl>
        )}

        <div className="mt-6 flex justify-end gap-2">
          <GhostButton onClick={() => resolveApproval(false)}>Reject</GhostButton>
          <GhostButton
            onClick={() => resolveApproval(false)}
            className="border-jarvis-yellow/40 text-jarvis-yellow hover:bg-jarvis-yellow/10"
          >
            Feedback
          </GhostButton>
          <PrimaryButton onClick={() => resolveApproval(true)} autoFocus>
            Approve
          </PrimaryButton>
        </div>
      </div>
    </div>
  );
}
