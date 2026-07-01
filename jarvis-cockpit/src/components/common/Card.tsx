import type { ReactNode } from "react";

// デザイン仕様書 §08: カード角丸12–14px、Panel背景、密度重視で余白最小。
export function Card({
  children,
  className = "",
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <section
      className={`rounded-[13px] border border-jarvis-line bg-jarvis-panel p-[18px] ${className}`}
    >
      {children}
    </section>
  );
}

export function CardHeading({ children }: { children: ReactNode }) {
  return (
    <h2 className="text-[11px] font-semibold uppercase tracking-[1.3px] text-jarvis-text3">
      {children}
    </h2>
  );
}
