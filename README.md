# Parsemux

Document parser orchestrator — auto-routes to the optimal OSS parser for each document.

## Quick Start

```bash
# Install (lightweight: PyMuPDF + Kreuzberg)
pip install -e ".[pymupdf,kreuzberg,cli]"

# Parse a document
parsemux parse document.pdf

# Start Web UI + API server
pip install -e ".[pymupdf,kreuzberg,serve,cli]"
parsemux serve --ui

# Use as MCP server
pip install -e ".[pymupdf,kreuzberg,mcp,cli]"
parsemux mcp
```

## Supported Parsers

| Parser | Install | Best For |
|--------|---------|----------|
| PyMuPDF | `pip install parsemux[pymupdf]` | Digital PDFs (fastest) |
| Kreuzberg | `pip install parsemux[kreuzberg]` | 91+ formats, OCR |
| Docling | `pip install parsemux[docling]` | Tables (97.9% accuracy) |
| MinerU | `pip install parsemux[mineru]` | Scanned docs (GPU) |
| Marker | `pip install parsemux[marker]` | Batch + LLM-enhanced |

## Docker

```bash
docker compose up
# API: http://localhost:8000
# UI:  http://localhost:7860
```

## BYOK (Bring Your Own Key)

LLM-enhanced features require your own API key:

```bash
parsemux parse doc.pdf --use-llm --llm-key sk-...
```

Or via API header: `X-LLM-API-Key: sk-...`

## License

MIT
