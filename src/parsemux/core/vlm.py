"""VLM (Vision Language Model) provider abstraction for image description."""

from __future__ import annotations

import asyncio
import logging
from abc import ABC, abstractmethod
from functools import lru_cache
from pathlib import Path
from typing import Any

import httpx

from parsemux.core.models import ExtractedImage, VLMProvider

logger = logging.getLogger("parsemux.vlm")

DEFAULT_PROMPT = (
    "Describe this image concisely. Include any text, diagrams, charts, "
    "tables, or data visible. Be specific about what the image shows."
)

_YAML_PATH = Path(__file__).parent / "vlm_models.yaml"


@lru_cache(maxsize=1)
def _load_registry() -> dict[str, Any]:
    """Load provider/model registry from YAML (cached)."""
    import yaml  # noqa: delay import

    with open(_YAML_PATH) as f:
        return yaml.safe_load(f)["providers"]


def get_provider_config(name: str) -> dict[str, Any]:
    return _load_registry()[name]


def get_default_model(provider_name: str) -> str:
    return get_provider_config(provider_name)["default_model"]


def get_cost_per_image(provider_name: str) -> float:
    return get_provider_config(provider_name).get("cost_per_image_usd", 0.0)


def get_key_prefixes(provider_name: str) -> list[str]:
    return get_provider_config(provider_name).get("key_prefixes", [])


def list_models(provider_name: str) -> dict[str, Any]:
    return get_provider_config(provider_name).get("models", {})


class BaseVLMProvider(ABC):
    """Abstract base for VLM providers."""

    def __init__(self, api_key: str, model: str | None = None):
        self.api_key = api_key
        self.model = model or get_default_model(self.provider_name)

    @property
    @abstractmethod
    def provider_name(self) -> str: ...

    @abstractmethod
    async def describe_image(self, image_b64: str, format: str) -> str:
        """Generate a text description for an image."""

    def estimate_cost(self, image_count: int) -> float:
        return image_count * get_cost_per_image(self.provider_name)


class OpenAIVLMProvider(BaseVLMProvider):
    provider_name = "openai"

    async def describe_image(self, image_b64: str, format: str) -> str:
        media_type = f"image/{format}"
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={
                    "model": self.model,
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": DEFAULT_PROMPT},
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:{media_type};base64,{image_b64}",
                                        "detail": "low",
                                    },
                                },
                            ],
                        }
                    ],
                    "max_tokens": 300,
                },
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]


class AnthropicVLMProvider(BaseVLMProvider):
    provider_name = "anthropic"

    async def describe_image(self, image_b64: str, format: str) -> str:
        media_type = f"image/{format}"
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": self.api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": self.model,
                    "max_tokens": 300,
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "image",
                                    "source": {
                                        "type": "base64",
                                        "media_type": media_type,
                                        "data": image_b64,
                                    },
                                },
                                {"type": "text", "text": DEFAULT_PROMPT},
                            ],
                        }
                    ],
                },
            )
            resp.raise_for_status()
            return resp.json()["content"][0]["text"]


class GoogleVLMProvider(BaseVLMProvider):
    provider_name = "google"

    async def describe_image(self, image_b64: str, format: str) -> str:
        mime = f"image/{format}"
        cfg = get_provider_config("google")
        base = cfg["api_base"]
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{base}/{self.model}:generateContent",
                params={"key": self.api_key},
                json={
                    "contents": [
                        {
                            "parts": [
                                {"text": DEFAULT_PROMPT},
                                {
                                    "inline_data": {
                                        "mime_type": mime,
                                        "data": image_b64,
                                    }
                                },
                            ]
                        }
                    ]
                },
            )
            resp.raise_for_status()
            return resp.json()["candidates"][0]["content"]["parts"][0]["text"]


class OllamaVLMProvider(BaseVLMProvider):
    provider_name = "ollama"

    def __init__(self, api_key: str = "", model: str | None = None):
        super().__init__(api_key, model)
        cfg = get_provider_config("ollama")
        self.base_url = cfg["api_base"].rsplit("/api/generate", 1)[0]

    async def describe_image(self, image_b64: str, format: str) -> str:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": DEFAULT_PROMPT,
                    "images": [image_b64],
                    "stream": False,
                },
            )
            resp.raise_for_status()
            return resp.json()["response"]


def _detect_provider(api_key: str) -> VLMProvider:
    """Auto-detect provider from API key prefix using YAML config."""
    registry = _load_registry()
    for name, cfg in registry.items():
        for prefix in cfg.get("key_prefixes", []):
            if api_key.startswith(prefix):
                # Anthropic's sk-ant- must match before OpenAI's sk-
                if name == "anthropic" and api_key.startswith("sk-ant-"):
                    return VLMProvider.ANTHROPIC
                if name == "openai" and api_key.startswith("sk-") and not api_key.startswith("sk-ant-"):
                    return VLMProvider.OPENAI
                if name not in ("openai", "anthropic"):
                    return VLMProvider(name)
    return VLMProvider.OLLAMA


def get_vlm_provider(
    provider: VLMProvider | None, api_key: str, model: str | None = None
) -> BaseVLMProvider:
    """Create a VLM provider instance. Auto-detects from key prefix if provider is None."""
    if provider is None:
        provider = _detect_provider(api_key)

    providers: dict[VLMProvider, type[BaseVLMProvider]] = {
        VLMProvider.OPENAI: OpenAIVLMProvider,
        VLMProvider.ANTHROPIC: AnthropicVLMProvider,
        VLMProvider.GOOGLE: GoogleVLMProvider,
        VLMProvider.OLLAMA: OllamaVLMProvider,
    }
    return providers[provider](api_key=api_key, model=model)


async def describe_images_batch(
    images: list[ExtractedImage],
    provider: BaseVLMProvider,
    max_concurrent: int = 5,
) -> list[ExtractedImage]:
    """Describe multiple images in parallel with concurrency limit."""
    semaphore = asyncio.Semaphore(max_concurrent)

    async def _describe_one(img: ExtractedImage) -> ExtractedImage:
        async with semaphore:
            try:
                desc = await provider.describe_image(img.data_b64, img.format)
                img.description = desc
                img.description_model = provider.model
            except Exception as e:
                logger.warning("VLM describe failed for image: %s", e)
                img.description = None
            return img

    return await asyncio.gather(*[_describe_one(img) for img in images])
