"""MCP server for parsemux — exposes document parsing as MCP tools."""

from __future__ import annotations

import json

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from parsemux.core.engine import parse_document
from parsemux.core.models import ParserBackend, ParseRequest, VLMProvider
from parsemux.core.registry import list_parser_info
from parsemux.core.router import select_parser, _detect_mime

server = Server("parsemux")


@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="parse_document",
            description=(
                "Parse a document file and extract structured content. "
                "Auto-routes to the optimal parser unless one is specified."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Absolute path to the document file",
                    },
                    "parser": {
                        "type": "string",
                        "enum": [b.value for b in ParserBackend],
                        "description": "Parser backend (omit for auto-routing)",
                    },
                    "output_format": {
                        "type": "string",
                        "enum": ["markdown", "json", "text"],
                        "default": "markdown",
                        "description": "Output format",
                    },
                    "use_llm": {
                        "type": "boolean",
                        "default": False,
                        "description": "Enable LLM-enhanced parsing (requires llm_api_key)",
                    },
                    "llm_api_key": {
                        "type": "string",
                        "description": "LLM API key for BYOK features",
                    },
                    "extract_images": {
                        "type": "boolean",
                        "default": False,
                        "description": "Extract images from document",
                    },
                    "describe_images": {
                        "type": "boolean",
                        "default": False,
                        "description": "Generate VLM descriptions for extracted images",
                    },
                    "vlm_provider": {
                        "type": "string",
                        "enum": ["openai", "anthropic", "google", "ollama"],
                        "description": "VLM provider for image description",
                    },
                    "vlm_api_key": {
                        "type": "string",
                        "description": "VLM API key (falls back to llm_api_key)",
                    },
                },
                "required": ["file_path"],
            },
        ),
        Tool(
            name="list_parsers",
            description="List all available parser backends and their capabilities.",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        Tool(
            name="detect_doc_type",
            description="Detect document type and recommend the best parser.",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Absolute path to the document file",
                    },
                },
                "required": ["file_path"],
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    if name == "parse_document":
        backend = ParserBackend(arguments["parser"]) if "parser" in arguments else None
        vlm = VLMProvider(arguments["vlm_provider"]) if "vlm_provider" in arguments else None
        request = ParseRequest(
            file_path=arguments["file_path"],
            file_name=arguments["file_path"].split("/")[-1],
            parser=backend,
            output_format=arguments.get("output_format", "markdown"),
            use_llm=arguments.get("use_llm", False),
            llm_api_key=arguments.get("llm_api_key"),
            extract_images=arguments.get("extract_images", False),
            describe_images=arguments.get("describe_images", False),
            vlm_provider=vlm,
            vlm_api_key=arguments.get("vlm_api_key"),
        )
        result = await parse_document(request)
        return [TextContent(
            type="text",
            text=json.dumps(result.model_dump(), indent=2, ensure_ascii=False),
        )]

    elif name == "list_parsers":
        infos = list_parser_info()
        data = [i.model_dump() for i in infos]
        return [TextContent(type="text", text=json.dumps(data, indent=2, ensure_ascii=False))]

    elif name == "detect_doc_type":
        request = ParseRequest(
            file_path=arguments["file_path"],
            file_name=arguments["file_path"].split("/")[-1],
        )
        mime = _detect_mime(request)
        recommended = select_parser(request)
        return [TextContent(
            type="text",
            text=json.dumps({
                "file": arguments["file_path"],
                "mime_type": mime,
                "recommended_parser": recommended.value,
            }, indent=2),
        )]

    else:
        return [TextContent(type="text", text=f"Unknown tool: {name}")]


async def run_mcp_server() -> None:
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())
