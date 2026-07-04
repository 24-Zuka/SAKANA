import importlib

import pytest
from fastapi.testclient import TestClient

TEST_TOKEN = "test-bridge-token"


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("AIRFLOW_HOME", str(tmp_path / "home"))
    monkeypatch.setenv("AIRFLOW_BRIDGE_TOKEN", TEST_TOKEN)
    monkeypatch.setenv("AIRFLOW_LAUNCH_AGENTS_DIR", str(tmp_path / "launchagents"))
    monkeypatch.setenv("AIRFLOW_LOG_DIR", str(tmp_path / "logs"))
    import airflow.bridge as bridge_module

    importlib.reload(bridge_module)
    return TestClient(bridge_module.app)


@pytest.fixture
def auth_headers():
    return {"Authorization": f"Bearer {TEST_TOKEN}"}


def test_health_does_not_require_auth(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["ok"] is True


def test_requests_without_token_are_rejected(client):
    assert client.get("/tickets").status_code == 401
    assert client.get("/agents").status_code == 401
    assert client.get("/quota").status_code == 401


def test_requests_with_wrong_token_are_rejected(client):
    response = client.get("/tickets", headers={"Authorization": "Bearer wrong-token"})
    assert response.status_code == 401


def test_create_and_list_tickets(client, auth_headers):
    create_response = client.post(
        "/tickets", json={"text": "A社との提携レート再交渉の方針を決めたい"}, headers=auth_headers
    )
    assert create_response.status_code == 200
    ticket = create_response.json()
    assert ticket["category"] == "Business"
    assert ticket["decision_required"] is True

    list_response = client.get("/tickets", headers=auth_headers)
    assert list_response.status_code == 200
    tickets = list_response.json()
    assert len(tickets) == 1
    assert tickets[0]["id"] == ticket["id"]


def test_get_ticket_by_id(client, auth_headers):
    create_response = client.post(
        "/tickets", json={"text": "動画のサムネイル案を3パターン作る"}, headers=auth_headers
    )
    ticket_id = create_response.json()["id"]

    response = client.get(f"/tickets/{ticket_id}", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["id"] == ticket_id


def test_get_missing_ticket_404(client, auth_headers):
    response = client.get("/tickets/TKT-99999999-999", headers=auth_headers)
    assert response.status_code == 404


def test_brief_latest(client, auth_headers):
    client.post(
        "/tickets", json={"text": "A社との提携レート再交渉の方針を決めたい"}, headers=auth_headers
    )
    response = client.get("/brief/latest", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert "今日の要判断" in body["content"]


def test_patch_ticket_rejects_invalid_transition(client, auth_headers):
    create = client.post(
        "/tickets", json={"text": "サイトのタイポ修正"}, headers=auth_headers
    )
    ticket_id = create.json()["id"]

    response = client.patch(f"/tickets/{ticket_id}", json={"status": "Done"}, headers=auth_headers)
    assert response.status_code == 400


def test_patch_ticket_requires_approval_when_risk_high(client, auth_headers):
    import airflow.bridge as bridge_module
    from airflow.models import Status

    create = client.post(
        "/tickets", json={"text": "サイトのタイポ修正"}, headers=auth_headers
    )
    ticket_id = create.json()["id"]
    bridge_module._store.update(ticket_id, status=Status.DOING, risk_score=4.0)

    denied = client.patch(f"/tickets/{ticket_id}", json={"status": "Done"}, headers=auth_headers)
    assert denied.status_code == 412

    approved = client.patch(
        f"/tickets/{ticket_id}", json={"status": "Done", "approved": True}, headers=auth_headers
    )
    assert approved.status_code == 200
    assert approved.json()["status"] == "Done"


def test_run_ticket_endpoint_degrades_gracefully(client, auth_headers):
    create = client.post(
        "/tickets", json={"text": "サイトのタイポ修正"}, headers=auth_headers
    )
    ticket_id = create.json()["id"]

    response = client.post(f"/tickets/{ticket_id}/run", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["status"] in ("Waiting", "Done")
    assert len(body["log"]) > 0


def test_list_agents_reports_real_availability(client, auth_headers):
    response = client.get("/agents", headers=auth_headers)
    assert response.status_code == 200
    agents = response.json()
    assert {a["id"] for a in agents} == {"codex", "gemini", "lmstudio"}
    for agent in agents:
        assert agent["status"] in ("online", "offline", "busy")


def test_worktree_build_review_diff_merge_lifecycle(client, auth_headers):
    import airflow.bridge as bridge_module

    create = client.post("/worktrees", json={"branch": "feature/test"}, headers=auth_headers)
    assert create.status_code == 200
    worktree_id = create.json()["id"]

    listing = client.get("/worktrees", headers=auth_headers)
    assert listing.status_code == 200
    assert any(w["id"] == worktree_id for w in listing.json())

    build = client.post("/build", json={"worktreeId": worktree_id}, headers=auth_headers)
    assert build.status_code == 200
    assert len(build.json()) > 0

    repo = bridge_module._demo_repo()
    worktree_path = bridge_module._worktree_path(repo, worktree_id)
    (worktree_path / "NEW.md").write_text("hello", encoding="utf-8")

    diff = client.get(f"/diff?worktreeId={worktree_id}", headers=auth_headers)
    assert diff.status_code == 200

    review = client.post("/review", json={"worktreeId": worktree_id}, headers=auth_headers)
    assert review.status_code == 200

    denied = client.post(
        "/merge", json={"worktreeId": worktree_id, "approved": False}, headers=auth_headers
    )
    assert denied.status_code == 412

    merged = client.post(
        "/merge", json={"worktreeId": worktree_id, "approved": True}, headers=auth_headers
    )
    assert merged.status_code == 200
    assert merged.json()["ok"] is True


def test_worktree_not_found_404(client, auth_headers):
    response = client.get("/diff?worktreeId=does-not-exist", headers=auth_headers)
    assert response.status_code == 404


def test_launchd_jobs_list_and_toggle(client, auth_headers):
    listing = client.get("/launchd", headers=auth_headers)
    assert listing.status_code == 200
    jobs = listing.json()
    assert len(jobs) == 3
    assert all(job["enabled"] is False for job in jobs)

    job_id = jobs[0]["id"]
    enabled = client.patch(f"/launchd/{job_id}", json={"enabled": True}, headers=auth_headers)
    assert enabled.status_code == 200
    assert any(j["id"] == job_id and j["enabled"] for j in enabled.json()["jobs"])

    disabled = client.patch(f"/launchd/{job_id}", json={"enabled": False}, headers=auth_headers)
    assert disabled.status_code == 200
    assert all(not j["enabled"] for j in disabled.json()["jobs"] if j["id"] == job_id)


def test_launchd_run_now_updates_log(client, auth_headers):
    from airflow.automation.launchd import JOB_GROOMING

    response = client.post(f"/launchd/{JOB_GROOMING}/run", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["ok"] is True

    jobs = client.get("/launchd", headers=auth_headers).json()
    grooming = next(j for j in jobs if j["id"] == JOB_GROOMING)
    assert grooming["lastRunAt"] is not None
    assert grooming["lastLogTail"] != ""


def test_quota_status_reports_api_key_red_flag(client, auth_headers, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-fake")
    response = client.get("/quota", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert "OPENAI_API_KEY" in body["apiKeyRedFlag"]
    assert body["codexWindowUsedPct"] is None  # codex CLI not installed in this sandbox


def test_settings_get_and_put(client, auth_headers):
    put_response = client.put(
        "/settings",
        json={"lmStudioBaseUrl": "http://localhost:9999/v1", "obsidianVaultPath": "/tmp/vault"},
        headers=auth_headers,
    )
    assert put_response.status_code == 200
    body = put_response.json()
    assert body["lmStudioBaseUrl"] == "http://localhost:9999/v1"
    assert body["bridgeToken"] == ""

    get_response = client.get("/settings", headers=auth_headers)
    assert get_response.status_code == 200
    assert get_response.json()["obsidianVaultPath"] == "/tmp/vault"
