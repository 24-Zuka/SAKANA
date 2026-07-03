"""開発用ブリッジ（FastAPI）— spec §7.3/§12.2 の暫定 Rust/axum `jarvis-bridge` 代替。

**これは spec §12.2 の本来の Rust/axum 製 `jarvis-bridge` ではない。**
本セッションはmacOS実機でもRustツールチェーンを使う前提でもないため、
jarvis-cockpit フロントエンドと実際の AirFlow エンジンをローカルで
繋いで動作確認するための、一時的なスタンドインとして用意した。

認証: Bearerトークン必須（`/health` のみ無認証・§8.4）。127.0.0.1へバインドし、
Originはlocalhost開発サーバーとGitHub Pages公開版のみ許可する。

トークンの扱い（Credential Materialization対策）: 初回起動時にトークンが未設定
なら自動生成し、Keychain（darwin）/ `secrets.json`（他OS）へ保存するが、
**生成した値そのものは標準出力・ログへ一切出力しない**。Cockpitの設定画面に
貼り付ける値は `airflowctl show-bridge-token` をユーザー自身の端末で実行して
確認する。

起動: `uvicorn airflow.bridge:app --port 8787`
"""

from __future__ import annotations

import secrets as token_secrets
from datetime import date, datetime
from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from . import devrepo, gitops
from . import secrets as secret_store
from .adapters.base import AdapterUnavailable
from .adapters.codex_cli import CodexCliAdapter
from .adapters.gemini_cli import GeminiCliAdapter
from .adapters.lm_studio import LMStudioAdapter
from .automation.launchd import (
    JOB_BRIEF,
    JOB_GROOMING,
    JOB_INBOX,
    append_job_log,
    default_launch_agents_dir,
    generate_brief_plist,
    generate_grooming_plist,
    generate_inbox_plist,
)
from .automation.launchd import install as launchd_install
from .automation.launchd import list_jobs as launchd_list_jobs
from .automation.launchd import resolve_airflowctl_bin
from .automation.launchd import set_enabled as launchd_set_enabled
from .config import AirflowConfig, check_no_api_keys
from .guard import GuardBlocked
from .inbox import import_inbox, import_inbox_from_dir
from .models import Category, Status, TaskCard, is_valid_status_transition
from .obsidian import ObsidianClient, ObsidianError, ObsidianFileNotFound
from .orchestrator.budget import DEFAULT_THRESHOLDS, BudgetTracker
from .orchestrator.run import run_ticket
from .risk import RISK_APPROVAL_THRESHOLD
from .scheduler.brief import generate_brief
from .scheduler.groom import groom as groom_store
from .store.ticket_store import TicketNotFoundError, TicketStore

BRIDGE_TOKEN_ACCOUNT = "bridge_token"

