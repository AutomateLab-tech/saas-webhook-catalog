"""Tests for the Zoom extractor — no network calls."""

import pytest
from unittest.mock import AsyncMock

from catalog.extractors.zoom import ZoomExtractor
from catalog.schema import validate


async def _collect(extractor, fetcher):
    rows = []
    async for row in extractor.extract(fetcher):
        rows.append(row)
    return rows


@pytest.mark.asyncio
async def test_zoom_instantiates():
    extractor = ZoomExtractor()
    assert extractor.slug == "zoom"


@pytest.mark.asyncio
async def test_zoom_yields_at_least_5_rows():
    fetcher = AsyncMock()
    extractor = ZoomExtractor()
    rows = await _collect(extractor, fetcher)
    assert len(rows) >= 5


@pytest.mark.asyncio
async def test_zoom_rows_pass_schema_validation():
    fetcher = AsyncMock()
    extractor = ZoomExtractor()
    rows = await _collect(extractor, fetcher)
    for row in rows:
        errors = validate(row)
        assert errors == [], f"Row {row['event_name']} failed: {errors}"


@pytest.mark.asyncio
async def test_zoom_confidence_in_range():
    fetcher = AsyncMock()
    extractor = ZoomExtractor()
    rows = await _collect(extractor, fetcher)
    for row in rows:
        assert 0.0 <= row["extraction_confidence"] <= 1.0


@pytest.mark.asyncio
async def test_zoom_core_events_present():
    fetcher = AsyncMock()
    extractor = ZoomExtractor()
    rows = await _collect(extractor, fetcher)
    event_names = [r["event_name"] for r in rows]
    assert "meeting.started" in event_names
    assert "meeting.ended" in event_names
    assert "recording.completed" in event_names
