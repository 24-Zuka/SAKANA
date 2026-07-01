import { useEffect, useState } from "react";
import { api } from "../../lib/api";
import type { LaunchdJob } from "../../types/cockpit";
import { Card } from "../../components/common/Card";
import { Toggle } from "../../components/common/Toggle";

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
      <h1 className="font-display text-2xl font-bold">Schedule 定時運用</h1>
      <p className="text-xs text-jarvis-text3">
        launchdはmacOS専用機能のため、本環境ではUI操作のみ・実際のジョブ登録は行われません。
      </p>
      <ul className="flex flex-col gap-2">
        {jobs.map((job) => (
          <li key={job.id}>
          <Card>
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-[15px] font-semibold">{job.label}</h2>
                <p className="text-xs text-jarvis-text2">{job.schedule}</p>
              </div>
              <label className="flex items-center gap-2 text-xs text-jarvis-text2">
                有効
                <Toggle
                  checked={job.enabled}
                  onChange={async (checked) => {
                    await api.toggleLaunchdJob(job.id, checked);
                    await refresh();
                  }}
                  label={`${job.label} を有効化`}
                />
              </label>
            </div>
            <div className="mt-2 flex items-center justify-between">
              <p className="font-mono text-xs text-jarvis-text3">
                最終実行: {job.lastRunAt ?? "未実行"}
              </p>
              <button
                type="button"
                onClick={async () => {
                  await api.runLaunchdJobNow(job.id);
                  await refresh();
                }}
                className="rounded-lg border border-jarvis-accent/40 px-2 py-1 text-xs font-semibold text-jarvis-accent hover:bg-jarvis-accent/20"
              >
                今すぐ実行
              </button>
            </div>
            {job.lastLogTail && (
              <pre className="mt-2 rounded-[7px] border border-jarvis-line bg-jarvis-logbg px-[10px] py-2 font-mono text-[11px] text-jarvis-text2">
                {job.lastLogTail}
              </pre>
            )}
          </Card>
          </li>
        ))}
      </ul>
    </div>
  );
}
