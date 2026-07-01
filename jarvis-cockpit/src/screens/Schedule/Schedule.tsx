import { useEffect, useState } from "react";
import { api } from "../../lib/api";
import type { LaunchdJob } from "../../types/cockpit";

// Schedule（定時運用）— spec §7.2/§10: launchdはmacOS専用のためこの環境では
// 実結線せず、静的表示＋UI操作のみ（docs/DEVIATIONS.md）。

export function Schedule() {
  const [jobs, setJobs] = useState<LaunchdJob[]>([]);

  async function refresh() {
    setJobs(await api.listLaunchdJobs());
  }

  useEffect(() => {
    refresh();
  }, []);

  return (
    <div className="flex flex-col gap-4">
      <h1 className="text-lg font-semibold">Schedule（定時運用）</h1>
      <p className="text-xs text-jarvis-text-muted">
        launchdはmacOS専用機能のため、本環境ではUI操作のみ・実際のジョブ登録は行われません。
      </p>
      <ul className="flex flex-col gap-2">
        {jobs.map((job) => (
          <li key={job.id} className="rounded-lg border border-jarvis-border bg-jarvis-surface p-4">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-sm font-semibold">{job.label}</h2>
                <p className="text-xs text-jarvis-text-muted">{job.schedule}</p>
              </div>
              <label className="flex items-center gap-2 text-xs text-jarvis-text-muted">
                <input
                  type="checkbox"
                  checked={job.enabled}
                  onChange={async (e) => {
                    await api.toggleLaunchdJob(job.id, e.target.checked);
                    await refresh();
                  }}
                />
                有効
              </label>
            </div>
            <div className="mt-2 flex items-center justify-between">
              <p className="font-mono text-xs text-jarvis-text-muted">
                最終実行: {job.lastRunAt ?? "未実行"}
              </p>
              <button
                type="button"
                onClick={async () => {
                  await api.runLaunchdJobNow(job.id);
                  await refresh();
                }}
                className="rounded border border-jarvis-accent-dim px-2 py-1 text-xs text-jarvis-accent hover:bg-jarvis-accent-dim/20"
              >
                今すぐ実行
              </button>
            </div>
            {job.lastLogTail && (
              <pre className="mt-2 rounded bg-jarvis-bg p-2 font-mono text-xs text-jarvis-text-muted">
                {job.lastLogTail}
              </pre>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}
