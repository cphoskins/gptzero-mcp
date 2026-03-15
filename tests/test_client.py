"""Tests for GPTZero API client — mocked, no credentials needed."""

from unittest.mock import MagicMock, patch

import pytest

from gptzero_mcp.client import GPTZeroClient, GPTZeroError


# ── Fixtures ─────────────────────────────────────────────────────────


@pytest.fixture
def client():
    """Create a client with a fake API key."""
    return GPTZeroClient(api_key="test-key-12345")


def _mock_response(status_code: int = 200, json_data: dict | None = None, text: str = ""):
    """Build a mock httpx.Response."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data or {}
    resp.text = text
    return resp


# ── Init ─────────────────────────────────────────────────────────────


def test_missing_api_key_raises():
    with pytest.raises(GPTZeroError, match="GPTZERO_API_KEY"):
        GPTZeroClient(api_key="")


def test_client_sets_headers(client):
    headers = client._client.headers
    assert headers["x-api-key"] == "test-key-12345"
    assert headers["accept"] == "application/json"


# ── detect_text ──────────────────────────────────────────────────────


def test_detect_text_success(client):
    expected = {
        "documents": [
            {
                "predicted_class": "ai",
                "confidence_category": "high",
                "confidence_score": 0.95,
                "average_generated_prob": 0.98,
                "completely_generated_prob": 0.95,
                "overall_burstiness": 0,
                "sentences": [
                    {
                        "sentence": "Test sentence.",
                        "generated_prob": 0.99,
                        "highlight_sentence_for_ai": True,
                        "perplexity": 5,
                    }
                ],
                "paragraphs": [
                    {
                        "completely_generated_prob": 0.87,
                        "num_sentences": 1,
                        "start_sentence_index": 0,
                    }
                ],
            }
        ],
        "scanId": "scan-123",
        "version": "2026-03-11-base",
    }
    with patch.object(client, "_request", return_value=expected) as mock_req:
        result = client.detect_text("Test sentence.")
        mock_req.assert_called_once_with(
            "POST", "/predict/text", json={"document": "Test sentence."}
        )
    assert result["documents"][0]["predicted_class"] == "ai"
    assert result["scanId"] == "scan-123"


def test_detect_text_with_version(client):
    with patch.object(client, "_request", return_value={"documents": []}) as mock_req:
        client.detect_text("Hello", version="2026-01-01")
        mock_req.assert_called_once_with(
            "POST",
            "/predict/text",
            json={"document": "Hello", "version": "2026-01-01"},
        )


def test_detect_text_multilingual(client):
    with patch.object(client, "_request", return_value={"documents": []}) as mock_req:
        client.detect_text("Bonjour", multilingual=True)
        mock_req.assert_called_once_with(
            "POST",
            "/predict/text",
            json={"document": "Bonjour", "multilingual": True},
        )


# ── list_model_versions ─────────────────────────────────────────────


def test_list_model_versions(client):
    expected = {"models": ["2026-03-11-base", "2025-05-14-multilingual"]}
    with patch.object(client, "_request", return_value=expected) as mock_req:
        result = client.list_model_versions()
        mock_req.assert_called_once_with("GET", "/model-versions/ai-scan")
    assert "models" in result


# ── Error handling ───────────────────────────────────────────────────


def test_401_raises_invalid_key(client):
    mock_resp = _mock_response(status_code=401)
    with patch.object(client._client, "request", return_value=mock_resp):
        with pytest.raises(GPTZeroError, match="Invalid API key"):
            client.detect_text("test")


def test_429_raises_rate_limit(client):
    mock_resp = _mock_response(status_code=429)
    with patch.object(client._client, "request", return_value=mock_resp):
        with pytest.raises(GPTZeroError, match="Rate limit"):
            client.detect_text("test")


def test_500_raises_api_error(client):
    mock_resp = _mock_response(status_code=500, text="Internal Server Error")
    with patch.object(client._client, "request", return_value=mock_resp):
        with pytest.raises(GPTZeroError, match="API error 500"):
            client.detect_text("test")
