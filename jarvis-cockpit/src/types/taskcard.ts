// Python `airflow.models.TaskCard` の TS ミラー — spec §4.3。

export type Category = "Business" | "Engineering" | "Content";
export type Status = "Inbox" | "Today" | "Doing" | "Waiting" | "Done";
export type Source = "email" | "manual" | "obsidian-inbox" | "ai";
export type Assignee = "codex" | "lmstudio" | "gemini" | "human";

export interface TaskCard {
  id: string;
  task_id: string | null;
  title: string;
  category: Category;
  status: Status;
  priority: 1 | 2 | 3;
  risk_score: number; // 0.1-5.0, >=3.0 で承認モーダル必須
  created: string;
  updated: string;
  due: string | null;
  source: Source;
  assignee: Assignee;
  tier: 1 | 2 | 3;
  decision_required: boolean;
  dependencies: string[];
  links: string[];
  log: string[];
  body: string;
}

export interface Brief {
  path: string;
  content: string;
}

export interface HealthStatus {
  ok: boolean;
  home: string;
  lm_studio_base_url: string;
  api_key_red_flag: string[];
  lm_studio_reachable: boolean;
  codex_cli_available: boolean;
  obsidian_connected: boolean;
}

export const RISK_APPROVAL_THRESHOLD = 3.0;
