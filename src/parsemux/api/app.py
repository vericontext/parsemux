"""FastAPI application factory."""

from __future__ import annotations

import time
from collections import defaultdict
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from parsemux.api.routes import router


# Simple in-memory rate limiter (per-IP, per-minute)
_rate_store: dict[str, list[float]] = defaultdict(list)


def _check_rate_limit(ip: str, limit: int) -> bool:
    """Return True if request is allowed, False if rate limited."""
    now = time.time()
    window = 60.0
    hits = _rate_store[ip]
    _rate_store[ip] = [t for t in hits if now - t < window]
    if len(_rate_store[ip]) >= limit:
        return False
    _rate_store[ip].append(now)
    return True


def create_app(with_ui: bool = False) -> FastAPI:
    from parsemux.core.config import settings

    # Setup MCP only if not in demo mode (or demo allows it)
    mcp_session_manager = None
    mcp_asgi_app = None
    if not (settings.is_demo and settings.demo_disable_mcp):
        try:
            from parsemux.mcp.server import mcp_server

            mcp_asgi_app = mcp_server.streamable_http_app()
            for route in mcp_asgi_app.routes:
                handler = getattr(route, "app", None)
                if handler and hasattr(handler, "session_manager"):
                    mcp_session_manager = handler.session_manager
                    break
        except Exception:
            pass

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        if mcp_session_manager:
            async with mcp_session_manager.run():
                yield
        else:
            yield

    app = FastAPI(
        title="Parsemux",
        description="Document parser orchestrator — auto-routes to the optimal OSS parser",
        version="0.1.0",
        lifespan=lifespan,
    )

    origins = [o.strip() for o in settings.cors_origins.split(",")]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Demo mode middleware: rate limit + file size enforcement
    if settings.is_demo:
        @app.middleware("http")
        async def demo_guard(request: Request, call_next) -> Response:
            ip = request.client.host if request.client else "unknown"

            # Rate limit on parse endpoints
            if request.url.path.startswith("/v1/parse"):
                if not _check_rate_limit(ip, settings.demo_rate_limit_per_min):
                    return JSONResponse(
                        {"error": "Rate limit exceeded. Demo allows "
                         f"{settings.demo_rate_limit_per_min} requests/min."},
                        status_code=429,
                    )

                # File size check via Content-Length header
                content_length = request.headers.get("content-length")
                if content_length and int(content_length) > settings.effective_max_file_size:
                    return JSONResponse(
                        {"error": f"File too large. Demo limit: {settings.demo_max_file_size_mb}MB."},
                        status_code=413,
                    )

            return await call_next(request)

    app.include_router(router, prefix="/v1")

    # Mount MCP Streamable HTTP (local mode only, or demo with mcp enabled)
    if mcp_asgi_app:
        app.mount("/", mcp_asgi_app)

    if with_ui:
        _mount_gradio(app)

    return app


def _mount_gradio(app: FastAPI) -> None:
    try:
        import gradio as gr
        from parsemux.ui.app import create_ui

        ui = create_ui()
        app = gr.mount_gradio_app(app, ui, path="/ui")
    except ImportError:
        import warnings
        warnings.warn("Gradio not installed. UI will not be available. pip install parsemux[ui]")
