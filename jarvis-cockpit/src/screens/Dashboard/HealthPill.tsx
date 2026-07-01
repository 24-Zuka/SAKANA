interface Props {
  name: string;
  ok: boolean | null; // null = 不明
}

export function HealthPill({ name, ok }: Props) {
  const color =
    ok === null
      ? "border-jarvis-border text-jarvis-text-muted"
      : ok
        ? "border-jarvis-success/40 text-jarvis-success"
        : "border-jarvis-danger/40 text-jarvis-danger";
  const label = ok === null ? "不明" : ok ? "正常" : "未接続";
  return (
    <span className={`inline-flex items-center gap-1.5 rounded border px-2.5 py-1 text-xs ${color}`}>
      <span
        className={`h-1.5 w-1.5 rounded-full ${
          ok === null ? "bg-jarvis-text-muted" : ok ? "bg-jarvis-success" : "bg-jarvis-danger"
        }`}
        aria-hidden
      />
      {name}: {label}
    </span>
  );
}
