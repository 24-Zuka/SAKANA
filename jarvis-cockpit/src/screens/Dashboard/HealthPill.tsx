interface Props {
  name: string;
  ok: boolean | null; // null = 不明
}

// デザイン仕様書 §06: ヘルスピル。高さ30px・padding 0 11px・radius 8px・bg Panel Raised・
// border 1px Line・font 11px・dotにbox-shadowのグロー。
const DOT_COLOR: Record<string, string> = {
  ok: "#3ed07e",
  bad: "#f26d6d",
  unknown: "#5d6b7b",
};

export function HealthPill({ name, ok }: Props) {
  const key = ok === null ? "unknown" : ok ? "ok" : "bad";
  const textColor =
    ok === null ? "text-jarvis-text3" : ok ? "text-jarvis-green" : "text-jarvis-red";
  const label = ok === null ? "不明" : ok ? "正常" : "未接続";
  return (
    <span
      className={`inline-flex h-[30px] items-center gap-[7px] rounded-lg border border-jarvis-line bg-jarvis-panel2 px-[11px] text-[11px] font-medium ${textColor}`}
    >
      <span
        className="h-2 w-2 rounded-full"
        style={{ backgroundColor: DOT_COLOR[key], boxShadow: `0 0 8px ${DOT_COLOR[key]}` }}
        aria-hidden
      />
      {name}: {label}
    </span>
  );
}
