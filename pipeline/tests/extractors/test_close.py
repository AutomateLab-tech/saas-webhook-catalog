"""Tests for the Close extractor — no network calls."""

import pytest
from unittest.mock import AsyncMock

from catalog.extractors.close import CloseExtractor
from catalog.schema import validate


async def _collect(extractor, fetcher):
    rows = []
    async for row in extractor.extract(fetcher):
        rows.append(row)
    return rows


@pytest.mark.asyncio
async def test_close_instantiates():
    extractor = CloseExtractor()
    assert extractor.slug == "close"


@pytest.mark.asyncio
async def test_close_yields_at_least_5_rows():
    fetcher = AsyncMock()
    extractor = CloseExtractor()
    rows = await _collect(extractor, fetcher)
    assert len(rows) >= 5


@pytest.mark.asyncio
async def test_close_rows_pass_schema_validation():
    fetcher = AsyncMock()
    extractor = CloseExtractor()
    rows = await _collect(extractor, fetcher)
    for row in rows:
        errors = validate(row)
        assert errors == [], f"Row {row['event_name']} failed: {errors}"


@pytest.mark.asyncio
async def test_close_confidence_in_range():
    fetcher = AsyncMock()
    extractor = CloseExtractor()
    rows = await _collect(extractor, fetcher)
    for row in rows:
        assert 0.0 <= row["extraction_confidence"] <= 1.0


@pytest.mark.asyncio
async def test_close_crm_events_present():
    fetcher = AsyncMock()
    extractor = CloseExtractor()
    rows = await _collect(extractor, fetcher)
    event_names = [r["event_name"] for r in rows]
    assert "lead.created" in event_names
    assert "opportunity.created" in event_names
    assert "activity.call.created" in event_names
