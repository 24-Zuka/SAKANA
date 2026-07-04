import type { Brief, HealthStatus, TaskCard } from "../types/taskcard";
import { RISK_APPROVAL_THRESHOLD } from "../types/taskcard";
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
import { isValidStatusTransition } from "./statusTransitions";

const delay = (ms = 150) => new Promise((resolve) => setTimeout(resolve, ms));

let tickets: TaskCard[] = [
  {
    id: "TKT-20260628-001",
    task_id: "TASK-2026-0628A",
    title: "A社との提携レート再交渉の方針を決める",
    category: "Business",
    status: "Waiting",
    priority: 1,
    risk_score: 3.2,
    created: "2026-06-28T09:00:00+09:00",
    updated: "2026-06-28T09:00:00+09:00",
    due: "2026-07-01",
    source: "email",
    assignee: "codex",
    tier: 3,
    decision_required: true,
    dependencies: [],
    links: ["[[rates]]"],
    log: ["2026-06-28T09:00 created by ai (classified by lmstudio)"],
    body: "## 背景\n選択肢A: 現行レート維持 / 選択肢B: 5%引き上げ提案。",
  },
  {
    id: "TKT-20260628-010",
    task_id: null,
    title: "バックアップ先の決定（ローカル/外付け）",
    category: "Engineering",
    status: "Today",
    priority: 2,
    risk_score: 2.0,
    created: "2026-06-28T08:00:00+09:00",
    updated: "2026-06-28T08:00:00+09:00",
    due: "2026-06-30",
    source: "manual",
    assignee: "human",
    tier: 2,
    decision_required: true,
    dependencies: [],
    links: [],
    log: ["2026-06-28T08:00 created by human"],
    body: "",
  },
  {
    id: "TKT-20260628-022",
    task_id: null,
    title: "次回動画のテーマ確定",
    category: "Content",
    status: "Waiting",
    priority: 2,
    risk_score: 1.0,
    created: "2026-06-27T20:00:00+09:00",
    updated: "2026-06-27T20:00:00+09:00",
    due: null,
    source: "manual",
    assignee: "human",
    tier: 1,
    decision_required: true,
    dependencies: [],
    links: [],
    log: ["2026-06-27T20:00 created by human"],
    body: "",
  },
  {
    id: "TKT-20260627-004",
    task_id: null,
    title: "Cockpit Dashboard画面の実装",
    category: "Engineering",
    status: "Doing",
    priority: 2,
    risk_score: 1.5,
    created: "2026-06-27T10:00:00+09:00",
    updated: "2026-06-28T07:00:00+09:00",
    due: null,
    source: "manual",
    assignee: "codex",
    tier: 3,
    decision_required: false,
    dependencies: [],
    links: [],
    log: ["2026-06-27T10:00 created by human"],
    body: "",
  },
  {
    id: "TKT-20260625-002",
    task_id: null,
    title: "SNS投稿の下書き作成",
    category: "Content",
    status: "Done",
    priority: 3,
    risk_score: 0.5,
    created: "2026-06-25T09:00:00+09:00",
    updated: "2026-06-26T09:00:00+09:00",
    due: null,
    source: "manual",
    assignee: "lmstudio",
    tier: 2,
    decision_required: false,
    dependencies: [],
    links: [],
    log: ["2026-06-25T09:00 created by human", "2026-06-26T09:00 done"],
    body: "",
  },
];

let nextTicketSeq = tickets.length + 1;

const CATEGORY_KEYWORDS: Record<TaskCard["category"], string[]> = {
  Engineering: ["バグ", "実装", "デプロイ", "コード", "API", "サーバー", "ビルド"],
  Content: ["動画", "記事", "投稿", "デザイン", "コンテンツ"],
  Business: ["契約", "レート", "交渉", "請求", "売上", "顧客", "取引", "支払い"],
};
const EXTERNAL_KEYWORDS = ["送信", "公開", "デプロイ", "投稿", "PR作成"];
const IRREVERSIBLE_KEYWORDS = ["削除", "支払い", "契約", "本番"];
const DECISION_KEYWORDS = ["方針を決める", "判断", "決定", "選択肢", "決めたい", "要判断"];
const URGENT_KEYWORDS = ["今すぐ", "緊急", "至急", "本日中"];

function classifyLocally(text: string): {
  category: TaskCard["category"];
  priority: 1 | 2 | 3;
  decisionRequired: boolean;
  external: boolean;
  irreversible: boolean;
} {
  const category =
    (Object.entries(CATEGORY_KEYWORDS).find(([, kws]) =>
      kws.some((k) => text.includes(k)),
    )?.[0] as TaskCard["category"]) ?? "Business";
  const priority: 1 | 2 | 3 = URGENT_KEYWORDS.some((k) => text.includes(k)) ? 1 : 2;
  const decisionRequired = DECISION_KEYWORDS.some((k) => text.includes(k));
  const external = EXTERNAL_KEYWORDS.some((k) => text.includes(k));
  const irreversible = IRREVERSIBLE_KEYWORDS.some((k) => text.includes(k));
  return { category, priority, decisionRequired, external, irreversible };
}

