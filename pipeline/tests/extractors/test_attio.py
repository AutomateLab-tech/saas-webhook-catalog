"""Tests for the Attio extractor — no network calls."""

import pytest
from unittest.mock import AsyncMock

from catalog.extractors.attio import AttioExtractor
from catalog.schema import validate


async def _collect(extractor, fetcher):
    rows = []
    async for row in extractor.extract(fetcher):
        rows.append(row)
    return rows


@pytest.mark.asyncio
async def test_attio_instantiates():
    extractor = AttioExtractor()
    assert extractor.slug == "attio"


@pytest.mark.asyncio
async def test_attio_yields_at_least_5_rows():
    fetcher = AsyncMock()
    extractor = AttioExtractor()
    rows = await _collect(extractor, fetcher)
    assert len(rows) >= 5


@pytest.mark.asyncio
async def test_attio_rows_pass_schema_validation():
    fetcher = AsyncMock()
    extractor = AttioExtractor()
    rows = await _collect(extractor, fetcher)
    for row in rows:
        errors = validate(row)
        assert errors == [], f"Row {row['event_name']} failed: {errors}"


@pytest.mark.asyncio
async def test_attio_confidence_in_range():
    fetcher = AsyncMock()
    extractor = AttioExtractor()
    rows = await _collect(extractor, fetcher)
    for row in rows:
        assert 0.0 <= row["extraction_confidence"] <= 1.0


@pytest.mark.asyncio
async def test_attio_core_events_present():
    fetcher = AsyncMock()
    extractor = AttioExtractor()
    rows = await _collect(extractor, fetcher)
    event_names = [r["event_name"] for r in rows]
    assert "record.created" in event_names
    assert "record.updated" in event_names
    assert "note.created" in event_names
