"""GPTZero MCP server for AI content detection.

Provides sentence-level and paragraph-level AI detection scores
so you can surgically identify and fix AI-generated content.

Requires GPTZERO_API_KEY environment variable.
Get your API key at https://app.gptzero.me/api
"""

import json
import os

from mcp.server.fastmcp import FastMCP

from .client import GPTZeroClient, GPTZeroError

mcp = FastMCP(
    "GPTZero",
    instructions=(
        "GPTZero AI content detection server. "
        "Use detect_text to analyze content and get sentence-level AI scores. "
        "Use detect_text_summary for a quick overall score. "
        "Use detect_files to scan documents (PDF, DOCX, TXT). "
        "Use list_model_versions to see available detection models. "
        "Requires GPTZERO_API_KEY environment variable."
    ),
)

_client: GPTZeroClient | None = None


def _get_client() -> GPTZeroClient:
    global _client
    if _client is None:
        _client = GPTZeroClient(
            api_key=os.environ.get("GPTZERO_API_KEY", ""),
        )
    return _client


def _format_sentences(sentences: list[dict]) -> list[dict]:
    """Format sentence-level results for readability."""
    results = []
    for i, s in enumerate(sentences):
        results.append({
            "index": i,
            "sentence": s.get("sentence", ""),
            "ai_probability": round(s.get("generated_prob", 0), 4),
            "flagged_as_ai": s.get("highlight_sentence_for_ai", False),
            "perplexity": s.get("perplexity", 0),
        })
    return results


def _format_paragraphs(paragraphs: list[dict]) -> list[dict]:
    """Format paragraph-level results for readability."""
    results = []
    for i, p in enumerate(paragraphs):
        results.append({
            "index": i,
            "ai_probability": round(p.get("completely_generated_prob", 0), 4),
            "num_sentences": p.get("num_sentences", 0),
            "start_sentence_index": p.get("start_sentence_index", 0),
        })
    return results


def _format_document(doc: dict) -> dict:
    """Format a single document prediction result."""
    result = {
        "classification": doc.get("predicted_class", "unknown"),
        "confidence": doc.get("confidence_category", "unknown"),
        "confidence_score": round(doc.get("confidence_score", 0), 4),
        "class_probabilities": {
            k: round(v, 4)
            for k, v in doc.get("class_probabilities", {}).items()
        },
        "average_ai_probability": round(
            doc.get("average_generated_prob", 0), 4
        ),
        "completely_generated_probability": round(
            doc.get("completely_generated_prob", 0), 4
        ),
        "burstiness": round(doc.get("overall_burstiness", 0), 4),
        "result_message": doc.get("result_message", ""),
    }

    if doc.get("sentences"):
        result["sentences"] = _format_sentences(doc["sentences"])
        flagged = [s for s in result["sentences"] if s["flagged_as_ai"]]
        result["flagged_sentence_count"] = len(flagged)
        result["total_sentence_count"] = len(result["sentences"])

    if doc.get("paragraphs"):
        result["paragraphs"] = _format_paragraphs(doc["paragraphs"])

    if doc.get("subclass"):
        result["subclass"] = doc["subclass"]

    return result


# ── Text Detection ────────────────────────────────────────────────────


@mcp.tool()
def detect_text(
    text: str,
    version: str = "",
    multilingual: bool = False,
) -> str:
    """Detect AI-generated content in text with full sentence-level detail.

    Returns overall classification plus per-sentence AI probability scores
    and flags, so you can identify exactly which sentences need rewriting.

    Args:
        text: The text content to analyze (minimum ~50 words for reliable results).
        version: Optional model version string (e.g. '2025-05-14-multilingual').
        multilingual: Set True for non-English content.
    """
    try:
        client = _get_client()
        raw = client.detect_text(
            document=text,
            version=version or None,
            multilingual=multilingual,
        )
        documents = raw.get("documents", [])
        if not documents:
            return json.dumps({"status": "error", "message": "No results returned"}, indent=2)

        result = _format_document(documents[0])
        result["scan_id"] = raw.get("scanId", "")
        result["model_version"] = raw.get("version", "")
        return json.dumps({"status": "success", "data": result}, indent=2)
    except GPTZeroError as e:
        return json.dumps({"status": "error", "message": str(e)}, indent=2)
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)}, indent=2)


@mcp.tool()
def detect_text_summary(
    text: str,
    version: str = "",
    multilingual: bool = False,
) -> str:
    """Quick AI detection summary — overall score and flagged sentences only.

    Use this for a fast overview. Use detect_text for full detail.

    Args:
        text: The text content to analyze.
        version: Optional model version string.
        multilingual: Set True for non-English content.
    """
    try:
        client = _get_client()
        raw = client.detect_text(
            document=text,
            version=version or None,
            multilingual=multilingual,
        )
        documents = raw.get("documents", [])
        if not documents:
            return json.dumps({"status": "error", "message": "No results returned"}, indent=2)

        doc = documents[0]
        flagged = [
            {
                "sentence": s.get("sentence", ""),
                "ai_probability": round(s.get("generated_prob", 0), 4),
            }
            for s in doc.get("sentences", [])
            if s.get("highlight_sentence_for_ai")
        ]

        summary = {
            "classification": doc.get("predicted_class", "unknown"),
            "confidence": doc.get("confidence_category", "unknown"),
            "average_ai_probability": round(
                doc.get("average_generated_prob", 0), 4
            ),
            "flagged_sentences": flagged,
            "flagged_count": len(flagged),
            "total_sentences": len(doc.get("sentences", [])),
        }
        return json.dumps({"status": "success", "data": summary}, indent=2)
    except GPTZeroError as e:
        return json.dumps({"status": "error", "message": str(e)}, indent=2)
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)}, indent=2)


# ── File Detection ────────────────────────────────────────────────────


@mcp.tool()
def detect_files(
    file_paths: list[str],
    version: str = "",
) -> str:
    """Detect AI-generated content in document files.

    Supports PDF, DOCX, TXT, and other text-based formats.
    Up to 50 files per request, 15MB combined, 50k chars per file.

    Args:
        file_paths: List of absolute file paths to analyze.
        version: Optional model version string.
    """
    try:
        client = _get_client()
        raw = client.detect_files(
            file_paths=file_paths,
            version=version or None,
        )
        documents = raw.get("documents", [])
        results = []
        for doc in documents:
            results.append(_format_document(doc))

        return json.dumps({
            "status": "success",
            "data": {
                "file_count": len(results),
                "documents": results,
            },
        }, indent=2)
    except GPTZeroError as e:
        return json.dumps({"status": "error", "message": str(e)}, indent=2)
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)}, indent=2)


# ── Model Versions ───────────────────────────────────────────────────


@mcp.tool()
def list_model_versions() -> str:
    """List available GPTZero model versions for AI detection.

    Use a specific version string with detect_text or detect_files
    to pin to a particular model.
    """
    try:
        client = _get_client()
        raw = client.list_model_versions()
        return json.dumps({"status": "success", "data": raw}, indent=2)
    except GPTZeroError as e:
        return json.dumps({"status": "error", "message": str(e)}, indent=2)
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)}, indent=2)


def main():
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
