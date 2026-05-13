"""Tests for the BambooHR extractor — no network calls."""

import pytest
from unittest.mock import AsyncMock

from catalog.extractors.bamboohr import BambooHRExtractor
from catalog.schema import validate


async def _collect(extractor, fetcher):
    rows = []
    async for row in extractor.extract(fetcher):
        rows.append(row)
    return rows


@pytest.mark.asyncio
async def test_bamboohr_instantiates():
    extractor = BambooHRExtractor()
    assert extractor.slug == "bamboohr"


@pytest.mark.asyncio
async def test_bamboohr_yields_at_least_5_rows():
    fetcher = AsyncMock()
    extractor = BambooHRExtractor()
    rows = await _collect(extractor, fetcher)
    assert len(rows) >= 5


@pytest.mark.asyncio
async def test_bamboohr_rows_pass_schema_validation():
    fetcher = AsyncMock()
    extractor = BambooHRExtractor()
    rows = await _collect(extractor, fetcher)
    for row in rows:
        errors = validate(row)
        assert errors == [], f"Row {row['event_name']} failed: {errors}"


@pytest.mark.asyncio
async def test_bamboohr_confidence_in_range():
    fetcher = AsyncMock()
    extractor = BambooHRExtractor()
    rows = await _collect(extractor, fetcher)
    for row in rows:
        assert 0.0 <= row["extraction_confidence"] <= 1.0


@pytest.mark.asyncio
async def test_bamboohr_hris_events_present():
    fetcher = AsyncMock()
    extractor = BambooHRExtractor()
    rows = await _collect(extractor, fetcher)
    event_names = [r["event_name"] for r in rows]
    assert "hired" in event_names
    assert "terminated" in event_names
    assert "changed" in event_names
