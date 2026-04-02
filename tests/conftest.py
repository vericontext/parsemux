"""Shared test fixtures."""

from __future__ import annotations

from pathlib import Path

import pymupdf
import pytest


@pytest.fixture
def sample_pdf(tmp_path: Path) -> Path:
    """Create a simple test PDF with text."""
    pdf_path = tmp_path / "test.pdf"
    doc = pymupdf.open()
    page = doc.new_page()
    tw = pymupdf.TextWriter(page.rect)
    tw.append((72, 72), "Hello Parsemux!")
    tw.append((72, 100), "This is a test document with multiple lines.")
    tw.append((72, 128), "It should be parsed correctly by all backends.")
    tw.write_text(page)
    doc.save(str(pdf_path))
    doc.close()
    return pdf_path


@pytest.fixture
def sample_txt(tmp_path: Path) -> Path:
    """Create a simple test text file."""
    txt_path = tmp_path / "test.txt"
    txt_path.write_text("Hello from a text file.\nSecond line here.\n")
    return txt_path


@pytest.fixture
def empty_pdf(tmp_path: Path) -> Path:
    """Create a PDF with no text (simulates scanned)."""
    pdf_path = tmp_path / "empty.pdf"
    doc = pymupdf.open()
    doc.new_page()
    doc.save(str(pdf_path))
    doc.close()
    return pdf_path


@pytest.fixture
def pdf_with_image(tmp_path: Path) -> Path:
    """Create a PDF with text and an embedded image."""
    pdf_path = tmp_path / "with_image.pdf"
    doc = pymupdf.open()
    page = doc.new_page()
    tw = pymupdf.TextWriter(page.rect)
    tw.append((72, 72), "Document with image")
    tw.write_text(page)
    # Insert a simple colored rectangle as a pixmap image
    pix = pymupdf.Pixmap(pymupdf.csRGB, pymupdf.IRect(0, 0, 100, 80), 1)
    pix.set_rect(pix.irect, (255, 180, 0, 255))  # amber fill with alpha
    page.insert_image(pymupdf.Rect(72, 150, 250, 300), pixmap=pix)
    doc.save(str(pdf_path))
    doc.close()
    return pdf_path
