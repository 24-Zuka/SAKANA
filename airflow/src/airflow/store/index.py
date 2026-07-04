"""SQLite索引（任意・検索/集計高速化用）— spec §4.5。

正データは常にMarkdown。この索引はtickets/*.mdから派生生成される二次的な
キャッシュであり、破損・消失しても`rebuild_index()`で再構築できる
（groom時に再構築される・§10）。
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from ..models import TaskCard
from .ticket_store import TicketStore

SCHEMA = """
CREATE TABLE IF NOT EXISTS tickets (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    category TEXT NOT NULL,
    status TEXT NOT NULL,
    priority INTEGER NOT NULL,
    risk_score REAL NOT NULL,
    due TEXT,
    decision_required INTEGER NOT NULL,
    updated TEXT NOT NULL
);
"""


def _row_for(ticket: TaskCard) -> tuple:
    return (
        ticket.id,
        ticket.title,
        ticket.category.value,
        ticket.status.value,
        ticket.priority,
        ticket.risk_score,
        ticket.due.isoformat() if ticket.due else None,
        1 if ticket.decision_required else 0,
        ticket.updated.isoformat(),
    )


def rebuild_index(store: TicketStore, index_path: Path) -> int:
    """tickets/*.md から index.sqlite を全件再構築する。戻り値は索引件数。"""
    index_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(index_path)
    try:
        conn.execute("DROP TABLE IF EXISTS tickets")
        conn.executescript(SCHEMA)
        tickets = store.list()
        conn.executemany(
            "INSERT INTO tickets "
            "(id, title, category, status, priority, risk_score, due, decision_required, updated) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [_row_for(t) for t in tickets],
        )
        conn.commit()
        return len(tickets)
    finally:
        conn.close()


def query_index(
    index_path: Path,
    *,
    status: str | None = None,
    category: str | None = None,
    decision_required: bool | None = None,
) -> list[dict]:
    """索引から条件検索する（速い経路・任意）。索引が無ければ空リストを返す。"""
    if not index_path.exists():
        return []
    conn = sqlite3.connect(index_path)
    conn.row_factory = sqlite3.Row
    try:
        clauses = []
        params: list = []
        if status is not None:
            clauses.append("status = ?")
            params.append(status)
        if category is not None:
            clauses.append("category = ?")
            params.append(category)
        if decision_required is not None:
            clauses.append("decision_required = ?")
            params.append(1 if decision_required else 0)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = conn.execute(f"SELECT * FROM tickets {where} ORDER BY id", params).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()