app = FastAPI(title="AirFlow dev bridge (temporary, not the final Rust jarvis-bridge)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "https://24-zuka.github.io",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)

_config = AirflowConfig.load()
_config.ensure_dirs()
_store = TicketStore(_config.home)


def _resolve_bridge_token(config: AirflowConfig) -> str:
    """Bearerトークンを解決する。設定/Keychainに無ければ新規生成し保存する。

    生成した値は絶対に標準出力・ログへ出さない。ユーザーは
    `airflowctl show-bridge-token` を自分の端末で実行して値を取得する。
    """
    if config.bridge_token:
        return config.bridge_token
    existing = secret_store.get_secret(BRIDGE_TOKEN_ACCOUNT, home=config.home)
    if existing:
        return existing
    token = token_secrets.token_urlsafe(32)
    secret_store.set_secret(BRIDGE_TOKEN_ACCOUNT, token, home=config.home)
    print(
        "[airflow.bridge] Bearerトークンを新規生成し保存しました（値は表示しません）。"
        " `airflowctl show-bridge-token` を実行して値を確認し、"
        "Cockpitの設定画面に貼り付けてください。"
    )
    return token


_bridge_token = _resolve_bridge_token(_config)


def require_auth(authorization: str | None = Header(default=None)) -> None:
    if authorization != f"Bearer {_bridge_token}":
        raise HTTPException(status_code=401, detail="unauthorized: valid Bearer token required")


class CreateTicketRequest(BaseModel):
    text: str


class TicketPatchRequest(BaseModel):
    status: Status | None = None
    approved: bool = False


class WorktreeCreateRequest(BaseModel):
    branch: str


class WorktreeIdRequest(BaseModel):
    worktreeId: str


class MergeRequest(BaseModel):
    worktreeId: str
    approved: bool = False


class LaunchdPatchRequest(BaseModel):
    enabled: bool


class SettingsPatchRequest(BaseModel):
    bridgeUrl: str | None = None
    bridgeToken: str | None = None
    lmStudioBaseUrl: str | None = None
    obsidianVaultPath: str | None = None


class VaultWriteRequest(BaseModel):
    content: str


@app.get("/health")
def health() -> dict:
    """疎通確認。認証不要（トークン未設定でも到達性を判定できるように・§8.4）。"""
    flagged = check_no_api_keys()
    lm_studio = LMStudioAdapter(base_url=_config.lm_studio_base_url)
    codex = CodexCliAdapter()
    obsidian = ObsidianClient(base_url=_config.obsidian_base_url, token=_config.obsidian_token or None)
    return {
        "ok": True,
        "home": str(_config.home),
        "lm_studio_base_url": _config.lm_studio_base_url,
        "api_key_red_flag": flagged,
        "lm_studio_reachable": lm_studio.is_reachable(),
        "codex_cli_available": codex.is_available(),
        "obsidian_connected": obsidian.is_reachable(),
    }


@app.get("/tickets")
def list_tickets(
    status: Status | None = None,
    category: Category | None = None,
    decision_required: bool | None = None,
    _: None = Depends(require_auth),
) -> list[TaskCard]:
    return _store.list(status=status, category=category, decision_required=decision_required)


@app.get("/tickets/{ticket_id}")
def get_ticket(ticket_id: str, _: None = Depends(require_auth)) -> TaskCard:
    try:
        return _store.get(ticket_id)
    except TicketNotFoundError:
        raise HTTPException(status_code=404, detail=f"ticket {ticket_id} not found")


@app.post("/tickets")
def create_ticket(payload: CreateTicketRequest, _: None = Depends(require_auth)) -> TaskCard:
    return import_inbox(_store, payload.text)


@app.patch("/tickets/{ticket_id}")
def patch_ticket(ticket_id: str, payload: TicketPatchRequest, _: None = Depends(require_auth)) -> TaskCard:
    """§4.4 ステータス遷移図を検証し、risk_score>=閾値なら`approved`必須にする（§8.3）。"""
    try:
        ticket = _store.get(ticket_id)
    except TicketNotFoundError:
        raise HTTPException(status_code=404, detail=f"ticket {ticket_id} not found")

    if payload.status is None:
        return ticket

    if not is_valid_status_transition(ticket.status, payload.status):
        raise HTTPException(
            status_code=400,
            detail=f"invalid status transition: {ticket.status.value} -> {payload.status.value}",
        )
    if ticket.risk_score >= RISK_APPROVAL_THRESHOLD and not payload.approved:
        raise HTTPException(
            status_code=412,
            detail=f"risk_score={ticket.risk_score} >= {RISK_APPROVAL_THRESHOLD} requires approval",
        )
    return _store.update(ticket_id, status=payload.status)


@app.post("/tickets/{ticket_id}/run")
def run_ticket_endpoint(ticket_id: str, _: None = Depends(require_auth)) -> TaskCard:
    """§5.1のPlan→Route→Execute→Verifyクローズドループを起動する。"""
    try:
        return run_ticket(ticket_id, _store, _config)
    except TicketNotFoundError:
        raise HTTPException(status_code=404, detail=f"ticket {ticket_id} not found")


@app.get("/brief/latest")
def latest_brief(_: None = Depends(require_auth)) -> dict:
    path = generate_brief(_store, _config.briefs_dir, on=date.today())
    return {"path": str(path), "content": path.read_text(encoding="utf-8")}


@app.get("/agents")
def list_agents(_: None = Depends(require_auth)) -> list[dict]:
    """§6のワーカー3種の実疎通状況をそのまま返す（捏造せず正直に・P7）。"""
    codex = CodexCliAdapter()
    gemini = GeminiCliAdapter()
    lmstudio = LMStudioAdapter(base_url=_config.lm_studio_base_url)
    return [
        {
            "id": "codex",
            "name": "Codex",
            "role": "開発",
            "model": "codex",
            "permissionTier": 3,
            "status": "online" if codex.is_available() else "offline",
        },
        {
            "id": "gemini",
            "name": "Gemini",
            "role": "調査",
            "model": "gemini",
            "permissionTier": 2,
            "status": "online" if gemini.is_available() else "offline",
        },
        {
            "id": "lmstudio",
            "name": "LM Studio",
            "role": "秘書",
            "model": "lmstudio",
            "permissionTier": 1,
            "status": "online" if lmstudio.is_reachable() else "offline",
        },
    ]


def _demo_repo() -> Path:
    return devrepo.ensure_demo_repo(_config.demo_repo_path)


def _worktree_path(repo: Path, worktree_id: str) -> Path:
    safe = gitops.sanitize_branch_name(worktree_id)
    path = repo / ".worktrees" / safe.replace("/", "-")
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"worktree {worktree_id} not found")
    return path


