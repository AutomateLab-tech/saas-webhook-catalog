"""Tests for the Calendly extractor — no network calls."""

import pytest
from unittest.mock import AsyncMock

from catalog.extractors.calendly import CalendlyExtractor
from catalog.schema import validate


async def _collect(extractor, fetcher):
    rows = []
    async for row in extractor.extract(fetcher):
        rows.append(row)
    return rows


@pytest.mark.asyncio
async def test_calendly_yields_expected_events():
    fetcher = AsyncMock()
    extractor = CalendlyExtractor()
    rows = await _collect(extractor, fetcher)
    event_names = [r["event_name"] for r in rows]
    assert "invitee.created" in event_names
    assert "invitee.canceled" in event_names


@pytest.mark.asyncio
async def test_calendly_row_count():
    fetcher = AsyncMock()
    extractor = CalendlyExtractor()
    rows = await _collect(extractor, fetcher)
    assert 2 <= len(rows) <= 15


@pytest.mark.asyncio
async def test_calendly_rows_pass_schema_validation():
    fetcher = AsyncMock()
    extractor = CalendlyExtractor()
    rows = await _collect(extractor, fetcher)
    for row in rows:
        errors = validate(row)
        assert errors == [], f"Row {row['event_name']} failed: {errors}"


@pytest.mark.asyncio
async def test_calendly_auth_method():
    fetcher = AsyncMock()
    extractor = CalendlyExtractor()
    rows = await _collect(extractor, fetcher)
    for row in rows:
        assert row["auth_method"] == "hmac-sha256"
