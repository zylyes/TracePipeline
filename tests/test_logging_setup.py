"""单元测试：日志初始化。"""
import logging

from trace_pipeline.cli.logging_setup import setup_logging


def test_setup_logging_is_idempotent(tmp_path):
    pkg_logger = logging.getLogger("trace_pipeline")
    old_handlers = list(pkg_logger.handlers)
    old_level = pkg_logger.level
    old_propagate = pkg_logger.propagate

    for handler in list(pkg_logger.handlers):
        pkg_logger.removeHandler(handler)

    try:
        setup_logging(log_dir=str(tmp_path))
        setup_logging(log_dir=str(tmp_path))

        managed = [
            h for h in pkg_logger.handlers
            if getattr(h, "_trace_pipeline_managed", False)
        ]
        stream_handlers = [
            h for h in managed
            if isinstance(h, logging.StreamHandler)
            and not isinstance(h, logging.FileHandler)
        ]
        file_handlers = [h for h in managed if isinstance(h, logging.FileHandler)]

        assert len(stream_handlers) == 1
        assert len(file_handlers) == 1
        assert len(list(tmp_path.glob("pipeline_*.log"))) == 1
        assert pkg_logger.propagate is False
    finally:
        for handler in list(pkg_logger.handlers):
            pkg_logger.removeHandler(handler)
            handler.close()
        pkg_logger.handlers[:] = old_handlers
        pkg_logger.setLevel(old_level)
        pkg_logger.propagate = old_propagate
