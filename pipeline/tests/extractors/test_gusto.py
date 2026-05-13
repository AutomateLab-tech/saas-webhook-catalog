"""Tests for the Gusto extractor — no network calls."""

import pytest
from unittest.mock import AsyncMock

from catalog.extractors.gusto import GustoExtractor
from catalog.schema import validate


async def _collect(extractor, fetcher):
    rows = []
    async for row in extractor.extract(fetcher):
        rows.append(row)
    return rows


@pytest.mark.asyncio
async def test_gusto_instantiates():
    extractor = GustoExtractor()
    assert extractor.slug == "gusto"


@pytest.mark.asyncio
async def test_gusto_yields_at_least_5_rows():
    fetcher = AsyncMock()
    extractor = GustoExtractor()
    rows = await _collect(extractor, fetcher)
    assert len(rows) >= 5


@pytest.mark.asyncio
async def test_gusto_rows_pass_schema_validation():
    fetcher = AsyncMock()
    extractor = GustoExtractor()
    rows = await _collect(extractor, fetcher)
    for row in rows:
        errors = validate(row)
        assert errors == [], f"Row {row['event_name']} failed: {errors}"


@pytest.mark.asyncio
async def test_gusto_confidence_in_range():
    fetcher = AsyncMock()
    extractor = GustoExtractor()
    rows = await _collect(extractor, fetcher)
    for row in rows:
        assert 0.0 <= row["extraction_confidence"] <= 1.0


@pytest.mark.asyncio
async def test_gusto_hris_events_present():
    fetcher = AsyncMock()
    extractor = GustoExtractor()
    rows = await _collect(extractor, fetcher)
    event_names = [r["event_name"] for r in rows]
    assert "employee.created" in event_names
    assert "employee.terminated" in event_names
    assert "payroll.submitted" in event_names
