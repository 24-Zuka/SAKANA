import { useEffect, useState } from "react";
import { api } from "../../lib/api";
import type { AgentInfo } from "../../types/cockpit";

const STATUS_COLOR: Record<AgentInfo["status"], string> = {
  online: "bg-jarvis-success",
  offline: "bg-jarvis-text-muted",
  busy: "bg-jarvis-warning",
};

// Agents（組織図）— spec §7.2: MVPでは静的ステータス表示のみ（実行制御は次段階）。

export function Agents() {
  const [agents, setAgents] = useState<AgentInfo[]>([]);

  useEffect(() => {
    api.listAgents().then(setAgents).catch(() => undefined);
  }, []);

  return (
    <div className="flex flex-col gap-4">
      <h1 className="text-lg font-semibold">Agents（組織図）</h1>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {agents.map((a) => (
          <div key={a.id} className="rounded-lg border border-jarvis-border bg-jarvis-surface p-4">
            <div className="flex items-center gap-2">
              <span className={`h-2 w-2 rounded-full ${STATUS_COLOR[a.status]}`} aria-hidden />
              <h2 className="text-sm font-semibold">{a.name}</h2>
            </div>
            <p className="mt-1 text-xs text-jarvis-text-muted">役割: {a.role}</p>
            <p className="text-xs text-jarvis-text-muted">割当モデル: {a.model}</p>
            <p className="text-xs text-jarvis-text-muted">権限Tier: {a.permissionTier}</p>
          </div>
        ))}
        {agents.length === 0 && (
          <p className="text-sm text-jarvis-text-muted">エージェント情報を取得できませんでした。</p>
        )}
      </div>
    </div>
  );
}
