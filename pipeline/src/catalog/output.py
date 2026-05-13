"""
output.py — writes rows to parquet (primary) and JSONL (debug/fallback).

Both files land under output/<YYYY-MM-DD>/ by default; the base path is
configurable via OutputWriter(base_dir=...).

Parquet is written via pyarrow; columns are derived from the rows themselves
(all keys present in any row). JSONL is one JSON object per line.
"""

import json
from datetime import date
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq


class OutputWriter:
    """
    Writes a batch of rows to parquet + JSONL under *base_dir*.

    Usage::

        writer = OutputWriter(vendor="example", base_dir=Path("output"))
        writer.write(rows)
        # -> output/2026-05-13/example.parquet
        # -> output/2026-05-13/example.jsonl
    """

    def __init__(
        self,
        vendor: str,
        base_dir: Path | None = None,
        run_date: date | None = None,
    ) -> None:
        self.vendor = vendor
        run_date = run_date or date.today()
        self.out_dir = (base_dir or Path("output")) / run_date.isoformat()
        self.out_dir.mkdir(parents=True, exist_ok=True)

    @property
    def parquet_path(self) -> Path:
        return self.out_dir / f"{self.vendor}.parquet"

    @property
    def jsonl_path(self) -> Path:
        return self.out_dir / f"{self.vendor}.jsonl"

    def write(self, rows: list[dict]) -> None:
        """Write *rows* to both parquet and JSONL."""
        if not rows:
            return
        self._write_jsonl(rows)
        self._write_parquet(rows)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _write_jsonl(self, rows: list[dict]) -> None:
        with self.jsonl_path.open("w", encoding="utf-8") as f:
            for row in rows:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")

    def _write_parquet(self, rows: list[dict]) -> None:
        # Collect all keys (union of all rows to handle sparse optional fields)
        all_keys: list[str] = list(
            {k for row in rows for k in row.keys()}
        )
        # Build column arrays; missing values become None
        arrays = {
            k: pa.array([_serialize_value(row.get(k)) for row in rows])
            for k in all_keys
        }
        table = pa.table(arrays)
        pq.write_table(table, self.parquet_path)


def _serialize_value(v):
    """Coerce complex values (dicts, lists) to JSON strings for parquet storage."""
    if v is None or isinstance(v, (bool, int, float, str)):
        return v
    return json.dumps(v, ensure_ascii=False)
