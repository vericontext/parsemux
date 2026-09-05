"""Docling parser adapter — best for tables (97.9% accuracy)."""

from __future__ import annotations

import asyncio
import base64
import io
import time
from typing import Any, ClassVar

from parsemux.core.models import ExtractedImage, ParseRequest, ParseResult, ParserBackend
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
    _converters: ClassVar[dict[tuple[bool, bool], Any]] = {}

    @classmethod
    def _check_deps(cls) -> None:
        from docling.document_converter import DocumentConverter  # noqa: F401

    @classmethod
    def _get_converter(cls, use_ocr: bool = True, extract_images: bool = False) -> Any:
        """Return cached DocumentConverter for given OCR/image settings."""
        key = (use_ocr, extract_images)
        if key not in cls._converters:
            from docling.datamodel.base_models import InputFormat
            from docling.datamodel.pipeline_options import PdfPipelineOptions
            from docling.document_converter import DocumentConverter, PdfFormatOption

            pipeline_opts = PdfPipelineOptions(
                do_ocr=use_ocr,
                generate_picture_images=extract_images,
            )
            converter = DocumentConverter(
                format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_opts)}
            )
            cls._converters[key] = converter
        return cls._converters[key]

    async def parse(self, request: ParseRequest) -> ParseResult:
        start = time.perf_counter()

        converter = self._get_converter(request.use_ocr, request.extract_images)

        if request.file_path:
            result = await asyncio.to_thread(converter.convert, request.file_path)
        else:
            raise ValueError("Docling requires file_path (file_bytes not supported)")

        content = result.document.export_to_markdown()
        elapsed = int((time.perf_counter() - start) * 1000)

        # Extract images if requested
        images: list[ExtractedImage] = []
        if request.extract_images:
            images = self._extract_images(result.document, request.max_images)

        confidence = min(1.0, len(content.strip()) / 100) if content.strip() else 0.0

        return ParseResult(
            content=content,
            parser_used=self.name,
            metadata={"source": "docling"},
            confidence=confidence,
            elapsed_ms=elapsed,
            images=images,
        )

    @staticmethod
    def _extract_images(document: Any, max_images: int) -> list[ExtractedImage]:
        """Extract images from Docling document as base64 PNGs."""
        images: list[ExtractedImage] = []
        for pic in document.pictures[:max_images]:
            pil_img = pic.get_image(document)
            if pil_img is None:
                continue
            buf = io.BytesIO()
            pil_img.save(buf, format="PNG")
            data_b64 = base64.b64encode(buf.getvalue()).decode()
            page_num = pic.prov[0].page_no if pic.prov else None
            images.append(
                ExtractedImage(
                    data_b64=data_b64,
                    format="png",
                    width=pil_img.width,
                    height=pil_img.height,
                    page_number=page_num,
                )
            )
        return images
