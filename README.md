# Parsemux

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![GitHub stars](https://img.shields.io/github/stars/vericontext/parsemux)](https://github.com/vericontext/parsemux/stargazers)

Document parser orchestrator — auto-routes to the optimal OSS parser for each document.

**[Try the demo](https://parsemux.com)** | [API Docs](https://parsemux-api.fly.dev/docs) | [GitHub](https://github.com/vericontext/parsemux)

## Why Parsemux?

- **Auto-routing** — detects document type and picks the best parser automatically
- **5 parsers, 1 interface** — PyMuPDF, Kreuzberg, Docling, MinerU, Marker
- **Every interface** — CLI, REST API, MCP server, Web UI
- **Image extraction + VLM description** — BYOK, auto-detects provider from key prefix
- **Compare mode** — run all parsers on the same doc, pick the best output
- **Cost comparison** — shows savings vs AWS Textract, Google Document AI, etc.
- **Zero config** — `pip install parsemux[pymupdf,cli]` and go

## Install

```bash
curl -fsSL https://raw.githubusercontent.com/vericontext/parsemux/main/install.sh | sh
```

Or with pip:

```bash
pip install parsemux[pymupdf,kreuzberg,cli]
```

## Usage

### Parse a document

```bash
parsemux parse document.pdf                          # auto-route, markdown output
parsemux parse document.pdf --parser kreuzberg       # explicit parser
parsemux parse document.pdf --format json            # JSON output
parsemux parse document.pdf --extract-images         # extract images as base64
parsemux parse document.pdf --dry-run                # preview routing without parsing
parsemux parse ./docs/ --batch                       # batch directory
```

### Image description with VLM (BYOK)

```bash
parsemux parse doc.pdf --extract-images --describe-images --vlm-key sk-...
```

Provider is auto-detected from key prefix (`sk-` → OpenAI, `sk-ant-` → Anthropic, `AI` → Google).
Default models: gpt-5.4-nano, claude-haiku-4.5, gemini-2.5-flash, qwen2.5vl:7b (local).

### Start your own server

```bash
parsemux serve                    # REST API at :8000 + MCP at /mcp
```

### MCP server

```bash
# Local (Claude Desktop, Cursor — stdio transport)
parsemux mcp

# Remote (Streamable HTTP)
parsemux mcp --remote --port 8000
```

**Claude Desktop config** (local):
```json
{
  "mcpServers": {
    "parsemux": {
      "command": "parsemux",
      "args": ["mcp"]
    }
  }
}
```

### For AI agents

```bash
parsemux schema                           # machine-readable command schemas
parsemux parse doc.pdf --dry-run          # preview routing
parsemux list-parsers --json              # available parsers as JSON
parsemux detect doc.pdf --json            # MIME + recommended parser
```

## Supported Parsers

| Parser | Best For | Speed |
|--------|----------|-------|
| **PyMuPDF** | Digital PDFs | 1,000+ pages/sec |
| **Kreuzberg** | 91+ formats, OCR | Rust core |
| **Docling** | Tables (97.9%) | CPU |
| **MinerU** | Scanned docs | GPU |
| **Marker** | Batch + LLM-enhanced | GPU |

## Cloud Demo vs Self-hosted

| | Self-hosted | [Demo](https://parsemux.com) |
|---|---|---|
| File limit | 100 MB | 10 MB |
| Rate limit | None | 10 req/min |
| MCP remote | `/mcp` | Disabled |
| VLM key | `.env` | BYOK (enter in UI) |

## Docker

```bash
docker compose up
# API: http://localhost:8000
# MCP: http://localhost:8000/mcp
```

## Contributing

Contributions welcome!

1. Fork the repo
2. Create a feature branch (`git checkout -b feat/my-feature`)
3. Run tests (`pytest -q`)
4. Open a PR

See [issues](https://github.com/vericontext/parsemux/issues) for ideas.

## Acknowledgments

Built on the shoulders of these excellent open-source parsers:

- [PyMuPDF](https://github.com/pymupdf/PyMuPDF) — blazing-fast digital PDF parsing
- [Kreuzberg](https://github.com/Goldziher/kreuzberg) — Rust-powered multi-format + OCR
- [Docling](https://github.com/DS4SD/docling) — best-in-class table extraction
- [MinerU](https://github.com/opendatalab/MinerU) — high-quality scanned doc pipeline
- [Marker](https://github.com/VikParuchuri/marker) — LLM-enhanced batch conversion

## License

[MIT](LICENSE)
