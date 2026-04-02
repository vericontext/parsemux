"""Parsemux CLI — human and agent friendly."""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Optional

import typer

from parsemux.core.models import ParserBackend, ParseRequest, VLMProvider

app = typer.Typer(
    name="parsemux",
    help="Document parser orchestrator — auto-routes to the optimal OSS parser.",
    no_args_is_help=True,
)

# Max file size (bytes) for input validation
_MAX_FILE_SIZE = 200 * 1024 * 1024  # 200 MB


def _validate_path(path: Path) -> None:
    """Validate file path for safety and existence."""
    # Path traversal check
    try:
        resolved = path.resolve()
    except (OSError, ValueError) as e:
        typer.echo(json.dumps({"error": f"Invalid path: {e}"}), err=True)
        raise typer.Exit(1)

    if not resolved.exists():
        typer.echo(json.dumps({"error": f"File not found: {path}"}), err=True)
        raise typer.Exit(1)

    if resolved.is_dir():
        return  # dirs handled separately

    # File size check
    size = resolved.stat().st_size
    if size > _MAX_FILE_SIZE:
        typer.echo(
            json.dumps({"error": f"File too large: {size} bytes (max {_MAX_FILE_SIZE})"}),
            err=True,
        )
        raise typer.Exit(1)

    if size == 0:
        typer.echo(json.dumps({"error": "File is empty"}), err=True)
        raise typer.Exit(1)


