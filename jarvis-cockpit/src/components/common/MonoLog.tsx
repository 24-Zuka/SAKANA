import type { BuildLogLine } from "../../types/cockpit";

// デザイン仕様書 §06: ログ行。mono 11px、bg #0A0D12、border 1px Line、radius 7px、padding 8px 10px。
const LEVEL_COLOR: Record<BuildLogLine["level"], string> = {
  info: "text-jarvis-text2",
  warn: "text-jarvis-yellow",
  error: "text-jarvis-red",
};

export function MonoLog({ lines }: { lines: BuildLogLine[] }) {
  if (lines.length === 0) {
    return <div className="font-mono text-[11px] text-jarvis-text3">（ログはまだありません）</div>;
  }
  return (
    <pre className="max-h-64 overflow-auto rounded-[7px] border border-jarvis-line bg-jarvis-logbg px-[10px] py-2 font-mono text-[11px] leading-relaxed">
      {lines.map((line, i) => (
        <div key={i} className={LEVEL_COLOR[line.level]}>
          <span className="text-jarvis-text3">{line.ts.slice(11, 19)}</span> {line.text}
        </div>
      ))}
    </pre>
  );
}
