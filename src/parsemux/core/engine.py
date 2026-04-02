"""Main parse engine — ties router + registry together with fallback chain."""

from __future__ import annotations

import logging

from parsemux.core.models import ParserBackend, ParseRequest, ParseResult
from parsemux.core.registry import get_available_parsers, get_parser
from parsemux.core.router import select_parser

logger = logging.getLogger("parsemux")

# Fallback order when primary parser fails
FALLBACK_ORDER: list[ParserBackend] = [
    ParserBackend.PYMUPDF,
    ParserBackend.KREUZBERG,
    ParserBackend.DOCLING,
    ParserBackend.MINERU,
    ParserBackend.MARKER,
]

# Confidence threshold — below this, try next parser
CONFIDENCE_THRESHOLD = 0.3


async def parse_document(request: ParseRequest) -> ParseResult:
    """Parse a document with automatic fallback on failure or low confidence."""
    primary = select_parser(request)
    available = set(get_available_parsers().keys())

    # If user explicitly chose a parser, don't fallback
    explicit = request.parser is not None
    if explicit:
        try_order = [primary]
    else:
        try_order = [primary] + [p for p in FALLBACK_ORDER if p in available and p != primary]

    errors: list[tuple[ParserBackend, str]] = []

    for backend in try_order:
        try:
            parser = get_parser(backend)
            result = await parser.parse(request)

            # If confidence is too low and more parsers available, try next
            if (
                result.confidence is not None
                and result.confidence < CONFIDENCE_THRESHOLD
                and backend != try_order[-1]
            ):
                logger.info(
                    "Parser %s returned low confidence %.2f, trying next",
                    backend.value,
                    result.confidence,
                )
                errors.append((backend, f"low confidence: {result.confidence:.2f}"))
                continue

            # Refine confidence with content analysis
            from parsemux.core.scoring import (
                count_pages_from_result,
                estimate_cost,
                refine_confidence,
            )

            result.confidence = refine_confidence(result)
            page_count = count_pages_from_result(result)
            result.cost_estimate = estimate_cost(page_count)
            result.metadata["page_count"] = page_count
            result.metadata["image_count"] = len(result.images)

            # VLM image description step
            if request.describe_images and result.images:
                from parsemux.core.config import settings

                vlm_key = (
                    request.vlm_api_key
                    or request.llm_api_key
                    or settings.vlm_api_key
                )

                if vlm_key:
                    try:
                        from parsemux.core.vlm import (
                            describe_images_batch,
                            get_vlm_provider,
                        )

                        provider = get_vlm_provider(request.vlm_provider, vlm_key)
                        result.images = await describe_images_batch(
                            result.images[: request.max_images], provider
                        )
                        # Embed descriptions as captions in content
                        result.content = _embed_image_descriptions(
                            result.content, result.images
                        )
                        # Update cost
                        described = sum(
                            1 for img in result.images if img.description
                        )
                        vlm_cost = provider.estimate_cost(described)
                        if result.cost_estimate:
                            result.cost_estimate.vlm_cost_usd = vlm_cost
                            result.cost_estimate.vlm_images_described = described
                            result.cost_estimate.parsemux_cost_usd += vlm_cost
                    except Exception as e:
                        logger.warning("VLM description failed: %s", e)

            # Add fallback info to metadata if we retried
            if errors:
                result.metadata["fallback_from"] = [
                    {"parser": e[0].value, "reason": e[1]} for e in errors
                ]

            return result

        except Exception as e:
            logger.warning("Parser %s failed: %s", backend.value, e)
            errors.append((backend, str(e)))
            continue

    # All parsers failed
    error_detail = "; ".join(f"{e[0].value}: {e[1]}" for e in errors)
    raise RuntimeError(f"All parsers failed. Errors: {error_detail}")


def _embed_image_descriptions(
    content: str, images: list
) -> str:
    """Insert VLM-generated descriptions as captions below images in markdown."""
    import re

    described = [img for img in images if img.description]
    if not described:
        return content

    # Add a caption block AFTER each base64 image tag (don't modify the tag itself)
    for img in described:
        pattern = re.compile(
            r"(!\[[^\]]*\]\(data:image/" + re.escape(img.format) + r";base64,"
            + re.escape(img.data_b64[:40]) + r"[A-Za-z0-9+/=\s]*\))"
        )
        match = pattern.search(content)
        if match:
            old_tag = match.group(0)
            # Clean description for markdown (single line, escape special chars)
            caption = img.description.replace("\n", " ").strip()
            if len(caption) > 300:
                caption = caption[:300] + "..."
            new_tag = old_tag + f"\n\n> **Image description:** {caption}"
            content = content.replace(old_tag, new_tag, 1)

    return content
