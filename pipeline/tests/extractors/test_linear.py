"""Tests for the Linear extractor — no network calls."""

import pytest
from unittest.mock import AsyncMock

from catalog.extractors.linear import LinearExtractor
from catalog.schema import validate


async def _collect(extractor, fetcher):
    rows = []
    async for row in extractor.extract(fetcher):
        rows.append(row)
    return rows


@pytest.mark.asyncio
async def test_linear_yields_expected_events():
    fetcher = AsyncMock()
    extractor = LinearExtractor()
    rows = await _collect(extractor, fetcher)
    event_names = [r["event_name"] for r in rows]
    assert "Issue.create" in event_names
    assert "Issue.update" in event_names
    assert "Issue.remove" in event_names
    assert "Comment.create" in event_names
    assert "Project.create" in event_names


@pytest.mark.asyncio
async def test_linear_includes_sla_events():
    fetcher = AsyncMock()
    extractor = LinearExtractor()
    rows = await _collect(extractor, fetcher)
    event_names = [r["event_name"] for r in rows]
    assert "IssueSla.set" in event_names
    assert "IssueSla.highRisk" in event_names
    assert "IssueSla.breached" in event_names


@pytest.mark.asyncio
async def test_linear_includes_oauth_revoked():
    fetcher = AsyncMock()
    extractor = LinearExtractor()
    rows = await _collect(extractor, fetcher)
    event_names = [r["event_name"] for r in rows]
    assert "OAuthClientApproval.revoked" in event_names


@pytest.mark.asyncio
async def test_linear_row_count_in_range():
    fetcher = AsyncMock()
    extractor = LinearExtractor()
    rows = await _collect(extractor, fetcher)
    assert 15 <= len(rows) <= 60


@pytest.mark.asyncio
async def test_linear_rows_pass_schema_validation():
    fetcher = AsyncMock()
    extractor = LinearExtractor()
    rows = await _collect(extractor, fetcher)
    for row in rows:
        errors = validate(row)
        assert errors == [], f"Row {row['event_name']} failed: {errors}"


@pytest.mark.asyncio
async def test_linear_extraction_method():
    fetcher = AsyncMock()
    extractor = LinearExtractor()
    rows = await _collect(extractor, fetcher)
    for row in rows:
        assert row["extraction_method"] == "vendor-graphql-schema"
