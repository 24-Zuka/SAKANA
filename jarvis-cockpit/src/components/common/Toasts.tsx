import { useAppStore } from "../../store/useAppStore";

const KIND_STYLES: Record<string, string> = {
  info: "border-jarvis-border text-jarvis-text",
  success: "border-jarvis-success/40 text-jarvis-success",
  error: "border-jarvis-danger/40 text-jarvis-danger",
};

export function Toasts() {
  const toasts = useAppStore((s) => s.toasts);
  const dismissToast = useAppStore((s) => s.dismissToast);

  return (
    <div className="pointer-events-none fixed bottom-4 right-4 z-50 flex flex-col gap-2">
      {toasts.map((t) => (
        <div
          key={t.id}
          role="status"
          className={`pointer-events-auto rounded border bg-jarvis-surface px-4 py-2 text-sm shadow-lg ${KIND_STYLES[t.kind]}`}
        >
          <div className="flex items-center gap-3">
            <span>{t.message}</span>
            <button
              type="button"
              onClick={() => dismissToast(t.id)}
              aria-label="閉じる"
              className="text-jarvis-text-muted hover:text-jarvis-text"
            >
              ×
            </button>
          </div>
        </div>
      ))}
    </div>
  );
}
