import type { Status } from "../../types/taskcard";

// デザイン仕様書 §04: ステータス・色対応表に厳密準拠。
// Inbox=灰 / Today=Accent / Doing=Green / Waiting=Yellow(要判断) / Done=灰(muted)。
const STATUS_DOT: Record<Status, string> = {
  Inbox: "bg-jarvis-text3",
  Today: "bg-jarvis-accent",
  Doing: "bg-jarvis-green",
  Waiting: "bg-jarvis-yellow",
  Done: "bg-jarvis-text3",
};

export function StatusBadge({ status }: { status: Status }) {
  return (
    <span className="inline-flex items-center gap-1.5 text-xs text-jarvis-text2">
      <span className={`h-2 w-2 rounded-full ${STATUS_DOT[status]}`} aria-hidden />
      {status}
      {status === "Waiting" && (
        <span className="inline-flex items-center rounded-[5px] bg-jarvis-yellow/12 px-2 py-0.5 text-[11px] font-semibold text-jarvis-yellow">
          要判断
        </span>
      )}
    </span>
  );
}
