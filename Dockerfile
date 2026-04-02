FROM python:3.12-slim AS base

WORKDIR /app

# System deps for OCR/document processing
RUN apt-get update && apt-get install -y --no-install-recommends \
    libmagic1 \
    tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

# Install uv for fast package management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

COPY pyproject.toml README.md ./
COPY src/ src/

# API-only install for production (no Gradio UI — frontend is on Vercel)
ARG PARSEMUX_EXTRAS="pymupdf,kreuzberg,docling,api,cli,vlm,mcp"
RUN uv pip install --system ".[${PARSEMUX_EXTRAS}]"

EXPOSE 8000

CMD ["parsemux", "serve", "--host", "0.0.0.0", "--port", "8000"]
