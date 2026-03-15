# gptzero-mcp

MCP server for [GPTZero](https://gptzero.me) AI content detection. Get sentence-level and paragraph-level AI probability scores so you can surgically identify and fix AI-generated content.

## Installation

```bash
pip install gptzero-mcp
```

## Configuration

Set your API key as an environment variable:

```bash
export GPTZERO_API_KEY=your_api_key_here
```

Get your API key at [app.gptzero.me/api](https://app.gptzero.me/api).

### Claude Code

```bash
claude mcp add -s user -e GPTZERO_API_KEY=your_key gptzero -- gptzero-mcp
```

### Claude Desktop

Add to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "gptzero": {
      "command": "gptzero-mcp",
      "env": {
        "GPTZERO_API_KEY": "your_key"
      }
    }
  }
}
```

## Tools

### `detect_text`

Full AI detection with sentence-level and paragraph-level scoring. Returns:
- Overall classification (human/ai/mixed) with confidence
- Per-sentence AI probability and flags
- Per-paragraph AI probability
- Burstiness and perplexity metrics

### `detect_text_summary`

Quick overview — overall score plus only the flagged sentences.

### `detect_files`

Scan document files (PDF, DOCX, TXT). Up to 50 files per request.

### `list_model_versions`

List available GPTZero detection model versions.

## Example

```
> detect_text("Your content here...")

{
  "classification": "ai",
  "confidence": "high",
  "confidence_score": 0.95,
  "sentences": [
    {
      "sentence": "Your content here...",
      "ai_probability": 0.98,
      "flagged_as_ai": true
    }
  ]
}
```

## License

MIT
