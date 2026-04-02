# Parsemux

Document parser orchestrator — auto-routes to the optimal OSS parser for each document.

**[Try the demo](https://parsemux.vercel.app)** | [API Docs](https://parsemux-api.fly.dev/docs)

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

Or set in `.env` for local dev:

```bash
PARSEMUX_VLM_API_KEY=AIza...  # your key here
```

### Start your own server

```bash
parsemux serve                    # REST API at :8000 + MCP at /mcp
parsemux serve --ui               # + Gradio UI
```

### MCP server

```bash
# Local (Claude Desktop, Cursor — stdio transport)
parsemux mcp

# Remote (Streamable HTTP — for remote MCP clients)
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
parsemux schema parse                     # single command schema
parsemux detect doc.pdf --json            # detect type + recommend parser
parsemux list-parsers --json              # available parsers
```

## Supported Parsers

| Parser | Install | Best For | Speed |
|--------|---------|----------|-------|
| PyMuPDF | `parsemux[pymupdf]` | Digital PDFs | 1,000+ pages/sec |
| Kreuzberg | `parsemux[kreuzberg]` | 91+ formats, OCR | Rust core |
| Docling | `parsemux[docling]` | Tables (97.9%) | CPU |
| MinerU | `parsemux[mineru]` | Scanned docs | GPU recommended |
| Marker | `parsemux[marker]` | Batch + LLM-enhanced | GPU recommended |

## Cloud Demo vs Local

| | Local (OSS) | Cloud Demo |
|---|---|---|
| **Install** | `pip install parsemux[...]` | None (browser) |
| **URL** | `localhost:8000` | [parsemux.vercel.app](https://parsemux.vercel.app) |
| **File limit** | 100 MB | 10 MB |
| **Rate limit** | None | 10 req/min |
| **MCP remote** | Full (`/mcp`) | Disabled |
| **VLM key** | `.env` or CLI flag | BYOK (enter in UI) |
| **Cost** | Your infra | Free (limited) |

## Docker

```bash
docker compose up
# API: http://localhost:8000
# MCP: http://localhost:8000/mcp
```

## Self-hosting

```bash
# Fly.io (recommended)
fly launch
fly deploy

# Set demo mode for public deployment
fly secrets set PARSEMUX_MODE=demo
fly secrets set PARSEMUX_CORS_ORIGINS=https://your-domain.com
```

## License

MIT
