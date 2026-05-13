"""Tests for the Front extractor — no network calls."""

import pytest
from unittest.mock import AsyncMock

from catalog.extractors.front import FrontExtractor
from catalog.schema import validate


async def _collect(extractor, fetcher):
    rows = []
    async for row in extractor.extract(fetcher):
        rows.append(row)
    return rows


@pytest.mark.asyncio
async def test_front_instantiates():
    extractor = FrontExtractor()
    assert extractor.slug == "front"


@pytest.mark.asyncio
async def test_front_yields_at_least_5_rows():
    fetcher = AsyncMock()
    extractor = FrontExtractor()
    rows = await _collect(extractor, fetcher)
    assert len(rows) >= 5


@pytest.mark.asyncio
async def test_front_rows_pass_schema_validation():
    fetcher = AsyncMock()
    extractor = FrontExtractor()
    rows = await _collect(extractor, fetcher)
    for row in rows:
        errors = validate(row)
        assert errors == [], f"Row {row['event_name']} failed: {errors}"


@pytest.mark.asyncio
async def test_front_confidence_in_range():
    fetcher = AsyncMock()
    extractor = FrontExtractor()
    rows = await _collect(extractor, fetcher)
    for row in rows:
        assert 0.0 <= row["extraction_confidence"] <= 1.0


@pytest.mark.asyncio
async def test_front_core_events_present():
    fetcher = AsyncMock()
    extractor = FrontExtractor()
    rows = await _collect(extractor, fetcher)
    event_names = [r["event_name"] for r in rows]
    assert "conversation_created" in event_names
    assert "message_received" in event_names
    assert "conversation_archived" in event_names
