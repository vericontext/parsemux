"""Gradio Web UI for parsemux — no login required."""

from __future__ import annotations

import asyncio
import json
import tempfile
from pathlib import Path

import gradio as gr

from parsemux.core.engine import parse_document
from parsemux.core.models import ParserBackend, ParseRequest, ParseResult
from parsemux.core.registry import list_parser_info, get_available_parsers, get_parser


def _parse_file(
    file_path: str | None,
    parser_choice: str,
    output_format: str,
    use_llm: bool,
    llm_key: str,
) -> tuple[str, str, str, str]:
    """Parse a file and return (rendered, raw, metadata, cost)."""
    if not file_path:
        return "", "", "Upload a file to begin.", ""

    backend = None if parser_choice == "Auto" else ParserBackend(parser_choice.lower())
    request = ParseRequest(
        file_path=file_path,
        file_name=Path(file_path).name,
        parser=backend,
        output_format=output_format.lower(),  # type: ignore[arg-type]
        use_llm=use_llm,
        llm_api_key=llm_key or None,
    )

    result = asyncio.run(parse_document(request))

    # Rendered content
    if output_format == "Markdown":
        rendered = result.content
    else:
        rendered = f"```\n{result.content}\n```"

    # Raw content
    raw = result.content

    # Metadata panel
    conf_bar = _confidence_bar(result.confidence or 0)
    meta = (
        f"### Parse Info\n\n"
        f"| | |\n|---|---|\n"
        f"| **Parser** | `{result.parser_used.value}` |\n"
        f"| **Confidence** | {conf_bar} {result.confidence:.0%} |\n"
        f"| **Time** | {result.elapsed_ms:,}ms |\n"
        f"| **Pages** | {result.metadata.get('page_count', '?')} |\n"
        f"| **File** | {Path(file_path).name} |\n"
    )
    if "fallback_from" in result.metadata:
        fallbacks = result.metadata["fallback_from"]
        meta += f"\n**Fallback chain:** {' → '.join(f['parser'] for f in fallbacks)} → {result.parser_used.value}\n"

    # Cost panel
    cost = _format_cost(result)

    return rendered, raw, meta, cost


def _confidence_bar(conf: float) -> str:
    filled = int(conf * 10)
    return "█" * filled + "░" * (10 - filled)


def _format_cost(result: ParseResult) -> str:
    if not result.cost_estimate:
        return ""
    ce = result.cost_estimate
    lines = [
        f"### Cost Comparison ({ce.page_count} pages)\n",
        f"| Service | Cost | vs Parsemux |",
        f"|---------|------|-------------|",
        f"| **Parsemux (self-hosted)** | **${ce.parsemux_cost_usd:.4f}** | — |",
    ]
    for name, cost in sorted(ce.cloud_costs.items(), key=lambda x: x[1]):
        ratio = cost / ce.parsemux_cost_usd if ce.parsemux_cost_usd > 0 else float("inf")
        lines.append(f"| {name} | ${cost:.4f} | {ratio:.0f}x more |")

    if ce.savings_vs_cheapest_cloud > 0:
        lines.append(
            f"\nSaving **${ce.savings_vs_cheapest_cloud:.4f}** vs cheapest cloud "
            f"({ce.savings_vs_cheapest_cloud / max(min(ce.cloud_costs.values()), 0.0001) * 100:.0f}% cheaper)"
        )
    return "\n".join(lines)


def _compare_file(file_path: str | None) -> str:
    """Parse with all available parsers and show comparison."""
    if not file_path:
        return "Upload a file first."

    available = get_available_parsers()
    sections = []

    for backend_name in available:
        request = ParseRequest(
            file_path=file_path,
            file_name=Path(file_path).name,
            parser=backend_name,
        )
        try:
            result = asyncio.run(parse_document(request))
            conf_bar = _confidence_bar(result.confidence or 0)
            sections.append(
                f"## `{backend_name.value}` — {result.elapsed_ms}ms — {conf_bar} {(result.confidence or 0):.0%}\n\n"
                f"{result.content[:3000]}"
                + ("\n\n*... (truncated)*" if len(result.content) > 3000 else "")
            )
        except Exception as e:
            sections.append(f"## `{backend_name.value}`\n\nError: {e}")

    return "\n\n---\n\n".join(sections) if sections else "No parsers available."


