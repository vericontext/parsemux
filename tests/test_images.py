"""Tests for image extraction and VLM provider."""

from __future__ import annotations

from pathlib import Path

import pytest

from parsemux.core.models import ParserBackend, ParseRequest, VLMProvider
from parsemux.core.vlm import get_vlm_provider


# --- Image Extraction Tests ---


@pytest.mark.asyncio
async def test_pymupdf_extract_images(pdf_with_image: Path):
    from parsemux.parsers.pymupdf import PyMuPDFParser

    parser = PyMuPDFParser()
    request = ParseRequest(
        file_path=str(pdf_with_image),
        file_name="with_image.pdf",
        extract_images=True,
    )
    result = await parser.parse(request)

    assert result.parser_used == ParserBackend.PYMUPDF
    assert len(result.images) > 0
    assert result.images[0].data_b64  # has base64 data
    assert result.images[0].format in ("png", "jpeg")


@pytest.mark.asyncio
async def test_pymupdf_no_images_by_default(pdf_with_image: Path):
    from parsemux.parsers.pymupdf import PyMuPDFParser

    parser = PyMuPDFParser()
    request = ParseRequest(
        file_path=str(pdf_with_image),
        file_name="with_image.pdf",
        extract_images=False,
    )
    result = await parser.parse(request)

    assert len(result.images) == 0
    assert "data:image" not in result.content


@pytest.mark.asyncio
async def test_engine_extract_images(pdf_with_image: Path):
    from parsemux.core.engine import parse_document

    request = ParseRequest(
        file_path=str(pdf_with_image),
        file_name="with_image.pdf",
        extract_images=True,
    )
    result = await parse_document(request)

    assert result.parser_used == ParserBackend.PYMUPDF
    assert len(result.images) > 0
    assert result.metadata.get("image_count", 0) > 0


@pytest.mark.asyncio
async def test_engine_no_images_default(sample_pdf: Path):
    from parsemux.core.engine import parse_document

    request = ParseRequest(
        file_path=str(sample_pdf),
        file_name="test.pdf",
    )
    result = await parse_document(request)

    assert len(result.images) == 0


# --- VLM Provider Tests ---


def test_vlm_provider_auto_detect_openai():
    provider = get_vlm_provider(None, "sk-proj-abc123")
    assert provider.provider_name == "openai"
    assert provider.model == "gpt-5.4-nano"


def test_vlm_provider_auto_detect_anthropic():
    provider = get_vlm_provider(None, "sk-ant-api03-abc123")
    assert provider.provider_name == "anthropic"
    assert provider.model == "claude-haiku-4-5-20251001"


def test_vlm_provider_auto_detect_google():
    provider = get_vlm_provider(None, "AIzaSyAbc123")
    assert provider.provider_name == "google"
    assert provider.model == "gemini-2.5-flash"


def test_vlm_provider_explicit():
    provider = get_vlm_provider(VLMProvider.OLLAMA, "")
    assert provider.provider_name == "ollama"
    assert provider.model == "qwen2.5vl:7b"


def test_vlm_provider_custom_model():
    provider = get_vlm_provider(VLMProvider.OPENAI, "sk-test", model="gpt-4o")
    assert provider.model == "gpt-4o"


def test_vlm_cost_estimate():
    provider = get_vlm_provider(VLMProvider.OPENAI, "sk-test")
    assert provider.estimate_cost(10) == pytest.approx(0.001)

    provider_free = get_vlm_provider(VLMProvider.OLLAMA, "")
    assert provider_free.estimate_cost(10) == 0.0
