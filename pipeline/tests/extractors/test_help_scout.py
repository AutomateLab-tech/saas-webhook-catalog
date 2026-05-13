"""Tests for the Help Scout extractor — no network calls."""

import pytest
from unittest.mock import AsyncMock

from catalog.extractors.help_scout import HelpScoutExtractor
from catalog.schema import validate


async def _collect(extractor, fetcher):
    rows = []
    async for row in extractor.extract(fetcher):
        rows.append(row)
    return rows


@pytest.mark.asyncio
async def test_help_scout_instantiates():
    extractor = HelpScoutExtractor()
    assert extractor.slug == "help-scout"


@pytest.mark.asyncio
async def test_help_scout_yields_at_least_5_rows():
    fetcher = AsyncMock()
    extractor = HelpScoutExtractor()
    rows = await _collect(extractor, fetcher)
    assert len(rows) >= 5


@pytest.mark.asyncio
async def test_help_scout_rows_pass_schema_validation():
    fetcher = AsyncMock()
    extractor = HelpScoutExtractor()
    rows = await _collect(extractor, fetcher)
    for row in rows:
        errors = validate(row)
        assert errors == [], f"Row {row['event_name']} failed: {errors}"


@pytest.mark.asyncio
async def test_help_scout_confidence_in_range():
    fetcher = AsyncMock()
    extractor = HelpScoutExtractor()
    rows = await _collect(extractor, fetcher)
    for row in rows:
        assert 0.0 <= row["extraction_confidence"] <= 1.0


@pytest.mark.asyncio
async def test_help_scout_core_events_present():
    fetcher = AsyncMock()
    extractor = HelpScoutExtractor()
    rows = await _collect(extractor, fetcher)
    event_names = [r["event_name"] for r in rows]
    assert "convo.created" in event_names
    assert "convo.agent.reply.created" in event_names   # canonical name (was convo.reply — fixed in audit)
    assert "satisfaction.ratings" in event_names
