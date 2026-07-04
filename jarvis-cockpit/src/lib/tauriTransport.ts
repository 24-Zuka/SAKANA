// Tauri トランスポート — spec §7.1。
//
// STUB: 本セッションは Tauri 2 のRustツールチェーン/デスクトップビルドを
// 実機検証できない環境のため、`invoke` 呼び出しの型だけ用意し、実処理は
// 全て NotImplementedError を投げる。macOS実機での続行作業を想定した土台。
// （docs/DEVIATIONS.md 参照）

import type { AirflowApi } from "./apiTypes";
import { NotImplementedError } from "./apiTypes";

declare global {
  interface Window {
    __TAURI__?: unknown;
  }
}

export function isTauriEnvironment(): boolean {
  return typeof window !== "undefined" && window.__TAURI__ !== undefined;
}

function notImplemented(method: string): never {
  throw new NotImplementedError("tauri", method);
}

export const tauriTransport: AirflowApi = {
  transportName: "tauri",
  health: async () => notImplemented("health"),
  listTickets: async () => notImplemented("listTickets"),
  getTicket: async () => notImplemented("getTicket"),
  createTicket: async () => notImplemented("createTicket"),
  updateTicketStatus: async () => notImplemented("updateTicketStatus"),
  runTicket: async () => notImplemented("runTicket"),
  getLatestBrief: async () => notImplemented("getLatestBrief"),
  listAgents: async () => notImplemented("listAgents"),
  listWorktrees: async () => notImplemented("listWorktrees"),
  createWorktree: async () => notImplemented("createWorktree"),
  runBuild: async () => notImplemented("runBuild"),
  runLocalReview: async () => notImplemented("runLocalReview"),
  getDiff: async () => notImplemented("getDiff"),
  mergeToMain: async () => notImplemented("mergeToMain"),
  listLaunchdJobs: async () => notImplemented("listLaunchdJobs"),
  toggleLaunchdJob: async () => notImplemented("toggleLaunchdJob"),
  runLaunchdJobNow: async () => notImplemented("runLaunchdJobNow"),
  getQuotaStatus: async () => notImplemented("getQuotaStatus"),
  getSettings: async () => notImplemented("getSettings"),
  updateSettings: async () => notImplemented("updateSettings"),
};
