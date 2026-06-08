from __future__ import annotations

import json
import logging

from trace_pipeline.logging.core import DailyRotatingJsonHandler, JsonFormatter, setup_logging


def test_setup_logging_is_idempotent(tmp_path) -> None:
    log_dir = tmp_path / "logs"

    logger = setup_logging(log_dir)
    same_logger = setup_logging(log_dir)

    assert same_logger is logger
    backend_logger = logging.getLogger("backend")
    assert any(isinstance(h, DailyRotatingJsonHandler) for h in backend_logger.handlers)


def test_json_formatter_replaces_non_finite_numbers() -> None:
    formatter = JsonFormatter()
    record = logging.LogRecord("test", logging.INFO, __file__, 1, "message", (), None)
    record.metric = float("nan")
    record.details = {"positive_inf": float("inf"), "items": [1.0, float("-inf")]}

    payload = json.loads(formatter.format(record))

    assert payload["extra"]["metric"] is None
    assert payload["extra"]["details"] == {"positive_inf": None, "items": [1.0, None]}
