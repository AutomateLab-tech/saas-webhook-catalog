"""Tests for the Freshdesk extractor — no network calls."""

import pytest
from unittest.mock import AsyncMock

from catalog.extractors.freshdesk import FreshdeskExtractor
from catalog.schema import validate


async def _collect(extractor, fetcher):
    rows = []
    async for row in extractor.extract(fetcher):
        rows.append(row)
    return rows


@pytest.mark.asyncio
async def test_freshdesk_instantiates():
    extractor = FreshdeskExtractor()
    assert extractor.slug == "freshdesk"


@pytest.mark.asyncio
async def test_freshdesk_yields_at_least_5_rows():
    fetcher = AsyncMock()
    extractor = FreshdeskExtractor()
    rows = await _collect(extractor, fetcher)
    assert len(rows) >= 5


@pytest.mark.asyncio
async def test_freshdesk_rows_pass_schema_validation():
    fetcher = AsyncMock()
    extractor = FreshdeskExtractor()
    rows = await _collect(extractor, fetcher)
    for row in rows:
        errors = validate(row)
        assert errors == [], f"Row {row['event_name']} failed: {errors}"


@pytest.mark.asyncio
async def test_freshdesk_confidence_in_range():
    fetcher = AsyncMock()
    extractor = FreshdeskExtractor()
    rows = await _collect(extractor, fetcher)
    for row in rows:
        assert 0.0 <= row["extraction_confidence"] <= 1.0


@pytest.mark.asyncio
async def test_freshdesk_ticket_events_present():
    fetcher = AsyncMock()
    extractor = FreshdeskExtractor()
    rows = await _collect(extractor, fetcher)
    event_names = [r["event_name"] for r in rows]
    assert "ticket.created" in event_names
    assert "ticket.resolved" in event_names
    assert "ticket.status_updated" in event_names
