"""Tests for the GitHub extractor — no network calls."""

import pytest
from unittest.mock import AsyncMock

from catalog.extractors.github import GitHubExtractor
from catalog.schema import validate


async def _collect(extractor, fetcher):
    rows = []
    async for row in extractor.extract(fetcher):
        rows.append(row)
    return rows


@pytest.mark.asyncio
async def test_github_yields_expected_events():
    fetcher = AsyncMock()
    extractor = GitHubExtractor()
    rows = await _collect(extractor, fetcher)
    event_names = [r["event_name"] for r in rows]
    assert "push" in event_names
    assert "pull_request" in event_names
    assert "issues" in event_names
    assert "release" in event_names
    assert "check_run" in event_names


@pytest.mark.asyncio
async def test_github_row_count_in_range():
    fetcher = AsyncMock()
    extractor = GitHubExtractor()
    rows = await _collect(extractor, fetcher)
    assert 50 <= len(rows) <= 90


@pytest.mark.asyncio
async def test_github_rows_pass_schema_validation():
    fetcher = AsyncMock()
    extractor = GitHubExtractor()
    rows = await _collect(extractor, fetcher)
    for row in rows:
        errors = validate(row)
        assert errors == [], f"Row {row['event_name']} failed: {errors}"


@pytest.mark.asyncio
async def test_github_idempotency_key():
    fetcher = AsyncMock()
    extractor = GitHubExtractor()
    rows = await _collect(extractor, fetcher)
    for row in rows:
        assert row["idempotency_key_header"] == "X-GitHub-Delivery"


@pytest.mark.asyncio
async def test_github_payload_size():
    fetcher = AsyncMock()
    extractor = GitHubExtractor()
    rows = await _collect(extractor, fetcher)
    for row in rows:
        assert row["max_payload_size_bytes"] == 25 * 1024 * 1024
