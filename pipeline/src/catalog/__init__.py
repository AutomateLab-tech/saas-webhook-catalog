"""
SaaS webhook event catalog — extraction pipeline.

Public API:
  catalog.schema    — validate(row) -> list[ValidationError]
  catalog.fetcher   — Fetcher (async httpx with per-domain throttle)
  catalog.extractor — ExtractorBase, register(), get_extractor()
  catalog.output    — OutputWriter (parquet + JSONL)
"""

from .schema import validate
from .extractor import ExtractorBase, register, get_extractor, list_slugs
from .fetcher import Fetcher
from .output import OutputWriter

__all__ = [
    "validate",
    "ExtractorBase",
    "register",
    "get_extractor",
    "list_slugs",
    "Fetcher",
    "OutputWriter",
]
