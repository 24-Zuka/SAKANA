"""AirFlow ⇔ JARVIS status/priority 対応表 — spec §4.4。

AirFlow の語彙を正とし、JARVIS TaskCard 値は互換マッピングで書き出す際に使う。
逆変換（AirFlow→JARVIS）は1対多を解消するため、既定値を決め打ちする。
"""

from __future__ import annotations

from datetime import date, datetime

from .models import Status, TaskCard

STATUS_TO_JARVIS: dict[Status, str] = {
    Status.INBOX: "TODO",
    Status.TODAY: "TODO",
    Status.DOING: "IN_PROGRESS",
    Status.WAITING: "AWAITING_DECISION",
    Status.DONE: "DONE",
}

PRIORITY_TO_JARVIS: dict[int, str] = {
    1: "HIGH",
    2: "MEDIUM",
    3: "LOW",
}


def to_jarvis_status(ticket: TaskCard, *, waiting_reason: str = "decision") -> str:
    """AirFlow status → JARVIS status。

    既定値: Waiting → AWAITING_DECISION。
    `waiting_reason="review"` の場合のみ PENDING_REVIEW（レビュー起因の保留）。
    """
    if ticket.status == Status.WAITING and waiting_reason == "review":
        return "PENDING_REVIEW"
    return STATUS_TO_JARVIS[ticket.status]


def to_jarvis_priority(ticket: TaskCard, *, now: datetime | date | None = None) -> str:
    """AirFlow priority → JARVIS priority。

    既定値: priority==1 → HIGH。
    `due` が24h以内 かつ `risk_score>=4.0` の時のみ CRITICAL。
    """
    if ticket.priority == 1 and ticket.due is not None:
        reference = now.date() if isinstance(now, datetime) else (now or date.today())
        within_24h = (ticket.due - reference).days <= 1
        if within_24h and ticket.risk_score >= 4.0:
            return "CRITICAL"
    return PRIORITY_TO_JARVIS[ticket.priority]
