"""
fetcher.py — async httpx fetcher with per-domain throttle and robots.txt support.

Throttle config is loaded from throttle.yaml (located next to this package).
Per-domain state (semaphore + last-fetch timestamp) is held in instance attrs
so multiple Fetcher instances are independent; a single Fetcher is shared
across all extractors in one pipeline run.
"""

import asyncio
import random
import time
from pathlib import Path
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import httpx
import yaml

_THROTTLE_PATH = Path(__file__).parent.parent.parent / "throttle.yaml"


def _load_throttle_config(path: Path = _THROTTLE_PATH) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"throttle.yaml not found at {path}")
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


class Fetcher:
    """
    Async HTTP fetcher.

    Usage::

        async with Fetcher() as fetcher:
            status, text = await fetcher.get("https://example.com/docs")

    The Fetcher respects per-domain RPS caps from throttle.yaml, adds random
    jitter, honours robots.txt (cached per domain), and sends the configured
    User-Agent on every request.
    """

    def __init__(
        self,
        throttle_config: dict | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        cfg = throttle_config or _load_throttle_config()
        self._default = cfg.get("default", {})
        self._overrides: dict[str, dict] = cfg.get("overrides", {})

        self._rps_default: float = float(self._default.get("rps", 1.0))
        self._jitter_default: float = float(self._default.get("jitter", 0.1))
        self._respect_robots: bool = bool(self._default.get("respect_robots", True))
        self._user_agent: str = self._default.get(
            "user_agent", "automatelab-webhook-catalog/0.1"
        )

        # Per-domain state
        self._semaphores: dict[str, asyncio.Semaphore] = {}
        self._last_fetch: dict[str, float] = {}
        self._robots_cache: dict[str, RobotFileParser | None] = {}

        self._transport = transport
        self._client: httpx.AsyncClient | None = None

    # ------------------------------------------------------------------
    # Context manager
    # ------------------------------------------------------------------

    async def __aenter__(self) -> "Fetcher":
        kwargs: dict = {"headers": {"User-Agent": self._user_agent}, "follow_redirects": True}
        if self._transport is not None:
            kwargs["transport"] = self._transport
        self._client = httpx.AsyncClient(**kwargs)
        return self

    async def __aexit__(self, *_) -> None:
        if self._client:
            await self._client.aclose()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def get(self, url: str) -> tuple[int, str]:
        """
        Fetch *url* with throttle + robots.txt enforcement.

        Returns ``(status_code, response_text)``.
        4xx/5xx are returned to the caller (not raised) so extractors can
        decide how to handle them.
        """
        if self._client is None:
            raise RuntimeError("Fetcher must be used as an async context manager")

        domain = self._domain(url)
        await self._throttle(domain)

        if self._respect_robots and not await self._robots_allowed(domain, url):
            return (403, f"blocked by robots.txt: {url}")

        response = await self._client.get(url)
        return (response.status_code, response.text)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    @staticmethod
    def _domain(url: str) -> str:
        return urlparse(url).netloc.lower()

    def _rps_for(self, domain: str) -> float:
        override = self._overrides.get(domain, {})
        return float(override.get("rps", self._rps_default))

    def _semaphore_for(self, domain: str) -> asyncio.Semaphore:
        if domain not in self._semaphores:
            self._semaphores[domain] = asyncio.Semaphore(1)
        return self._semaphores[domain]

    async def _throttle(self, domain: str) -> None:
        sem = self._semaphore_for(domain)
        async with sem:
            rps = self._rps_for(domain)
            min_interval = 1.0 / rps
            elapsed = time.monotonic() - self._last_fetch.get(domain, 0.0)
            wait = max(0.0, min_interval - elapsed)
            wait += random.uniform(0, self._jitter_default)
            if wait > 0:
                await asyncio.sleep(wait)
            self._last_fetch[domain] = time.monotonic()

    async def _robots_allowed(self, domain: str, url: str) -> bool:
        if domain not in self._robots_cache:
            self._robots_cache[domain] = await self._fetch_robots(domain)
        rp = self._robots_cache[domain]
        if rp is None:
            return True
        return rp.can_fetch(self._user_agent, url)

    async def _fetch_robots(self, domain: str) -> RobotFileParser | None:
        robots_url = f"https://{domain}/robots.txt"
        try:
            response = await self._client.get(robots_url)  # type: ignore[union-attr]
            if response.status_code == 200:
                rp = RobotFileParser()
                rp.parse(response.text.splitlines())
                return rp
        except Exception:
            pass
        return None
