import type { DiffFile } from "../../types/cockpit";

function diffLineClass(line: string): string {
  if (line.startsWith("+") && !line.startsWith("+++")) return "text-jarvis-green";
  if (line.startsWith("-") && !line.startsWith("---")) return "text-jarvis-red";
  return "text-jarvis-text2";
}

export function DiffView({ files }: { files: DiffFile[] }) {
  if (files.length === 0) {
    return <div className="font-mono text-xs text-jarvis-text2">（差分はありません）</div>;
  }
  return (
    <div className="space-y-4">
      {files.map((file) => (
        <div key={file.path} className="rounded-[10px] border border-jarvis-line bg-jarvis-logbg">
          <div className="border-b border-jarvis-line px-3 py-1.5 font-mono text-xs text-jarvis-accent">
            {file.path}
          </div>
          <pre className="overflow-auto p-3 font-mono text-[12.5px] leading-relaxed">
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
