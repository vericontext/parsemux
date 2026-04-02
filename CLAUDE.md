# Parsemux

Document parser orchestrator. Auto-routes documents to optimal OSS parser.

## Architecture

```
src/parsemux/
├── core/           # Engine, models, router, config, scoring, VLM
├── parsers/        # Adapters: pymupdf, kreuzberg, docling, mineru, marker
├── api/            # FastAPI REST + MCP mount at /mcp
├── mcp/            # FastMCP server (stdio + Streamable HTTP)
├── cli/            # Typer CLI (agentic: schema, --dry-run, --json)
└── ui/             # Gradio UI (optional)
web/                # Next.js frontend (Vercel)
```

## Key files

- `core/models.py` — ParseRequest, ParseResult, ExtractedImage, VLMProvider enums
- `core/engine.py` — Orchestrates parsing with fallback chain + VLM description
- `core/vlm.py` — VLM provider abstraction, reads from `vlm_models.yaml`
- `core/vlm_models.yaml` — **SSOT** for all VLM provider/model/pricing info
- `core/config.py` — Settings via env vars (`PARSEMUX_` prefix), `.env` support
- `core/router.py` — Auto-selects parser by MIME type + digital PDF detection
- `api/app.py` — FastAPI factory, CORS, demo mode guard, MCP mount
- `mcp/server.py` — FastMCP with 3 tools: parse_document_tool, list_parsers_tool, detect_doc_type

## Commands

```bash
parsemux parse doc.pdf                    # auto-route, markdown
parsemux parse doc.pdf --format json      # JSON output
parsemux parse doc.pdf --extract-images   # with base64 images
parsemux parse doc.pdf --dry-run          # preview routing
parsemux schema                           # machine-readable schemas
parsemux list-parsers --json              # available parsers
parsemux detect doc.pdf --json            # MIME + recommended parser
parsemux serve                            # REST API + MCP at /mcp
parsemux mcp                              # MCP stdio (local)
parsemux mcp --remote                     # MCP Streamable HTTP
```

## Running tests

```bash
pytest -q          # 33 tests, all should pass
```

## Modes

- `PARSEMUX_MODE=local` (default) — Full features, no limits, MCP remote enabled
- `PARSEMUX_MODE=demo` — Rate limit 10/min, 10MB file limit, MCP disabled

## Deployment

- **Frontend**: Vercel (auto-deploy on git push, root dir: `web/`)
- **Backend**: Fly.io (`flyctl deploy`, Tokyo region, demo mode)
- See `INTERNAL.md` (gitignored) for secrets, URLs, cost details

## Code patterns

- All parsers implement `BaseParser` ABC with `async parse(request) -> ParseResult`
- `is_available()` checks if deps are installed — optional deps pattern
- Engine fallback: tries parsers in order, skips on low confidence (< 0.3)
- VLM keys: per-request header (`X-VLM-API-Key`) > env (`PARSEMUX_VLM_API_KEY`)
- BYOK: keys never stored server-side, never logged
- Images: embedded as base64 in markdown content + separate `images[]` in ParseResult

## Versioning

Semver (`MAJOR.MINOR.PATCH`). Version lives in two files — both must match:
- `pyproject.toml` → `version = "X.Y.Z"`
- `src/parsemux/__init__.py` → `__version__ = "X.Y.Z"`

`scripts/check-version.sh` verifies consistency. Claude Code hook runs it before `git commit`.

**When to bump:**
- **PATCH** (0.2.0 → 0.2.1): bug fix, docs, refactor, dependency update
- **MINOR** (0.2 → 0.3): new feature, new CLI command, new parser, new API endpoint
- **MAJOR** (0.x → 1.0): stable public API, PyPI publish, breaking changes

**Rule: bump version in the same commit as the feature, not after.**

## Do not

- Do not hardcode VLM model names in Python — update `vlm_models.yaml` instead
- When updating cloud pricing in `core/scoring.py`, also update the date in `web/src/components/cost-panel.tsx`
- Do not add auth to demo mode — it's intentionally open (rate-limited)
- Do not store API keys in config or git — `.env` is gitignored
- Do not install Gradio on Fly.io — frontend is on Vercel
