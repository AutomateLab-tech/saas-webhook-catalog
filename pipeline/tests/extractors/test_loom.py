"""Tests for the Loom extractor — no network calls."""

import pytest
from unittest.mock import AsyncMock

from catalog.extractors.loom import LoomExtractor
from catalog.schema import validate


async def _collect(extractor, fetcher):
    rows = []
    async for row in extractor.extract(fetcher):
        rows.append(row)
    return rows


@pytest.mark.asyncio
async def test_loom_instantiates():
    extractor = LoomExtractor()
    assert extractor.slug == "loom"


@pytest.mark.asyncio
async def test_loom_yields_at_least_5_rows():
    fetcher = AsyncMock()
    extractor = LoomExtractor()
    rows = await _collect(extractor, fetcher)
    assert len(rows) >= 5


@pytest.mark.asyncio
async def test_loom_rows_pass_schema_validation():
    fetcher = AsyncMock()
    extractor = LoomExtractor()
    rows = await _collect(extractor, fetcher)
    for row in rows:
        errors = validate(row)
        assert errors == [], f"Row {row['event_name']} failed: {errors}"


@pytest.mark.asyncio
async def test_loom_confidence_in_range():
    fetcher = AsyncMock()
    extractor = LoomExtractor()
    rows = await _collect(extractor, fetcher)
    for row in rows:
        assert 0.0 <= row["extraction_confidence"] <= 1.0


@pytest.mark.asyncio
async def test_loom_core_events_present():
    fetcher = AsyncMock()
    extractor = LoomExtractor()
    rows = await _collect(extractor, fetcher)
    event_names = [r["event_name"] for r in rows]
    assert "video.created" in event_names
    assert "video.deleted" in event_names
    assert "video.comment.created" in event_names
