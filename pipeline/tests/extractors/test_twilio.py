"""Tests for the Twilio extractor — no network calls."""

import pytest
from unittest.mock import AsyncMock

from catalog.extractors.twilio import TwilioExtractor
from catalog.schema import validate


async def _collect(extractor, fetcher):
    rows = []
    async for row in extractor.extract(fetcher):
        rows.append(row)
    return rows


@pytest.mark.asyncio
async def test_twilio_instantiates():
    extractor = TwilioExtractor()
    assert extractor.slug == "twilio"


@pytest.mark.asyncio
async def test_twilio_yields_at_least_5_rows():
    fetcher = AsyncMock()
    extractor = TwilioExtractor()
    rows = await _collect(extractor, fetcher)
    assert len(rows) >= 5


@pytest.mark.asyncio
async def test_twilio_rows_pass_schema_validation():
    fetcher = AsyncMock()
    extractor = TwilioExtractor()
    rows = await _collect(extractor, fetcher)
    for row in rows:
        errors = validate(row)
        assert errors == [], f"Row {row['event_name']} failed: {errors}"


@pytest.mark.asyncio
async def test_twilio_confidence_in_range():
    fetcher = AsyncMock()
    extractor = TwilioExtractor()
    rows = await _collect(extractor, fetcher)
    for row in rows:
        assert 0.0 <= row["extraction_confidence"] <= 1.0


@pytest.mark.asyncio
async def test_twilio_scope_decision():
    """Scope: messaging + conversations only; no voice TwiML."""
    fetcher = AsyncMock()
    extractor = TwilioExtractor()
    rows = await _collect(extractor, fetcher)
    namespaces = {r["event_namespace"] for r in rows}
    assert "messaging" in namespaces
    assert "conversations" in namespaces
    # Voice scope excluded
    assert "voice" not in namespaces
