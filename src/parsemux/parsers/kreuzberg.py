"""Kreuzberg parser adapter — Rust core, 91+ formats, built-in OCR."""

from __future__ import annotations

import base64
import time
from pathlib import Path
from typing import ClassVar

from parsemux.core.models import ExtractedImage, ParseRequest, ParseResult, ParserBackend
from parsemux.parsers.base import BaseParser


class KreuzbergParser(BaseParser):
    name: ClassVar = ParserBackend.KREUZBERG
    supported_mimes: ClassVar = {
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "application/msword",
        "application/vnd.ms-excel",
        "application/vnd.ms-powerpoint",
        "text/html",
        "text/plain",
        "text/csv",
        "text/markdown",
        "application/rtf",
        "application/epub+zip",
        "image/png",
        "image/jpeg",
        "image/tiff",
        "image/webp",
        "image/bmp",
    }
    description: ClassVar = (
        "Rust-core parser supporting 91+ formats with OCR. Best general-purpose backend."
    )

    @classmethod
    def _check_deps(cls) -> None:
        import kreuzberg  # noqa: F401

    async def parse(self, request: ParseRequest) -> ParseResult:
        from kreuzberg import extract_file, extract_bytes

        start = time.perf_counter()

        if request.file_path:
            result = await extract_file(Path(request.file_path))
        elif request.file_bytes:
            mime = _guess_mime(request.file_name) if request.file_name else "application/pdf"
            result = await extract_bytes(request.file_bytes, mime_type=mime)
        else:
            raise ValueError("Either file_path or file_bytes must be provided")

        elapsed = int((time.perf_counter() - start) * 1000)

        content = result.content if hasattr(result, "content") else str(result)
        confidence = min(1.0, len(content.strip()) / 100) if content.strip() else 0.0

        # Extract images if requested and available
        images: list[ExtractedImage] = []
        if request.extract_images and hasattr(result, "images") and result.images:
            for img in result.images:
                try:
                    img_data = img.get("data") or img.data if hasattr(img, "data") else None
                    if img_data:
                        b64 = base64.b64encode(img_data).decode() if isinstance(img_data, bytes) else str(img_data)
                        fmt = (img.get("format") if isinstance(img, dict) else getattr(img, "format", "png")) or "png"
                        images.append(
                            ExtractedImage(
                                data_b64=b64,
                                format=fmt,
                                width=img.get("width") if isinstance(img, dict) else getattr(img, "width", None),
                                height=img.get("height") if isinstance(img, dict) else getattr(img, "height", None),
                                page_number=img.get("page_number") if isinstance(img, dict) else getattr(img, "page_number", None),
                            )
                        )
                except Exception:
                    pass

            # Embed images in markdown content
            if images:
                img_md = "\n\n".join(
                    f"![image {i+1}](data:image/{img.format};base64,{img.data_b64})"
                    for i, img in enumerate(images)
                )
                content = content + "\n\n" + img_md

        return ParseResult(
            content=content,
            parser_used=self.name,
            metadata={"source": "kreuzberg"},
            confidence=confidence,
            elapsed_ms=elapsed,
            images=images,
        )


def _guess_mime(filename: str) -> str:
    ext_map = {
        ".pdf": "application/pdf",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        ".doc": "application/msword",
        ".html": "text/html",
        ".htm": "text/html",
        ".txt": "text/plain",
        ".csv": "text/csv",
        ".md": "text/markdown",
        ".rtf": "application/rtf",
        ".epub": "application/epub+zip",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".tiff": "image/tiff",
        ".tif": "image/tiff",
        ".webp": "image/webp",
        ".bmp": "image/bmp",
    }
    suffix = Path(filename).suffix.lower()
    return ext_map.get(suffix, "application/octet-stream")
