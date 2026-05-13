"""Tests for the Discord extractor — no network calls."""

import pytest
from unittest.mock import AsyncMock

from catalog.extractors.discord import DiscordExtractor
from catalog.schema import validate


async def _collect(extractor, fetcher):
    rows = []
    async for row in extractor.extract(fetcher):
        rows.append(row)
    return rows


@pytest.mark.asyncio
async def test_discord_instantiates():
    extractor = DiscordExtractor()
    assert extractor.slug == "discord"


@pytest.mark.asyncio
async def test_discord_yields_at_least_5_rows():
    fetcher = AsyncMock()
    extractor = DiscordExtractor()
    rows = await _collect(extractor, fetcher)
    assert len(rows) >= 5


@pytest.mark.asyncio
async def test_discord_rows_pass_schema_validation():
    fetcher = AsyncMock()
    extractor = DiscordExtractor()
    rows = await _collect(extractor, fetcher)
    for row in rows:
        errors = validate(row)
        assert errors == [], f"Row {row['event_name']} failed: {errors}"


@pytest.mark.asyncio
async def test_discord_confidence_in_range():
    fetcher = AsyncMock()
    extractor = DiscordExtractor()
    rows = await _collect(extractor, fetcher)
    for row in rows:
        assert 0.0 <= row["extraction_confidence"] <= 1.0


@pytest.mark.asyncio
async def test_discord_delivery_tagged_correctly():
    """Compliance (ToS audit 2026-05-13): Gateway events = websocket, interaction webhooks = webhook (explicit)."""
    fetcher = AsyncMock()
    extractor = DiscordExtractor()
    rows = await _collect(extractor, fetcher)
    gateway_rows = [r for r in rows if r["event_namespace"] == "gateway"]
    interaction_rows = [r for r in rows if r["event_namespace"] == "interactions"]
    assert len(gateway_rows) > 0
    assert len(interaction_rows) > 0
    for row in gateway_rows:
        assert row["delivery"] == "websocket"
    for row in interaction_rows:
        assert row["delivery"] == "webhook"  # Explicitly tagged per ToS compliance obligation


@pytest.mark.asyncio
async def test_discord_no_verbatim_descriptions():
    """Compliance: descriptions must be paraphrased."""
    fetcher = AsyncMock()
    extractor = DiscordExtractor()
    rows = await _collect(extractor, fetcher)
    for row in rows:
        desc = row["trigger_description"]
        assert len(desc) <= 500
        assert len(desc) >= 10
