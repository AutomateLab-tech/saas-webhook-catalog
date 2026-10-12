import json
from catalog.output import OutputWriter


def test_static_rows_do_not_invent_source_check_dates(tmp_path):
    rows = [
        {"vendor": "gusto", "event_name": "employee.created", "last_introspected_at": "2026-10-12T00:00:00Z", "extraction_method": "llm-assisted"},
        {"vendor": "zendesk", "event_name": "ticket.created", "last_introspected_at": "2026-10-12T00:00:00Z", "extraction_method": "manual-html"},
    ]
    writer = OutputWriter("fixture", base_dir=tmp_path)
    writer.write(rows)
    actual = [json.loads(line) for line in writer.jsonl_path.read_text().splitlines()]
    assert all(row["source_checked_at"] is None for row in actual)
    assert all(row["last_introspected_at"] == "2026-10-12T00:00:00Z" for row in actual)


def test_explicit_source_check_is_preserved(tmp_path):
    checked = "2026-09-14T12:00:00Z"
    writer = OutputWriter("fixture", base_dir=tmp_path)
    writer.write([{"vendor": "fixture", "event_name": "created", "source_checked_at": checked}])
    actual = json.loads(writer.jsonl_path.read_text())
    assert actual["source_checked_at"] == checked
