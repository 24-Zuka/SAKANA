"""risk_score 算出規則 — spec §4.6（HITL発火条件の定義）。

risk_score = base(category) + modifiers
  base:      Business 1.0 / Content 1.0 / Engineering 1.5
  +2.0  外部送信・公開を伴う（メール送信・PR作成・デプロイ・投稿）
  +2.0  不可逆操作を伴う（削除・支払い・契約・本番変更）
  +1.0  due が24時間以内
  +0.5  priority == 1
  → 上限5.0でクリップ

最終値は Router（この規則）が正。LLM の補正提案があっても採用しない。
"""

from __future__ import annotations

from datetime import date, datetime

from .models import Category

BASE_BY_CATEGORY: dict[Category, float] = {
    Category.BUSINESS: 1.0,
    Category.CONTENT: 1.0,
    Category.ENGINEERING: 1.5,
}

MIN_RISK_SCORE = 0.1
MAX_RISK_SCORE = 5.0
RISK_APPROVAL_THRESHOLD = 3.0  # §8.3: risk_score>=3.0 は承認モーダル必須

EXTERNAL_SEND_KEYWORDS = (
    "メール送信",
    "送信",
    "公開",
    "PR作成",
    "プルリク",
    "デプロイ",
    "投稿",
)
IRREVERSIBLE_KEYWORDS = (
    "削除",
    "支払い",
    "契約",
    "本番変更",
    "本番",
)


def contains_any(text: str, keywords: tuple[str, ...]) -> bool:
    return any(keyword in text for keyword in keywords)


def compute_risk_score(
    *,
    category: Category,
    priority: int,
    due: date | None = None,
    text: str = "",
    involves_external_send: bool | None = None,
    involves_irreversible_action: bool | None = None,
    now: datetime | date | None = None,
) -> float:
    """§4.6の規則で risk_score を算出する。

    `involves_external_send` / `involves_irreversible_action` を明示しない場合は
    `text`（タイトル・本文など）のキーワード判定にフォールバックする。
    """
    score = BASE_BY_CATEGORY[category]

    external = (
        involves_external_send
        if involves_external_send is not None
        else contains_any(text, EXTERNAL_SEND_KEYWORDS)
    )
    if external:
        score += 2.0

    irreversible = (
        involves_irreversible_action
        if involves_irreversible_action is not None
        else contains_any(text, IRREVERSIBLE_KEYWORDS)
    )
    if irreversible:
        score += 2.0

    if due is not None:
        reference = now.date() if isinstance(now, datetime) else (now or date.today())
        due_date = due.date() if isinstance(due, datetime) else due
        if (due_date - reference).days <= 1:
            score += 1.0

    if priority == 1:
        score += 0.5

    return max(MIN_RISK_SCORE, min(MAX_RISK_SCORE, score))
