"""ローカル規則フォールバック分類器 — spec P7「静かに壊れない」の実装。

LM Studio が疎通不可の場合でも、AirFlowは常に何らかの分類結果を返す。
LLM を使わないため無料・無制限・即応。最終的な risk_score は §4.6 の規則
（risk.py）が正であり、ここでの判定はその入力材料（category/priority/
external_send/irreversible フラグ）を提供するだけ。
"""

from __future__ import annotations

from ..models import Category
from ..risk import EXTERNAL_SEND_KEYWORDS, IRREVERSIBLE_KEYWORDS, contains_any
from .base import ClassificationResult

CATEGORY_KEYWORDS: dict[Category, tuple[str, ...]] = {
    Category.ENGINEERING: (
        "バグ",
        "実装",
        "デプロイ",
        "コード",
        "API",
        "サーバー",
        "ビルド",
        "リファクタ",
        "テスト",
    ),
    Category.CONTENT: (
        "動画",
        "記事",
        "投稿",
        "デザイン",
        "コンテンツ",
        "ブログ",
        "SNS",
    ),
    Category.BUSINESS: (
        "契約",
        "レート",
        "交渉",
        "請求",
        "売上",
        "顧客",
        "取引",
        "支払い",
    ),
}

URGENT_KEYWORDS = ("今すぐ", "緊急", "至急", "本日中")
LOW_PRIORITY_KEYWORDS = ("いつか", "そのうち", "低優先", "余裕があれば")
DECISION_KEYWORDS = ("方針を決める", "判断", "決定", "選択肢", "決めたい", "要判断")


class RuleBasedClassifier:
    worker = "rule_based"

    def classify(self, text: str) -> ClassificationResult:
        category = self._detect_category(text)
        priority = self._detect_priority(text)
        decision_required = contains_any(text, DECISION_KEYWORDS)
        external = contains_any(text, EXTERNAL_SEND_KEYWORDS)
        irreversible = contains_any(text, IRREVERSIBLE_KEYWORDS)
        return ClassificationResult(
            category=category,
            priority=priority,
            decision_required=decision_required,
            involves_external_send=external,
            involves_irreversible_action=irreversible,
            worker=self.worker,
            summary=text.strip().splitlines()[0][:80] if text.strip() else "",
        )

    @staticmethod
    def _detect_category(text: str) -> Category:
        for category, keywords in CATEGORY_KEYWORDS.items():
            if contains_any(text, keywords):
                return category
        return Category.BUSINESS

    @staticmethod
    def _detect_priority(text: str) -> int:
        if contains_any(text, URGENT_KEYWORDS):
            return 1
        if contains_any(text, LOW_PRIORITY_KEYWORDS):
            return 3
        return 2
