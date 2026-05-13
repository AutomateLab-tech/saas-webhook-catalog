"""Tests for the Ashby extractor — no network calls."""

import pytest
from unittest.mock import AsyncMock

from catalog.extractors.ashby import AshbyExtractor
from catalog.schema import validate


async def _collect(extractor, fetcher):
    rows = []
    async for row in extractor.extract(fetcher):
        rows.append(row)
    return rows


@pytest.mark.asyncio
async def test_ashby_instantiates():
    extractor = AshbyExtractor()
    assert extractor.slug == "ashby"


@pytest.mark.asyncio
async def test_ashby_yields_at_least_5_rows():
    fetcher = AsyncMock()
    extractor = AshbyExtractor()
    rows = await _collect(extractor, fetcher)
    assert len(rows) >= 5


@pytest.mark.asyncio
async def test_ashby_rows_pass_schema_validation():
    fetcher = AsyncMock()
    extractor = AshbyExtractor()
    rows = await _collect(extractor, fetcher)
    for row in rows:
        errors = validate(row)
        assert errors == [], f"Row {row['event_name']} failed: {errors}"


@pytest.mark.asyncio
async def test_ashby_confidence_in_range():
    fetcher = AsyncMock()
    extractor = AshbyExtractor()
    rows = await _collect(extractor, fetcher)
    for row in rows:
        assert 0.0 <= row["extraction_confidence"] <= 1.0


@pytest.mark.asyncio
async def test_ashby_ats_events_present():
    fetcher = AsyncMock()
    extractor = AshbyExtractor()
    rows = await _collect(extractor, fetcher)
    event_names = [r["event_name"] for r in rows]
    assert "application.created" in event_names
    assert "application.hired" in event_names
    assert "interview.created" in event_names
    assert "offer.created" in event_names
    assert "job.created" in event_names
