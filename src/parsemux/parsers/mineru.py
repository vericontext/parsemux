"""MinerU parser adapter — best for scanned documents with GPU."""

from __future__ import annotations

import asyncio
import time
from typing import ClassVar

from parsemux.core.models import ParseRequest, ParseResult, ParserBackend
from parsemux.parsers.base import BaseParser


class MinerUParser(BaseParser):
    name: ClassVar = ParserBackend.MINERU
    supported_mimes: ClassVar = {
        "application/pdf",
        "image/png",
        "image/jpeg",
        "image/tiff",
    }
    description: ClassVar = "MinerU — best for scanned/image PDFs. GPU recommended (0.21s/page)."
    requires_gpu: ClassVar = True

    @classmethod
    def _check_deps(cls) -> None:
        from magic_pdf.data.data_reader_writer import FileBasedDataWriter  # noqa: F401

    async def parse(self, request: ParseRequest) -> ParseResult:
        import subprocess
        import tempfile
        from pathlib import Path

        start = time.perf_counter()

        if not request.file_path:
            raise ValueError("MinerU requires file_path")

        with tempfile.TemporaryDirectory() as tmpdir:
            cmd = [
                "magic-pdf",
                "-p", request.file_path,
                "-o", tmpdir,
                "-m", "auto",
            ]
            await asyncio.to_thread(
                subprocess.run, cmd, check=True, capture_output=True, text=True
            )

            # Find output markdown
            md_files = list(Path(tmpdir).rglob("*.md"))
            content = md_files[0].read_text() if md_files else ""

        elapsed = int((time.perf_counter() - start) * 1000)
        confidence = min(1.0, len(content.strip()) / 100) if content.strip() else 0.0

        return ParseResult(
            content=content,
            parser_used=self.name,
            metadata={"source": "mineru"},
            confidence=confidence,
            elapsed_ms=elapsed,
        )
