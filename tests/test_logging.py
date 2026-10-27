import json
import logging

from app.logging_config import JSONFormatter


def make_record(**extra) -> logging.LogRecord:
    record = logging.LogRecord("app.api", logging.WARNING, __file__, 1, "request_finished", None, None)
    record.__dict__.update(extra)  # logger.info(..., extra={...}) ile aynı etki
    return record


def test_json_formatter_produces_one_json_line_with_extra_fields():
    line = JSONFormatter().format(make_record(endpoint="/ask", duration_ms=12.5))
    data = json.loads(line)  # Geçerli JSON olmalı
    assert "\n" not in line
    assert data["level"] == "WARNING" and data["logger"] == "app.api" and data["msg"] == "request_finished"
    assert data["endpoint"] == "/ask" and data["duration_ms"] == 12.5
    assert data["ts"].endswith("+00:00")  # UTC zaman damgası


def test_non_json_values_are_stringified():
    from datetime import date

    data = json.loads(JSONFormatter().format(make_record(day=date(2026, 1, 2))))
    assert data["day"] == "2026-01-02"
