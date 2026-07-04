"""実行ループ（クローズドループ）— spec §5.1/§18。

Discover(00_Rules読込・任意) → Plan(Codex/フォールバック単一ステップ) → Route
→ Execute(worker) → Verify(別ワーカー・maker≠checker) の順で処理し、
合格でチケットをDoneへ、不合格は再Plan（最大N回）、上限超過で
decision_required=true にして人間へエスカレーションする（朝礼に載る）。

全段の結果はチケット`log`へ追記する。
"""

from __future__ import annotations

from datetime import datetime

from ..adapters.base import AdapterUnavailable, Result
from ..adapters.codex_cli import CodexCliAdapter
from ..adapters.gemini_cli import GeminiCliAdapter
from ..adapters.lm_studio import LMStudioAdapter
from ..config import AirflowConfig
from ..models import Category, Status, TaskCard
from ..store.ticket_store import TicketStore
from .budget import BudgetTracker
from .router import route

MAX_RETRIES_DEFAULT = 3
MAX_WORKER_CALLS_DEFAULT = 10

# チケットのカテゴリからExecute段階のタスク種別（ルーティングキー）へのマッピング。
WORKER_KIND_BY_CATEGORY: dict[Category, str] = {
    Category.ENGINEERING: "code",
    Category.BUSINESS: "plan",
    Category.CONTENT: "plan",
}


def _log_line(msg: str) -> str:
    return f"{datetime.now().astimezone().isoformat(timespec='seconds')} {msg}"


def run_ticket(
    ticket_id: str,
    store: TicketStore,
    config: AirflowConfig,
    *,
    budget: BudgetTracker | None = None,
    codex: CodexCliAdapter | None = None,
    gemini: GeminiCliAdapter | None = None,
    lmstudio: LMStudioAdapter | None = None,
    max_retries: int = MAX_RETRIES_DEFAULT,
    max_worker_calls: int = MAX_WORKER_CALLS_DEFAULT,
) -> TaskCard:
    """1チケットに対してPlan→Route→Execute→Verifyのクローズドループを実行する。"""
    ticket = store.get(ticket_id)

    budget = budget or BudgetTracker(config.home / "budget.json")
    codex = codex or CodexCliAdapter(workspace_root=config.home)
    gemini = gemini or GeminiCliAdapter(workspace_root=config.home)
    lmstudio = lmstudio or LMStudioAdapter(base_url=config.lm_studio_base_url)
    workers: dict[str, CodexCliAdapter | GeminiCliAdapter | LMStudioAdapter] = {
        "codex": codex,
        "gemini": gemini,
        "lmstudio": lmstudio,
    }

    call_count = 0
    log_entries: list[str] = []

    def call(worker_name: str, prompt: str) -> Result:
        nonlocal call_count
        call_count += 1
        budget.record_call(worker_name)
        return workers[worker_name].run(prompt)

    # --- Plan ---
    plan_prompt = f"{ticket.title}\n\n{ticket.body}".strip()
    plan_result = call("codex", plan_prompt)
    if plan_result.ok and plan_result.text.strip():
        plan_text = plan_result.text
        log_entries.append(_log_line("Plan by codex: ok"))
    else:
        plan_text = plan_prompt
        log_entries.append(
            _log_line(f"Plan by codex failed ({plan_result.error}); falling back to single-step plan")
        )

    kind = WORKER_KIND_BY_CATEGORY.get(ticket.category, "plan")

    # --- Route -> Execute -> Verify（最大 max_retries 回） ---
    outcome = "escalate"
    for _attempt in range(max_retries):
        if call_count >= max_worker_calls:
            log_entries.append(_log_line(f"worker呼び出し上限（{max_worker_calls}）に到達"))
            break

        exec_worker = route(kind, budget)
        exec_result = call(exec_worker, plan_text)
        log_entries.append(
            _log_line(
                f"Execute by {exec_worker}: {'ok' if exec_result.ok else f'failed ({exec_result.error})'}"
            )
        )
        if not exec_result.ok:
            continue

        if call_count >= max_worker_calls:
            log_entries.append(_log_line(f"worker呼び出し上限（{max_worker_calls}）に到達（Verify前）"))
            break

        call_count += 1
        budget.record_call("lmstudio")
        try:
            passed, reason = lmstudio.verify(
                exec_result.text, f"タスク「{ticket.title}」の要求を満たしているか"
            )
            log_entries.append(_log_line(f"Verify by lmstudio: {'pass' if passed else 'fail'} ({reason})"))
        except AdapterUnavailable as exc:
            passed = bool(exec_result.text.strip())
            log_entries.append(
                _log_line(
                    f"Verify by lmstudio unavailable ({exc}); "
                    f"falling back to non-empty-output rule: {'pass' if passed else 'fail'}"
                )
            )

        if passed:
            outcome = "done"
            break

    if outcome == "done":
        return store.update(
            ticket_id,
            status=Status.DONE,
            decision_required=False,
            log=ticket.log + log_entries,
        )

    log_entries.append(_log_line(f"{max_retries}回の試行後も合格せず、人間の判断へエスカレーション"))
    return store.update(
        ticket_id,
        status=Status.WAITING,
        decision_required=True,
        log=ticket.log + log_entries,
    )
