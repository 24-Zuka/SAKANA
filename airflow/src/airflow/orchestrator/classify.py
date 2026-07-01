"""分類ルーティング — spec §5.2「ローカルで足りるものは必ずLM Studio」。

LM Studio を試し、疎通不可・失敗時はローカル規則（RuleBasedClassifier）へ
フォールバックする。呼び出し側に例外を伝播させない（P7: 静かに壊れない）。
"""

from __future__ import annotations

import logging

from ..adapters.base import AdapterUnavailable, ClassificationResult, ClassifierAdapter
from ..adapters.lm_studio import LMStudioAdapter
from ..adapters.rule_based import RuleBasedClassifier

logger = logging.getLogger(__name__)


def classify_text(
    text: str,
    *,
    primary: ClassifierAdapter | None = None,
    fallback: ClassifierAdapter | None = None,
) -> ClassificationResult:
    """LM Studio（既定）→ ローカル規則の順で分類を試みる。常に結果を返す。"""
    fallback = fallback or RuleBasedClassifier()
    if primary is None:
        primary = LMStudioAdapter(base_url="http://localhost:1234/v1")

    try:
        return primary.classify(text)
    except AdapterUnavailable as exc:
        logger.warning("primary classifier unavailable, falling back to rule-based: %s", exc)
        return fallback.classify(text)
