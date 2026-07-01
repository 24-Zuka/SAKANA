import { useEffect, useState } from "react";
import { api } from "../../lib/api";
import { useAppStore } from "../../store/useAppStore";

const TRANSPORT_LABEL: Record<string, string> = {
  tauri: "Desktop",
  bridge: "Bridge",
  mock: "Demo",
};

export function TopBar() {
  const [homeLabel, setHomeLabel] = useState<string>("接続中…");
  const toggleCommandPalette = useAppStore((s) => s.toggleCommandPalette);

  useEffect(() => {
    let cancelled = false;
    api
      .health()
      .then((h) => {
        if (!cancelled) setHomeLabel(h.home);
      })
      .catch(() => {
        if (!cancelled) setHomeLabel("不明（接続不可）");
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <header className="flex h-14 shrink-0 items-center justify-between border-b border-jarvis-border bg-jarvis-surface px-4">
      <div className="flex items-center gap-3 text-sm text-jarvis-text-muted">
        <span className="rounded border border-jarvis-accent-dim px-2 py-0.5 font-mono text-xs text-jarvis-accent">
          {TRANSPORT_LABEL[api.transportName]}
        </span>
        <span className="font-mono text-xs">{homeLabel}</span>
      </div>
      <button
        type="button"
        onClick={toggleCommandPalette}
        className="rounded border border-jarvis-border px-3 py-1 text-xs text-jarvis-text-muted hover:bg-jarvis-surface-raised"
      >
        ⌘K コマンド
      </button>
    </header>
  );
}
