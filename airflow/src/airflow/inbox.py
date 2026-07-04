"""自然文の取り込み → 分類 → 起票 — spec §10.2。

「外部送信・公開・削除・支払い・契約・不可逆操作に関わる内容は、自動実行せず
Waiting + 要判断に送る」というガードをここで適用する。
"""

from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path

from .adapters.base import ClassifierAdapter
from .models import Assignee, Source, Status, TaskCard
from .orchestrator.classify import classify_text
from .risk import compute_risk_score
from .store.ticket_store import TicketStore

DEFAULT_ASSIGNEE_BY_CATEGORY = {
    "Engineering": Assignee.CODEX,
}


def import_inbox(
    store: TicketStore,
    text: str,
    *,
    source: Source = Source.MANUAL,
    primary: ClassifierAdapter | None = None,
) -> TaskCard:
    now = datetime.now().astimezone()
    result = classify_text(text, primary=primary)

    needs_human_decision = (
        result.decision_required
        or result.involves_external_send
        or result.involves_irreversible_action
    )
    status = Status.WAITING if needs_human_decision else Status.TODAY

    risk_score = compute_risk_score(
        category=result.category,
        priority=result.priority,
        involves_external_send=result.involves_external_send,
        involves_irreversible_action=result.involves_irreversible_action,
        now=now,
    )

    fallback_title = text.strip().splitlines()[0][:120] if text.strip() else "(no title)"
    title = result.summary or fallback_title
    assignee = DEFAULT_ASSIGNEE_BY_CATEGORY.get(result.category.value, Assignee.HUMAN)

    ticket = TaskCard(
        id=store.next_id(on=now),
        title=title,
        category=result.category,
        status=status,
        priority=result.priority,
        risk_score=risk_score,
        created=now,
        updated=now,
        source=source,
        assignee=assignee,
        tier=2,
        decision_required=needs_human_decision,
        dependencies=[],
        links=[],
        log=[f"{now.isoformat()} created by ai (classified by {result.worker})"],
        body=text,
    )
    return store.create(ticket)


def import_inbox_from_dir(store: TicketStore, inbox_dir: Path, processed_dir: Path) -> int:
    """inbox/ 配下の .md / .txt を取り込み、起票して processed/ へ退避する（§10.2）。"""
    count = 0
    for path in sorted(inbox_dir.glob("*")):
        if path.is_dir() or path.suffix not in (".md", ".txt"):
            continue
        text = path.read_text(encoding="utf-8")
        import_inbox(store, text)
        dest = processed_dir / path.name
        shutil.move(str(path), str(dest))
        count += 1
    return count
