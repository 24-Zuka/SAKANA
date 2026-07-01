"""ワーカー共通インターフェース — spec §6。

`run(prompt, context) -> Result` が共通IF。分類用途では `ClassifierAdapter.classify()`
という薄いラッパーを使う（Result = {ok, text, worker, elapsed, error} 相当の情報を
`ClassificationResult` に正規化して返す）。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from ..models import Category


class AdapterUnavailable(Exception):
    """ワーカーが疎通不可・失敗した場合に送出する。呼び出し側はフォールバックする（P7）。"""


@dataclass
class ClassificationResult:
    category: Category
    priority: int  # 1(高)-3(低)
    decision_required: bool
    involves_external_send: bool
    involves_irreversible_action: bool
    worker: str  # "lmstudio" | "rule_based" | ...
    summary: str = ""


class ClassifierAdapter(Protocol):
    def classify(self, text: str) -> ClassificationResult: ...
