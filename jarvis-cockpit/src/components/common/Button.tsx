import type { ButtonHTMLAttributes } from "react";

// デザイン仕様書 §06: プライマリ/ゴースト、高さ30px・padding 0 13px・radius 8px・12px/600。
type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement>;

export function PrimaryButton({ className = "", ...props }: ButtonProps) {
  return (
    <button
      type="button"
      className={`inline-flex h-[30px] items-center rounded-lg bg-jarvis-accent px-[13px] text-xs font-semibold text-[#04101f] hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-40 ${className}`}
      {...props}
    />
  );
}

export function GhostButton({ className = "", ...props }: ButtonProps) {
  return (
    <button
      type="button"
      className={`inline-flex h-[30px] items-center rounded-lg border border-jarvis-line bg-transparent px-[13px] text-xs font-semibold text-jarvis-text hover:bg-jarvis-panel2 disabled:cursor-not-allowed disabled:opacity-40 ${className}`}
      {...props}
    />
  );
}