function computeRiskScore(
  category: TaskCard["category"],
  priority: number,
  external: boolean,
  irreversible: boolean,
): number {
  const base = category === "Engineering" ? 1.5 : 1.0;
  let score = base;
  if (external) score += 2.0;
  if (irreversible) score += 2.0;
  if (priority === 1) score += 0.5;
  return Math.min(5.0, Math.max(0.1, score));
}

function renderBrief(all: TaskCard[]): string {
  const today = new Date().toISOString().slice(0, 10);
  const decisionItems = all.filter((t) => t.decision_required || t.status === "Today");
  const order: TaskCard["category"][] = ["Business", "Engineering", "Content"];
  const lines = [`# 朝礼 ${today}`, "", `## 今日の要判断（${decisionItems.length}件）`];
  let n = 1;
  for (const category of order) {
    const items = decisionItems.filter((t) => t.category === category);
    if (items.length === 0) continue;
    lines.push(`### ${category}`);
    for (const t of items) {
      const due = t.due ? `（期限: ${t.due.slice(5)}）` : "";
      lines.push(`${n}. [${t.id}] ${t.title}${due}`);
      n += 1;
    }
  }
  lines.push("", "## 進行中（参考）");
  const doing = all.filter((t) => t.status === "Doing");
  if (doing.length === 0) {
    lines.push("- （なし）");
  } else {
    for (const t of doing) lines.push(`- [${t.id}] ${t.title}`);
  }
  return lines.join("\n") + "\n";
}

const agents: AgentInfo[] = [
  { id: "agt-secretary", name: "秘書AI", role: "秘書", model: "lmstudio", permissionTier: 2, status: "online" },
  { id: "agt-dev", name: "開発AI", role: "開発", model: "codex", permissionTier: 3, status: "online" },
  { id: "agt-review", name: "レビューAI", role: "レビュー", model: "lmstudio", permissionTier: 1, status: "online" },
  { id: "agt-research", name: "調査AI", role: "調査", model: "gemini", permissionTier: 1, status: "offline" },
  { id: "agt-ops", name: "運用AI", role: "運用", model: "lmstudio", permissionTier: 2, status: "online" },
  { id: "agt-strategy", name: "戦略AI", role: "戦略", model: "codex", permissionTier: 2, status: "busy" },
];

let worktrees: Worktree[] = [
  { id: "wt-main-feature", branch: "feature/dashboard-ui", status: "clean", createdAt: "2026-06-27T10:00:00+09:00" },
];

let launchdJobs: LaunchdJob[] = [
  {
    id: "com.local.AirFlow.brief",
    label: "朝礼レポート生成",
    schedule: "毎朝 7:30",
    enabled: true,
    lastRunAt: "2026-06-28T07:30:00+09:00",
    lastLogTail: "briefs/2026-06-28.md を生成しました。",
  },
  {
    id: "com.local.AirFlow.grooming",
    label: "夜間グルーミング",
    schedule: "毎晩 23:00",
    enabled: true,
    lastRunAt: "2026-06-27T23:00:00+09:00",
    lastLogTail: "期限切れ整理・Done圧縮・索引再構築を実行しました。",
  },
  {
    id: "com.local.AirFlow.inbox",
    label: "Inbox監視",
    schedule: "常時",
    enabled: false,
    lastRunAt: null,
    lastLogTail: "",
  },
];

let settings: CockpitSettings = {
  bridgeUrl: "http://127.0.0.1:8787",
  bridgeToken: "",
  lmStudioBaseUrl: "http://localhost:1234/v1",
  obsidianVaultPath: "",
};

function matchesFilter(t: TaskCard, filter?: TicketFilter): boolean {
  if (!filter) return true;
  if (filter.status && t.status !== filter.status) return false;
  if (filter.category && t.category !== filter.category) return false;
  if (filter.decisionRequired !== undefined && t.decision_required !== filter.decisionRequired) return false;
  return true;
}

