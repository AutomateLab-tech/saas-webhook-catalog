"""
test_output.py

1. OutputWriter writes parquet and JSONL
2. Round-trip: read back JSONL and verify contents match
3. Round-trip: read back parquet and verify row count and a string field
4. Handles rows with optional fields absent (sparse rows)
"""

import json
import tempfile
from pathlib import Path

import pyarrow.parquet as pq
import pytest

from catalog.output import OutputWriter
from datetime import date


SAMPLE_ROWS = [
    {
        "vendor": "test-vendor",
        "vendor_display_name": "Test Vendor",
        "category": "dev-tools",
        "event_name": "resource.created",
        "trigger_description": "A resource was created.",
        "payload_schema": {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "type": "object",
        },
        "auth_method": "hmac-sha256",
        "docs_url": "https://example.com/webhooks",
        "last_introspected_at": "2026-05-13T00:00:00Z",
        "source_extractor_version": "v0.1",
        "extraction_method": "manual-html",
    },
    {
        "vendor": "test-vendor",
        "vendor_display_name": "Test Vendor",
        "category": "dev-tools",
        "event_name": "resource.deleted",
        "trigger_description": "A resource was deleted.",
        "payload_schema": {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "type": "object",
        },
        "auth_method": "hmac-sha256",
        "docs_url": "https://example.com/webhooks",
        "last_introspected_at": "2026-05-13T00:00:00Z",
        "source_extractor_version": "v0.1",
        "extraction_method": "manual-html",
        "notes": "optional field present on second row only",
    },
]


@pytest.fixture
def tmp_writer(tmp_path):
    return OutputWriter(
        vendor="test-vendor",
        base_dir=tmp_path,
        run_date=date(2026, 5, 13),
    )


def test_output_paths(tmp_writer, tmp_path):
    assert tmp_writer.parquet_path == tmp_path / "2026-05-13" / "test-vendor.parquet"
    assert tmp_writer.jsonl_path == tmp_path / "2026-05-13" / "test-vendor.jsonl"


def test_write_creates_files(tmp_writer):
    tmp_writer.write(SAMPLE_ROWS)
    assert tmp_writer.parquet_path.exists()
    assert tmp_writer.jsonl_path.exists()


def test_jsonl_round_trip(tmp_writer):
    tmp_writer.write(SAMPLE_ROWS)
    lines = tmp_writer.jsonl_path.read_text(encoding="utf-8").strip().split("\n")
    assert len(lines) == 2
    row0 = json.loads(lines[0])
    assert row0["event_name"] == "resource.created"
    row1 = json.loads(lines[1])
    assert row1["event_name"] == "resource.deleted"
    assert row1["notes"] == "optional field present on second row only"


def test_parquet_row_count(tmp_writer):
    tmp_writer.write(SAMPLE_ROWS)
    table = pq.read_table(tmp_writer.parquet_path)
    assert table.num_rows == 2


def test_parquet_vendor_column(tmp_writer):
    tmp_writer.write(SAMPLE_ROWS)
    table = pq.read_table(tmp_writer.parquet_path)
    vendors = table.column("vendor").to_pylist()
    assert vendors == ["test-vendor", "test-vendor"]


def test_parquet_sparse_optional_field(tmp_writer):
    """Rows missing optional fields should produce None in parquet column."""
    tmp_writer.write(SAMPLE_ROWS)
    table = pq.read_table(tmp_writer.parquet_path)
    notes = table.column("notes").to_pylist()
    # Row 0 has no 'notes', row 1 has notes
    assert notes[0] is None
    assert notes[1] == "optional field present on second row only"


def test_write_empty_rows_is_noop(tmp_writer):
    tmp_writer.write([])
    assert not tmp_writer.parquet_path.exists()
    assert not tmp_writer.jsonl_path.exists()


def test_parquet_dict_field_serialized(tmp_writer):
    """Dict fields (payload_schema) are JSON-serialized in parquet."""
    tmp_writer.write(SAMPLE_ROWS)
    table = pq.read_table(tmp_writer.parquet_path)
    schemas = table.column("payload_schema").to_pylist()
    # Should be a JSON string in parquet
    assert isinstance(schemas[0], str)
    parsed = json.loads(schemas[0])
    assert parsed["$schema"] == "https://json-schema.org/draft/2020-12/schema"
