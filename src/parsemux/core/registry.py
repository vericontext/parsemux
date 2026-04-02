"""Parser registry — discovers and manages available parser backends."""

from __future__ import annotations

from parsemux.core.models import ParserBackend, ParserInfo
from parsemux.parsers.base import BaseParser


# All known parser classes (imported lazily)
_PARSER_CLASSES: dict[ParserBackend, type[BaseParser]] = {}
_instances: dict[ParserBackend, BaseParser] = {}


def _discover() -> None:
    """Import and register all parser adapters."""
    if _PARSER_CLASSES:
        return

    from parsemux.parsers.pymupdf import PyMuPDFParser
    from parsemux.parsers.kreuzberg import KreuzbergParser

    for cls in [PyMuPDFParser, KreuzbergParser]:
        _PARSER_CLASSES[cls.name] = cls

    # Optional parsers — don't fail if not installed
    try:
        from parsemux.parsers.docling import DoclingParser

        _PARSER_CLASSES[DoclingParser.name] = DoclingParser
    except ImportError:
        pass

    try:
        from parsemux.parsers.mineru import MinerUParser

        _PARSER_CLASSES[MinerUParser.name] = MinerUParser
    except ImportError:
        pass

    try:
        from parsemux.parsers.marker import MarkerParser

        _PARSER_CLASSES[MarkerParser.name] = MarkerParser
    except ImportError:
        pass


def get_available_parsers() -> dict[ParserBackend, type[BaseParser]]:
    """Return only parsers whose dependencies are installed."""
    _discover()
    return {name: cls for name, cls in _PARSER_CLASSES.items() if cls.is_available()}


def get_all_parsers() -> dict[ParserBackend, type[BaseParser]]:
    """Return all known parsers regardless of availability."""
    _discover()
    return dict(_PARSER_CLASSES)


def get_parser(backend: ParserBackend) -> BaseParser:
    """Get a singleton parser instance by backend name."""
    if backend not in _instances:
        _discover()
        cls = _PARSER_CLASSES.get(backend)
        if cls is None:
            raise ValueError(f"Unknown parser backend: {backend}")
        if not cls.is_available():
            raise RuntimeError(
                f"Parser '{backend.value}' is not available. "
                f"Install it with: pip install parsemux[{backend.value}]"
            )
        _instances[backend] = cls()
    return _instances[backend]


def list_parser_info() -> list[ParserInfo]:
    """Return info about all known parsers."""
    _discover()
    return [cls.info() for cls in _PARSER_CLASSES.values()]