export const browserMock: AirflowApi = {
  transportName: "mock",

  async health(): Promise<HealthStatus> {
    await delay();
    return {
      ok: true,
      home: "(mock) ~/.airflow",
      lm_studio_base_url: settings.lmStudioBaseUrl,
      api_key_red_flag: [],
      lm_studio_reachable: false,
      codex_cli_available: false,
      obsidian_connected: false,
    };
  },

  async listTickets(filter) {
    await delay();
    return tickets.filter((t) => matchesFilter(t, filter));
  },

  async getTicket(id) {
    await delay();
    const ticket = tickets.find((t) => t.id === id);
    if (!ticket) throw new Error(`ticket ${id} not found`);
    return ticket;
  },

  async createTicket(text) {
    await delay(250);
    const now = new Date().toISOString();
    const { category, priority, decisionRequired, external, irreversible } = classifyLocally(text);
    const needsDecision = decisionRequired || external || irreversible;
    const ticket: TaskCard = {
      id: `TKT-MOCK-${String(nextTicketSeq).padStart(3, "0")}`,
      task_id: null,
      title: text.split("\n")[0].slice(0, 120) || "(no title)",
      category,
      status: needsDecision ? "Waiting" : "Today",
      priority,
      risk_score: computeRiskScore(category, priority, external, irreversible),
      created: now,
      updated: now,
      due: null,
      source: "manual",
      assignee: category === "Engineering" ? "codex" : "human",
      tier: 2,
      decision_required: needsDecision,
      dependencies: [],
      links: [],
      log: [`${now} created by ai (classified by rule_based mock)`],
      body: text,
    };
    nextTicketSeq += 1;
    tickets = [ticket, ...tickets];
    return ticket;
  },

  async updateTicketStatus(id, status, options) {
    await delay(150);
    const ticket = tickets.find((t) => t.id === id);
    if (!ticket) throw new Error(`ticket ${id} not found`);
    if (!isValidStatusTransition(ticket.status, status)) {
      throw new Error(`invalid status transition: ${ticket.status} -> ${status}`);
    }
    if (ticket.risk_score >= RISK_APPROVAL_THRESHOLD && !options?.approved) {
      throw new Error(`risk_score=${ticket.risk_score} requires approval`);
    }
    const now = new Date().toISOString();
    const updated: TaskCard = { ...ticket, status, updated: now };
    tickets = tickets.map((t) => (t.id === id ? updated : t));
    return updated;
  },

  async runTicket(id) {
    await delay(400);
    const ticket = tickets.find((t) => t.id === id);
    if (!ticket) throw new Error(`ticket ${id} not found`);
    const now = new Date().toISOString();
    const updated: TaskCard = {
      ...ticket,
      status: "Done",
      decision_required: false,
      updated: now,
      log: [...ticket.log, `${now} Plan→Route→Execute→Verify 完了（mock）`],
    };
    tickets = tickets.map((t) => (t.id === id ? updated : t));
    return updated;
  },

  async getLatestBrief(): Promise<Brief> {
    await delay();
    return { path: "(mock) briefs/today.md", content: renderBrief(tickets) };
  },

  async listAgents() {
    await delay();
    return agents;
  },

  async listWorktrees() {
    await delay();
    return worktrees;
  },

  async createWorktree(branch: string) {
    await delay(300);
    const wt: Worktree = {
      id: `wt-${branch.replace(/[^a-zA-Z0-9-]/g, "-")}`,
      branch,
      status: "clean",
      createdAt: new Date().toISOString(),
    };
    worktrees = [wt, ...worktrees];
    return wt;
  },

  async runBuild(worktreeId: string): Promise<BuildLogLine[]> {
    await delay(500);
    worktrees = worktrees.map((w) => (w.id === worktreeId ? { ...w, status: "building" } : w));
    const now = () => new Date().toISOString();
    const log: BuildLogLine[] = [
      { ts: now(), level: "info", text: `codex exec --json でビルド開始 (${worktreeId})` },
      { ts: now(), level: "info", text: "依存関係を解決しています…" },
      { ts: now(), level: "info", text: "ビルド成功。" },
    ];
    worktrees = worktrees.map((w) => (w.id === worktreeId ? { ...w, status: "review" } : w));
    return log;
  },

  async runLocalReview(worktreeId: string): Promise<ReviewFinding[]> {
    await delay(400);
    return [
      { id: `${worktreeId}-r1`, severity: "MEDIUM", file: "src/App.tsx", summary: "未使用のimportがあります。" },
      { id: `${worktreeId}-r2`, severity: "LOW", file: "src/index.css", summary: "コメントの表記ゆれ。" },
    ];
  },

  async getDiff(worktreeId: string): Promise<DiffFile[]> {
    await delay(200);
    return [
      {
        path: "src/App.tsx",
        patch: `--- a/src/App.tsx\n+++ b/src/App.tsx\n@@ -1,3 +1,4 @@\n+// ${worktreeId} での変更\n import React from 'react'\n`,
      },
    ];
  },

  async mergeToMain(worktreeId: string) {
    await delay(400);
    worktrees = worktrees.map((w) => (w.id === worktreeId ? { ...w, status: "merged" } : w));
    return { ok: true };
  },

  async listLaunchdJobs() {
    await delay();
    return launchdJobs;
  },

  async toggleLaunchdJob(id: string, enabled: boolean) {
    await delay(150);
    launchdJobs = launchdJobs.map((j) => (j.id === id ? { ...j, enabled } : j));
  },

  async runLaunchdJobNow(id: string) {
    await delay(300);
    launchdJobs = launchdJobs.map((j) =>
      j.id === id ? { ...j, lastRunAt: new Date().toISOString(), lastLogTail: "手動実行しました。" } : j,
    );
  },

  async getQuotaStatus(): Promise<QuotaStatus> {
    await delay();
    return {
      codexWindowUsedPct: null, // 公式API無し・取得不能=不明（§16）
      geminiWindowUsedPct: null,
      authOk: true,
      apiKeyRedFlag: [],
      fallbackModeActive: false,
    };
  },

  async getSettings() {
    await delay();
    return settings;
  },

  async updateSettings(partial: Partial<CockpitSettings>) {
    await delay(150);
    settings = { ...settings, ...partial };
    return settings;
  },
};
