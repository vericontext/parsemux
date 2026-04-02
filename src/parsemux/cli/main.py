"""Parsemux CLI."""

from __future__ import annotations

import asyncio
import json
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
) -> None:
    """Parse a document and output structured content."""
    p = Path(path)

    if batch and p.is_dir():
        files = [f for f in p.iterdir() if f.is_file() and not f.name.startswith(".")]
        if not files:
            typer.echo("No files found in directory.", err=True)
            raise typer.Exit(1)
        for f in sorted(files):
            typer.echo(f"--- {f.name} ---")
            _parse_single(f, parser, format, use_llm, llm_key, extract_images, describe_images, vlm_provider, vlm_key, output=None)
            typer.echo()
        return

    if not p.exists():
        typer.echo(f"File not found: {path}", err=True)
        raise typer.Exit(1)

    _parse_single(p, parser, format, use_llm, llm_key, extract_images, describe_images, vlm_provider, vlm_key, output)


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
def list_parsers() -> None:
    """List all known parser backends and their availability."""
    from parsemux.core.registry import list_parser_info

    infos = list_parser_info()
    for info in infos:
        status = "✓" if info.available else "✗"
        typer.echo(f"  {status} {info.name.value:12s} — {info.description}")
        if not info.available:
            typer.echo(f"    Install: pip install parsemux[{info.name.value}]")


@app.command()
def detect(
    path: str = typer.Argument(help="File path to analyze"),
) -> None:
    """Detect document type and recommend the best parser."""
    from parsemux.core.router import select_parser, _detect_mime

    p = Path(path)
    if not p.exists():
        typer.echo(f"File not found: {path}", err=True)
        raise typer.Exit(1)

    request = ParseRequest(file_path=str(p), file_name=p.name)
    mime = _detect_mime(request)
    backend = select_parser(request)

    typer.echo(f"File: {p.name}")
    typer.echo(f"MIME: {mime}")
    typer.echo(f"Recommended parser: {backend.value}")


@app.command()
def serve(
    host: str = typer.Option("0.0.0.0", "--host", help="Bind host"),
    port: int = typer.Option(8000, "--port", help="API port"),
    ui: bool = typer.Option(False, "--ui", help="Also launch Gradio UI"),
) -> None:
    """Start the REST API server (and optionally the Web UI)."""
    import uvicorn

    from parsemux.api.app import create_app

    app = create_app(with_ui=ui)
    uvicorn.run(app, host=host, port=port)


@app.command()
def mcp() -> None:
    """Start the MCP server (stdio transport)."""
    from parsemux.mcp.server import run_mcp_server

    asyncio.run(run_mcp_server())


@app.command()
def version() -> None:
    """Show version."""
    from parsemux import __version__

    typer.echo(f"parsemux {__version__}")


if __name__ == "__main__":
    app()
