"""GPTZero API client.

Wraps the GPTZero v2 API for AI content detection.
Requires GPTZERO_API_KEY environment variable.
"""

import httpx


class GPTZeroError(Exception):
    """Raised when the GPTZero API returns an error."""


class GPTZeroClient:
    BASE_URL = "https://api.gptzero.me/v2"

    def __init__(self, api_key: str):
        if not api_key:
            raise GPTZeroError(
                "GPTZERO_API_KEY environment variable is required. "
                "Get your API key at https://app.gptzero.me/api"
            )
        self._client = httpx.Client(
            base_url=self.BASE_URL,
            headers={
                "x-api-key": api_key,
                "Accept": "application/json",
            },
            timeout=30.0,
        )

    def _request(self, method: str, path: str, **kwargs) -> dict:
        resp = self._client.request(method, path, **kwargs)
        if resp.status_code == 401:
            raise GPTZeroError("Invalid API key")
        if resp.status_code == 429:
            raise GPTZeroError("Rate limit exceeded — wait and retry")
        if resp.status_code >= 400:
            raise GPTZeroError(f"API error {resp.status_code}: {resp.text}")
        return resp.json()

    def detect_text(
        self,
        document: str,
        version: str | None = None,
        multilingual: bool = False,
    ) -> dict:
        """Detect AI-generated content in text.

        Returns overall classification plus sentence-level and
        paragraph-level AI probability scores.
        """
        payload: dict = {"document": document}
        if version:
            payload["version"] = version
        if multilingual:
            payload["multilingual"] = True
        return self._request("POST", "/predict/text", json=payload)

    def detect_files(
        self,
        file_paths: list[str],
        version: str | None = None,
    ) -> dict:
        """Detect AI-generated content in uploaded files.

        Accepts up to 50 files, 15MB combined, 50k chars per file.
        Supports PDF, DOCX, TXT, and other text-based formats.
        """
        files = []
        for path in file_paths:
            name = path.rsplit("/", 1)[-1]
            files.append(("files", (name, open(path, "rb"))))
        data = {}
        if version:
            data["version"] = version
        try:
            return self._request("POST", "/predict/files", files=files, data=data)
        finally:
            for _, (_, f) in files:
                f.close()

    def list_model_versions(self) -> dict:
        """Get available model versions for AI detection."""
        return self._request("GET", "/model-versions/ai-scan")
