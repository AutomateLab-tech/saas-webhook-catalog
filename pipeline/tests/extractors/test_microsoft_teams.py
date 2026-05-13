"""Tests for the Microsoft Teams extractor — no network calls."""

import pytest
from unittest.mock import AsyncMock

from catalog.extractors.microsoft_teams import MicrosoftTeamsExtractor
from catalog.schema import validate


async def _collect(extractor, fetcher):
    rows = []
    async for row in extractor.extract(fetcher):
        rows.append(row)
    return rows


@pytest.mark.asyncio
async def test_msteams_instantiates():
    extractor = MicrosoftTeamsExtractor()
    assert extractor.slug == "microsoft-teams"


@pytest.mark.asyncio
async def test_msteams_yields_at_least_5_rows():
    fetcher = AsyncMock()
    extractor = MicrosoftTeamsExtractor()
    rows = await _collect(extractor, fetcher)
    assert len(rows) >= 5


@pytest.mark.asyncio
async def test_msteams_rows_pass_schema_validation():
    fetcher = AsyncMock()
    extractor = MicrosoftTeamsExtractor()
    rows = await _collect(extractor, fetcher)
    for row in rows:
        errors = validate(row)
        assert errors == [], f"Row {row['event_name']} failed: {errors}"


@pytest.mark.asyncio
async def test_msteams_confidence_in_range():
    fetcher = AsyncMock()
    extractor = MicrosoftTeamsExtractor()
    rows = await _collect(extractor, fetcher)
    for row in rows:
        assert 0.0 <= row["extraction_confidence"] <= 1.0


@pytest.mark.asyncio
async def test_msteams_graph_notifications_only():
    fetcher = AsyncMock()
    extractor = MicrosoftTeamsExtractor()
    rows = await _collect(extractor, fetcher)
    for row in rows:
        # All events should be Graph change notifications scope
        assert row["event_namespace"] == "graph-change-notifications"
        # docs_url must be the compliance-required URL
        assert row["docs_url"] == "https://learn.microsoft.com/en-us/graph/webhooks"
