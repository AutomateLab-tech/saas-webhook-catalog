"""Tests for the Stripe extractor — no network calls."""

import pytest
from unittest.mock import AsyncMock

from catalog.extractors.stripe import StripeExtractor
from catalog.schema import validate


async def _collect(extractor, fetcher):
    rows = []
    async for row in extractor.extract(fetcher):
        rows.append(row)
    return rows


@pytest.mark.asyncio
async def test_stripe_yields_expected_events():
    fetcher = AsyncMock()
    extractor = StripeExtractor()
    rows = await _collect(extractor, fetcher)
    event_names = [r["event_name"] for r in rows]
    assert "charge.succeeded" in event_names
    assert "customer.subscription.created" in event_names
    assert "invoice.paid" in event_names
    assert "payment_intent.succeeded" in event_names
    assert "customer.created" in event_names


@pytest.mark.asyncio
async def test_stripe_row_count_in_range():
    fetcher = AsyncMock()
    extractor = StripeExtractor()
    rows = await _collect(extractor, fetcher)
    assert 200 <= len(rows) <= 260


@pytest.mark.asyncio
async def test_stripe_rows_pass_schema_validation():
    fetcher = AsyncMock()
    extractor = StripeExtractor()
    rows = await _collect(extractor, fetcher)
    for row in rows:
        errors = validate(row)
        assert errors == [], f"Row {row['event_name']} failed: {errors}"


@pytest.mark.asyncio
async def test_stripe_auth_method():
    fetcher = AsyncMock()
    extractor = StripeExtractor()
    rows = await _collect(extractor, fetcher)
    for row in rows:
        assert row["auth_method"] == "hmac-sha256"
        assert row["signature_header"] == "Stripe-Signature"


@pytest.mark.asyncio
async def test_stripe_extraction_method():
    fetcher = AsyncMock()
    extractor = StripeExtractor()
    rows = await _collect(extractor, fetcher)
    for row in rows:
        assert row["extraction_method"] == "manual-html"
