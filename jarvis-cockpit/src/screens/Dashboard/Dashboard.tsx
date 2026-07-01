import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../../lib/api";
import type { HealthStatus, TaskCard } from "../../types/taskcard";
import type { QuotaStatus } from "../../types/cockpit";
import { StatusBadge } from "../../components/common/StatusBadge";
import { RiskBadge } from "../../components/common/RiskBadge";
import { CategoryBadge } from "../../components/common/CategoryBadge";
import { Card, CardHeading } from "../../components/common/Card";
import { PrimaryButton, GhostButton } from "../../components/common/Button";
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
        <h1 className="font-display text-2xl font-bold">Dashboard 司令室</h1>
        <div className="mt-3 flex flex-wrap gap-2">
          <HealthPill name="Codex" ok={health ? health.codex_cli_available : null} />
          <HealthPill name="LM Studio" ok={health ? health.lm_studio_reachable : null} />
          <HealthPill name="Obsidian" ok={health ? health.obsidian_connected : null} />
        </div>
      </div>

      <Card>
        <CardHeading>airflow add（自然文でチケットを起票）</CardHeading>
        <div className="mt-3 flex gap-2">
          <input
            value={newTicketText}
            onChange={(e) => setNewTicketText(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleAddTicket()}
            placeholder="例: A社との提携レート再交渉の方針を決めたい"
            className="flex-1 rounded-lg border border-jarvis-line bg-jarvis-bg px-3 py-1.5 text-sm outline-none focus:border-jarvis-accent"
          />
          <PrimaryButton disabled={creating} onClick={handleAddTicket}>
            起票
          </PrimaryButton>
        </div>
      </Card>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <Card>
          <CardHeading>Plus残量</CardHeading>
          <p className="mt-2 font-display text-2xl font-bold text-jarvis-text2">
            {quota?.codexWindowUsedPct === null || quota === null ? "不明" : `${quota.codexWindowUsedPct}%`}
          </p>
          <p className="mt-1 text-xs text-jarvis-text3">
            公式APIが無いため取得不能。正直に「不明」と表示する（§16）。
          </p>
        </Card>

        <Card>
          <CardHeading>アクティブ</CardHeading>
          <p className="mt-2 font-display text-2xl font-bold">{activeDoing.length}</p>
          <p className="mt-1 text-xs text-jarvis-text3">実行中スレッド・ジョブ数</p>
        </Card>

        <Card>
          <CardHeading>要判断</CardHeading>
          <p className="mt-2 font-display text-2xl font-bold text-jarvis-yellow">{decisionRequired.length}</p>
          <p className="mt-1 text-xs text-jarvis-text3">承認/判断待ちのチケット</p>
        </Card>
      </div>

      <Card>
        <div className="flex items-center justify-between">
          <CardHeading>今日のブリーフ（抜粋）</CardHeading>
          <button
            type="button"
            onClick={() => navigate("/schedule")}
            className="text-xs text-jarvis-accent hover:underline"
          >
            Scheduleで詳細を見る
          </button>
        </div>
        <pre className="mt-2 whitespace-pre-wrap font-mono text-xs text-jarvis-text">{briefExcerpt}</pre>
      </Card>

      <Card>
        <CardHeading>クイックアクション</CardHeading>
        <div className="mt-3 flex flex-wrap gap-2">
          <GhostButton
            onClick={() => runQuickAction("朝会", () => api.getLatestBrief())}
            className="border-jarvis-accent/40 text-jarvis-accent hover:bg-jarvis-accent/20"
          >
            朝会
          </GhostButton>
          <GhostButton onClick={() => navigate("/build")}>レビュー</GhostButton>
          <GhostButton onClick={() => navigate("/research")}>調査</GhostButton>
        </div>
      </Card>

      <Card>
        <CardHeading>チケット一覧</CardHeading>
        <ul className="mt-3 flex flex-col gap-2">
          {tickets.map((t) => (
            <li
              key={t.id}
              className="flex flex-wrap items-center gap-2 rounded-lg border border-jarvis-line px-3 py-2 text-sm"
            >
              <span className="font-mono text-xs text-jarvis-text3">{t.id}</span>
              <StatusBadge status={t.status} />
              <RiskBadge score={t.risk_score} />
              <CategoryBadge category={t.category} />
              <span className="flex-1">{t.title}</span>
            </li>
          ))}
        </ul>
      </Card>
    </div>
  );
}
