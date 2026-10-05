from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_root_redirects_to_docs():
    response = client.get("/", follow_redirects=False)
    assert response.status_code in (302, 307)
    assert response.headers["location"] == "/docs"


def test_swagger_ui_is_served():
    response = client.get("/docs")
    assert response.status_code == 200
    assert "swagger-ui" in response.text.lower()


def test_openapi_schema_is_served():
    response = client.get("/openapi.json")
    assert response.status_code == 200
    schema = response.json()
    assert schema["info"]["title"] == "Log Filter Service"
    assert "/logs" in schema["paths"]


def test_ingest_log():
    response = client.post(
        "/logs",
        json={"source": "cisco-switch-01", "level": "error", "message": "link down"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["level"] == "ERROR"
    assert body["source"] == "cisco-switch-01"
    assert "id" in body


def test_ingest_log_invalid_level():
    response = client.post(
        "/logs",
        json={"source": "cisco-switch-01", "level": "NOT_A_LEVEL", "message": "oops"},
    )
    assert response.status_code == 422


def test_list_and_filter_logs():
    client.post("/logs", json={"source": "router-a", "level": "info", "message": "boot ok"})
    client.post("/logs", json={"source": "router-b", "level": "critical", "message": "fan failure"})

    all_logs = client.get("/logs").json()
    assert len(all_logs) >= 2

    critical_only = client.get("/logs", params={"level": "critical"}).json()
    assert all(entry["level"] == "CRITICAL" for entry in critical_only)


def test_get_log_not_found():
    response = client.get("/logs/does-not-exist")
    assert response.status_code == 404


def test_delete_log():
    created = client.post(
        "/logs",
        json={"source": "switch-c", "level": "warning", "message": "high temp"},
    ).json()
    log_id = created["id"]

    delete_response = client.delete(f"/logs/{log_id}")
    assert delete_response.status_code == 204

    get_response = client.get(f"/logs/{log_id}")
    assert get_response.status_code == 404
