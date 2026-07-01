import { useEffect, useState } from "react";
import { api } from "../../lib/api";
import type { BuildLogLine, DiffFile, ReviewFinding, Worktree } from "../../types/cockpit";
import { MonoLog } from "../../components/common/MonoLog";
import { DiffView } from "../../components/common/DiffView";
import { useAppStore } from "../../store/useAppStore";

const SEVERITY_COLOR: Record<ReviewFinding["severity"], string> = {
  HIGH: "text-jarvis-danger",
  MEDIUM: "text-jarvis-warning",
  LOW: "text-jarvis-text-muted",
};

export function Build() {
  const [worktrees, setWorktrees] = useState<Worktree[]>([]);
  const [newBranch, setNewBranch] = useState("");
  const [selected, setSelected] = useState<string | null>(null);
  const [log, setLog] = useState<BuildLogLine[]>([]);
  const [findings, setFindings] = useState<ReviewFinding[]>([]);
  const [diff, setDiff] = useState<DiffFile[]>([]);
  const [busy, setBusy] = useState(false);
  const requestApproval = useAppStore((s) => s.requestApproval);
  const pushToast = useAppStore((s) => s.pushToast);

  async function refreshWorktrees() {
    setWorktrees(await api.listWorktrees());
  }

  useEffect(() => {
    refreshWorktrees();
  }, []);

  async function handleCreateWorktree() {
    if (!newBranch.trim()) return;
    const wt = await api.createWorktree(newBranch.trim());
    setNewBranch("");
    await refreshWorktrees();
    setSelected(wt.id);
  }

  async function handleBuild(worktreeId: string) {
    setBusy(true);
    setSelected(worktreeId);
    try {
      const lines = await api.runBuild(worktreeId);
      setLog(lines);
      const [reviewFindings, diffFiles] = await Promise.all([
        api.runLocalReview(worktreeId),
        api.getDiff(worktreeId),
      ]);
      setFindings(reviewFindings);
      setDiff(diffFiles);
      await refreshWorktrees();
    } finally {
      setBusy(false);
    }
  }

  function handleMergeRequest(worktreeId: string) {
    // §7.2: mainマージは要承認。§8.3: risk_score>=3.0 または要承認操作は承認モーダル必須。
    requestApproval({
      title: `${worktreeId} を main へマージ`,
      description: "この操作は不可逆です（§8.3: mainへのマージ/リリースは要承認）。",
      riskScore: 3.5,
      onApprove: async () => {
        await api.mergeToMain(worktreeId);
        await refreshWorktrees();
        pushToast("main へマージしました", "success");
      },
      onReject: () => pushToast("マージを見送りました", "info"),
    });
  }

  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-lg font-semibold">Build（開発パイプライン）</h1>

      <section className="rounded-lg border border-jarvis-border bg-jarvis-surface p-4">
        <h2 className="text-sm font-semibold text-jarvis-text-muted">Worktree一覧</h2>
        <div className="mt-3 flex gap-2">
          <input
            value={newBranch}
            onChange={(e) => setNewBranch(e.target.value)}
            placeholder="新しいブランチ名"
            className="flex-1 rounded border border-jarvis-border bg-jarvis-bg px-3 py-1.5 text-sm outline-none focus:border-jarvis-accent"
          />
          <button
            type="button"
            onClick={handleCreateWorktree}
            className="rounded bg-jarvis-accent px-3 py-1.5 text-sm font-medium text-jarvis-bg hover:opacity-90"
          >
            worktree作成
          </button>
        </div>
        <ul className="mt-3 flex flex-col gap-2">
          {worktrees.map((wt) => (
            <li
              key={wt.id}
              className="flex items-center gap-3 rounded border border-jarvis-border px-3 py-2 text-sm"
            >
              <span className="font-mono text-xs">{wt.branch}</span>
              <span className="text-jarvis-text-muted">{wt.status}</span>
              <div className="ml-auto flex gap-2">
                <button
                  type="button"
                  disabled={busy}
                  onClick={() => handleBuild(wt.id)}
                  className="rounded border border-jarvis-accent-dim px-2 py-1 text-xs text-jarvis-accent hover:bg-jarvis-accent-dim/20 disabled:opacity-50"
                >
                  ビルド実行
                </button>
                <button
                  type="button"
                  disabled={wt.status !== "review"}
                  onClick={() => handleMergeRequest(wt.id)}
                  className="rounded border border-jarvis-warning/40 px-2 py-1 text-xs text-jarvis-warning hover:bg-jarvis-warning/10 disabled:opacity-30"
                >
                  mainへマージ
                </button>
              </div>
            </li>
          ))}
        </ul>
      </section>

      {selected && (
        <>
          <section className="rounded-lg border border-jarvis-border bg-jarvis-surface p-4">
            <h2 className="text-sm font-semibold text-jarvis-text-muted">ビルドログ</h2>
            <div className="mt-3">
              <MonoLog lines={log} />
            </div>
          </section>

          <section className="rounded-lg border border-jarvis-border bg-jarvis-surface p-4">
            <h2 className="text-sm font-semibold text-jarvis-text-muted">ローカルレビュー</h2>
            <ul className="mt-3 flex flex-col gap-1">
              {findings.map((f) => (
                <li key={f.id} className="flex gap-2 text-sm">
                  <span className={`font-mono text-xs ${SEVERITY_COLOR[f.severity]}`}>{f.severity}</span>
                  <span className="font-mono text-xs text-jarvis-text-muted">{f.file}</span>
                  <span>{f.summary}</span>
                </li>
              ))}
              {findings.length === 0 && (
                <li className="text-sm text-jarvis-text-muted">（レビュー結果はまだありません）</li>
              )}
            </ul>
          </section>

          <section className="rounded-lg border border-jarvis-border bg-jarvis-surface p-4">
            <h2 className="text-sm font-semibold text-jarvis-text-muted">Diff</h2>
            <div className="mt-3">
              <DiffView files={diff} />
            </div>
          </section>
        </>
      )}
    </div>
  );
}