@app.get("/worktrees")
def list_worktrees_ep(_: None = Depends(require_auth)) -> list[dict]:
    """§7.2: 隔離サンドボックスデモリポジトリ（devrepo）内のworktreeのみを扱う。"""
    repo = _demo_repo()
    entries = gitops.list_worktrees(repo)
    result = []
    for entry in entries:
        if entry["branch"] == "main":
            continue
        path = Path(entry["path"])
        has_diff = bool(gitops.diff_files(path)) if path.exists() else False
        created = (
            datetime.fromtimestamp(path.stat().st_mtime).astimezone().isoformat() if path.exists() else ""
        )
        result.append(
            {
                "id": entry["branch"],
                "branch": entry["branch"],
                "status": "review" if has_diff else "clean",
                "createdAt": created,
            }
        )
    return result


@app.post("/worktrees")
def create_worktree_ep(payload: WorktreeCreateRequest, _: None = Depends(require_auth)) -> dict:
    repo = _demo_repo()
    result = gitops.create_worktree(repo, payload.branch)
    path = Path(result["path"])
    created = datetime.fromtimestamp(path.stat().st_mtime).astimezone().isoformat()
    return {"id": result["branch"], "branch": result["branch"], "status": "clean", "createdAt": created}


@app.post("/build")
def run_build(payload: WorktreeIdRequest, _: None = Depends(require_auth)) -> list[dict]:
    """デモリポジトリには実ビルドシステムが無いため、`git status` の結果を
    ビルドログ代わりに返す（捏造せず正直に代替だと明記する・P7）。
    """
    repo = _demo_repo()
    worktree_path = _worktree_path(repo, payload.worktreeId)
    output = gitops.status(worktree_path)
    now = datetime.now().astimezone().isoformat()
    lines = [f"$ git status （{worktree_path.name}）"] + (output.splitlines() or ["(no output)"])
    log = [{"ts": now, "level": "info", "text": line} for line in lines]
    log.append(
        {
            "ts": now,
            "level": "info",
            "text": (
                "デモリポジトリには実ビルドシステムが無いため、"
                "git statusの結果をビルドログ代わりに表示しています。"
            ),
        }
    )
    return log


