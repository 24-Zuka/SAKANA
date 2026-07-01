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
    <header className="flex h-14 shrink-0 items-center justify-between border-b border-jarvis-line bg-jarvis-panel px-4">
      <div className="flex items-center gap-3 text-sm text-jarvis-text2">
        <span className="rounded-[5px] bg-jarvis-accent/12 px-2 py-0.5 font-mono text-xs font-semibold text-jarvis-accent">
          {TRANSPORT_LABEL[api.transportName]}
        </span>
        <span className="font-mono text-xs text-jarvis-text3">{homeLabel}</span>
      </div>
      <button
        type="button"
        onClick={toggleCommandPalette}
        className="rounded-lg border border-jarvis-line px-3 py-1 text-xs text-jarvis-text2 hover:bg-jarvis-panel2"
      >
        ⌘K コマンド
      </button>
    </header>
  );
}
