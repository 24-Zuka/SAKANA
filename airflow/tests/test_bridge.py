import importlib

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("AIRFLOW_HOME", str(tmp_path / "home"))
    import airflow.bridge as bridge_module

    importlib.reload(bridge_module)
    return TestClient(bridge_module.app)


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True


def test_create_and_list_tickets(client):
    create_response = client.post("/tickets", json={"text": "A社との提携レート再交渉の方針を決めたい"})
    assert create_response.status_code == 200
    ticket = create_response.json()
    assert ticket["category"] == "Business"
    assert ticket["decision_required"] is True

    list_response = client.get("/tickets")
    assert list_response.status_code == 200
    tickets = list_response.json()
    assert len(tickets) == 1
    assert tickets[0]["id"] == ticket["id"]


def test_get_ticket_by_id(client):
    create_response = client.post("/tickets", json={"text": "動画のサムネイル案を3パターン作る"})
    ticket_id = create_response.json()["id"]

    response = client.get(f"/tickets/{ticket_id}")
    assert response.status_code == 200
    assert response.json()["id"] == ticket_id


def test_get_missing_ticket_404(client):
    response = client.get("/tickets/TKT-99999999-999")
    assert response.status_code == 404


def test_brief_latest(client):
    client.post("/tickets", json={"text": "A社との提携レート再交渉の方針を決めたい"})
    response = client.get("/brief/latest")
    assert response.status_code == 200
    body = response.json()
    assert "今日の要判断" in body["content"]
