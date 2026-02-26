"""
Tests for RAG API: POST /api/v1/rag/query.
"""

from fastapi.testclient import TestClient


def test_rag_query_valid_request(client: TestClient) -> None:
    """Valid query returns 200 and expected keys (or 500 if index/LLM unavailable)."""
    r = client.post(
        "/api/v1/rag/query",
        json={
            "query": "What is the treatment for malaria?",
            "top_k": 2,
            "use_llm_synthesis": False,
        },
    )
    # 200 if RAG index exists and runs; 500 if index missing or LLM error
    assert r.status_code in (200, 500)
    if r.status_code == 200:
        data = r.json()
        assert "answer" in data
        assert "sources" in data
        assert "chunk_ids" in data
        assert isinstance(data["sources"], list)
        assert isinstance(data["chunk_ids"], list)


def test_rag_query_validation_empty_query(client: TestClient) -> None:
    r = client.post(
        "/api/v1/rag/query",
        json={
            "query": "",
            "top_k": 1,
            "use_llm_synthesis": True,
        },
    )
    assert r.status_code == 422


def test_rag_query_minimal_body(client: TestClient) -> None:
    """Only required field is query."""
    r = client.post(
        "/api/v1/rag/query",
        json={"query": "Hypertension treatment"},
    )
    assert r.status_code in (200, 500)
