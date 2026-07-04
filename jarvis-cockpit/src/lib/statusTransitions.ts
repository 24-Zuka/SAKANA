import type { Status } from "../types/taskcard";

// §4.4 ステータス遷移図の TS ミラー（`airflow.models.ALLOWED_STATUS_TRANSITIONS` と対応）。
export const ALLOWED_STATUS_TRANSITIONS: Record<Status, Status[]> = {
  Inbox: ["Today"],
  Today: ["Doing"],
  Doing: ["Waiting", "Done"],
  Waiting: ["Done"],
  Done: [],
};

export function nextStatusOptions(current: Status): Status[] {
  return ALLOWED_STATUS_TRANSITIONS[current] ?? [];
}

export function isValidStatusTransition(current: Status, target: Status): boolean {
  return current === target || ALLOWED_STATUS_TRANSITIONS[current].includes(target);
}
