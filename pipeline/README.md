# SaaS webhook catalog — extraction pipeline

Extraction framework for the `saas-webhook-catalog` dataset (AL-170 sub 1.4).
Sub 1.5 (tier-1 extractors) and sub 1.6 (tier-2 extractors) plug into this framework.

## Structure

```
pipeline/
├── pyproject.toml              deps + project metadata
├── throttle.yaml               per-domain RPS caps (audit obligations baked in)
├── src/catalog/
│   ├── schema.py               loads schema.json; exposes validate(row)
│   ├── fetcher.py              async httpx with throttle + robots.txt
│   ├── extractor.py            ExtractorBase ABC + registry
│   ├── output.py               parquet (primary) + JSONL (debug) writer
│   ├── cli.py                  python -m catalog ...
│   └── extractors/
│       ├── __init__.py         imports every extractor module (triggers registration)
│       └── example_stub.py    pattern stub; replace with real extractors in sub 1.5
└── tests/
    ├── conftest.py
    ├── test_schema.py
    ├── test_fetcher.py
    └── test_output.py
```

## Dependencies

- **httpx** - async HTTP fetching
- **jsonschema** - Draft 2020-12 row validation against `../schema.json`
- **pyarrow** - parquet output
- **beautifulsoup4 + lxml** - HTML parsing (used by sub 1.5 extractors)
- **pyyaml** - throttle config loading
- **pytest + pytest-asyncio** - tests (dev dep)

## Setup

```bash
# From this directory:
python -m venv .venv
.venv/Scripts/pip install -e ".[dev]"   # Windows
# or: .venv/bin/pip install -e ".[dev]"  # Linux/macOS
```

## How to run

```bash
# Run one vendor
python -m catalog run --vendor example

# Run all registered vendors
python -m catalog run --all

# List registered vendor slugs
python -m catalog list

# Validate an existing JSONL file
python -m catalog validate output/2026-05-13/example.jsonl

# Custom output directory
python -m catalog run --vendor example --output-dir /tmp/my-output
```

Output lands under `output/<YYYY-MM-DD>/` (one parquet + one JSONL per vendor per run).

## Throttle config (`throttle.yaml`)

Controls per-domain fetch rate. The `default` block applies to all domains not in
`overrides`. Three domains have hardcoded lower caps per the ToS audit (2026-05-13):

| domain | cap | reason |
|---|---|---|
| `developer.zendesk.com` | 1.0 req/s | ToS audit: throttle required |
| `developer.atlassian.com` | 1.0 req/s | ToS audit: throttle required |
| `learn.microsoft.com` | 0.5 req/s | ToS audit: respectful cadence required |

The `user_agent` field is sent on every request. `respect_robots: true` caches and
honours `robots.txt` per domain.

## Adding a real extractor (sub 1.5 / sub 1.6)

1. Create `src/catalog/extractors/<vendor_slug>.py`
2. Subclass `ExtractorBase`, set `slug` (must match `vendors.yaml`) and `docs_urls`
3. Implement `extract(self, fetcher) -> AsyncIterator[dict]` — yield dicts matching `schema.json`
4. Call `register(MyExtractor)` at module level
5. Add `from . import <vendor_slug>` to `src/catalog/extractors/__init__.py`

See `example_stub.py` for the full pattern.

Validation runs in the pipeline runner after `extract()` yields each row. Validation
errors are collected and reported at the end; a single bad row does not abort the run.

## Tests

```bash
pytest tests/
```

31 tests covering schema validation, throttle config loading, fetcher mocking, and
parquet/JSONL round-trips. No real network access — fetcher tests use `httpx.MockTransport`.

## Schema note

`src/catalog/schema.py` loads `../schema.json` (one level above `pipeline/`) at import
time using a relative path from `__file__`. Do not move `schema.json` without updating
the path in `schema.py`.
