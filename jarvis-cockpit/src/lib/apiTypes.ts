import type { TaskCard } from "../types/taskcard";
import type { Brief, HealthStatus } from "../types/taskcard";
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

// 3トランスポート（Tauri / Bridge / Mock）共通の唯一の窓口インターフェース — spec §7.1/§7.3。
export interface AirflowApi {
  transportName: "tauri" | "bridge" | "mock";

  health(): Promise<HealthStatus>;
  listTickets(filter?: TicketFilter): Promise<TaskCard[]>;
  getTicket(id: string): Promise<TaskCard>;
  createTicket(text: string): Promise<TaskCard>;
  getLatestBrief(): Promise<Brief>;

  listAgents(): Promise<AgentInfo[]>;

  listWorktrees(): Promise<Worktree[]>;
  createWorktree(branch: string): Promise<Worktree>;
  runBuild(worktreeId: string): Promise<BuildLogLine[]>;
  runLocalReview(worktreeId: string): Promise<ReviewFinding[]>;
  getDiff(worktreeId: string): Promise<DiffFile[]>;
  mergeToMain(worktreeId: string): Promise<{ ok: boolean }>;

  listLaunchdJobs(): Promise<LaunchdJob[]>;
  toggleLaunchdJob(id: string, enabled: boolean): Promise<void>;
  runLaunchdJobNow(id: string): Promise<void>;

  getQuotaStatus(): Promise<QuotaStatus>;

  getSettings(): Promise<CockpitSettings>;
  updateSettings(settings: Partial<CockpitSettings>): Promise<CockpitSettings>;
}

export class NotImplementedError extends Error {
  constructor(transport: string, method: string) {
    super(`${method} is not implemented in the "${transport}" transport yet.`);
    this.name = "NotImplementedError";
  }
}
