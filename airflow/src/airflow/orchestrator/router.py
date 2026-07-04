"""ルーティング規則（コスト優先）— spec §5.2。

「ローカルで足りるものは必ずLM Studio」。Codex/Geminiは枠の通貨として節約して使う。
Budget Guard（§5.3）で閾値超過時は自動的にLM Studioへダウングレードする。
"""

from __future__ import annotations

from datetime import datetime

from .budget import BudgetTracker

# 付録A ルーティング早見表:
#   分類・要約・整形・検証           -> LM Studio（無料・無制限）
#   計画・複雑推論・コード・実行      -> Codex（サブスク枠／温存）
#   長文・大量context・画像          -> Gemini（サブスク枠）
ROUTING_TABLE: dict[str, str] = {
    "classify": "lmstudio",
    "summarize": "lmstudio",
    "verify": "lmstudio",
    "plan": "codex",
    "code": "codex",
    "long_context": "gemini",
    "multimodal": "gemini",
}


def route(task_kind: str, budget: BudgetTracker, *, now: datetime | None = None) -> str:
    """タスク種別からワーカーを決定する。枠逼迫時はLM Studioへ自動ダウングレード。"""
    worker = ROUTING_TABLE.get(task_kind, "lmstudio")
    if worker in ("codex", "gemini") and budget.should_downgrade(worker, now=now):
        return "lmstudio"
    return worker
