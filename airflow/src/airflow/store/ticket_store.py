"""チケット（TaskCard）の Markdown+YAML CRUD — spec §4.2/§4.3。"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from ..models import Category, Status, TaskCard


class TicketNotFoundError(KeyError):
    pass


class TicketStore:
    def __init__(self, root: Path) -> None:
        self.root = Path(root)
        self.tickets_dir = self.root / "tickets"
        self.tickets_dir.mkdir(parents=True, exist_ok=True)

    def _path(self, ticket_id: str) -> Path:
        return self.tickets_dir / f"{ticket_id}.md"

    def next_id(self, *, on: datetime | None = None) -> str:
        """次の表示ID（TKT-YYYYMMDD-NNN）を発番する。当日分の連番をカウント。"""
        day = (on or datetime.now()).strftime("%Y%m%d")
        prefix = f"TKT-{day}-"
        existing = [p.stem for p in self.tickets_dir.glob(f"{prefix}*.md")]
        seq = 1
        used = set()
        for name in existing:
            suffix = name[len(prefix) :]
            if suffix.isdigit():
                used.add(int(suffix))
        while seq in used:
            seq += 1
        return f"{prefix}{seq:03d}"

    def create(self, ticket: TaskCard) -> TaskCard:
        path = self._path(ticket.id)
        if path.exists():
            raise FileExistsError(f"ticket {ticket.id} already exists")
        path.write_text(ticket.to_markdown(), encoding="utf-8")
        return ticket

    def get(self, ticket_id: str) -> TaskCard:
        path = self._path(ticket_id)
        if not path.exists():
            raise TicketNotFoundError(ticket_id)
        return TaskCard.from_markdown(path.read_text(encoding="utf-8"))

    def update(self, ticket_id: str, **fields) -> TaskCard:
        ticket = self.get(ticket_id)
        fields.setdefault("updated", datetime.now().astimezone())
        updated = ticket.model_copy(update=fields)
        self._path(ticket_id).write_text(updated.to_markdown(), encoding="utf-8")
        return updated

    def delete(self, ticket_id: str) -> None:
        path = self._path(ticket_id)
        if not path.exists():
            raise TicketNotFoundError(ticket_id)
        path.unlink()

    def list(
        self,
        *,
        status: Status | None = None,
        category: Category | None = None,
        decision_required: bool | None = None,
    ) -> list[TaskCard]:
        tickets = []
        for path in sorted(self.tickets_dir.glob("*.md")):
            ticket = TaskCard.from_markdown(path.read_text(encoding="utf-8"))
            if status is not None and ticket.status != status:
                continue
            if category is not None and ticket.category != category:
                continue
            if decision_required is not None and ticket.decision_required != decision_required:
                continue
            tickets.append(ticket)
        return tickets
