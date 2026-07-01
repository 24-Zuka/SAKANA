from datetime import date, datetime, timezone

import pytest
from pydantic import ValidationError

from airflow.models import Assignee, Category, Source, Status, TaskCard


def make_ticket(**overrides) -> TaskCard:
    defaults = dict(
        id="TKT-20260628-001",
        task_id="TASK-2026-0628A",
        title="A社との提携レート再交渉の方針を決める",
        category=Category.BUSINESS,
        status=Status.WAITING,
        priority=1,
        risk_score=3.2,
        created=datetime(2026, 6, 28, 9, 0, tzinfo=timezone.utc),
        updated=datetime(2026, 6, 28, 9, 0, tzinfo=timezone.utc),
        due=date(2026, 7, 1),
        source=Source.EMAIL,
        assignee=Assignee.CODEX,
        tier=3,
        decision_required=True,
        dependencies=[],
        links=["[[rates]]", "TKT-20260620-004"],
        log=["2026-06-28T09:00 created by ai (classified by lmstudio)"],
        body="## 背景\n本文。",
    )
    defaults.update(overrides)
    return TaskCard(**defaults)


def test_round_trip_markdown():
    ticket = make_ticket()
    md = ticket.to_markdown()
    restored = TaskCard.from_markdown(md)
    assert restored.model_dump(mode="json") == ticket.model_dump(mode="json")


def test_markdown_contains_front_matter_and_body():
    ticket = make_ticket()
    md = ticket.to_markdown()
    assert md.startswith("---\n")
    assert "id: TKT-20260628-001" in md
    assert "## 背景" in md


def test_task_id_pattern_validation():
    with pytest.raises(ValidationError):
        make_ticket(task_id="NOT-VALID")


def test_task_id_optional():
    ticket = make_ticket(task_id=None)
    assert ticket.task_id is None


def test_risk_score_bounds():
    with pytest.raises(ValidationError):
        make_ticket(risk_score=0.0)
    with pytest.raises(ValidationError):
        make_ticket(risk_score=5.1)


def test_priority_bounds():
    with pytest.raises(ValidationError):
        make_ticket(priority=0)
    with pytest.raises(ValidationError):
        make_ticket(priority=4)
