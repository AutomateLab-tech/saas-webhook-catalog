"""Tests for the Notion extractor — no network calls."""

import pytest
from unittest.mock import AsyncMock

from catalog.extractors.notion import NotionExtractor
from catalog.schema import validate


async def _collect(extractor, fetcher):
    rows = []
    async for row in extractor.extract(fetcher):
        rows.append(row)
    return rows


@pytest.mark.asyncio
async def test_notion_yields_expected_events():
    fetcher = AsyncMock()
    extractor = NotionExtractor()
    rows = await _collect(extractor, fetcher)
    event_names = [r["event_name"] for r in rows]
    assert "page.content_updated" in event_names
    assert "comment.created" in event_names
    assert "page.locked" in event_names


@pytest.mark.asyncio
async def test_notion_row_count():
    fetcher = AsyncMock()
    extractor = NotionExtractor()
    rows = await _collect(extractor, fetcher)
    assert 3 <= len(rows) <= 20


@pytest.mark.asyncio
async def test_notion_rows_pass_schema_validation():
    fetcher = AsyncMock()
    extractor = NotionExtractor()
    rows = await _collect(extractor, fetcher)
    for row in rows:
        errors = validate(row)
        assert errors == [], f"Row {row['event_name']} failed: {errors}"


@pytest.mark.asyncio
async def test_notion_auth_method():
    fetcher = AsyncMock()
    extractor = NotionExtractor()
    rows = await _collect(extractor, fetcher)
    for row in rows:
        assert row["auth_method"] == "hmac-sha256"
        assert row["signature_header"] == "X-Notion-Signature"
