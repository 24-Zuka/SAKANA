from datetime import datetime, timedelta

from airflow.orchestrator.budget import BudgetTracker


def test_record_and_count_calls_in_window(tmp_path):
    tracker = BudgetTracker(tmp_path / "budget.json")
    now = datetime(2026, 7, 1, 12, 0)
    tracker.record_call("codex", now=now)
    tracker.record_call("codex", now=now - timedelta(hours=1))
    tracker.record_call("gemini", now=now)

    assert tracker.calls_in_window("codex", now=now) == 2
    assert tracker.calls_in_window("gemini", now=now) == 1


def test_calls_outside_window_are_excluded(tmp_path):
    tracker = BudgetTracker(tmp_path / "budget.json")
    now = datetime(2026, 7, 1, 12, 0)
    tracker.record_call("codex", now=now - timedelta(hours=6))
    assert tracker.calls_in_window("codex", window_hours=5, now=now) == 0


def test_should_downgrade_when_threshold_reached(tmp_path):
    tracker = BudgetTracker(tmp_path / "budget.json")
    now = datetime(2026, 7, 1, 12, 0)
    for _ in range(3):
        tracker.record_call("codex", now=now)
    assert tracker.should_downgrade("codex", threshold=3, now=now) is True
    assert tracker.should_downgrade("codex", threshold=4, now=now) is False


def test_persists_across_instances(tmp_path):
    path = tmp_path / "budget.json"
    tracker1 = BudgetTracker(path)
    now = datetime(2026, 7, 1, 12, 0)
    tracker1.record_call("codex", now=now)

    tracker2 = BudgetTracker(path)
    assert tracker2.calls_in_window("codex", now=now) == 1


def test_missing_file_starts_empty(tmp_path):
    tracker = BudgetTracker(tmp_path / "does_not_exist.json")
    assert tracker.calls_in_window("codex") == 0
