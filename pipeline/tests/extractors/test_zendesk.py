"""Tests for the Zendesk extractor — no network calls."""

import pytest
from unittest.mock import AsyncMock

from catalog.extractors.zendesk import ZendeskExtractor
from catalog.schema import validate


async def _collect(extractor, fetcher):
    rows = []
    async for row in extractor.extract(fetcher):
        rows.append(row)
    return rows


@pytest.mark.asyncio
async def test_zendesk_yields_expected_events():
    fetcher = AsyncMock()
    extractor = ZendeskExtractor()
    rows = await _collect(extractor, fetcher)
    event_names = [r["event_name"] for r in rows]
    assert "zen:event-type/ticket.TicketCreated" in event_names
    assert "zen:event-type/user.UserCreated" in event_names
    assert "zen:event-type/organization.OrganizationCreated" in event_names
    assert "zen:event-type/article.ArticlePublished" in event_names


@pytest.mark.asyncio
async def test_zendesk_row_count_in_range():
    fetcher = AsyncMock()
    extractor = ZendeskExtractor()
    rows = await _collect(extractor, fetcher)
    assert 30 <= len(rows) <= 100


@pytest.mark.asyncio
async def test_zendesk_rows_pass_schema_validation():
    fetcher = AsyncMock()
    extractor = ZendeskExtractor()
    rows = await _collect(extractor, fetcher)
    for row in rows:
        errors = validate(row)
        assert errors == [], f"Row {row['event_name']} failed: {errors}"


@pytest.mark.asyncio
async def test_zendesk_auth_method():
    fetcher = AsyncMock()
    extractor = ZendeskExtractor()
    rows = await _collect(extractor, fetcher)
    for row in rows:
        assert row["auth_method"] == "hmac-sha256"
        assert row["signature_header"] == "X-Zendesk-Webhook-Signature"
