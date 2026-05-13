"""
schema.py — loads schema.json once and exposes a validate() function.

Uses jsonschema.Draft202012Validator as required by the spec. The schema file
is located relative to this module's package root; if it cannot be found or
parsed, the import raises immediately so misconfiguration is caught early.
"""

import json
from pathlib import Path

import jsonschema
from jsonschema import Draft202012Validator, ValidationError  # noqa: F401 (re-exported)

# Walk up from src/catalog/ -> src/ -> pipeline/ -> v0/ -> schema.json
_SCHEMA_PATH = Path(__file__).parent.parent.parent.parent / "schema.json"

if not _SCHEMA_PATH.exists():
    raise FileNotFoundError(
        f"schema.json not found at {_SCHEMA_PATH}. "
        "Run the pipeline from within the v0/ directory tree."
    )

with _SCHEMA_PATH.open(encoding="utf-8") as _f:
    _SCHEMA = json.load(_f)

_VALIDATOR = Draft202012Validator(_SCHEMA)


def validate(row: dict) -> list[ValidationError]:
    """
    Validate a single row dict against schema.json.

    Returns an empty list when the row is valid; a list of
    jsonschema.ValidationError objects otherwise (one per violation).
    """
    return sorted(_VALIDATOR.iter_errors(row), key=lambda e: str(e.json_path))
