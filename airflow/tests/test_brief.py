from datetime import date, datetime, timezone

from airflow.models import Category, Source, Status, TaskCard
from airflow.scheduler.brief import generate_brief
from airflow.store.ticket_store import TicketStore


def make_ticket(store, **overrides) -> TaskCard:
    now = datetime(2026, 6, 28, 9, 0, tzinfo=timezone.utc)
    defaults = dict(
        id=store.next_id(on=now),
        title="ticket",
        category=Category.BUSINESS,
        status=Status.WAITING,
        priority=2,
        risk_score=1.0,
        created=now,
        updated=now,
        source=Source.MANUAL,
        decision_required=False,
    )
    defaults.update(overrides)
    ticket = TaskCard(**defaults)
    store.create(ticket)
    return ticket


def test_brief_groups_by_category_and_writes_file(tmp_path):
    store = TicketStore(tmp_path / "store")
    b1 = make_ticket(
        store,
        title="A社レート再交渉の方針",
        category=Category.BUSINESS,
        decision_required=True,
        due=date(2026, 7, 1),
        risk_score=3.2,
    )
    e1 = make_ticket(
        store,
        title="バックアップ先の決定",
        category=Category.ENGINEERING,
        status=Status.TODAY,
        risk_score=2.0,
    )
    c1 = make_ticket(
        store,
        title="次回動画のテーマ確定",
        category=Category.CONTENT,
        decision_required=True,
        risk_score=1.0,
    )
    doing = make_ticket(store, title="実装中の何か", category=Category.ENGINEERING, status=Status.DOING)

    briefs_dir = tmp_path / "briefs"
    path = generate_brief(store, briefs_dir, on=date(2026, 6, 28))

    assert path == briefs_dir / "2026-06-28.md"
    content = path.read_text(encoding="utf-8")

    assert "# 朝礼 2026-06-28" in content
    assert "## 今日の要判断（3件）" in content
    assert "### Business" in content
    assert f"[{b1.id}] A社レート再交渉の方針（期限: 07-01）" in content
    assert "### Engineering" in content
    assert f"[{e1.id}] バックアップ先の決定" in content
    assert "### Content" in content
    assert f"[{c1.id}] 次回動画のテーマ確定" in content
    assert "## 進行中（参考）" in content
    assert f"[{doing.id}] 実装中の何か" in content


def test_brief_excludes_non_decision_non_today(tmp_path):
    store = TicketStore(tmp_path / "store")
    make_ticket(store, title="ただのInboxチケット", status=Status.INBOX, decision_required=False)
    briefs_dir = tmp_path / "briefs"
    path = generate_brief(store, briefs_dir, on=date(2026, 6, 28))
    content = path.read_text(encoding="utf-8")
    assert "ただのInboxチケット" not in content
    assert "## 今日の要判断（0件）" in content


def test_brief_sorts_by_risk_score_descending_within_category(tmp_path):
    store = TicketStore(tmp_path / "store")
    low = make_ticket(store, title="低リスク", decision_required=True, risk_score=1.0)
    high = make_ticket(store, title="高リスク", decision_required=True, risk_score=4.0)

    briefs_dir = tmp_path / "briefs"
    path = generate_brief(store, briefs_dir, on=date(2026, 6, 28))
    content = path.read_text(encoding="utf-8")
    assert content.index("高リスク") < content.index("低リスク")
