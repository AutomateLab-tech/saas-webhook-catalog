"""
cli.py — command-line entry point for the catalog pipeline.

Usage:
    python -m catalog run --vendor <slug>
    python -m catalog run --all
    python -m catalog list
    python -m catalog validate <jsonl_file>
"""

import argparse
import asyncio
import json
import sys
from datetime import date
from pathlib import Path

# Import extractors subpackage to trigger registry population
import catalog.extractors  # noqa: F401

from catalog.extractor import get_extractor, list_slugs
from catalog.fetcher import Fetcher
from catalog.output import OutputWriter
from catalog.schema import validate


# ---------------------------------------------------------------------------
# Sub-commands
# ---------------------------------------------------------------------------


async def _run_vendor(slug: str, output_dir: Path) -> int:
    """Run a single extractor. Returns exit code."""
    try:
        extractor = get_extractor(slug)
    except KeyError:
        print(f"error: unknown vendor slug '{slug}'. Run `python -m catalog list`.", file=sys.stderr)
        return 1

    rows: list[dict] = []
    errors: list[tuple[int, list]] = []

    async with Fetcher() as fetcher:
        async for row in extractor.extract(fetcher):
            errs = validate(row)
            if errs:
                errors.append((len(rows), [str(e) for e in errs]))
            rows.append(row)

    writer = OutputWriter(vendor=slug, base_dir=output_dir)
    writer.write(rows)

    print(f"wrote {len(rows)} row(s) to {writer.parquet_path}")
    print(f"       JSONL debug: {writer.jsonl_path}")

    if errors:
        print(f"\n{len(errors)} row(s) had validation errors:", file=sys.stderr)
        for idx, msgs in errors:
            for msg in msgs:
                print(f"  row {idx}: {msg}", file=sys.stderr)
        return 2

    return 0


async def _run_all(output_dir: Path) -> int:
    slugs = list_slugs()
    if not slugs:
        print("no extractors registered", file=sys.stderr)
        return 1

    exit_code = 0
    for slug in slugs:
        code = await _run_vendor(slug, output_dir)
        if code != 0:
            exit_code = code
    return exit_code


def _list_command() -> None:
    slugs = list_slugs()
    if slugs:
        for slug in slugs:
            print(slug)
    else:
        print("(no extractors registered)")


def _validate_command(jsonl_file: str) -> int:
    path = Path(jsonl_file)
    if not path.exists():
        print(f"error: file not found: {jsonl_file}", file=sys.stderr)
        return 1

    total = 0
    bad = 0
    with path.open(encoding="utf-8") as f:
        for i, line in enumerate(f):
            line = line.strip()
            if not line:
                continue
            total += 1
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                print(f"row {i}: JSON parse error: {exc}", file=sys.stderr)
                bad += 1
                continue
            errs = validate(row)
            if errs:
                bad += 1
                for err in errs:
                    print(f"row {i}: [{err.json_path}] {err.message}", file=sys.stderr)

    print(f"validated {total} rows — {bad} invalid")
    return 0 if bad == 0 else 2


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="catalog")
    sub = parser.add_subparsers(dest="command")

    run_p = sub.add_parser("run", help="Run extractor(s)")
    run_group = run_p.add_mutually_exclusive_group(required=True)
    run_group.add_argument("--vendor", metavar="SLUG", help="Run one extractor by slug")
    run_group.add_argument("--all", action="store_true", help="Run all registered extractors")
    run_p.add_argument(
        "--output-dir",
        metavar="DIR",
        default="output",
        help="Base output directory (default: output/)",
    )

    sub.add_parser("list", help="List registered extractor slugs")

    val_p = sub.add_parser("validate", help="Validate an existing JSONL file against schema.json")
    val_p.add_argument("jsonl_file", metavar="FILE")

    args = parser.parse_args(argv)

    if args.command == "run":
        output_dir = Path(args.output_dir)
        if args.all:
            return asyncio.run(_run_all(output_dir))
        return asyncio.run(_run_vendor(args.vendor, output_dir))

    if args.command == "list":
        _list_command()
        return 0

    if args.command == "validate":
        return _validate_command(args.jsonl_file)

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
