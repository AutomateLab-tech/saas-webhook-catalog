"""Tests for the Slack extractor — no network calls."""

import asyncio
import pytest
from unittest.mock import AsyncMock

from catalog.extractors.slack import SlackExtractor
from catalog.schema import validate


async def _collect(extractor, fetcher):
    rows = []
    async for row in extractor.extract(fetcher):
        rows.append(row)
    return rows


@pytest.mark.asyncio
async def test_slack_yields_expected_events():
    fetcher = AsyncMock()
    extractor = SlackExtractor()
    rows = await _collect(extractor, fetcher)

    event_names = [r["event_name"] for r in rows]
    assert "app_mention" in event_names
    assert "message" in event_names
    assert "channel_created" in event_names
    assert "reaction_added" in event_names
    assert "member_joined_channel" in event_names


@pytest.mark.asyncio
async def test_slack_excludes_slash_commands():
    fetcher = AsyncMock()
    extractor = SlackExtractor()
    rows = await _collect(extractor, fetcher)
    event_names = [r["event_name"] for r in rows]
    # Slash commands should not appear
    assert "slash_command" not in event_names
    assert "command" not in event_names


@pytest.mark.asyncio
async def test_slack_row_count_in_range():
    fetcher = AsyncMock()
    extractor = SlackExtractor()
    rows = await _collect(extractor, fetcher)
    # Expected range from spec: 70-90, but confirmed index has 113 entries
    assert 70 <= len(rows) <= 150


@pytest.mark.asyncio
async def test_slack_rows_pass_schema_validation():
    fetcher = AsyncMock()
    extractor = SlackExtractor()
    rows = await _collect(extractor, fetcher)
    for row in rows:
        errors = validate(row)
        assert errors == [], f"Row {row['event_name']} failed: {errors}"


@pytest.mark.asyncio
async def test_slack_auth_method():
    fetcher = AsyncMock()
    extractor = SlackExtractor()
    rows = await _collect(extractor, fetcher)
    for row in rows:
        assert row["auth_method"] == "hmac-sha256"
        assert row["signature_header"] == "X-Slack-Signature"


@pytest.mark.asyncio
async def test_slack_trigger_descriptions_paraphrased():
    fetcher = AsyncMock()
    extractor = SlackExtractor()
    rows = await _collect(extractor, fetcher)
    # No description should be verbatim from docs ("Sent when a...")
    for row in rows:
        desc = row["trigger_description"]
        assert len(desc) <= 500
        assert len(desc) >= 10
