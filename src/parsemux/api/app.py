"""FastAPI application factory."""

from __future__ import annotations

import time
from collections import defaultdict
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from parsemux.api.routes import router


# Simple in-memory rate limiter (per-IP, per-minute)
_rate_store: dict[str, list[float]] = defaultdict(list)


def _check_rate_limit(ip: str, limit: int) -> bool:
    now = time.time()
    window = 60.0
    hits = _rate_store[ip]
    _rate_store[ip] = [t for t in hits if now - t < window]
    if len(_rate_store[ip]) >= limit:
        return False
    _rate_store[ip].append(now)
    return True


class MCPRoutingMiddleware:
    """Route /mcp requests to the MCP ASGI app, everything else to FastAPI."""

    def __init__(self, app: ASGIApp, mcp_app: ASGIApp):
        self.app = app
        self.mcp_app = mcp_app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http" and scope["path"] == "/mcp":
            await self.mcp_app(scope, receive, send)
        else:
            await self.app(scope, receive, send)


def create_app(with_ui: bool = False) -> FastAPI:
    from parsemux.core.config import settings

    # Setup MCP
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

    # Demo mode guard
    if settings.is_demo:
        @app.middleware("http")
        async def demo_guard(request: Request, call_next) -> Response:
            ip = request.client.host if request.client else "unknown"
            if request.url.path.startswith("/v1/parse"):
                if not _check_rate_limit(ip, settings.demo_rate_limit_per_min):
                    return JSONResponse(
                        {"error": f"Rate limit exceeded. Demo allows {settings.demo_rate_limit_per_min} requests/min."},
                        status_code=429,
                    )
                content_length = request.headers.get("content-length")
                if content_length and int(content_length) > settings.effective_max_file_size:
                    return JSONResponse(
                        {"error": f"File too large. Demo limit: {settings.demo_max_file_size_mb}MB."},
                        status_code=413,
                    )
            return await call_next(request)

    app.include_router(router, prefix="/v1")

    # Mount UI (Next.js static export)
    if with_ui:
        _mount_nextjs_ui(app)

    # Wrap with MCP routing middleware (handles /mcp before FastAPI)
    final_app: ASGIApp = app
    if mcp_asgi_app:
        final_app = MCPRoutingMiddleware(app, mcp_asgi_app)

    # Store reference for uvicorn
    app._final_app = final_app  # type: ignore[attr-defined]

    return app


def _mount_nextjs_ui(app: FastAPI) -> None:
    """Serve the Next.js static export from web/out/."""
    import os
    from pathlib import Path

    from fastapi.responses import FileResponse
    from fastapi.staticfiles import StaticFiles

    candidates = [
        Path(os.getcwd()) / "web" / "out",
        Path(__file__).resolve().parent.parent.parent.parent / "web" / "out",
    ]

    static_dir = None
    for c in candidates:
        if (c / "index.html").exists():
            static_dir = c
            break

    if static_dir is None:
        import warnings

        warnings.warn(
            "Web UI not found. Build it first:\n"
            "  cd web && npm install && npm run build\n"
            "Then run: parsemux serve --ui"
        )
        return

    # Serve _next/ static assets
    next_dir = static_dir / "_next"
    if next_dir.exists():
        app.mount("/_next", StaticFiles(directory=str(next_dir)), name="next-static")

    # Catch-all: serve static files or fall back to index.html (SPA)
    @app.get("/{path:path}")
    async def serve_ui(path: str):
        file_path = static_dir / path
        if file_path.is_file() and ".." not in path:
            return FileResponse(str(file_path))
        return FileResponse(str(static_dir / "index.html"))
