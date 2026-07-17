"""Foundation tests: landing page, health, error handling, security headers."""

from fastapi.testclient import TestClient


def test_landing_page(client: TestClient) -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "CyberArena" in response.text


def test_health_endpoint(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["database"] == "ok"
    assert body["app"] == "CyberArena"


def test_security_headers(client: TestClient) -> None:
    response = client.get("/")
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert "content-security-policy" in response.headers
    assert "referrer-policy" in response.headers


def test_404_html_for_browser(client: TestClient) -> None:
    response = client.get("/nonexistent", headers={"accept": "text/html"})
    assert response.status_code == 404
    assert "text/html" in response.headers["content-type"]
    assert "404" in response.text


def test_404_json_for_api_clients(client: TestClient) -> None:
    response = client.get("/nonexistent", headers={"accept": "application/json"})
    assert response.status_code == 404
    assert response.json() == {"detail": "Not Found"}


def test_static_files_served(client: TestClient) -> None:
    response = client.get("/static/css/main.css")
    assert response.status_code == 200
