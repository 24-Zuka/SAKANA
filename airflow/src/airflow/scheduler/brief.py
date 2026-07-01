"""朝礼レポート生成 — spec §9。

フロー（§9.1）:
  動的ストアから decision_required=true と status=Today を収集
  → Business / Engineering / Content で分類し「処理しやすい順」にソート
  → briefs/YYYY-MM-DD.md へ出力
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

from ..models import Category, Status, TaskCard
from ..store.ticket_store import TicketStore

CATEGORY_ORDER = (Category.BUSINESS, Category.ENGINEERING, Category.CONTENT)


def _sort_key(ticket: TaskCard):
    # 「処理しやすい順」＝ risk_score が高いもの・期限が近いものを先に。
    due_sort = ticket.due or date.max
    return (-ticket.risk_score, due_sort)


def _collect_decision_items(store: TicketStore) -> dict[Category, list[TaskCard]]:
    candidates = {t.id: t for t in store.list(decision_required=True)}
    for t in store.list(status=Status.TODAY):
        candidates[t.id] = t

    grouped: dict[Category, list[TaskCard]] = {c: [] for c in CATEGORY_ORDER}
    for ticket in candidates.values():
        grouped[ticket.category].append(ticket)
    for category in grouped:
        grouped[category].sort(key=_sort_key)
    return grouped


def render_brief(grouped: dict[Category, list[TaskCard]], in_progress: list[TaskCard], *, on: date) -> str:
    total = sum(len(items) for items in grouped.values())
    lines = [f"# 朝礼 {on.isoformat()}", "", f"## 今日の要判断（{total}件）"]

    counter = 1
    for category in CATEGORY_ORDER:
        items = grouped[category]
        if not items:
            continue
        lines.append(f"### {category.value}")
        for ticket in items:
            due_str = f"（期限: {ticket.due.strftime('%m-%d')}）" if ticket.due else ""
            lines.append(f"{counter}. [{ticket.id}] {ticket.title}{due_str}")
            counter += 1

    lines.append("")
    lines.append("## 進行中（参考）")
    if in_progress:
        for ticket in in_progress:
            lines.append(f"- [{ticket.id}] {ticket.title}")
    else:
        lines.append("- （なし）")

    return "\n".join(lines) + "\n"


def generate_brief(store: TicketStore, briefs_dir: Path, *, on: date | None = None) -> Path:
    on = on or date.today()
    grouped = _collect_decision_items(store)
    in_progress = store.list(status=Status.DOING)

    content = render_brief(grouped, in_progress, on=on)

    briefs_dir.mkdir(parents=True, exist_ok=True)
    path = briefs_dir / f"{on.isoformat()}.md"
    path.write_text(content, encoding="utf-8")
    return path
