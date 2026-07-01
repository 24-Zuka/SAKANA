from airflow.inbox import import_inbox
from airflow.models import Category, Status
from airflow.store.ticket_store import TicketStore


def test_import_inbox_creates_ticket_with_rule_based_fallback(tmp_path):
    store = TicketStore(tmp_path)
    ticket = import_inbox(store, "A社との提携レート再交渉の方針を決めたい")

    assert ticket.category == Category.BUSINESS
    assert ticket.decision_required is True
    assert ticket.status == Status.WAITING
    assert ticket.tier == 2
    assert "created by ai" in ticket.log[0]

    refetched = store.get(ticket.id)
    assert refetched.title == ticket.title


def test_import_inbox_external_send_forces_waiting(tmp_path):
    store = TicketStore(tmp_path)
    ticket = import_inbox(store, "請求書PDFの支払いを実行してメールで完了報告を送信する")
    assert ticket.status == Status.WAITING
    assert ticket.decision_required is True
    assert ticket.risk_score >= 3.0  # 承認モーダル必須の閾値


def test_import_inbox_routine_task_goes_to_today(tmp_path):
    store = TicketStore(tmp_path)
    ticket = import_inbox(store, "動画のサムネイル案を3パターン作る")
    assert ticket.status == Status.TODAY
    assert ticket.decision_required is False
