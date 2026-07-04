from datetime import datetime, timedelta, timezone

from airflow.models import Category, Source, Status, TaskCard
from airflow.scheduler.groom import archive_done_tickets, flag_overdue_tickets, groom
from airflow.store.ticket_store import TicketStore


def _ticket(store, **overrides) -> TaskCard:
    now = datetime(2026, 7, 1, 9, 0, tzinfo=timezone.utc)
    defaults = dict(
        id=store.next_id(on=now),
        title="t",
        category=Category.BUSINESS,
        status=Status.TODAY,
        priority=2,
        risk_score=1.0,
        created=now,
        updated=now,
        source=Source.MANUAL,
    )
    defaults.update(overrides)
    ticket = TaskCard(**defaults)
    store.create(ticket)
    return ticket


def test_flag_overdue_tickets_adds_log_note(tmp_path):
    store = TicketStore(tmp_path)
    ticket = _ticket(store, due=None)
    store.update(ticket.id, due=__import__("datetime").date(2026, 6, 1))
    now = datetime(2026, 7, 1, tzinfo=timezone.utc)

    flagged = flag_overdue_tickets(store, now=now)
    assert flagged == [ticket.id]
    refreshed = store.get(ticket.id)
    assert any("期限切れ" in line for line in refreshed.log)


def test_flag_overdue_tickets_is_idempotent(tmp_path):
    store = TicketStore(tmp_path)
    ticket = _ticket(store)
    store.update(ticket.id, due=__import__("datetime").date(2026, 6, 1))
    now = datetime(2026, 7, 1, tzinfo=timezone.utc)

    flag_overdue_tickets(store, now=now)
    second_pass = flag_overdue_tickets(store, now=now)
    assert second_pass == []


def test_flag_overdue_skips_done_tickets(tmp_path):
    store = TicketStore(tmp_path)
    ticket = _ticket(store, status=Status.DONE)
    store.update(ticket.id, due=__import__("datetime").date(2026, 6, 1))
    now = datetime(2026, 7, 1, tzinfo=timezone.utc)
    assert flag_overdue_tickets(store, now=now) == []


def test_archive_done_tickets_moves_old_done_tickets(tmp_path):
    store = TicketStore(tmp_path)
    old_done = _ticket(store, status=Status.DONE)
    recent_done = _ticket(
        store,
        id=store.next_id(on=datetime(2026, 7, 1, tzinfo=timezone.utc)),
        status=Status.DONE,
        updated=datetime(2026, 7, 26, tzinfo=timezone.utc),
    )

    now = datetime(2026, 7, 1, 9, 0, tzinfo=timezone.utc)
    archived = archive_done_tickets(store, older_than_days=30, now=now + timedelta(days=31))

    assert archived == [old_done.id]
    assert (store.tickets_dir / "archive" / f"{old_done.id}.md").exists()
    assert not (store.tickets_dir / f"{old_done.id}.md").exists()
    # 直近のDoneはアーカイブされない
    assert (store.tickets_dir / f"{recent_done.id}.md").exists()


def test_archived_tickets_disappear_from_list(tmp_path):
    store = TicketStore(tmp_path)
    ticket = _ticket(store, status=Status.DONE)
    now = datetime(2026, 7, 1, 9, 0, tzinfo=timezone.utc)
    archive_done_tickets(store, older_than_days=30, now=now + timedelta(days=31))
    assert store.list() == []


def test_groom_runs_both_steps(tmp_path):
    store = TicketStore(tmp_path)
    overdue = _ticket(store)
    store.update(overdue.id, due=__import__("datetime").date(2026, 6, 1))
    old_done = _ticket(
        store,
        id=store.next_id(on=datetime(2026, 6, 1, tzinfo=timezone.utc)),
        status=Status.DONE,
        updated=datetime(2026, 6, 1, tzinfo=timezone.utc),
    )

    now = datetime(2026, 7, 1, 9, 0, tzinfo=timezone.utc)
    result = groom(store, now=now)

    assert overdue.id in result["flagged_overdue"]
    assert old_done.id in result["archived_done"]
    assert result["indexed_count"] == 1  # old_doneはアーカイブ済みのためoverdueのみ索引される
    assert (store.root / "index.sqlite").exists()
