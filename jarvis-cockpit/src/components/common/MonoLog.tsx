import type { BuildLogLine } from "../../types/cockpit";

const LEVEL_COLOR: Record<BuildLogLine["level"], string> = {
  info: "text-jarvis-text-muted",
  warn: "text-jarvis-warning",
  error: "text-jarvis-danger",
};

export function MonoLog({ lines }: { lines: BuildLogLine[] }) {
  if (lines.length === 0) {
    return <div className="font-mono text-xs text-jarvis-text-muted">（ログはまだありません）</div>;
  }
  return (
    <pre className="max-h-64 overflow-auto rounded border border-jarvis-border bg-jarvis-bg p-3 font-mono text-xs leading-relaxed">
      {lines.map((line, i) => (
        <div key={i} className={LEVEL_COLOR[line.level]}>
          <span className="text-jarvis-text-muted">{line.ts.slice(11, 19)}</span> {line.text}
        </div>
      ))}
    </pre>
  );
}
