"""Tests for the document router."""

from __future__ import annotations

from pathlib import Path

import pytest

from parsemux.core.models import ParserBackend, ParseRequest
from parsemux.core.router import _detect_mime, _is_digital_pdf, select_parser, validate_supported_file_type


def test_auto_route_digital_pdf(sample_pdf: Path):
    request = ParseRequest(file_path=str(sample_pdf), file_name="test.pdf")
    backend = select_parser(request)
    assert backend == ParserBackend.PYMUPDF


def test_auto_route_txt():
    request = ParseRequest(file_path="/tmp/test.txt", file_name="test.txt")
    backend = select_parser(request)
    assert backend == ParserBackend.KREUZBERG


def test_auto_route_docx():
    request = ParseRequest(file_path="/tmp/test.docx", file_name="test.docx")
    backend = select_parser(request)
    assert backend == ParserBackend.KREUZBERG


def test_explicit_parser():
    request = ParseRequest(
        file_path="/tmp/test.pdf",
        file_name="test.pdf",
        parser=ParserBackend.KREUZBERG,
    )
    backend = select_parser(request)
    assert backend == ParserBackend.KREUZBERG


def test_detect_mime():
    assert _detect_mime(ParseRequest(file_name="test.pdf")) == "application/pdf"
    assert _detect_mime(ParseRequest(file_name="test.docx")).startswith("application/vnd.openxml")
    assert _detect_mime(ParseRequest(file_name="test.png")) == "image/png"
    assert _detect_mime(ParseRequest(file_name="test.unknown")) == "application/octet-stream"


def test_is_digital_pdf(sample_pdf: Path):
    request = ParseRequest(file_path=str(sample_pdf), file_name="test.pdf")
    assert _is_digital_pdf(request) is True


def test_empty_pdf_not_digital(empty_pdf: Path):
    request = ParseRequest(file_path=str(empty_pdf), file_name="empty.pdf")
    assert _is_digital_pdf(request) is False


def test_unavailable_parser_raises():
    request = ParseRequest(
        file_path="/tmp/test.pdf",
        file_name="test.pdf",
        parser=ParserBackend.MINERU,  # MinerU is not installed
    )
    with pytest.raises(RuntimeError, match="not available"):
        select_parser(request)


def test_validate_supported_file_type_rejects_unknown_extension():
    request = ParseRequest(file_path="/tmp/archive.zip", file_name="archive.zip")

    with pytest.raises(ValueError, match=r"Unsupported file type '.zip'"):
        validate_supported_file_type(request)
