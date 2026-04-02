"""Tests for parser adapters."""

from __future__ import annotations

from pathlib import Path

import pytest

from parsemux.core.models import ParserBackend, ParseRequest


@pytest.mark.asyncio
async def test_pymupdf_parse(sample_pdf: Path):
    from parsemux.parsers.pymupdf import PyMuPDFParser

    parser = PyMuPDFParser()
    request = ParseRequest(file_path=str(sample_pdf), file_name="test.pdf")
    result = await parser.parse(request)

    assert result.parser_used == ParserBackend.PYMUPDF
    assert "Hello Parsemux" in result.content
    assert result.elapsed_ms >= 0
    assert result.confidence is not None
    assert result.confidence > 0


@pytest.mark.asyncio
async def test_kreuzberg_parse_pdf(sample_pdf: Path):
    from parsemux.parsers.kreuzberg import KreuzbergParser

    parser = KreuzbergParser()
    request = ParseRequest(file_path=str(sample_pdf), file_name="test.pdf")
    result = await parser.parse(request)

    assert result.parser_used == ParserBackend.KREUZBERG
    assert "Hello Parsemux" in result.content
    assert result.elapsed_ms >= 0


@pytest.mark.asyncio
async def test_kreuzberg_parse_txt(sample_txt: Path):
    from parsemux.parsers.kreuzberg import KreuzbergParser

    parser = KreuzbergParser()
    request = ParseRequest(file_path=str(sample_txt), file_name="test.txt")
    result = await parser.parse(request)

    assert result.parser_used == ParserBackend.KREUZBERG
    assert "Hello from a text file" in result.content


def test_pymupdf_available():
    from parsemux.parsers.pymupdf import PyMuPDFParser

    assert PyMuPDFParser.is_available() is True


def test_kreuzberg_available():
    from parsemux.parsers.kreuzberg import KreuzbergParser

    assert KreuzbergParser.is_available() is True


def test_docling_available():
    from parsemux.parsers.docling import DoclingParser

    assert DoclingParser.is_available() is True


@pytest.mark.asyncio
async def test_docling_parse(sample_pdf: Path):
    from parsemux.parsers.docling import DoclingParser

    parser = DoclingParser()
    request = ParseRequest(file_path=str(sample_pdf), file_name="test.pdf")
    result = await parser.parse(request)

    assert result.parser_used == ParserBackend.DOCLING
    assert len(result.content) > 0
    assert result.elapsed_ms >= 0


@pytest.mark.asyncio
async def test_parse_no_input():
    from parsemux.parsers.pymupdf import PyMuPDFParser

    parser = PyMuPDFParser()
    request = ParseRequest(file_name="test.pdf")

    with pytest.raises(ValueError, match="file_path or file_bytes"):
        await parser.parse(request)