@app.command()
def parse(
    path: str = typer.Argument(help="File path or directory to parse"),
    parser: Optional[str] = typer.Option(None, "--parser", "-p", help="Parser backend (auto if omitted)"),
    format: str = typer.Option("markdown", "--format", "-f", help="Output format: markdown, json, text"),
    use_llm: bool = typer.Option(False, "--use-llm", help="Enable LLM-enhanced parsing (BYOK)"),
    llm_key: Optional[str] = typer.Option(None, "--llm-key", help="LLM API key for BYOK"),
    extract_images: bool = typer.Option(False, "--extract-images", help="Extract images from document"),
    describe_images: bool = typer.Option(False, "--describe-images", help="Generate VLM descriptions for images"),
    vlm_provider: Optional[str] = typer.Option(None, "--vlm-provider", help="VLM provider: openai, anthropic, google, ollama"),
    vlm_key: Optional[str] = typer.Option(None, "--vlm-key", help="VLM API key (falls back to --llm-key)"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output file path"),
    batch: bool = typer.Option(False, "--batch", help="Process directory as batch"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Validate request and show routing without parsing"),
) -> None:
    """Parse a document and output structured content."""
    p = Path(path)
    _validate_path(p)

    if dry_run:
        _dry_run(p, parser)
        return

    if batch and p.is_dir():
        files = [f for f in p.iterdir() if f.is_file() and not f.name.startswith(".")]
        if not files:
            typer.echo(json.dumps({"error": "No files found in directory"}), err=True)
            raise typer.Exit(1)
        for f in sorted(files):
            typer.echo(f"--- {f.name} ---")
            _parse_single(f, parser, format, use_llm, llm_key, extract_images, describe_images, vlm_provider, vlm_key, output=None)
            typer.echo()
        return

    _parse_single(p, parser, format, use_llm, llm_key, extract_images, describe_images, vlm_provider, vlm_key, output)


def _dry_run(path: Path, parser: str | None) -> None:
    """Validate and preview routing without parsing."""
    from parsemux.core.router import select_parser, _detect_mime, _is_digital_pdf

    request = ParseRequest(
        file_path=str(path),
        file_name=path.name,
        parser=ParserBackend(parser) if parser else None,
    )
    mime = _detect_mime(request)
    backend = select_parser(request)
    is_digital = _is_digital_pdf(request) if mime == "application/pdf" else None
    file_size = path.stat().st_size if path.is_file() else None

    result = {
        "file": path.name,
        "mime_type": mime,
        "router_selection": backend.value,
        "is_digital_pdf": is_digital,
        "file_size_bytes": file_size,
        "valid": True,
    }
    typer.echo(json.dumps(result, indent=2))


def _parse_single(
    path: Path,
    parser: str | None,
    format: str,
    use_llm: bool,
    llm_key: str | None,
    extract_images: bool = False,
    describe_images: bool = False,
    vlm_provider: str | None = None,
    vlm_key: str | None = None,
    output: str | None = None,
) -> None:
    from parsemux.core.engine import parse_document

    backend = ParserBackend(parser) if parser else None
    vlm = VLMProvider(vlm_provider) if vlm_provider else None
    request = ParseRequest(
        file_path=str(path),
        file_name=path.name,
        parser=backend,
        output_format=format,  # type: ignore[arg-type]
        use_llm=use_llm,
        llm_api_key=llm_key,
        extract_images=extract_images,
        describe_images=describe_images,
        vlm_provider=vlm,
        vlm_api_key=vlm_key,
    )

    result = asyncio.run(parse_document(request))

    if format == "json":
        text = json.dumps(result.model_dump(), indent=2, ensure_ascii=False)
    else:
        text = result.content

    if output:
        Path(output).write_text(text, encoding="utf-8")
        typer.echo(f"Written to {output}")
    else:
        typer.echo(text)

    # Print metadata to stderr
    typer.echo(
        f"\n[parsemux] parser={result.parser_used.value} "
        f"confidence={result.confidence:.2f} "
        f"elapsed={result.elapsed_ms}ms",
        err=True,
    )


@app.command("list-parsers")
def list_parsers(
    output_json: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    """List all known parser backends and their availability."""
    from parsemux.core.registry import list_parser_info

    infos = list_parser_info()

    if output_json:
        typer.echo(json.dumps([i.model_dump() for i in infos], indent=2, ensure_ascii=False))
        return

    for info in infos:
        status = "✓" if info.available else "✗"
        typer.echo(f"  {status} {info.name.value:12s} — {info.description}")
        if not info.available:
            typer.echo(f"    Install: pip install parsemux[{info.name.value}]")


@app.command()
def detect(
    path: str = typer.Argument(help="File path to analyze"),
    output_json: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    """Detect document type and recommend the best parser."""
    from parsemux.core.router import select_parser, _detect_mime

    p = Path(path)
    _validate_path(p)

    request = ParseRequest(file_path=str(p), file_name=p.name)
    mime = _detect_mime(request)
    backend = select_parser(request)

    if output_json:
        typer.echo(json.dumps({
            "file": p.name,
            "mime_type": mime,
            "recommended_parser": backend.value,
        }, indent=2))
    else:
        typer.echo(f"File: {p.name}")
        typer.echo(f"MIME: {mime}")
        typer.echo(f"Recommended parser: {backend.value}")


@app.command()
def schema(
    command: Optional[str] = typer.Argument(None, help="Command name (omit for all)"),
    output_schema: bool = typer.Option(False, "--output-schema", help="Print the ParseResult JSON Schema"),
) -> None:
    """Show machine-readable schema for CLI commands (for AI agents)."""
    if output_schema:
        from parsemux.core.models import ParseResult

        typer.echo(json.dumps(ParseResult.model_json_schema(), indent=2))
        return

    schemas = {
        "parse": {
            "description": "Parse a document and extract structured content",
            "arguments": {"path": {"type": "string", "required": True, "description": "File path or directory"}},
            "options": {
                "parser": {"type": "string", "enum": [b.value for b in ParserBackend], "description": "Parser backend"},
                "format": {"type": "string", "enum": ["markdown", "json", "text"], "default": "markdown"},
                "extract_images": {"type": "boolean", "default": False},
                "describe_images": {"type": "boolean", "default": False},
                "vlm_provider": {"type": "string", "enum": ["openai", "anthropic", "google", "ollama"]},
                "vlm_key": {"type": "string", "description": "VLM API key (BYOK)"},
                "dry_run": {"type": "boolean", "default": False, "description": "Validate without parsing"},
                "output": {"type": "string", "description": "Output file path"},
                "batch": {"type": "boolean", "default": False},
            },
        },
        "detect": {
            "description": "Detect document type and recommend the best parser",
            "arguments": {"path": {"type": "string", "required": True}},
            "options": {"json": {"type": "boolean", "default": False}},
        },
        "list-parsers": {
            "description": "List available parser backends",
            "options": {"json": {"type": "boolean", "default": False}},
        },
        "schema": {
            "description": "Show machine-readable command schemas (this command)",
            "arguments": {"command": {"type": "string", "required": False}},
        },
        "serve": {
            "description": "Start REST API server (+ optional Gradio UI)",
            "options": {
                "host": {"type": "string", "default": "0.0.0.0"},
                "port": {"type": "integer", "default": 8000},
                "ui": {"type": "boolean", "default": False},
            },
        },
        "mcp": {
            "description": "Start MCP server (stdio or remote HTTP)",
            "options": {
                "remote": {"type": "boolean", "default": False, "description": "Use Streamable HTTP transport"},
                "host": {"type": "string", "default": "0.0.0.0"},
                "port": {"type": "integer", "default": 8000},
            },
        },
    }

    if command:
        if command not in schemas:
            typer.echo(json.dumps({"error": f"Unknown command: {command}"}), err=True)
            raise typer.Exit(1)
        typer.echo(json.dumps({command: schemas[command]}, indent=2))
    else:
        typer.echo(json.dumps(schemas, indent=2))


@app.command()
def serve(
    host: str = typer.Option("0.0.0.0", "--host", help="Bind host"),
    port: int = typer.Option(8000, "--port", help="API port"),
    ui: bool = typer.Option(False, "--ui", help="Serve Next.js Web UI"),
) -> None:
    """Start the REST API server (and optionally the Web UI). MCP remote is always available at /mcp."""
    import uvicorn

    from parsemux.api.app import create_app

    fastapi_app = create_app(with_ui=ui)
    # Use the MCP-wrapped ASGI app if available
    asgi_app = getattr(fastapi_app, "_final_app", fastapi_app)
    uvicorn.run(asgi_app, host=host, port=port)


@app.command()
def mcp(
    remote: bool = typer.Option(False, "--remote", help="Use Streamable HTTP transport (remote)"),
    host: str = typer.Option("0.0.0.0", "--host", help="Bind host (remote mode)"),
    port: int = typer.Option(8000, "--port", help="Bind port (remote mode)"),
) -> None:
    """Start the MCP server. Default: stdio. Use --remote for HTTP transport."""
    if remote:
        from parsemux.mcp.server import run_mcp_remote

        run_mcp_remote(host=host, port=port)
    else:
        from parsemux.mcp.server import run_mcp_stdio

        run_mcp_stdio()


@app.command()
def version() -> None:
    """Show version."""
    from parsemux import __version__

    typer.echo(f"parsemux {__version__}")


if __name__ == "__main__":
    app()
