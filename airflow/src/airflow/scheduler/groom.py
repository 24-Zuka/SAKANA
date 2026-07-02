"""夜間グルーミング — spec §10。

期限切れチケットへの注記、Doneチケットの圧縮（tickets/archive/への退避）、
SQLite索引（§4.5）の再構築を行う。
"""

from __future__ import annotations

from datetime import date, datetime

from ..models import Status
from ..store.index import rebuild_index
from ..store.ticket_store import TicketStore

DEFAULT_ARCHIVE_AFTER_DAYS = 30


def flag_overdue_tickets(store: TicketStore, *, now: datetime | None = None) -> list[str]:
    """期限切れかつ未完了のチケットにログで注記する（ステータスは変更しない）。"""
    now = now or datetime.now().astimezone()
    today = now.date() if isinstance(now, datetime) else now
    flagged: list[str] = []
    for ticket in store.list():
        if ticket.status == Status.DONE or ticket.due is None:
            continue
        if ticket.due < today and not any("期限切れ" in line for line in ticket.log):
            store.update(
                ticket.id,
                log=ticket.log + [f"{now.isoformat(timespec='seconds')} 期限切れ（due={ticket.due}）"],
            )
            flagged.append(ticket.id)
    return flagged


def archive_done_tickets(
    store: TicketStore, *, older_than_days: int = DEFAULT_ARCHIVE_AFTER_DAYS, now: datetime | None = None
) -> list[str]:
    """更新から一定日数が経過したDoneチケットを tickets/archive/ へ退避する。"""
    now = now or datetime.now().astimezone()
    archive_dir = store.tickets_dir / "archive"
    archived: list[str] = []
    for ticket in store.list(status=Status.DONE):
        updated = ticket.updated
        if updated.tzinfo is None:
            age_days = (now.replace(tzinfo=None) - updated).days
        else:
            age_days = (now - updated).days
        if age_days < older_than_days:
            continue
        archive_dir.mkdir(parents=True, exist_ok=True)
        src = store.tickets_dir / f"{ticket.id}.md"
        dest = archive_dir / f"{ticket.id}.md"
        src.rename(dest)
        archived.append(ticket.id)
    return archived


def groom(store: TicketStore, *, now: datetime | None = None) -> dict[str, object]:
    now = now or datetime.now().astimezone()
    flagged = flag_overdue_tickets(store, now=now)
    archived = archive_done_tickets(store, now=now)
    indexed_count = rebuild_index(store, store.root / "index.sqlite")
    return {"flagged_overdue": flagged, "archived_done": archived, "indexed_count": indexed_count}
