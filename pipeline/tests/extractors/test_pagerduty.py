"""Tests for the PagerDuty extractor — no network calls."""

import pytest
from unittest.mock import AsyncMock

from catalog.extractors.pagerduty import PagerDutyExtractor
from catalog.schema import validate


async def _collect(extractor, fetcher):
    rows = []
    async for row in extractor.extract(fetcher):
        rows.append(row)
    return rows


@pytest.mark.asyncio
async def test_pagerduty_instantiates():
    extractor = PagerDutyExtractor()
    assert extractor.slug == "pagerduty"


@pytest.mark.asyncio
async def test_pagerduty_yields_at_least_5_rows():
    fetcher = AsyncMock()
    extractor = PagerDutyExtractor()
    rows = await _collect(extractor, fetcher)
    assert len(rows) >= 5


@pytest.mark.asyncio
async def test_pagerduty_rows_pass_schema_validation():
    fetcher = AsyncMock()
    extractor = PagerDutyExtractor()
    rows = await _collect(extractor, fetcher)
    for row in rows:
        errors = validate(row)
        assert errors == [], f"Row {row['event_name']} failed: {errors}"


@pytest.mark.asyncio
async def test_pagerduty_confidence_in_range():
    fetcher = AsyncMock()
    extractor = PagerDutyExtractor()
    rows = await _collect(extractor, fetcher)
    for row in rows:
        assert 0.0 <= row["extraction_confidence"] <= 1.0


@pytest.mark.asyncio
async def test_pagerduty_includes_incident_events():
    fetcher = AsyncMock()
    extractor = PagerDutyExtractor()
    rows = await _collect(extractor, fetcher)
    event_names = [r["event_name"] for r in rows]
    assert "incident.triggered" in event_names
    assert "incident.acknowledged" in event_names
    assert "incident.resolved" in event_names
