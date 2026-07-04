from datetime import datetime, timezone

import pytest

from airflow.adapters.base import AdapterUnavailable, Result
from airflow.config import AirflowConfig
from airflow.models import Category, Source, Status, TaskCard
from airflow.orchestrator.budget import BudgetTracker
from airflow.orchestrator.run import run_ticket
from airflow.store.ticket_store import TicketStore


class FakeWorker:
    """run()を持つ Codex/Gemini 用のテストダブル。結果を順番に返す。"""

    def __init__(self, worker: str, results: list[Result]):
        self.worker = worker
        self._results = list(results)
        self.calls: list[str] = []

    def run(self, prompt: str, context=None) -> Result:
        self.calls.append(prompt)
        if len(self._results) > 1:
            return self._results.pop(0)
        return self._results[0]


class FakeLMStudio(FakeWorker):
    """verify()も持つ LM Studio 用のテストダブル。"""

    def __init__(self, results: list[Result], verify_results: list):
        super().__init__("lmstudio", results)
        self._verify_results = list(verify_results)
        self.verify_calls: list[tuple[str, str]] = []

    def verify(self, artifact: str, criteria: str):
        self.verify_calls.append((artifact, criteria))
        item = self._verify_results.pop(0) if len(self._verify_results) > 1 else self._verify_results[0]
        if isinstance(item, Exception):
            raise item
        return item


def _make_ticket(store: TicketStore, **overrides) -> TaskCard:
    now = datetime(2026, 7, 1, 9, 0, tzinfo=timezone.utc)
    defaults = dict(
        id=store.next_id(on=now),
        title="サーバーのバグを修正する",
        category=Category.ENGINEERING,
        status=Status.TODAY,
        priority=2,
        risk_score=1.5,
        created=now,
        updated=now,
        source=Source.MANUAL,
        body="詳細な背景説明",
    )
    defaults.update(overrides)
    ticket = TaskCard(**defaults)
    store.create(ticket)
    return ticket


def _config(tmp_path) -> AirflowConfig:
    return AirflowConfig(home=tmp_path)


def test_successful_loop_marks_ticket_done(tmp_path):
    store = TicketStore(tmp_path)
    ticket = _make_ticket(store)
    config = _config(tmp_path)
    budget = BudgetTracker(tmp_path / "budget.json")

    codex = FakeWorker("codex", [Result(True, "計画: バグを直す", "codex", 0.1, None)])
    gemini = FakeWorker("gemini", [Result(True, "unused", "gemini", 0.1, None)])
    lmstudio = FakeLMStudio(
        [Result(True, "unused", "lmstudio", 0.1, None)],
        [(True, "基準を満たす")],
    )

    updated = run_ticket(
        ticket.id, store, config, budget=budget, codex=codex, gemini=gemini, lmstudio=lmstudio
    )

    assert updated.status == Status.DONE
    assert updated.decision_required is False
    assert any("Plan by codex: ok" in line for line in updated.log)
    assert any("Execute by codex: ok" in line for line in updated.log)
    assert any("Verify by lmstudio: pass" in line for line in updated.log)


def test_plan_failure_falls_back_to_ticket_text(tmp_path):
    store = TicketStore(tmp_path)
    ticket = _make_ticket(store)
    config = _config(tmp_path)
    budget = BudgetTracker(tmp_path / "budget.json")

    codex = FakeWorker(
        "codex",
        [
            Result(False, "", "codex", 0.1, "codex CLI unavailable"),
            Result(True, "実行結果", "codex", 0.1, None),
        ],
    )
    gemini = FakeWorker("gemini", [Result(True, "unused", "gemini", 0.1, None)])
    lmstudio = FakeLMStudio(
        [Result(True, "unused", "lmstudio", 0.1, None)],
        [(True, "基準を満たす")],
    )

    updated = run_ticket(
        ticket.id, store, config, budget=budget, codex=codex, gemini=gemini, lmstudio=lmstudio
    )

    assert any("Plan by codex failed" in line for line in updated.log)
    assert updated.status == Status.DONE


