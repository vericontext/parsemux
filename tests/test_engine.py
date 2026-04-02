"""Tests for the parse engine (integration)."""

from __future__ import annotations

from pathlib import Path

import pytest

from parsemux.core.engine import parse_document
from parsemux.core.models import ParserBackend, ParseRequest


@pytest.mark.asyncio
async def test_parse_document_auto(sample_pdf: Path):
    request = ParseRequest(file_path=str(sample_pdf), file_name="test.pdf")
    result = await parse_document(request)

    assert result.parser_used == ParserBackend.PYMUPDF
    assert "Hello Parsemux" in result.content
    assert result.confidence is not None
    assert result.confidence > 0
    assert result.cost_estimate is not None
    assert result.cost_estimate.parsemux_cost_usd >= 0
    assert result.cost_estimate.page_count >= 1


@pytest.mark.asyncio
async def test_parse_document_kreuzberg(sample_pdf: Path):
    request = ParseRequest(
        file_path=str(sample_pdf),
        file_name="test.pdf",
        parser=ParserBackend.KREUZBERG,
    )
    result = await parse_document(request)

    assert result.parser_used == ParserBackend.KREUZBERG
    assert "Hello Parsemux" in result.content


@pytest.mark.asyncio
async def test_parse_txt_auto_routes_kreuzberg(sample_txt: Path):
    request = ParseRequest(file_path=str(sample_txt), file_name="test.txt")
    result = await parse_document(request)

    assert result.parser_used == ParserBackend.KREUZBERG
    assert "Hello from a text file" in result.content


@pytest.mark.asyncio
async def test_cost_estimate_present(sample_pdf: Path):
    request = ParseRequest(file_path=str(sample_pdf), file_name="test.pdf")
    result = await parse_document(request)

    assert result.cost_estimate is not None
    assert "AWS Textract" in result.cost_estimate.cloud_costs
    assert result.cost_estimate.savings_vs_cheapest_cloud >= 0
