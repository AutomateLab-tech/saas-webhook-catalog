"""Tests for the Greenhouse extractor — no network calls."""

import pytest
from unittest.mock import AsyncMock

from catalog.extractors.greenhouse import GreenhouseExtractor
from catalog.schema import validate


async def _collect(extractor, fetcher):
    rows = []
    async for row in extractor.extract(fetcher):
        rows.append(row)
    return rows


@pytest.mark.asyncio
async def test_greenhouse_instantiates():
    extractor = GreenhouseExtractor()
    assert extractor.slug == "greenhouse"


@pytest.mark.asyncio
async def test_greenhouse_yields_at_least_5_rows():
    fetcher = AsyncMock()
    extractor = GreenhouseExtractor()
    rows = await _collect(extractor, fetcher)
    assert len(rows) >= 5


@pytest.mark.asyncio
async def test_greenhouse_rows_pass_schema_validation():
    fetcher = AsyncMock()
    extractor = GreenhouseExtractor()
    rows = await _collect(extractor, fetcher)
    for row in rows:
        errors = validate(row)
        assert errors == [], f"Row {row['event_name']} failed: {errors}"


@pytest.mark.asyncio
async def test_greenhouse_confidence_in_range():
    fetcher = AsyncMock()
    extractor = GreenhouseExtractor()
    rows = await _collect(extractor, fetcher)
    for row in rows:
        assert 0.0 <= row["extraction_confidence"] <= 1.0


@pytest.mark.asyncio
async def test_greenhouse_ats_events_present():
    fetcher = AsyncMock()
    extractor = GreenhouseExtractor()
    rows = await _collect(extractor, fetcher)
    event_names = [r["event_name"] for r in rows]
    assert "hire_candidate" in event_names      # canonical Greenhouse event name (was candidate_hired — fixed in audit)
    assert "offer_created" in event_names       # canonical name (was offer_extended — fixed in audit)
    assert "job_created" in event_names
