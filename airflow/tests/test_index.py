from datetime import datetime, timezone

from airflow.models import Category, Source, Status, TaskCard
from airflow.store.index import query_index, rebuild_index
from airflow.store.ticket_store import TicketStore


def _ticket(store, **overrides) -> TaskCard:
    now = datetime(2026, 7, 1, 9, 0, tzinfo=timezone.utc)
    defaults = dict(
        id=store.next_id(on=now),
        title="t",
        category=Category.BUSINESS,
        status=Status.WAITING,
        priority=1,
        risk_score=3.2,
        created=now,
        updated=now,
        source=Source.MANUAL,
        decision_required=True,
    )
    defaults.update(overrides)
    ticket = TaskCard(**defaults)
    store.create(ticket)
    return ticket


def test_rebuild_index_creates_expected_rows(tmp_path):
    store = TicketStore(tmp_path)
    t1 = _ticket(store, category=Category.ENGINEERING, status=Status.DOING, decision_required=False)
    t2 = _ticket(store, id=store.next_id(on=datetime(2026, 7, 1, tzinfo=timezone.utc)))

    index_path = tmp_path / "index.sqlite"
    count = rebuild_index(store, index_path)
    assert count == 2
    assert index_path.exists()

    rows = query_index(index_path)
    ids = {r["id"] for r in rows}
    assert ids == {t1.id, t2.id}


def test_query_index_filters_by_status_category_decision(tmp_path):
    store = TicketStore(tmp_path)
    t1 = _ticket(store, category=Category.ENGINEERING, status=Status.DOING, decision_required=False)
    t2 = _ticket(
        store,
        id=store.next_id(on=datetime(2026, 7, 1, tzinfo=timezone.utc)),
        category=Category.BUSINESS,
        status=Status.WAITING,
        decision_required=True,
    )
    index_path = tmp_path / "index.sqlite"
    rebuild_index(store, index_path)

    assert [r["id"] for r in query_index(index_path, status="Doing")] == [t1.id]
    assert [r["id"] for r in query_index(index_path, category="Business")] == [t2.id]
    assert [r["id"] for r in query_index(index_path, decision_required=True)] == [t2.id]


def test_rebuild_is_idempotent_and_drops_stale_rows(tmp_path):
    store = TicketStore(tmp_path)
    ticket = _ticket(store)
    index_path = tmp_path / "index.sqlite"
    rebuild_index(store, index_path)

    store.delete(ticket.id)
    count = rebuild_index(store, index_path)
    assert count == 0
    assert query_index(index_path) == []


def test_query_index_returns_empty_when_missing(tmp_path):
    assert query_index(tmp_path / "does_not_exist.sqlite") == []
