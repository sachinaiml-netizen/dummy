from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_assistant_returns_grounded_answer():
    response = client.post(
        "/assistant/query",
        json={"question": "What should happen when a critical vendor is delayed?"},
    )
    assert response.status_code == 200
    body = response.json()
    assert "vendor" in body["answer"].lower()
    assert body["sources"]


def test_home_page_loads():
    response = client.get("/")
    assert response.status_code == 200
    assert "ProjectIQ" in response.text
