"""一時的な開発用ブリッジ（FastAPI）。

**これは spec §12.2 の本来の Rust/axum 製 `jarvis-bridge` ではない。**
本セッションはmacOS実機でもRustツールチェーンを使う前提でもないため、
jarvis-cockpit フロントエンドと実際の AirFlow エンジンをローカルで
繋いで動作確認するための、最小限・一時的なスタンドインとして用意した。
認証なし・CORSはlocalhost開発用に全開放。本番/公開環境では絶対に使わないこと。

起動: `uvicorn airflow.bridge:app --port 8787`
"""

from __future__ import annotations

from datetime import date

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .adapters.codex_cli import CodexCliAdapter
from .adapters.lm_studio import LMStudioAdapter
from .config import AirflowConfig, check_no_api_keys
from .inbox import import_inbox
from .models import Category, Status, TaskCard
from .scheduler.brief import generate_brief
from .store.ticket_store import TicketNotFoundError, TicketStore

app = FastAPI(title="AirFlow dev bridge (temporary, not the final Rust jarvis-bridge)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_config = AirflowConfig.load()
_config.ensure_dirs()
_store = TicketStore(_config.home)


class CreateTicketRequest(BaseModel):
    text: str


@app.get("/health")
def health() -> dict:
    flagged = check_no_api_keys()
    lm_studio = LMStudioAdapter(base_url=_config.lm_studio_base_url)
    codex = CodexCliAdapter()
    return {
        "ok": True,
        "home": str(_config.home),
        "lm_studio_base_url": _config.lm_studio_base_url,
        "api_key_red_flag": flagged,
        "lm_studio_reachable": lm_studio.is_reachable(),
        "codex_cli_available": codex.is_available(),
        "obsidian_connected": False,  # Obsidian REST連携はMVPスコープ外（docs/DEVIATIONS.md）
    }


@app.get("/tickets")
def list_tickets(
    status: Status | None = None,
    category: Category | None = None,
    decision_required: bool | None = None,
) -> list[TaskCard]:
    return _store.list(status=status, category=category, decision_required=decision_required)


@app.get("/tickets/{ticket_id}")
def get_ticket(ticket_id: str) -> TaskCard:
    try:
        return _store.get(ticket_id)
    except TicketNotFoundError:
        raise HTTPException(status_code=404, detail=f"ticket {ticket_id} not found")


@app.post("/tickets")
def create_ticket(payload: CreateTicketRequest) -> TaskCard:
    return import_inbox(_store, payload.text)


@app.get("/brief/latest")
def latest_brief() -> dict:
    path = generate_brief(_store, _config.briefs_dir, on=date.today())
    return {"path": str(path), "content": path.read_text(encoding="utf-8")}
