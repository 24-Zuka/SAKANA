// ⌘Kコマンドパレット — spec §7.2 横断機能。

import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAppStore } from "../store/useAppStore";

interface Command {
  id: string;
  label: string;
  run: () => void;
}

export function CommandPalette() {
  const open = useAppStore((s) => s.commandPaletteOpen);
  const setOpen = useAppStore((s) => s.setCommandPaletteOpen);
  const toggle = useAppStore((s) => s.toggleCommandPalette);
  const [query, setQuery] = useState("");
  const navigate = useNavigate();

  useEffect(() => {
    function onKeyDown(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        toggle();
      } else if (e.key === "Escape") {
        setOpen(false);
      }
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [toggle, setOpen]);

  const commands: Command[] = useMemo(
    () => [
      { id: "goto-dashboard", label: "Dashboard へ移動", run: () => navigate("/") },
      { id: "goto-agents", label: "Agents へ移動", run: () => navigate("/agents") },
      { id: "goto-build", label: "Build へ移動", run: () => navigate("/build") },
      { id: "goto-memory", label: "Memory へ移動", run: () => navigate("/memory") },
      { id: "goto-schedule", label: "Schedule へ移動", run: () => navigate("/schedule") },
      { id: "goto-research", label: "Research へ移動", run: () => navigate("/research") },
      { id: "goto-quota", label: "Quota & Cost へ移動", run: () => navigate("/quota") },
      { id: "goto-settings", label: "Settings へ移動", run: () => navigate("/settings") },
    ],
    [navigate],
  );

  const filtered = commands.filter((c) => c.label.toLowerCase().includes(query.toLowerCase()));

  if (!open) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="コマンドパレット"
      className="fixed inset-0 z-50 flex items-start justify-center bg-black/60 pt-32"
      onClick={() => setOpen(false)}
    >
      <div
        className="w-full max-w-lg rounded-[13px] border border-jarvis-line bg-jarvis-panel shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center gap-2 border-b border-jarvis-line px-4 py-2">
          <span className="inline-flex items-center rounded-[5px] bg-jarvis-accent/12 px-2 py-0.5 text-[11px] font-semibold text-jarvis-accent">
            ⌘K
          </span>
          <span className="text-[11px] text-jarvis-text3">全操作をキーボードから</span>
        </div>
        <input
          autoFocus
          placeholder="コマンドを検索… (⌘K)"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          className="w-full border-b border-jarvis-line bg-transparent px-4 py-3 text-sm text-jarvis-text outline-none placeholder:text-jarvis-text2"
        />
        <ul className="max-h-72 overflow-auto py-1">
          {filtered.length === 0 && (
            <li className="px-4 py-2 text-sm text-jarvis-text2">一致するコマンドがありません</li>
          )}
          {filtered.map((c) => (
            <li key={c.id}>
              <button
                type="button"
                onClick={() => {
                  c.run();
                  setOpen(false);
                  setQuery("");
                }}
                className="w-full px-4 py-2 text-left text-sm text-jarvis-text hover:bg-jarvis-panel2"
              >
                {c.label}
              </button>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
