from datetime import date

import pytest

from airflow.models import Category
from airflow.risk import compute_risk_score


@pytest.mark.parametrize(
    "category,expected_base",
    [
        (Category.BUSINESS, 1.0),
        (Category.CONTENT, 1.0),
        (Category.ENGINEERING, 1.5),
    ],
)
def test_base_by_category(category, expected_base):
    score = compute_risk_score(category=category, priority=3)
    assert score == pytest.approx(expected_base)


def test_external_send_modifier():
    score = compute_risk_score(
        category=Category.BUSINESS, priority=3, involves_external_send=True
    )
    assert score == pytest.approx(1.0 + 2.0)


def test_irreversible_modifier():
    score = compute_risk_score(
        category=Category.BUSINESS, priority=3, involves_irreversible_action=True
    )
    assert score == pytest.approx(1.0 + 2.0)


def test_due_within_24h_modifier():
    score = compute_risk_score(
        category=Category.BUSINESS,
        priority=3,
        due=date(2026, 6, 29),
        now=date(2026, 6, 28),
    )
    assert score == pytest.approx(1.0 + 1.0)


def test_due_far_away_no_modifier():
    score = compute_risk_score(
        category=Category.BUSINESS,
        priority=3,
        due=date(2026, 7, 10),
        now=date(2026, 6, 28),
    )
    assert score == pytest.approx(1.0)


def test_priority_1_modifier():
    score = compute_risk_score(category=Category.BUSINESS, priority=1)
    assert score == pytest.approx(1.0 + 0.5)


def test_all_modifiers_combine_and_clip_to_max():
    score = compute_risk_score(
        category=Category.ENGINEERING,
        priority=1,
        due=date(2026, 6, 29),
        now=date(2026, 6, 28),
        involves_external_send=True,
        involves_irreversible_action=True,
    )
    # 1.5 + 2.0 + 2.0 + 1.0 + 0.5 = 7.0 -> clipped to 5.0
    assert score == pytest.approx(5.0)


def test_min_clip():
    score = compute_risk_score(category=Category.BUSINESS, priority=3)
    assert score >= 0.1


def test_keyword_fallback_detects_external_send_and_irreversible():
    score = compute_risk_score(
        category=Category.BUSINESS,
        priority=2,
        text="請求書の支払いを実行し、完了メールを送信する",
    )
    assert score == pytest.approx(1.0 + 2.0 + 2.0)


def test_explicit_flags_override_text_when_given_as_false():
    score = compute_risk_score(
        category=Category.BUSINESS,
        priority=2,
        text="送信 削除",
        involves_external_send=False,
        involves_irreversible_action=False,
    )
    assert score == pytest.approx(1.0)
