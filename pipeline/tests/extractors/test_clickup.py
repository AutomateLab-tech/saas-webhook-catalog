"""Tests for the ClickUp extractor — no network calls."""

import pytest
from unittest.mock import AsyncMock

from catalog.extractors.clickup import ClickUpExtractor
from catalog.schema import validate


async def _collect(extractor, fetcher):
    rows = []
    async for row in extractor.extract(fetcher):
        rows.append(row)
    return rows


@pytest.mark.asyncio
async def test_clickup_instantiates():
    extractor = ClickUpExtractor()
    assert extractor.slug == "clickup"


@pytest.mark.asyncio
async def test_clickup_yields_at_least_5_rows():
    fetcher = AsyncMock()
    extractor = ClickUpExtractor()
    rows = await _collect(extractor, fetcher)
    assert len(rows) >= 5


@pytest.mark.asyncio
async def test_clickup_rows_pass_schema_validation():
    fetcher = AsyncMock()
    extractor = ClickUpExtractor()
    rows = await _collect(extractor, fetcher)
    for row in rows:
        errors = validate(row)
        assert errors == [], f"Row {row['event_name']} failed: {errors}"


@pytest.mark.asyncio
async def test_clickup_confidence_in_range():
    fetcher = AsyncMock()
    extractor = ClickUpExtractor()
    rows = await _collect(extractor, fetcher)
    for row in rows:
        assert 0.0 <= row["extraction_confidence"] <= 1.0


@pytest.mark.asyncio
async def test_clickup_core_task_events_present():
    fetcher = AsyncMock()
    extractor = ClickUpExtractor()
    rows = await _collect(extractor, fetcher)
    event_names = [r["event_name"] for r in rows]
    assert "taskCreated" in event_names
    assert "taskUpdated" in event_names
    assert "taskStatusUpdated" in event_names
