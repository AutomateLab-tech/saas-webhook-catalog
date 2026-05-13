"""Tests for the HubSpot extractor — no network calls."""

import pytest
from unittest.mock import AsyncMock

from catalog.extractors.hubspot import HubSpotExtractor
from catalog.schema import validate


async def _collect(extractor, fetcher):
    rows = []
    async for row in extractor.extract(fetcher):
        rows.append(row)
    return rows


@pytest.mark.asyncio
async def test_hubspot_yields_crm_events():
    fetcher = AsyncMock()
    extractor = HubSpotExtractor()
    rows = await _collect(extractor, fetcher)
    event_names = [r["event_name"] for r in rows]
    assert "contact.creation" in event_names
    assert "contact.propertyChange" in event_names
    assert "deal.creation" in event_names
    assert "company.deletion" in event_names


@pytest.mark.asyncio
async def test_hubspot_row_count_in_range():
    fetcher = AsyncMock()
    extractor = HubSpotExtractor()
    rows = await _collect(extractor, fetcher)
    assert 30 <= len(rows) <= 100


@pytest.mark.asyncio
async def test_hubspot_rows_pass_schema_validation():
    fetcher = AsyncMock()
    extractor = HubSpotExtractor()
    rows = await _collect(extractor, fetcher)
    for row in rows:
        errors = validate(row)
        assert errors == [], f"Row {row['event_name']} failed: {errors}"


@pytest.mark.asyncio
async def test_hubspot_auth_method():
    fetcher = AsyncMock()
    extractor = HubSpotExtractor()
    rows = await _collect(extractor, fetcher)
    for row in rows:
        assert row["auth_method"] == "hmac-sha256"
        assert row["signature_header"] == "X-HubSpot-Signature"


@pytest.mark.asyncio
async def test_hubspot_no_cms_events():
    fetcher = AsyncMock()
    extractor = HubSpotExtractor()
    rows = await _collect(extractor, fetcher)
    event_names = [r["event_name"] for r in rows]
    # CMS webhooks should not appear
    for name in event_names:
        assert not name.startswith("content."), f"CMS event found: {name}"
        assert not name.startswith("blog."), f"CMS event found: {name}"
