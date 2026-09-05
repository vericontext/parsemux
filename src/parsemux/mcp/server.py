"""MCP server for parsemux — exposes document parsing as MCP tools.

Supports both stdio (local) and Streamable HTTP (remote) transports.
"""

from __future__ import annotations

import json

from mcp.server.fastmcp import FastMCP

from parsemux.core.engine import parse_document
from parsemux.core.models import ParserBackend, ParseRequest, VLMProvider
from parsemux.core.registry import list_parser_info
from parsemux.core.router import select_parser, _detect_mime

mcp_server = FastMCP(
    "parsemux",
    instructions=(
        "Parsemux is a document parser orchestrator. "
        "Upload or provide a file path to parse documents into structured markdown/text/json. "
        "It auto-routes to the best OSS parser (PyMuPDF, Kreuzberg, Docling, etc). "
        "Supports image extraction and VLM-based image description (BYOK)."
    ),
    host="0.0.0.0",
    stateless_http=True,
    json_response=True,
)


@mcp_server.tool()
async def parse_document_tool(
    file_path: str,
    parser: str | None = None,
    output_format: str = "markdown",
    use_llm: bool = False,
    llm_api_key: str | None = None,
    extract_images: bool = False,
    describe_images: bool = False,
    use_ocr: bool = True,
    vlm_provider: str | None = None,
    vlm_api_key: str | None = None,
) -> str:
    """Parse a document file and extract structured content.

    Auto-routes to the optimal parser unless one is specified.
    Supports PDF, DOCX, XLSX, PPTX, HTML, TXT, images, and 91+ formats.

    Args:
        file_path: Absolute path to the document file.
        parser: Parser backend (pymupdf, kreuzberg, docling, mineru, marker). Omit for auto-routing.
        output_format: Output format — markdown, json, or text.
        use_llm: Enable LLM-enhanced parsing (requires llm_api_key).
        llm_api_key: LLM API key for BYOK features.
        extract_images: Extract images from document as base64.
        describe_images: Generate VLM descriptions for extracted images.
        use_ocr: Enable OCR for scanned/image-based documents (default True, used by Docling).
        vlm_provider: VLM provider (openai, anthropic, google, ollama). Auto-detected from key if omitted.
        vlm_api_key: VLM API key (falls back to llm_api_key).
    """
    backend = ParserBackend(parser) if parser else None
    vlm = VLMProvider(vlm_provider) if vlm_provider else None
    request = ParseRequest(
        file_path=file_path,
        file_name=file_path.split("/")[-1],
        parser=backend,
        output_format=output_format,  # type: ignore[arg-type]
        use_llm=use_llm,
        llm_api_key=llm_api_key,
        extract_images=extract_images,
        describe_images=describe_images,
        use_ocr=use_ocr,
        vlm_provider=vlm,
        vlm_api_key=vlm_api_key,
    )
    result = await parse_document(request)
    return json.dumps(result.model_dump(), indent=2, ensure_ascii=False)


@mcp_server.tool()
async def list_parsers_tool() -> str:
    """List all available parser backends and their capabilities."""
    infos = list_parser_info()
    data = [i.model_dump() for i in infos]
    return json.dumps(data, indent=2, ensure_ascii=False)


@mcp_server.tool()
async def detect_doc_type(file_path: str) -> str:
    """Detect document type and recommend the best parser.

    Args:
        file_path: Absolute path to the document file.
    """
    request = ParseRequest(
        file_path=file_path,
        file_name=file_path.split("/")[-1],
    )
    mime = _detect_mime(request)
    recommended = select_parser(request)
    return json.dumps(
        {
            "file": file_path,
            "mime_type": mime,
            "recommended_parser": recommended.value,
        },
        indent=2,
    )


def run_mcp_stdio() -> None:
    """Run MCP server with stdio transport (for local clients like Claude Desktop)."""
    mcp_server.run(transport="stdio")


def run_mcp_remote(host: str = "0.0.0.0", port: int = 8000) -> None:
    """Run MCP server with Streamable HTTP transport (standalone remote server)."""
    import uvicorn

    app = mcp_server.streamable_http_app()
    uvicorn.run(app, host=host, port=port)
