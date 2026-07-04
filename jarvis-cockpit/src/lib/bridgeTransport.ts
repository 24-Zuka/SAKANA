// Bridge トランスポート — spec §7.1/§7.3。
//
// FastAPI dev bridge（airflow/src/airflow/bridge.py）に接続する。
// これは本来の Rust/axum 製 `jarvis-bridge` ではないが、Bearer認証込みで
// フロントエンドAirflowApiの全メソッドを実装する（§7.3参照）。

import type { Brief, HealthStatus, Status, TaskCard } from "../types/taskcard";
import type {
  AgentInfo,
  BuildLogLine,
  CockpitSettings,
  DiffFile,
  LaunchdJob,
  QuotaStatus,
  ReviewFinding,
  TicketFilter,
  Worktree,
} from "../types/cockpit";
import type { AirflowApi } from "./apiTypes";

export const DEFAULT_BRIDGE_URL = "http://127.0.0.1:8787";

export function createBridgeTransport(baseUrl: string, token?: string): AirflowApi {
  const base = (baseUrl || DEFAULT_BRIDGE_URL).replace(/\/+$/, "");

  async function request<T>(path: string, init?: RequestInit): Promise<T> {
    const headers: Record<string, string> = { "Content-Type": "application/json" };
    if (token) headers.Authorization = `Bearer ${token}`;
    if (init?.headers) Object.assign(headers, init.headers as Record<string, string>);

    const response = await fetch(`${base}${path}`, { ...init, headers });
    if (!response.ok) {
      throw new Error(`bridge request failed: ${response.status} ${await response.text()}`);
    }
    if (response.status === 204) return undefined as T;
    return (await response.json()) as T;
  }

  return {
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

    updateTicketStatus: (id: string, status: Status, options?: { approved?: boolean }) =>
      request<TaskCard>(`/tickets/${id}`, {
        method: "PATCH",
        body: JSON.stringify({ status, approved: options?.approved ?? false }),
      }),

    runTicket: (id: string) => request<TaskCard>(`/tickets/${id}/run`, { method: "POST" }),

    getLatestBrief: () => request<Brief>("/brief/latest"),

    listAgents: () => request<AgentInfo[]>("/agents"),

    listWorktrees: () => request<Worktree[]>("/worktrees"),

    createWorktree: (branch: string) =>
      request<Worktree>("/worktrees", { method: "POST", body: JSON.stringify({ branch }) }),

    runBuild: (worktreeId: string) =>
      request<BuildLogLine[]>("/build", { method: "POST", body: JSON.stringify({ worktreeId }) }),

    runLocalReview: (worktreeId: string) =>
      request<ReviewFinding[]>("/review", { method: "POST", body: JSON.stringify({ worktreeId }) }),

    getDiff: (worktreeId: string) =>
      request<DiffFile[]>(`/diff?worktreeId=${encodeURIComponent(worktreeId)}`),

    mergeToMain: (worktreeId: string) =>
      request<{ ok: boolean }>("/merge", {
        method: "POST",
        body: JSON.stringify({ worktreeId, approved: true }),
      }),

    listLaunchdJobs: () => request<LaunchdJob[]>("/launchd"),

    toggleLaunchdJob: async (id: string, enabled: boolean) => {
      await request(`/launchd/${id}`, { method: "PATCH", body: JSON.stringify({ enabled }) });
    },

    runLaunchdJobNow: async (id: string) => {
      await request(`/launchd/${id}/run`, { method: "POST" });
    },

    getQuotaStatus: () => request<QuotaStatus>("/quota"),

    getSettings: () => request<CockpitSettings>("/settings"),

    updateSettings: (settings: Partial<CockpitSettings>) =>
      request<CockpitSettings>("/settings", { method: "PUT", body: JSON.stringify(settings) }),
  };
}
