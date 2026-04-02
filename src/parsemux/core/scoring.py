"""Confidence scoring and cost estimation."""

from __future__ import annotations

import re

from parsemux.core.models import CostEstimate, ParseResult

# Cloud pricing per 1,000 pages (USD) — OCR/text extraction tier
# Sources (verified 2026-04):
#   AWS Textract: aws.amazon.com/textract/pricing ($1.50/1K for Read)
#   Google Doc AI: cloud.google.com/document-ai/pricing ($1.50/1K Enterprise OCR)
#   Azure Doc Intel: azure.microsoft.com/pricing/details/document-intelligence ($1.50/1K Read)
#   LlamaParse: llamaindex.ai/pricing ($1.25/1K credits, 1 credit/page basic mode)
#   Reducto: reducto.ai/pricing ($0.015/page = $15/1K)
#   Mistral OCR: mistral.ai/pricing ($2/1K standard, $1/1K batch)
CLOUD_PRICING = {
    "AWS Textract": 1.50,
    "Google Document AI": 1.50,
    "Azure Doc Intelligence": 1.50,
    "Reducto": 15.00,
    "LlamaParse": 1.25,
    "Mistral OCR": 2.00,
}

# Self-hosted cost estimate per 1,000 pages (electricity + amortized hardware)
SELF_HOSTED_COST_PER_1K = 0.05  # ~$50 per 1M pages


def refine_confidence(result: ParseResult) -> float:
    """Compute a refined confidence score based on content analysis."""
    content = result.content
    if not content or not content.strip():
        return 0.0

    scores: list[float] = []

    # 1. Text density: chars per estimated page (assume ~2000 chars/page for good extraction)
    char_count = len(content.strip())
    text_density = min(1.0, char_count / 500)  # 500 chars minimum for decent result
    scores.append(text_density)

    # 2. Structure signals: presence of markdown headings, lists, tables
    has_headings = bool(re.search(r"^#{1,6}\s", content, re.MULTILINE))
    has_lists = bool(re.search(r"^[\-\*]\s", content, re.MULTILINE))
    has_tables = bool(re.search(r"\|.*\|.*\|", content))
    structure_score = 0.5 + (0.2 if has_headings else 0) + (0.15 if has_lists else 0) + (0.15 if has_tables else 0)
    scores.append(structure_score)

    # 3. Garbage detection: high ratio of non-printable or garbled characters
    printable = sum(1 for c in content if c.isprintable() or c in "\n\t\r")
    clean_ratio = printable / max(len(content), 1)
    scores.append(clean_ratio)

    # 4. Word density: reasonable words per line
    lines = [l for l in content.split("\n") if l.strip()]
    if lines:
        avg_words = sum(len(l.split()) for l in lines) / len(lines)
        word_score = min(1.0, avg_words / 5)  # expect at least 5 words/line average
        scores.append(word_score)

    return round(sum(scores) / len(scores), 2)


def estimate_cost(page_count: int) -> CostEstimate:
    """Estimate cost savings vs cloud services."""
    if page_count <= 0:
        return CostEstimate()

    parsemux_cost = (page_count / 1000) * SELF_HOSTED_COST_PER_1K
    cloud_costs = {name: (page_count / 1000) * price for name, price in CLOUD_PRICING.items()}
    cheapest_cloud = min(cloud_costs.values())

    return CostEstimate(
        parsemux_cost_usd=round(parsemux_cost, 4),
        cloud_costs={k: round(v, 4) for k, v in cloud_costs.items()},
        savings_vs_cheapest_cloud=round(cheapest_cloud - parsemux_cost, 4),
        page_count=page_count,
    )


def count_pages_from_result(result: ParseResult) -> int:
    """Estimate page count from metadata or content."""
    if "page_count" in result.metadata:
        return result.metadata["page_count"]
    # Rough estimate: ~2000 chars per page
    return max(1, len(result.content) // 2000)
