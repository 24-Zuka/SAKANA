import type { Status } from "../../types/taskcard";

const STATUS_STYLES: Record<Status, string> = {
  Inbox: "bg-jarvis-surface-raised text-jarvis-text-muted border-jarvis-border",
  Today: "bg-jarvis-accent-dim/30 text-jarvis-accent border-jarvis-accent-dim",
  Doing: "bg-jarvis-warning/15 text-jarvis-warning border-jarvis-warning/40",
  Waiting: "bg-jarvis-danger/15 text-jarvis-danger border-jarvis-danger/40",
  Done: "bg-jarvis-success/15 text-jarvis-success border-jarvis-success/40",
};

export function StatusBadge({ status }: { status: Status }) {
  return (
    <span
      className={`inline-flex items-center rounded border px-2 py-0.5 text-xs font-mono ${STATUS_STYLES[status]}`}
    >
      {status}
    </span>
  );
}
