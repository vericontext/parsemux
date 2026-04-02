"""API route handlers."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, File, Header, Query, UploadFile
from pydantic import BaseModel

from parsemux.core.engine import parse_document
from parsemux.core.models import ParserBackend, ParseRequest, ParseResult, ParserInfo, VLMProvider
from parsemux.core.registry import list_parser_info

router = APIRouter()


class HealthResponse(BaseModel):
    status: str
    version: str
    mode: str
    parsers_available: int
    has_server_key: bool = False
    mcp_remote: bool = False
    limits: dict | None = None


@router.get("/health")
async def health() -> HealthResponse:
    from parsemux.core.config import settings

    infos = list_parser_info()
    available = sum(1 for i in infos if i.available)
    limits = None
    if settings.is_demo:
        limits = {
            "max_file_size_mb": settings.demo_max_file_size_mb,
            "rate_limit_per_min": settings.demo_rate_limit_per_min,
            "max_pages": settings.demo_max_pages,
        }
    return HealthResponse(
        status="ok",
        version="0.1.0",
        mode=settings.mode,
        parsers_available=available,
        has_server_key=bool(settings.vlm_api_key),
        mcp_remote=not (settings.is_demo and settings.demo_disable_mcp),
        limits=limits,
    )


@router.get("/parsers")
async def parsers() -> list[ParserInfo]:
    return list_parser_info()


@router.post("/parse")
async def parse(
    file: UploadFile = File(...),
    parser: Optional[str] = Query(None, description="Parser backend (auto if omitted)"),
    format: str = Query("markdown", description="Output format: markdown, json, text"),
    use_llm: bool = Query(False, description="Enable LLM-enhanced parsing"),
    extract_images: bool = Query(False, description="Extract images from document"),
    describe_images: bool = Query(False, description="Generate VLM descriptions for images"),
    vlm_provider: Optional[str] = Query(None, description="VLM provider: openai, anthropic, google, ollama"),
    x_llm_api_key: Optional[str] = Header(None, alias="X-LLM-API-Key"),
    x_vlm_api_key: Optional[str] = Header(None, alias="X-VLM-API-Key"),
) -> ParseResult:
    # Save uploaded file to temp
    content = await file.read()
    suffix = Path(file.filename or "upload").suffix
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    try:
        backend = ParserBackend(parser) if parser else None
        vlm = VLMProvider(vlm_provider) if vlm_provider else None
        request = ParseRequest(
            file_path=tmp_path,
            file_name=file.filename or "upload",
            parser=backend,
            output_format=format,  # type: ignore[arg-type]
            use_llm=use_llm,
            llm_api_key=x_llm_api_key,
            extract_images=extract_images,
            describe_images=describe_images,
            vlm_provider=vlm,
            vlm_api_key=x_vlm_api_key,
        )
        return await parse_document(request)
    finally:
        Path(tmp_path).unlink(missing_ok=True)


@router.post("/parse/compare")
async def parse_compare(
    file: UploadFile = File(...),
    format: str = Query("markdown"),
    x_llm_api_key: Optional[str] = Header(None, alias="X-LLM-API-Key"),
) -> list[ParseResult]:
    """Parse with all available backends and return comparison."""
    import asyncio

    from parsemux.core.registry import get_available_parsers, get_parser

    content = await file.read()
    suffix = Path(file.filename or "upload").suffix
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    try:
        available = get_available_parsers()
        tasks = []
        for backend in available:
            request = ParseRequest(
                file_path=tmp_path,
                file_name=file.filename or "upload",
                parser=backend,
                output_format=format,  # type: ignore[arg-type]
                llm_api_key=x_llm_api_key,
            )
            parser = get_parser(backend)
            tasks.append(_safe_parse(parser, request))

        results = await asyncio.gather(*tasks)
        return [r for r in results if r is not None]
    finally:
        Path(tmp_path).unlink(missing_ok=True)


async def _safe_parse(parser, request: ParseRequest) -> ParseResult | None:
    try:
        return await parser.parse(request)
    except Exception:
        return None
