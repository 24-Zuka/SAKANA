import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../../lib/api";
import type { HealthStatus, TaskCard } from "../../types/taskcard";
import type { QuotaStatus } from "../../types/cockpit";
import { StatusBadge } from "../../components/common/StatusBadge";
import { RiskBadge } from "../../components/common/RiskBadge";
import { useAppStore } from "../../store/useAppStore";
import { HealthPill } from "./HealthPill";

export function Dashboard() {
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [quota, setQuota] = useState<QuotaStatus | null>(null);
  const [tickets, setTickets] = useState<TaskCard[]>([]);
  const [briefExcerpt, setBriefExcerpt] = useState<string>("");
  const [newTicketText, setNewTicketText] = useState("");
  const [creating, setCreating] = useState(false);
  const pushToast = useAppStore((s) => s.pushToast);
  const navigate = useNavigate();

  async function refreshTickets() {
    setTickets(await api.listTickets());
  }

  useEffect(() => {
    let cancelled = false;
    api.health().then((h) => !cancelled && setHealth(h)).catch(() => undefined);
    api.getQuotaStatus().then((q) => !cancelled && setQuota(q)).catch(() => undefined);
    api.listTickets().then((t) => !cancelled && setTickets(t)).catch(() => undefined);
    api
      .getLatestBrief()
      .then((b) => !cancelled && setBriefExcerpt(b.content.split("\n").slice(0, 6).join("\n")))
      .catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, []);

  const activeDoing = tickets.filter((t) => t.status === "Doing");
  const decisionRequired = tickets.filter((t) => t.decision_required);

  async function runQuickAction(label: string, action: () => Promise<unknown>) {
    try {
      await action();
      pushToast(`${label} を実行しました`, "success");
    } catch {
      pushToast(`${label} に失敗しました`, "error");
    }
  }

  async function handleAddTicket() {
    if (!newTicketText.trim()) return;
    setCreating(true);
    try {
      const ticket = await api.createTicket(newTicketText.trim());
      setNewTicketText("");
      await refreshTickets();
      pushToast(`起票しました: ${ticket.id}`, "success");
    } catch {
      pushToast("起票に失敗しました", "error");
    } finally {
      setCreating(false);
    }
  }

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-lg font-semibold">Dashboard（司令室）</h1>
        <div className="mt-3 flex flex-wrap gap-2">
          <HealthPill name="Codex" ok={health ? health.codex_cli_available : null} />
          <HealthPill name="LM Studio" ok={health ? health.lm_studio_reachable : null} />
          <HealthPill name="Obsidian" ok={health ? health.obsidian_connected : null} />
        </div>
      </div>

      <section className="rounded-lg border border-jarvis-border bg-jarvis-surface p-4">
        <h2 className="text-sm font-semibold text-jarvis-text-muted">airflow add（自然文でチケットを起票）</h2>
        <div className="mt-3 flex gap-2">
          <input
            value={newTicketText}
            onChange={(e) => setNewTicketText(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleAddTicket()}
            placeholder="例: A社との提携レート再交渉の方針を決めたい"
            className="flex-1 rounded border border-jarvis-border bg-jarvis-bg px-3 py-1.5 text-sm outline-none focus:border-jarvis-accent"
          />
          <button
            type="button"
            disabled={creating}
            onClick={handleAddTicket}
            className="rounded bg-jarvis-accent px-3 py-1.5 text-sm font-medium text-jarvis-bg hover:opacity-90 disabled:opacity-50"
          >
            起票
          </button>
        </div>
      </section>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <section className="rounded-lg border border-jarvis-border bg-jarvis-surface p-4">
          <h2 className="text-sm font-semibold text-jarvis-text-muted">Plus残量</h2>
          <p className="mt-2 font-mono text-2xl text-jarvis-text-muted">
            {quota?.codexWindowUsedPct === null || quota === null ? "不明" : `${quota.codexWindowUsedPct}%`}
          </p>
          <p className="mt-1 text-xs text-jarvis-text-muted">
            公式APIが無いため取得不能。正直に「不明」と表示する（§16）。
          </p>
        </section>

        <section className="rounded-lg border border-jarvis-border bg-jarvis-surface p-4">
          <h2 className="text-sm font-semibold text-jarvis-text-muted">アクティブ</h2>
          <p className="mt-2 text-2xl font-mono">{activeDoing.length}</p>
          <p className="mt-1 text-xs text-jarvis-text-muted">実行中スレッド・ジョブ数</p>
        </section>

        <section className="rounded-lg border border-jarvis-border bg-jarvis-surface p-4">
          <h2 className="text-sm font-semibold text-jarvis-text-muted">要判断</h2>
          <p className="mt-2 text-2xl font-mono text-jarvis-danger">{decisionRequired.length}</p>
          <p className="mt-1 text-xs text-jarvis-text-muted">承認/判断待ちのチケット</p>
        </section>
      </div>

      <section className="rounded-lg border border-jarvis-border bg-jarvis-surface p-4">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-semibold text-jarvis-text-muted">今日のブリーフ（抜粋）</h2>
          <button
            type="button"
            onClick={() => navigate("/schedule")}
            className="text-xs text-jarvis-accent hover:underline"
          >
            Scheduleで詳細を見る
          </button>
        </div>
        <pre className="mt-2 whitespace-pre-wrap font-mono text-xs text-jarvis-text">{briefExcerpt}</pre>
      </section>

      <section className="rounded-lg border border-jarvis-border bg-jarvis-surface p-4">
        <h2 className="text-sm font-semibold text-jarvis-text-muted">クイックアクション</h2>
        <div className="mt-3 flex flex-wrap gap-2">
          <button
            type="button"
            onClick={() => runQuickAction("朝会", () => api.getLatestBrief())}
            className="rounded border border-jarvis-accent-dim px-3 py-1.5 text-sm text-jarvis-accent hover:bg-jarvis-accent-dim/20"
          >
            朝会
          </button>
          <button
            type="button"
            onClick={() => navigate("/build")}
            className="rounded border border-jarvis-border px-3 py-1.5 text-sm text-jarvis-text-muted hover:bg-jarvis-surface-raised"
          >
            レビュー
          </button>
          <button
            type="button"
            onClick={() => navigate("/research")}
            className="rounded border border-jarvis-border px-3 py-1.5 text-sm text-jarvis-text-muted hover:bg-jarvis-surface-raised"
          >
            調査
          </button>
        </div>
      </section>

      <section className="rounded-lg border border-jarvis-border bg-jarvis-surface p-4">
        <h2 className="text-sm font-semibold text-jarvis-text-muted">チケット一覧</h2>
        <ul className="mt-3 flex flex-col gap-2">
          {tickets.map((t) => (
            <li
              key={t.id}
              className="flex flex-wrap items-center gap-2 rounded border border-jarvis-border px-3 py-2 text-sm"
            >
              <span className="font-mono text-xs text-jarvis-text-muted">{t.id}</span>
              <StatusBadge status={t.status} />
              <RiskBadge score={t.risk_score} />
              <span className="text-jarvis-text-muted">{t.category}</span>
              <span className="flex-1">{t.title}</span>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