def _download_result(raw_content: str, file_path: str | None, output_format: str) -> str | None:
    """Save result to a temp file for download."""
    if not raw_content:
        return None
    ext = {"Markdown": ".md", "Text": ".txt", "JSON": ".json"}.get(output_format, ".txt")
    name = Path(file_path).stem if file_path else "output"
    out = Path(tempfile.gettempdir()) / f"{name}_parsed{ext}"
    out.write_text(raw_content, encoding="utf-8")
    return str(out)


def create_ui() -> gr.Blocks:
    """Create the Gradio UI."""
    available = [p.name.value for p in list_parser_info() if p.available]
    parser_choices = ["Auto"] + [p.capitalize() for p in available]

    # Parser info for display
    all_parsers = list_parser_info()
    parser_table = "| Parser | Status | Best For |\n|--------|--------|----------|\n"
    for p in all_parsers:
        status = "Available" if p.available else "Not installed"
        parser_table += f"| `{p.name.value}` | {status} | {p.description[:60]} |\n"

    with gr.Blocks(title="Parsemux") as demo:
        gr.Markdown(
            "# Parsemux\n"
            "**Document parser orchestrator** — upload any document and get structured content. "
            "Auto-routes to the optimal OSS parser.\n"
        )

        with gr.Row():
            # Left sidebar: controls
            with gr.Column(scale=1, min_width=300):
                file_input = gr.File(
                    label="Document",
                    type="filepath",
                    file_types=[
                        ".pdf", ".docx", ".xlsx", ".pptx", ".doc",
                        ".html", ".txt", ".csv", ".md", ".rtf", ".epub",
                        ".png", ".jpg", ".jpeg", ".tiff", ".tif", ".webp", ".bmp",
                    ],
                )

                parser_dropdown = gr.Dropdown(
                    choices=parser_choices,
                    value="Auto",
                    label="Parser",
                    info="Auto selects the best parser for your document",
                )

                format_radio = gr.Radio(
                    choices=["Markdown", "Text", "JSON"],
                    value="Markdown",
                    label="Output Format",
                )

                with gr.Accordion("LLM Settings (BYOK)", open=False):
                    gr.Markdown(
                        "*Provide your own API key for LLM-enhanced parsing. "
                        "Keys are never stored on the server.*"
                    )
                    use_llm_checkbox = gr.Checkbox(
                        label="Enable LLM-enhanced parsing",
                        value=False,
                    )
                    llm_key_input = gr.Textbox(
                        label="API Key",
                        placeholder="sk-...",
                        type="password",
                    )

                parse_btn = gr.Button("Parse Document", variant="primary", size="lg")
                compare_btn = gr.Button("Compare All Parsers", variant="secondary")

                with gr.Accordion("Available Parsers", open=False):
                    gr.Markdown(parser_table)

            # Right: results
            with gr.Column(scale=2):
                with gr.Tabs():
                    with gr.TabItem("Result"):
                        output_content = gr.Markdown(label="Parsed Content")
                    with gr.TabItem("Raw"):
                        output_raw = gr.Textbox(label="Raw Output", lines=25)
                    with gr.TabItem("Compare"):
                        compare_output = gr.Markdown(label="Parser Comparison")

                with gr.Row():
                    with gr.Column():
                        output_meta = gr.Markdown(label="Info")
                    with gr.Column():
                        output_cost = gr.Markdown(label="Cost")

                download_btn = gr.Button("Download Result", variant="secondary", size="sm")
                download_file = gr.File(label="Download", visible=False)

        # Parse action
        parse_btn.click(
            fn=_parse_file,
            inputs=[file_input, parser_dropdown, format_radio, use_llm_checkbox, llm_key_input],
            outputs=[output_content, output_raw, output_meta, output_cost],
        )

        # Compare action
        compare_btn.click(
            fn=_compare_file,
            inputs=[file_input],
            outputs=[compare_output],
        )

        # Download action
        download_btn.click(
            fn=_download_result,
            inputs=[output_raw, file_input, format_radio],
            outputs=[download_file],
        ).then(
            fn=lambda: gr.update(visible=True),
            outputs=[download_file],
        )

    return demo


def launch_ui(host: str = "0.0.0.0", port: int = 7860) -> None:
    """Launch the Gradio UI standalone."""
    demo = create_ui()
    demo.launch(server_name=host, server_port=port)


if __name__ == "__main__":
    launch_ui()
