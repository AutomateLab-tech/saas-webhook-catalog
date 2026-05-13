"""Tests for the Salesforce extractor — no network calls."""

import pytest
from unittest.mock import AsyncMock

from catalog.extractors.salesforce import SalesforceExtractor
from catalog.schema import validate


async def _collect(extractor, fetcher):
    rows = []
    async for row in extractor.extract(fetcher):
        rows.append(row)
    return rows


@pytest.mark.asyncio
async def test_salesforce_yields_platform_events():
    fetcher = AsyncMock()
    extractor = SalesforceExtractor()
    rows = await _collect(extractor, fetcher)
    event_names = [r["event_name"] for r in rows]
    assert "/event/LoginEventStream" in event_names
    assert "/event/ApiEventStream" in event_names


@pytest.mark.asyncio
async def test_salesforce_yields_cdc_events():
    fetcher = AsyncMock()
    extractor = SalesforceExtractor()
    rows = await _collect(extractor, fetcher)
    event_names = [r["event_name"] for r in rows]
    assert "/data/AccountChangeEvent" in event_names
    assert "/data/ContactChangeEvent" in event_names
    assert "/data/LeadChangeEvent" in event_names
    assert "/data/OpportunityChangeEvent" in event_names


@pytest.mark.asyncio
async def test_salesforce_excludes_outbound_messages():
    fetcher = AsyncMock()
    extractor = SalesforceExtractor()
    rows = await _collect(extractor, fetcher)
    event_names = [r["event_name"] for r in rows]
    # Outbound Messages are SOAP-based and out of scope
    for name in event_names:
        assert "OutboundMessage" not in name


@pytest.mark.asyncio
async def test_salesforce_row_count_in_range():
    fetcher = AsyncMock()
    extractor = SalesforceExtractor()
    rows = await _collect(extractor, fetcher)
    assert 30 <= len(rows) <= 100


@pytest.mark.asyncio
async def test_salesforce_rows_pass_schema_validation():
    fetcher = AsyncMock()
    extractor = SalesforceExtractor()
    rows = await _collect(extractor, fetcher)
    for row in rows:
        errors = validate(row)
        assert errors == [], f"Row {row['event_name']} failed: {errors}"


@pytest.mark.asyncio
async def test_salesforce_auth_method():
    fetcher = AsyncMock()
    extractor = SalesforceExtractor()
    rows = await _collect(extractor, fetcher)
    for row in rows:
        assert row["auth_method"] == "bearer-token"


@pytest.mark.asyncio
async def test_salesforce_namespaces():
    fetcher = AsyncMock()
    extractor = SalesforceExtractor()
    rows = await _collect(extractor, fetcher)
    namespaces = {r["event_namespace"] for r in rows}
    assert "platform_events" in namespaces
    assert "change_data_capture" in namespaces
