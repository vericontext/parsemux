"""FastAPI application factory."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from parsemux.api.routes import router


def create_app(with_ui: bool = False) -> FastAPI:
    app = FastAPI(
        title="Parsemux",
        description="Document parser orchestrator — auto-routes to the optimal OSS parser",
        version="0.1.0",
    )
    from parsemux.core.config import settings

    origins = [o.strip() for o in settings.cors_origins.split(",")]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(router, prefix="/v1")

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
