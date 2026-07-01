import type { Category } from "../../types/taskcard";

// デザイン仕様書 §02/§06: カテゴリ色 Business=Accent / Engineering=Teal / Content=Yellow。
const CATEGORY_STYLES: Record<Category, string> = {
  Business: "text-jarvis-accent bg-jarvis-accent/12",
  Engineering: "text-jarvis-teal bg-jarvis-teal/12",
  Content: "text-jarvis-yellow bg-jarvis-yellow/12",
};

export function CategoryBadge({ category }: { category: Category }) {
  return (
    <span
      className={`inline-flex items-center rounded-[5px] px-2 py-0.5 text-[11px] font-semibold ${CATEGORY_STYLES[category]}`}
    >
      {category}
    </span>
  );
}
