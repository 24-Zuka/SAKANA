from datetime import datetime

from airflow.orchestrator.budget import BudgetTracker
from airflow.orchestrator.router import route


def test_routes_classify_summarize_verify_to_lmstudio(tmp_path):
    budget = BudgetTracker(tmp_path / "budget.json")
    for kind in ("classify", "summarize", "verify"):
        assert route(kind, budget) == "lmstudio"


def test_routes_plan_and_code_to_codex(tmp_path):
    budget = BudgetTracker(tmp_path / "budget.json")
    assert route("plan", budget) == "codex"
    assert route("code", budget) == "codex"


def test_routes_long_context_and_multimodal_to_gemini(tmp_path):
    budget = BudgetTracker(tmp_path / "budget.json")
    assert route("long_context", budget) == "gemini"
    assert route("multimodal", budget) == "gemini"


def test_unknown_kind_defaults_to_lmstudio(tmp_path):
    budget = BudgetTracker(tmp_path / "budget.json")
    assert route("something_unrecognized", budget) == "lmstudio"


def test_downgrades_codex_to_lmstudio_when_budget_exhausted(tmp_path):
    budget = BudgetTracker(tmp_path / "budget.json")
    now = datetime(2026, 7, 1, 12, 0)
    for _ in range(30):
        budget.record_call("codex", now=now)
    assert route("code", budget, now=now) == "lmstudio"


def test_downgrades_gemini_to_lmstudio_when_budget_exhausted(tmp_path):
    budget = BudgetTracker(tmp_path / "budget.json")
    now = datetime(2026, 7, 1, 12, 0)
    for _ in range(30):
        budget.record_call("gemini", now=now)
    assert route("long_context", budget, now=now) == "lmstudio"
