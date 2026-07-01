import { useEffect, useState } from "react";
import { api } from "../../lib/api";
import type { TaskCard } from "../../types/taskcard";
import { StatusBadge } from "../../components/common/StatusBadge";
import { Card } from "../../components/common/Card";

// Memory（記憶/Vault）— spec §7.2: MVPスコープは「読取専用」。
// MEMORY上書き・削除は要承認のため、このMVPでは書込操作自体を提供しない。

export function Memory() {
  const [tickets, setTickets] = useState<TaskCard[]>([]);
  const [selected, setSelected] = useState<TaskCard | null>(null);

  useEffect(() => {
    api.listTickets().then(setTickets).catch(() => undefined);
  }, []);

  return (
    <div className="flex flex-col gap-4">
      <h1 className="font-display text-2xl font-bold">Memory 記憶 / Vault（読取専用）</h1>
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-[280px_1fr]">
        <nav className="rounded-[13px] border border-jarvis-line bg-jarvis-panel p-2">
          <ul className="flex flex-col gap-1">
            {tickets.map((t) => (
              <li key={t.id}>
                <button
                  type="button"
                  onClick={() => setSelected(t)}
                  className={`w-full rounded-lg px-2 py-1.5 text-left font-mono text-xs ${
                    selected?.id === t.id
                      ? "bg-jarvis-accent/12 text-jarvis-accent"
                      : "text-jarvis-text2 hover:bg-jarvis-panel2"
                  }`}
                >
                  {t.id}
                </button>
              </li>
            ))}
          </ul>
        </nav>
        <Card>
          {selected ? (
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-[15px] font-semibold">{selected.title}</h2>
                <StatusBadge status={selected.status} />
              </div>
              <pre className="mt-3 whitespace-pre-wrap rounded-[10px] border border-jarvis-line bg-jarvis-logbg p-3 font-mono text-xs text-jarvis-text2">
                {`---\nid: ${selected.id}\ncategory: ${selected.category}\nstatus: ${selected.status}\npriority: ${selected.priority}\nrisk_score: ${selected.risk_score}\n---\n\n${selected.body || "(本文なし)"}`}
              </pre>
            </div>
          ) : (
            <p className="text-sm text-jarvis-text3">左のリストからチケットを選択してください。</p>
          )}
        </Card>
      </div>
    </div>
  );
}
