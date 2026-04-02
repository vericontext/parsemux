"""Document router — selects the optimal parser for each document."""

from __future__ import annotations

import asyncio
from pathlib import Path

from parsemux.core.models import ParserBackend, ParseRequest
from parsemux.core.registry import get_available_parsers


def select_parser(request: ParseRequest) -> ParserBackend:
    """Select the best available parser for the given request."""
    available = set(get_available_parsers().keys())

    if not available:
        raise RuntimeError("No parsers are available. Install at least one parser backend.")

    # 1. User explicitly chose a parser
    if request.parser is not None:
        if request.parser not in available:
            raise RuntimeError(
                f"Parser '{request.parser.value}' is not available. "
                f"Available: {[p.value for p in available]}"
            )
        return request.parser

    # 2. LLM-enhanced mode → Marker
    if request.use_llm and ParserBackend.MARKER in available:
        return ParserBackend.MARKER

    # Determine file type
    mime = _detect_mime(request)

    # 3. Digital PDF → PyMuPDF (fastest)
    if mime == "application/pdf" and ParserBackend.PYMUPDF in available:
        if _is_digital_pdf(request):
            return ParserBackend.PYMUPDF

    # 4. Scanned PDF → MinerU (GPU) or Kreuzberg (CPU OCR)
    if mime == "application/pdf":
        if ParserBackend.MINERU in available:
            return ParserBackend.MINERU
        if ParserBackend.KREUZBERG in available:
            return ParserBackend.KREUZBERG
        if ParserBackend.DOCLING in available:
            return ParserBackend.DOCLING

    # 5. Non-PDF formats → Kreuzberg (91+ formats)
    if ParserBackend.KREUZBERG in available:
        return ParserBackend.KREUZBERG

    # 6. Fallback: Docling, then first available
    if ParserBackend.DOCLING in available:
        return ParserBackend.DOCLING

    return next(iter(available))


def _detect_mime(request: ParseRequest) -> str:
    """Detect MIME type from file path or name."""
    filename = request.file_name or (request.file_path or "")
    suffix = Path(filename).suffix.lower()
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
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".tiff": "image/tiff",
        ".tif": "image/tiff",
    }
    return ext_map.get(suffix, "application/octet-stream")


def _is_digital_pdf(request: ParseRequest) -> bool:
    """Quick check: does the PDF have extractable text? (< 100ms)"""
    try:
        import pymupdf

        if request.file_path:
            doc = pymupdf.open(request.file_path)
        elif request.file_bytes:
            doc = pymupdf.open(stream=request.file_bytes, filetype="pdf")
        else:
            return True

        # Sample first 3 pages
        total_text = 0
        pages_to_check = min(3, len(doc))
        for i in range(pages_to_check):
            total_text += len(doc[i].get_text().strip())
        doc.close()

        # If average text per page is > 50 chars, it's likely digital
        return (total_text / max(pages_to_check, 1)) > 50

    except Exception:
        return True  # Default to digital (PyMuPDF) on error
