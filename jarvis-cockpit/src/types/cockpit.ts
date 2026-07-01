// フロントエンド全体で使う補助型（8画面ぶん）。TaskCard以外のドメイン型はここに集約する。

export type AgentRole =
  | "秘書"
  | "開発"
  | "レビュー"
  | "調査"
  | "運用"
  | "戦略";

export interface AgentInfo {
  id: string;
  name: string;
  role: AgentRole;
  model: "codex" | "lmstudio" | "gemini";
  permissionTier: 1 | 2 | 3;
  status: "online" | "offline" | "busy";
}

export type WorktreeStatus = "clean" | "building" | "review" | "merged" | "error";

export interface Worktree {
  id: string;
  branch: string;
  status: WorktreeStatus;
  createdAt: string;
}

export interface BuildLogLine {
  ts: string;
  level: "info" | "warn" | "error";
  text: string;
}

export type ReviewSeverity = "HIGH" | "MEDIUM" | "LOW";

export interface ReviewFinding {
  id: string;
  severity: ReviewSeverity;
  file: string;
  summary: string;
}

export interface DiffFile {
  path: string;
  patch: string;
}

export interface LaunchdJob {
  id: string;
  label: string;
  schedule: string;
  enabled: boolean;
  lastRunAt: string | null;
  lastLogTail: string;
}

export interface QuotaStatus {
  codexWindowUsedPct: number | null; // null = 不明（取得不能）
  geminiWindowUsedPct: number | null;
  authOk: boolean;
  apiKeyRedFlag: string[]; // 検出されたAPIキー環境変数
  fallbackModeActive: boolean;
}

export interface CockpitSettings {
  bridgeUrl: string;
  bridgeToken: string;
  lmStudioBaseUrl: string;
  obsidianVaultPath: string;
}

export interface TicketFilter {
  status?: string;
  category?: string;
  decisionRequired?: boolean;
}

export interface HealthPill {
  name: "Codex" | "LM Studio" | "Obsidian";
  ok: boolean | null; // null = 不明
  detail?: string;
}
