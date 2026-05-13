"""Tests for the Intercom extractor — no network calls."""

import pytest
from unittest.mock import AsyncMock

from catalog.extractors.intercom import IntercomExtractor
from catalog.schema import validate


async def _collect(extractor, fetcher):
    rows = []
    async for row in extractor.extract(fetcher):
        rows.append(row)
    return rows


@pytest.mark.asyncio
async def test_intercom_yields_expected_topics():
    fetcher = AsyncMock()
    extractor = IntercomExtractor()
    rows = await _collect(extractor, fetcher)
    event_names = [r["event_name"] for r in rows]
    assert "conversation.user.created" in event_names
    assert "conversation.admin.assigned" in event_names
    assert "contact.user.created" in event_names
    assert "ticket.created" in event_names
    assert "ping" in event_names


@pytest.mark.asyncio
async def test_intercom_row_count_in_range():
    fetcher = AsyncMock()
    extractor = IntercomExtractor()
    rows = await _collect(extractor, fetcher)
    assert 30 <= len(rows) <= 130


@pytest.mark.asyncio
async def test_intercom_rows_pass_schema_validation():
    fetcher = AsyncMock()
    extractor = IntercomExtractor()
    rows = await _collect(extractor, fetcher)
    for row in rows:
        errors = validate(row)
        assert errors == [], f"Row {row['event_name']} failed: {errors}"


@pytest.mark.asyncio
async def test_intercom_auth_method():
    fetcher = AsyncMock()
    extractor = IntercomExtractor()
    rows = await _collect(extractor, fetcher)
    for row in rows:
        assert row["auth_method"] == "hmac-sha1"
        assert row["signature_header"] == "X-Hub-Signature"
