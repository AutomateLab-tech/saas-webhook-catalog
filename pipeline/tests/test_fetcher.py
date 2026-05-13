"""
test_fetcher.py

1. throttle.yaml loads correctly and contains expected domains
2. Per-domain RPS caps are respected (mock httpx transport, no real network)
3. robots.txt blocking works
4. Unknown domain falls back to default config
"""

import asyncio
import time
from pathlib import Path
from unittest.mock import AsyncMock

import httpx
import pytest

from catalog.fetcher import Fetcher, _load_throttle_config, _THROTTLE_PATH


# ---------------------------------------------------------------------------
# Config loading
# ---------------------------------------------------------------------------


def test_throttle_config_loads():
    cfg = _load_throttle_config()
    assert "default" in cfg
    assert "overrides" in cfg


def test_throttle_config_default_fields():
    cfg = _load_throttle_config()
    d = cfg["default"]
    assert "rps" in d
    assert "jitter" in d
    assert "respect_robots" in d
    assert "user_agent" in d


def test_throttle_config_audit_overrides():
    cfg = _load_throttle_config()
    overrides = cfg["overrides"]
    assert "developer.zendesk.com" in overrides
    assert "developer.atlassian.com" in overrides
    assert "learn.microsoft.com" in overrides


def test_zendesk_rps_cap():
    cfg = _load_throttle_config()
    assert float(cfg["overrides"]["developer.zendesk.com"]["rps"]) <= 1.0


def test_atlassian_rps_cap():
    cfg = _load_throttle_config()
    assert float(cfg["overrides"]["developer.atlassian.com"]["rps"]) <= 1.0


def test_microsoft_rps_cap():
    cfg = _load_throttle_config()
    assert float(cfg["overrides"]["learn.microsoft.com"]["rps"]) <= 0.5


# ---------------------------------------------------------------------------
# Helpers for mock transport
# ---------------------------------------------------------------------------

def _make_mock_transport(responses: dict[str, tuple[int, str]]) -> httpx.MockTransport:
    """
    Build a MockTransport that returns (status, text) by URL.
    Unmatched URLs return 200 with empty body.
    """
    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        for prefix, (status, body) in responses.items():
            if url.startswith(prefix):
                return httpx.Response(status, text=body)
        return httpx.Response(200, text="")
    return httpx.MockTransport(handler)


# ---------------------------------------------------------------------------
# Fetcher with mock transport
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_fetcher_returns_status_and_text():
    transport = _make_mock_transport({
        "https://example.com/robots.txt": (200, "User-agent: *\nAllow: /"),
        "https://example.com/": (200, "hello"),
    })
    # Use minimal throttle config to avoid sleeps in tests
    cfg = {
        "default": {"rps": 100.0, "jitter": 0.0, "respect_robots": True, "user_agent": "test/1"},
        "overrides": {},
    }
    async with Fetcher(throttle_config=cfg, transport=transport) as fetcher:
        status, text = await fetcher.get("https://example.com/")
    assert status == 200
    assert text == "hello"


@pytest.mark.asyncio
async def test_fetcher_propagates_4xx():
    transport = _make_mock_transport({
        "https://example.com/robots.txt": (200, "User-agent: *\nAllow: /"),
        "https://example.com/missing": (404, "not found"),
    })
    cfg = {
        "default": {"rps": 100.0, "jitter": 0.0, "respect_robots": True, "user_agent": "test/1"},
        "overrides": {},
    }
    async with Fetcher(throttle_config=cfg, transport=transport) as fetcher:
        status, text = await fetcher.get("https://example.com/missing")
    assert status == 404


@pytest.mark.asyncio
async def test_fetcher_robots_blocked():
    transport = _make_mock_transport({
        "https://example.com/robots.txt": (200, "User-agent: *\nDisallow: /"),
        "https://example.com/docs": (200, "docs content"),
    })
    cfg = {
        "default": {"rps": 100.0, "jitter": 0.0, "respect_robots": True, "user_agent": "test/1"},
        "overrides": {},
    }
    async with Fetcher(throttle_config=cfg, transport=transport) as fetcher:
        status, text = await fetcher.get("https://example.com/docs")
    # robots.txt blocks /, so we expect the 403 sentinel
    assert status == 403
    assert "robots.txt" in text


@pytest.mark.asyncio
async def test_fetcher_robots_disabled():
    transport = _make_mock_transport({
        "https://example.com/robots.txt": (200, "User-agent: *\nDisallow: /"),
        "https://example.com/docs": (200, "docs content"),
    })
    cfg = {
        "default": {"rps": 100.0, "jitter": 0.0, "respect_robots": False, "user_agent": "test/1"},
        "overrides": {},
    }
    async with Fetcher(throttle_config=cfg, transport=transport) as fetcher:
        status, text = await fetcher.get("https://example.com/docs")
    assert status == 200


@pytest.mark.asyncio
async def test_fetcher_domain_override_rps():
    """Verify that per-domain rps override is used over default."""
    transport = _make_mock_transport({
        "https://slow.example.com/robots.txt": (404, ""),
        "https://slow.example.com/page": (200, "ok"),
    })
    cfg = {
        "default": {"rps": 1000.0, "jitter": 0.0, "respect_robots": False, "user_agent": "test/1"},
        "overrides": {
            "slow.example.com": {"rps": 0.5},
        },
    }
    async with Fetcher(throttle_config=cfg, transport=transport) as fetcher:
        # Override domain should use 0.5 rps (2s interval) not default 1000 rps
        assert fetcher._rps_for("slow.example.com") == 0.5
        assert fetcher._rps_for("other.example.com") == 1000.0
