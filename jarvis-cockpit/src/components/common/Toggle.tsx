// デザイン仕様書 §06: トグル 38×22px・radius 11px。ON=Accent/つまみleft:18px。OFF=Raise+border/left:2px。
export function Toggle({
  checked,
  onChange,
  label,
}: {
  checked: boolean;
  onChange: (checked: boolean) => void;
  label?: string;
}) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      aria-label={label}
      onClick={() => onChange(!checked)}
      className={`relative inline-block h-[22px] w-[38px] shrink-0 rounded-full transition-colors ${
        checked ? "bg-jarvis-accent" : "border border-jarvis-line bg-jarvis-raise"
      }`}
    >
      <span
        className="absolute top-[2px] h-4 w-4 rounded-full bg-white transition-all"
        style={{ left: checked ? 18 : 2 }}
      />
    </button>
  );
}
