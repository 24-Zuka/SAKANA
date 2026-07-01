from datetime import datetime, timezone

import pytest

from airflow.models import Category, Source, Status, TaskCard
from airflow.store.ticket_store import TicketNotFoundError, TicketStore


def make_ticket(store: TicketStore, **overrides) -> TaskCard:
    now = datetime(2026, 6, 28, 9, 0, tzinfo=timezone.utc)
    defaults = dict(
        id=store.next_id(on=now),
        title="test ticket",
        category=Category.ENGINEERING,
        status=Status.INBOX,
        priority=2,
        risk_score=1.5,
        created=now,
        updated=now,
        source=Source.MANUAL,
    )
    defaults.update(overrides)
    return TaskCard(**defaults)


def test_next_id_increments(tmp_path):
    store = TicketStore(tmp_path)
    now = datetime(2026, 6, 28)
    first = store.next_id(on=now)
    assert first == "TKT-20260628-001"
    store.create(make_ticket(store, id=first))
    second = store.next_id(on=now)
    assert second == "TKT-20260628-002"


def test_create_and_get_round_trip(tmp_path):
    store = TicketStore(tmp_path)
    ticket = make_ticket(store)
    store.create(ticket)
    fetched = store.get(ticket.id)
    assert fetched.title == ticket.title
    assert fetched.id == ticket.id


def test_create_duplicate_raises(tmp_path):
    store = TicketStore(tmp_path)
    ticket = make_ticket(store)
    store.create(ticket)
    with pytest.raises(FileExistsError):
        store.create(ticket)


def test_get_missing_raises(tmp_path):
    store = TicketStore(tmp_path)
    with pytest.raises(TicketNotFoundError):
        store.get("TKT-20260101-999")


def test_update_changes_fields_and_bumps_updated(tmp_path):
    store = TicketStore(tmp_path)
    ticket = make_ticket(store)
    store.create(ticket)
    updated = store.update(ticket.id, status=Status.DOING, priority=1)
    assert updated.status == Status.DOING
    assert updated.priority == 1
    assert updated.updated >= ticket.updated
    refetched = store.get(ticket.id)
    assert refetched.status == Status.DOING


def test_delete_removes_ticket(tmp_path):
    store = TicketStore(tmp_path)
    ticket = make_ticket(store)
    store.create(ticket)
    store.delete(ticket.id)
    with pytest.raises(TicketNotFoundError):
        store.get(ticket.id)


def test_list_filters_by_status_category_decision(tmp_path):
    store = TicketStore(tmp_path)
    t1 = make_ticket(store, category=Category.BUSINESS, status=Status.WAITING, decision_required=True)
    store.create(t1)
    t2 = make_ticket(store, id=store.next_id(on=datetime(2026, 6, 28)), category=Category.ENGINEERING, status=Status.DOING)
    store.create(t2)

    assert [t.id for t in store.list(status=Status.WAITING)] == [t1.id]
    assert [t.id for t in store.list(category=Category.ENGINEERING)] == [t2.id]
    assert [t.id for t in store.list(decision_required=True)] == [t1.id]
    assert len(store.list()) == 2
