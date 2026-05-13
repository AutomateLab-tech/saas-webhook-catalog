"""Tests for the Pipedrive extractor — no network calls."""

import pytest
from unittest.mock import AsyncMock

from catalog.extractors.pipedrive import PipedriveExtractor
from catalog.schema import validate


async def _collect(extractor, fetcher):
    rows = []
    async for row in extractor.extract(fetcher):
        rows.append(row)
    return rows


@pytest.mark.asyncio
async def test_pipedrive_instantiates():
    extractor = PipedriveExtractor()
    assert extractor.slug == "pipedrive"


@pytest.mark.asyncio
async def test_pipedrive_yields_at_least_5_rows():
    fetcher = AsyncMock()
    extractor = PipedriveExtractor()
    rows = await _collect(extractor, fetcher)
    assert len(rows) >= 5


@pytest.mark.asyncio
async def test_pipedrive_rows_pass_schema_validation():
    fetcher = AsyncMock()
    extractor = PipedriveExtractor()
    rows = await _collect(extractor, fetcher)
    for row in rows:
        errors = validate(row)
        assert errors == [], f"Row {row['event_name']} failed: {errors}"


@pytest.mark.asyncio
async def test_pipedrive_confidence_in_range():
    fetcher = AsyncMock()
    extractor = PipedriveExtractor()
    rows = await _collect(extractor, fetcher)
    for row in rows:
        assert 0.0 <= row["extraction_confidence"] <= 1.0


@pytest.mark.asyncio
async def test_pipedrive_crm_events_present():
    fetcher = AsyncMock()
    extractor = PipedriveExtractor()
    rows = await _collect(extractor, fetcher)
    event_names = [r["event_name"] for r in rows]
    assert "added.deal" in event_names
    assert "updated.deal" in event_names
    assert "added.person" in event_names
