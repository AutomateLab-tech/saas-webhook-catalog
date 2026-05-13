"""
extractor.py — ExtractorBase abstract class and extractor registry.

Each extractor module defines a subclass of ExtractorBase and calls
``register(MyExtractor)`` at import time. The registry maps slug -> class.

The CLI and pipeline runner import ``catalog.extractors`` (the subpackage)
which in turn imports every extractor module, triggering registration.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import AsyncIterator, TYPE_CHECKING

if TYPE_CHECKING:
    from .fetcher import Fetcher

_REGISTRY: dict[str, type["ExtractorBase"]] = {}


class ExtractorBase(ABC):
    """
    Base class for all per-vendor extractors.

    Subclass, set ``slug`` and ``docs_urls``, implement ``extract()``,
    then call ``register(MyExtractor)`` at module level.
    """

    slug: str
    docs_urls: list[str]

    @abstractmethod
    async def extract(self, fetcher: "Fetcher") -> AsyncIterator[dict]:
        """
        Yield rows matching schema.json.

        Validation happens in the pipeline runner, not here — yield raw
        dicts and let the runner collect validation errors.
        """


def register(extractor_cls: type[ExtractorBase]) -> None:
    """Register an extractor class by its slug."""
    slug = extractor_cls.slug
    if not slug:
        raise ValueError(f"{extractor_cls.__name__} has no slug")
    if slug in _REGISTRY:
        raise ValueError(f"Extractor slug '{slug}' is already registered")
    _REGISTRY[slug] = extractor_cls


def get_extractor(slug: str) -> ExtractorBase:
    """Return an instance of the extractor for *slug*, or raise KeyError."""
    cls = _REGISTRY[slug]
    return cls()


def list_slugs() -> list[str]:
    """Return all registered extractor slugs in sorted order."""
    return sorted(_REGISTRY.keys())
