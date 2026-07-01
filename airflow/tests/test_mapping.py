from datetime import date, datetime, timezone

from airflow.mapping import to_jarvis_priority, to_jarvis_status
from airflow.models import Assignee, Category, Source, Status, TaskCard


def make_ticket(**overrides) -> TaskCard:
    defaults = dict(
        id="TKT-20260628-001",
        title="t",
        category=Category.ENGINEERING,
        status=Status.WAITING,
        priority=2,
        risk_score=1.5,
        created=datetime(2026, 6, 28, 9, 0, tzinfo=timezone.utc),
        updated=datetime(2026, 6, 28, 9, 0, tzinfo=timezone.utc),
        due=None,
        source=Source.MANUAL,
        assignee=Assignee.HUMAN,
        tier=1,
    )
    defaults.update(overrides)
    return TaskCard(**defaults)


def test_status_mapping_table():
    assert to_jarvis_status(make_ticket(status=Status.INBOX)) == "TODO"
    assert to_jarvis_status(make_ticket(status=Status.TODAY)) == "TODO"
    assert to_jarvis_status(make_ticket(status=Status.DOING)) == "IN_PROGRESS"
    assert to_jarvis_status(make_ticket(status=Status.DONE)) == "DONE"


def test_waiting_defaults_to_awaiting_decision():
    assert to_jarvis_status(make_ticket(status=Status.WAITING)) == "AWAITING_DECISION"


def test_waiting_review_reason_maps_to_pending_review():
    ticket = make_ticket(status=Status.WAITING)
    assert to_jarvis_status(ticket, waiting_reason="review") == "PENDING_REVIEW"


def test_priority_mapping_defaults():
    assert to_jarvis_priority(make_ticket(priority=2)) == "MEDIUM"
    assert to_jarvis_priority(make_ticket(priority=3)) == "LOW"
    # priority 1 without a due date can't qualify for CRITICAL
    assert to_jarvis_priority(make_ticket(priority=1, due=None)) == "HIGH"


def test_priority_1_high_when_not_urgent_enough():
    now = date(2026, 6, 28)
    # due far away -> HIGH even with high risk
    ticket = make_ticket(priority=1, due=date(2026, 7, 10), risk_score=4.5)
    assert to_jarvis_priority(ticket, now=now) == "HIGH"
    # due soon but risk below 4.0 -> HIGH, not CRITICAL
    ticket2 = make_ticket(priority=1, due=date(2026, 6, 29), risk_score=3.9)
    assert to_jarvis_priority(ticket2, now=now) == "HIGH"


def test_priority_1_critical_when_due_within_24h_and_high_risk():
    now = date(2026, 6, 28)
    ticket = make_ticket(priority=1, due=date(2026, 6, 29), risk_score=4.0)
    assert to_jarvis_priority(ticket, now=now) == "CRITICAL"