@app.post("/review")
def run_review(payload: WorktreeIdRequest, _: None = Depends(require_auth)) -> list[dict]:
    """maker≠checkerのVerify段階と同じ考え方でLM Studioにレビューさせる（不在時はルールベース）。"""
    repo = _demo_repo()
    worktree_path = _worktree_path(repo, payload.worktreeId)
    files = gitops.diff_files(worktree_path)
    lmstudio = LMStudioAdapter(base_url=_config.lm_studio_base_url)
    findings = []
    for i, f in enumerate(files, start=1):
        try:
            passed, reason = lmstudio.verify(f["patch"], "コード品質・意図しない副作用が無いか")
            severity = "LOW" if passed else "MEDIUM"
            summary = reason or ("問題なし" if passed else "要確認")
        except AdapterUnavailable:
            severity = "LOW"
            summary = "LM Studio不在のため簡易チェックのみ（差分の検出のみ）"
        findings.append({"id": f"finding-{i}", "severity": severity, "file": f["path"], "summary": summary})
    return findings


@app.get("/diff")
def get_diff(worktreeId: str, _: None = Depends(require_auth)) -> list[dict]:
    repo = _demo_repo()
    worktree_path = _worktree_path(repo, worktreeId)
    return gitops.diff_files(worktree_path)


@app.post("/merge")
def merge_worktree(payload: MergeRequest, _: None = Depends(require_auth)) -> dict:
    """§8.3: 承認必須。隔離サンドボックス内でのローカルマージのみ（push無し）。"""
    if not payload.approved:
        raise HTTPException(status_code=412, detail="approval required before merge")
    repo = _demo_repo()
    worktree_path = _worktree_path(repo, payload.worktreeId)
    branch = gitops.sanitize_branch_name(payload.worktreeId)
    gitops.commit_all(worktree_path, f"AirFlow Cockpit: changes from {branch}")
    try:
        gitops.merge_branch(repo, branch, into="main")
    except GuardBlocked as exc:
        raise HTTPException(status_code=423, detail=str(exc))
    return {"ok": True}


@app.get("/launchd")
def get_launchd_jobs(_: None = Depends(require_auth)) -> list[dict]:
    return launchd_list_jobs()


@app.patch("/launchd/{job_id}")
def patch_launchd_job(job_id: str, payload: LaunchdPatchRequest, _: None = Depends(require_auth)) -> dict:
    if job_id not in (JOB_BRIEF, JOB_GROOMING, JOB_INBOX):
        raise HTTPException(status_code=404, detail=f"unknown job {job_id}")

    target_dir = default_launch_agents_dir()
    plist_path = target_dir / f"{job_id}.plist"
    disabled_path = target_dir / f"{job_id}.plist.disabled"
    if payload.enabled and not plist_path.exists() and not disabled_path.exists():
        bin_path = resolve_airflowctl_bin()
        if job_id == JOB_BRIEF:
            plist_bytes = generate_brief_plist(bin_path)
        elif job_id == JOB_GROOMING:
            plist_bytes = generate_grooming_plist(bin_path)
        else:
            plist_bytes = generate_inbox_plist(bin_path, _config.inbox_dir)
        launchd_install(job_id, plist_bytes)
    else:
        launchd_set_enabled(job_id, payload.enabled)
    return {"ok": True, "jobs": launchd_list_jobs()}