def test_verify_failure_then_success_retries(tmp_path):
    store = TicketStore(tmp_path)
    ticket = _make_ticket(store)
    config = _config(tmp_path)
    budget = BudgetTracker(tmp_path / "budget.json")

    codex = FakeWorker(
        "codex",
        [
            Result(True, "計画", "codex", 0.1, None),
            Result(True, "実行結果1", "codex", 0.1, None),
            Result(True, "実行結果2", "codex", 0.1, None),
        ],
    )
    gemini = FakeWorker("gemini", [Result(True, "unused", "gemini", 0.1, None)])
    lmstudio = FakeLMStudio(
        [Result(True, "unused", "lmstudio", 0.1, None)],
        [(False, "基準未達"), (True, "今度は合格")],
    )

    updated = run_ticket(
        ticket.id, store, config, budget=budget, codex=codex, gemini=gemini, lmstudio=lmstudio, max_retries=3
    )

    assert updated.status == Status.DONE
    fail_lines = [line for line in updated.log if "Verify by lmstudio: fail" in line]
    pass_lines = [line for line in updated.log if "Verify by lmstudio: pass" in line]
    assert len(fail_lines) == 1
    assert len(pass_lines) == 1


def test_exceeding_max_retries_escalates_to_human(tmp_path):
    store = TicketStore(tmp_path)
    ticket = _make_ticket(store)
    config = _config(tmp_path)
    budget = BudgetTracker(tmp_path / "budget.json")

    codex = FakeWorker("codex", [Result(True, "計画", "codex", 0.1, None)])
    gemini = FakeWorker("gemini", [Result(True, "unused", "gemini", 0.1, None)])
    lmstudio = FakeLMStudio(
        [Result(True, "unused", "lmstudio", 0.1, None)],
        [(False, "基準未達")],
    )

    updated = run_ticket(
        ticket.id, store, config, budget=budget, codex=codex, gemini=gemini, lmstudio=lmstudio, max_retries=2
    )

    assert updated.status == Status.WAITING
    assert updated.decision_required is True
    assert any("人間の判断へエスカレーション" in line for line in updated.log)


def test_execute_failure_every_attempt_escalates(tmp_path):
    store = TicketStore(tmp_path)
    ticket = _make_ticket(store)
    config = _config(tmp_path)
    budget = BudgetTracker(tmp_path / "budget.json")

    codex = FakeWorker(
        "codex",
        [
            Result(True, "計画", "codex", 0.1, None),
            Result(False, "", "codex", 0.1, "実行失敗"),
        ],
    )
    gemini = FakeWorker("gemini", [Result(True, "unused", "gemini", 0.1, None)])
    lmstudio = FakeLMStudio(
        [Result(True, "unused", "lmstudio", 0.1, None)],
        [(True, "基準を満たす")],
    )

    updated = run_ticket(
        ticket.id, store, config, budget=budget, codex=codex, gemini=gemini, lmstudio=lmstudio, max_retries=2
    )

    assert updated.status == Status.WAITING
    assert updated.decision_required is True
    assert lmstudio.verify_calls == []  # Executeが失敗し続けるためVerifyには到達しない


def test_worker_call_limit_escalates_early(tmp_path):
    store = TicketStore(tmp_path)
    ticket = _make_ticket(store)
    config = _config(tmp_path)
    budget = BudgetTracker(tmp_path / "budget.json")

    codex = FakeWorker("codex", [Result(True, "計画", "codex", 0.1, None)])
    gemini = FakeWorker("gemini", [Result(True, "unused", "gemini", 0.1, None)])
    lmstudio = FakeLMStudio(
        [Result(True, "unused", "lmstudio", 0.1, None)],
        [(False, "基準未達")],
    )

    updated = run_ticket(
        ticket.id,
        store,
        config,
        budget=budget,
        codex=codex,
        gemini=gemini,
        lmstudio=lmstudio,
        max_retries=10,
        max_worker_calls=2,
    )

    assert updated.status == Status.WAITING
    assert any("worker呼び出し上限" in line for line in updated.log)


def test_verify_unavailable_falls_back_to_nonempty_rule(tmp_path):
    store = TicketStore(tmp_path)
    ticket = _make_ticket(store)
    config = _config(tmp_path)
    budget = BudgetTracker(tmp_path / "budget.json")

    codex = FakeWorker(
        "codex",
        [Result(True, "計画", "codex", 0.1, None), Result(True, "非空の実行結果", "codex", 0.1, None)],
    )
    gemini = FakeWorker("gemini", [Result(True, "unused", "gemini", 0.1, None)])
    lmstudio = FakeLMStudio(
        [Result(True, "unused", "lmstudio", 0.1, None)],
        [AdapterUnavailable("LM Studio not running")],
    )

    updated = run_ticket(
        ticket.id, store, config, budget=budget, codex=codex, gemini=gemini, lmstudio=lmstudio
    )

    assert updated.status == Status.DONE
    assert any("Verify by lmstudio unavailable" in line for line in updated.log)
