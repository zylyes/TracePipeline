from __future__ import annotations

import logging

from trace_pipeline.logging.core import DailyRotatingJsonHandler, setup_logging


def test_setup_logging_is_idempotent(tmp_path) -> None:
    log_dir = tmp_path / "logs"

    logger = setup_logging(log_dir)
    same_logger = setup_logging(log_dir)

    assert same_logger is logger
    backend_logger = logging.getLogger("backend")
    assert any(isinstance(h, DailyRotatingJsonHandler) for h in backend_logger.handlers)
