import os

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_check():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_ask_rejects_empty_question():
    response = client.post("/api/ask", json={"question": "   "})
    assert response.status_code == 400


def test_ask_rejects_missing_question_field():
    response = client.post("/api/ask", json={})
    assert response.status_code == 422


@pytest.mark.skipif(bool(os.environ.get("GROQ_API_KEY")), reason="only meaningful without a key")
def test_ask_returns_503_when_no_api_key_configured():
    response = client.post("/api/ask", json={"question": "What are my best sellers?"})
    assert response.status_code == 503


@pytest.mark.skipif(not os.environ.get("GROQ_API_KEY"), reason="requires GROQ_API_KEY")
def test_ask_returns_grounded_answer_for_lowest_margin_question():
    response = client.post(
        "/api/ask", json={"question": "Which menu items have the lowest profit margin?"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["answer_text"]
    assert body["recommendation"] and body["recommendation"].strip()
    assert body["sql"].lower().startswith(("select", "with"))
    assert body["row_count"] > 0
    assert body["chart"] is not None
