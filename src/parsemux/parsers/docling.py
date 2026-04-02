"""Docling parser adapter — best for tables (97.9% accuracy)."""

from __future__ import annotations

import asyncio
import time
from typing import Any, ClassVar

from parsemux.core.models import ParseRequest, ParseResult, ParserBackend
from parsemux.parsers.base import BaseParser


class DoclingParser(BaseParser):
    name: ClassVar = ParserBackend.DOCLING
    supported_mimes: ClassVar = {
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "text/html",
        "image/png",
        "image/jpeg",
        "image/tiff",
    }
    description: ClassVar = (
        "IBM Docling — best table extraction (97.9%), 65+ formats. Runs on CPU."
    )
    _converter: ClassVar[Any] = None

    @classmethod
    def _check_deps(cls) -> None:
        from docling.document_converter import DocumentConverter  # noqa: F401

    @classmethod
    def _get_converter(cls) -> Any:
        """Return cached DocumentConverter (creates on first call)."""
        if cls._converter is None:
            from docling.document_converter import DocumentConverter

            cls._converter = DocumentConverter()
        return cls._converter

    async def parse(self, request: ParseRequest) -> ParseResult:
        start = time.perf_counter()

        converter = self._get_converter()

        if request.file_path:
            result = await asyncio.to_thread(converter.convert, request.file_path)
        else:
            raise ValueError("Docling requires file_path (file_bytes not supported)")

        content = result.document.export_to_markdown()
        elapsed = int((time.perf_counter() - start) * 1000)

        confidence = min(1.0, len(content.strip()) / 100) if content.strip() else 0.0

        return ParseResult(
            content=content,
            parser_used=self.name,
            metadata={"source": "docling"},
            confidence=confidence,
            elapsed_ms=elapsed,
        )
