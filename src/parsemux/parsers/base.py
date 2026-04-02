"""Base parser interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import ClassVar

from parsemux.core.models import ParseRequest, ParseResult, ParserBackend, ParserInfo


class BaseParser(ABC):
    """Abstract base for all parser backends."""

    name: ClassVar[ParserBackend]
    supported_mimes: ClassVar[set[str]]
    description: ClassVar[str]
    requires_gpu: ClassVar[bool] = False
    requires_llm_key: ClassVar[bool] = False

    @abstractmethod
    async def parse(self, request: ParseRequest) -> ParseResult:
        """Parse a document and return structured result."""

    @classmethod
    def is_available(cls) -> bool:
        try:
            cls._check_deps()
            return True
        except (ImportError, Exception):
            return False

    @classmethod
    @abstractmethod
    def _check_deps(cls) -> None:
        """Raise ImportError if dependencies are not installed."""

    @classmethod
    def info(cls) -> ParserInfo:
        return ParserInfo(
            name=cls.name,
            available=cls.is_available(),
            supported_mimes=sorted(cls.supported_mimes),
            description=cls.description,
            requires_gpu=cls.requires_gpu,
            requires_llm_key=cls.requires_llm_key,
        )
