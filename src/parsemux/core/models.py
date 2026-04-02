"""Core data models for parsemux."""

from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field


class ParserBackend(str, Enum):
    PYMUPDF = "pymupdf"
    KREUZBERG = "kreuzberg"
    DOCLING = "docling"
    MINERU = "mineru"
    MARKER = "marker"


class VLMProvider(str, Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    OLLAMA = "ollama"


class ExtractedImage(BaseModel):
    """An image extracted from a document."""

    data_b64: str
    format: str = "png"
    width: int | None = None
    height: int | None = None
    page_number: int | None = None
    description: str | None = None
    description_model: str | None = None


class ParseRequest(BaseModel):
    """Request to parse a document."""

    file_path: str | None = None
    file_bytes: bytes | None = None
    file_name: str = ""
    parser: ParserBackend | None = None
    output_format: Literal["markdown", "json", "text"] = "markdown"
    pages: list[int] | None = None
    use_llm: bool = False
    llm_api_key: str | None = Field(default=None, exclude=True)
    # Image extraction
    extract_images: bool = False
    describe_images: bool = False
    vlm_provider: VLMProvider | None = None
    vlm_api_key: str | None = Field(default=None, exclude=True)
    max_images: int = 50


class CostEstimate(BaseModel):
    """Cost comparison: parsemux vs cloud services."""

    parsemux_cost_usd: float = 0.0
    cloud_costs: dict[str, float] = Field(default_factory=dict)
    savings_vs_cheapest_cloud: float = 0.0
    page_count: int = 0
    vlm_cost_usd: float = 0.0
    vlm_images_described: int = 0


class ParseResult(BaseModel):
    """Result from parsing a document."""

    content: str
    parser_used: ParserBackend
    metadata: dict[str, Any] = Field(default_factory=dict)
    confidence: float | None = None
    elapsed_ms: int = 0
    cost_estimate: CostEstimate | None = None
    images: list[ExtractedImage] = Field(default_factory=list)


class ParserInfo(BaseModel):
    """Information about an available parser backend."""

    name: ParserBackend
    available: bool
    supported_mimes: list[str]
    description: str
    requires_gpu: bool = False
    requires_llm_key: bool = False