@app.post("/launchd/{job_id}/run")
def run_launchd_job(job_id: str, _: None = Depends(require_auth)) -> dict:
    if job_id == JOB_BRIEF:
        path = generate_brief(_store, _config.briefs_dir)
        detail = f"朝礼を生成しました: {path}"
    elif job_id == JOB_GROOMING:
        result = groom_store(_store)
        detail = (
            f"期限切れ注記: {len(result['flagged_overdue'])}件 / "
            f"Done圧縮: {len(result['archived_done'])}件 / 索引再構築: {result['indexed_count']}件"
        )
    elif job_id == JOB_INBOX:
        count = import_inbox_from_dir(_store, _config.inbox_dir, _config.inbox_processed_dir)
        detail = f"{count}件のファイルを取り込みました。"
    else:
        raise HTTPException(status_code=404, detail=f"unknown job {job_id}")
    append_job_log(job_id, detail)
    return {"ok": True, "detail": detail}


@app.get("/quota")
def quota_status(_: None = Depends(require_auth)) -> dict:
    """§5.3 Budget Guardの実データ＋APIキー赤旗を返す（公式残枠APIは無いためベストエフォート）。"""
    budget = BudgetTracker(_config.home / "budget.json")
    flagged = check_no_api_keys()
    codex = CodexCliAdapter()
    gemini = GeminiCliAdapter()

    def pct(worker: str) -> float:
        threshold = DEFAULT_THRESHOLDS.get(worker, 30)
        return round(min(100.0, 100 * budget.calls_in_window(worker) / threshold), 1)

    return {
        "codexWindowUsedPct": pct("codex") if codex.is_available() else None,
        "geminiWindowUsedPct": pct("gemini") if gemini.is_available() else None,
        "authOk": codex.login_status() if codex.is_available() else False,
        "apiKeyRedFlag": flagged,
        "fallbackModeActive": budget.should_downgrade("codex") or budget.should_downgrade("gemini"),
    }


@app.get("/settings")
def get_settings(_: None = Depends(require_auth)) -> dict:
    return {
        "bridgeUrl": "",
        "bridgeToken": "",
        "lmStudioBaseUrl": _config.lm_studio_base_url,
        "obsidianVaultPath": _config.vault_path,
    }


@app.put("/settings")
def put_settings(payload: SettingsPatchRequest, _: None = Depends(require_auth)) -> dict:
    """bridgeUrl/bridgeTokenはフロント側の接続先設定のためサーバーには保存・返却しない。"""
    global _config
    _config = _config.update_settings(
        lm_studio_base_url=payload.lmStudioBaseUrl,
        vault_path=payload.obsidianVaultPath,
    )
    return {
        "bridgeUrl": payload.bridgeUrl or "",
        "bridgeToken": "",
        "lmStudioBaseUrl": _config.lm_studio_base_url,
        "obsidianVaultPath": _config.vault_path,
    }


@app.get("/vault/{path:path}")
def vault_read(path: str, _: None = Depends(require_auth)) -> dict:
    client = ObsidianClient(base_url=_config.obsidian_base_url, token=_config.obsidian_token or None)
    try:
        return {"path": path, "content": client.read(path)}
    except ObsidianFileNotFound:
        raise HTTPException(status_code=404, detail=f"{path} not found")
    except ObsidianError as exc:
        raise HTTPException(status_code=502, detail=str(exc))


@app.put("/vault/{path:path}")
def vault_write(path: str, payload: VaultWriteRequest, _: None = Depends(require_auth)) -> dict:
    client = ObsidianClient(base_url=_config.obsidian_base_url, token=_config.obsidian_token or None)
    try:
        client.write(path, payload.content)
    except ObsidianError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    return {"ok": True}


@app.delete("/vault/{path:path}")
def vault_delete(path: str, _: None = Depends(require_auth)) -> dict:
    client = ObsidianClient(base_url=_config.obsidian_base_url, token=_config.obsidian_token or None)
    try:
        trash_path = client.delete(path)
    except ObsidianError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    return {"ok": True, "trashPath": trash_path}


@app.get("/vault-search")
def vault_search(query: str, _: None = Depends(require_auth)) -> list[dict]:
    client = ObsidianClient(base_url=_config.obsidian_base_url, token=_config.obsidian_token or None)
    try:
        return client.search(query)
    except ObsidianError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
