"""PyMuPDF4LLM parser adapter — fastest for digital PDFs."""

from __future__ import annotations

import asyncio
import base64
import re
import time
from typing import ClassVar

from parsemux.core.models import ExtractedImage, ParseRequest, ParseResult, ParserBackend
from parsemux.parsers.base import BaseParser

# Regex to find base64 images embedded by pymupdf4llm
_B64_IMAGE_RE = re.compile(
    r"!\[([^\]]*)\]\(data:image/(\w+);base64,([A-Za-z0-9+/=\s]+)\)"
)


class PyMuPDFParser(BaseParser):
    name: ClassVar = ParserBackend.PYMUPDF
    supported_mimes: ClassVar = {"application/pdf"}
    description: ClassVar = "Fastest parser for digital PDFs (1,000+ pages/sec). No GPU required."

    @classmethod
    def _check_deps(cls) -> None:
        import pymupdf4llm  # noqa: F401

    async def parse(self, request: ParseRequest) -> ParseResult:
        import pymupdf4llm

        start = time.perf_counter()

        kwargs: dict = {}
        if request.pages is not None:
            kwargs["pages"] = request.pages
        if request.extract_images:
            kwargs["embed_images"] = True

        if request.file_path:
            source = request.file_path
        elif request.file_bytes:
            import pymupdf

            source = pymupdf.open(stream=request.file_bytes, filetype="pdf")
        else:
            raise ValueError("Either file_path or file_bytes must be provided")

        md_text = await asyncio.to_thread(pymupdf4llm.to_markdown, source, **kwargs)

        elapsed = int((time.perf_counter() - start) * 1000)

        content = md_text if isinstance(md_text, str) else "\n".join(
            chunk["text"] for chunk in md_text
        )
        confidence = min(1.0, len(content.strip()) / 100) if content.strip() else 0.0

        # Extract image metadata from embedded base64 images
        images: list[ExtractedImage] = []
        if request.extract_images:
            for match in _B64_IMAGE_RE.finditer(content):
                alt, fmt, data_b64 = match.group(1), match.group(2), match.group(3)
                data_b64_clean = data_b64.replace("\n", "").replace(" ", "")
                try:
                    raw = base64.b64decode(data_b64_clean)
                    images.append(
                        ExtractedImage(
                            data_b64=data_b64_clean,
                            format=fmt,
                            width=None,
                            height=None,
                            description=alt if alt else None,
                        )
                    )
                except Exception:
                    pass

        return ParseResult(
            content=content,
            parser_used=self.name,
            metadata={"source": "pymupdf4llm"},
            confidence=confidence,
            elapsed_ms=elapsed,
            images=images,
        )
