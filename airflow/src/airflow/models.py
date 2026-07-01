"""TaskCard data model — spec §4.3 (統合チケット・スキーマ)."""

from __future__ import annotations

import re
from datetime import date, datetime
from enum import Enum
from typing import Any

import frontmatter
from pydantic import BaseModel, Field, field_validator

TASK_ID_PATTERN = re.compile(r"^TASK-[0-9]{4}-[0-9]{4}[A-Z]$")


class Category(str, Enum):
    BUSINESS = "Business"
    ENGINEERING = "Engineering"
    CONTENT = "Content"


class Status(str, Enum):
    INBOX = "Inbox"
    TODAY = "Today"
    DOING = "Doing"
    WAITING = "Waiting"
    DONE = "Done"


class Source(str, Enum):
    EMAIL = "email"
    MANUAL = "manual"
    OBSIDIAN_INBOX = "obsidian-inbox"
    AI = "ai"


class Assignee(str, Enum):
    CODEX = "codex"
    LMSTUDIO = "lmstudio"
    GEMINI = "gemini"
    HUMAN = "human"


class TaskCard(BaseModel):
    """統合チケット（AirFlow軽量チケット + JARVIS TaskCard）。YAML front-matter が正表現。"""

    id: str = Field(..., description="表示ID（人間可読）。例: TKT-20260628-001")
    task_id: str | None = Field(
        default=None, description="機械ID。JARVIS互換・任意。^TASK-[0-9]{4}-[0-9]{4}[A-Z]$"
    )
    title: str
    category: Category
    status: Status = Status.INBOX
    priority: int = Field(default=2, ge=1, le=3)
    risk_score: float = Field(default=0.1, ge=0.1, le=5.0)
    created: datetime
    updated: datetime
    due: date | None = None
    source: Source = Source.MANUAL
    assignee: Assignee = Assignee.HUMAN
    tier: int = Field(default=1, ge=1, le=3, description="1=観測 2=起票 3=実行")
    decision_required: bool = False
    dependencies: list[str] = Field(default_factory=list)
    links: list[str] = Field(default_factory=list)
    log: list[str] = Field(default_factory=list)
    body: str = ""

    @field_validator("task_id")
    @classmethod
    def _validate_task_id(cls, v: str | None) -> str | None:
        if v is not None and not TASK_ID_PATTERN.match(v):
            raise ValueError(f"task_id must match {TASK_ID_PATTERN.pattern!r}, got {v!r}")
        return v

    def to_markdown(self) -> str:
        metadata: dict[str, Any] = self.model_dump(
            mode="json", exclude={"body"}, exclude_none=True
        )
        post = frontmatter.Post(self.body, **metadata)
        return frontmatter.dumps(post) + "\n"

    @classmethod
    def from_markdown(cls, text: str) -> "TaskCard":
        post = frontmatter.loads(text)
        data = dict(post.metadata)
        data["body"] = post.content
        return cls.model_validate(data)
