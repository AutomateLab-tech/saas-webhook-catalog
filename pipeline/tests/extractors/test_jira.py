"""Tests for the Jira (Cloud) extractor — no network calls."""

import pytest
from unittest.mock import AsyncMock

from catalog.extractors.jira import JiraExtractor
from catalog.schema import validate


async def _collect(extractor, fetcher):
    rows = []
    async for row in extractor.extract(fetcher):
        rows.append(row)
    return rows


@pytest.mark.asyncio
async def test_jira_instantiates():
    extractor = JiraExtractor()
    assert extractor.slug == "jira"


@pytest.mark.asyncio
async def test_jira_yields_at_least_5_rows():
    fetcher = AsyncMock()
    extractor = JiraExtractor()
    rows = await _collect(extractor, fetcher)
    assert len(rows) >= 5


@pytest.mark.asyncio
async def test_jira_rows_pass_schema_validation():
    fetcher = AsyncMock()
    extractor = JiraExtractor()
    rows = await _collect(extractor, fetcher)
    for row in rows:
        errors = validate(row)
        assert errors == [], f"Row {row['event_name']} failed: {errors}"


@pytest.mark.asyncio
async def test_jira_confidence_in_range():
    fetcher = AsyncMock()
    extractor = JiraExtractor()
    rows = await _collect(extractor, fetcher)
    for row in rows:
        assert 0.0 <= row["extraction_confidence"] <= 1.0


@pytest.mark.asyncio
async def test_jira_includes_key_events():
    fetcher = AsyncMock()
    extractor = JiraExtractor()
    rows = await _collect(extractor, fetcher)
    event_names = [r["event_name"] for r in rows]
    assert "jira:issue_created" in event_names
    assert "jira:issue_updated" in event_names
    assert "sprint_started" in event_names
