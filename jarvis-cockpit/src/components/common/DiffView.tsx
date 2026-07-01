import type { DiffFile } from "../../types/cockpit";

function diffLineClass(line: string): string {
  if (line.startsWith("+") && !line.startsWith("+++")) return "text-jarvis-success";
  if (line.startsWith("-") && !line.startsWith("---")) return "text-jarvis-danger";
  return "text-jarvis-text-muted";
}

export function DiffView({ files }: { files: DiffFile[] }) {
  if (files.length === 0) {
    return <div className="font-mono text-xs text-jarvis-text-muted">（差分はありません）</div>;
  }
  return (
    <div className="space-y-4">
      {files.map((file) => (
        <div key={file.path} className="rounded border border-jarvis-border bg-jarvis-bg">
          <div className="border-b border-jarvis-border px-3 py-1.5 font-mono text-xs text-jarvis-accent">
            {file.path}
          </div>
          <pre className="overflow-auto p-3 font-mono text-xs leading-relaxed">
            {file.patch.split("\n").map((line, i) => (
              <div key={i} className={diffLineClass(line)}>
                {line}
              </div>
            ))}
          </pre>
        </div>
      ))}
    </div>
  );
}
