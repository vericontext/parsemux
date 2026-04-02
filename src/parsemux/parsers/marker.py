"""Marker parser adapter — batch processing with optional LLM enhancement."""

from __future__ import annotations

import asyncio
import time
from typing import ClassVar

from parsemux.core.models import ParseRequest, ParseResult, ParserBackend
from parsemux.parsers.base import BaseParser


class MarkerParser(BaseParser):
    name: ClassVar = ParserBackend.MARKER
    supported_mimes: ClassVar = {"application/pdf"}
    description: ClassVar = (
        "Marker — batch PDF processing (120 pages/sec). "
        "Optional LLM-enhanced mode with BYOK."
    )
    requires_gpu: ClassVar = True
    requires_llm_key: ClassVar = True

    @classmethod
    def _check_deps(cls) -> None:
        from marker.converters.pdf import PdfConverter  # noqa: F401

    async def parse(self, request: ParseRequest) -> ParseResult:
        import subprocess
        import tempfile
        from pathlib import Path

        start = time.perf_counter()

        if not request.file_path:
            raise ValueError("Marker requires file_path")

        with tempfile.TemporaryDirectory() as tmpdir:
            cmd = ["marker_single", request.file_path, "-o", tmpdir]
            if request.use_llm and request.llm_api_key:
                cmd.extend(["--use_llm", "--llm_api_key", request.llm_api_key])

            await asyncio.to_thread(
                subprocess.run, cmd, check=True, capture_output=True, text=True
            )

            md_files = list(Path(tmpdir).rglob("*.md"))
            content = md_files[0].read_text() if md_files else ""

        elapsed = int((time.perf_counter() - start) * 1000)
        confidence = min(1.0, len(content.strip()) / 100) if content.strip() else 0.0

        return ParseResult(
            content=content,
            parser_used=self.name,
            metadata={"source": "marker", "llm_enhanced": request.use_llm},
            confidence=confidence,
            elapsed_ms=elapsed,
        )
