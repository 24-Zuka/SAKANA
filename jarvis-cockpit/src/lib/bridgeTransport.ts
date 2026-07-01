// Bridge トランスポート — spec §7.1/§7.3。
//
// 一時的な FastAPI dev bridge（airflow/src/airflow/bridge.py）に接続する。
// これは本来の Rust/axum 製 `jarvis-bridge` ではない。
// tickets/brief/health のみ実装し、それ以外（Build/Agents/Schedule/Quota/Settings）
// は NotImplementedError を投げる（この開発ブリッジのスコープ外・§12.2参照）。

import type { Brief, HealthStatus, TaskCard } from "../types/taskcard";
import type { TicketFilter } from "../types/cockpit";
import type { AirflowApi } from "./apiTypes";
import { NotImplementedError } from "./apiTypes";

const BASE_URL = import.meta.env.VITE_BRIDGE_URL ?? "http://127.0.0.1:8787";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!response.ok) {
    throw new Error(`bridge request failed: ${response.status} ${await response.text()}`);
  }
  return (await response.json()) as T;
}

function notImplemented(method: string): never {
  throw new NotImplementedError("bridge", method);
}

export const bridgeTransport: AirflowApi = {
  transportName: "bridge",

  health: () => request<HealthStatus>("/health"),

  listTickets: (filter?: TicketFilter) => {
    const params = new URLSearchParams();
    if (filter?.status) params.set("status", filter.status);
    if (filter?.category) params.set("category", filter.category);
    if (filter?.decisionRequired !== undefined) {
      params.set("decision_required", String(filter.decisionRequired));
    }
    const qs = params.toString();
    return request<TaskCard[]>(`/tickets${qs ? `?${qs}` : ""}`);
  },

  getTicket: (id: string) => request<TaskCard>(`/tickets/${id}`),

  createTicket: (text: string) =>
    request<TaskCard>("/tickets", { method: "POST", body: JSON.stringify({ text }) }),

  getLatestBrief: () => request<Brief>("/brief/latest"),

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
