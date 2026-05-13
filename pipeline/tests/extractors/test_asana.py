"""Tests for the Asana extractor — no network calls."""

import pytest
from unittest.mock import AsyncMock

from catalog.extractors.asana import AsanaExtractor
from catalog.schema import validate


async def _collect(extractor, fetcher):
    rows = []
    async for row in extractor.extract(fetcher):
        rows.append(row)
    return rows


@pytest.mark.asyncio
async def test_asana_instantiates():
    extractor = AsanaExtractor()
    assert extractor.slug == "asana"


@pytest.mark.asyncio
async def test_asana_yields_at_least_5_rows():
    fetcher = AsyncMock()
    extractor = AsanaExtractor()
    rows = await _collect(extractor, fetcher)
    assert len(rows) >= 5


@pytest.mark.asyncio
async def test_asana_rows_pass_schema_validation():
    fetcher = AsyncMock()
    extractor = AsanaExtractor()
    rows = await _collect(extractor, fetcher)
    for row in rows:
        errors = validate(row)
        assert errors == [], f"Row {row['event_name']} failed: {errors}"


@pytest.mark.asyncio
async def test_asana_confidence_in_range():
    fetcher = AsyncMock()
    extractor = AsanaExtractor()
    rows = await _collect(extractor, fetcher)
    for row in rows:
        assert 0.0 <= row["extraction_confidence"] <= 1.0


@pytest.mark.asyncio
async def test_asana_extraction_method():
    fetcher = AsyncMock()
    extractor = AsanaExtractor()
    rows = await _collect(extractor, fetcher)
    for row in rows:
        assert row["extraction_method"] == "llm-assisted"
        assert row["vendor"] == "asana"
