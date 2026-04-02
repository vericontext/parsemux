"""Tests for the REST API."""

from __future__ import annotations

from pathlib import Path

import pymupdf
import pytest
from fastapi.testclient import TestClient

from parsemux.api.app import create_app


@pytest.fixture
def client():
    app = create_app(with_ui=False)
    return TestClient(app)


@pytest.fixture
def pdf_bytes() -> bytes:
    doc = pymupdf.open()
    page = doc.new_page()
    tw = pymupdf.TextWriter(page.rect)
    tw.append((72, 72), "API test document")
    tw.write_text(page)
    data = doc.tobytes()
    doc.close()
    return data


def test_health(client: TestClient):
    resp = client.get("/v1/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["parsers_available"] >= 2


def test_list_parsers(client: TestClient):
    resp = client.get("/v1/parsers")
    assert resp.status_code == 200
    parsers = resp.json()
    assert len(parsers) >= 2
    names = {p["name"] for p in parsers}
    assert "pymupdf" in names
    assert "kreuzberg" in names


def test_parse_pdf(client: TestClient, pdf_bytes: bytes):
    resp = client.post(
        "/v1/parse",
        files={"file": ("test.pdf", pdf_bytes, "application/pdf")},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "API test document" in data["content"]
    assert data["parser_used"] == "pymupdf"
    assert data["cost_estimate"] is not None


def test_parse_with_explicit_parser(client: TestClient, pdf_bytes: bytes):
    resp = client.post(
        "/v1/parse?parser=kreuzberg",
        files={"file": ("test.pdf", pdf_bytes, "application/pdf")},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["parser_used"] == "kreuzberg"
