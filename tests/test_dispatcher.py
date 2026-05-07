"""单元测试：CLI 目标调度。"""
import logging
import time

from tests.conftest import base_config
from trace_pipeline.cli import dispatcher
from trace_pipeline.io.discovery import TraceFile
from trace_pipeline.models import RunResult


def test_batch_run_config_uses_outcrop_prefix():
    cfg = base_config(process_all=True, output_prefix="Custom")
    run_cfg = dispatcher._build_run_config(
        cfg, "in", "out", TraceFile(stem="O77_process", outcrop="O77")
    )

    assert run_cfg.output_prefix == "O77"


def test_single_run_config_honors_custom_output_prefix():
    cfg = base_config(process_all=False, output_prefix="Custom")
    run_cfg = dispatcher._build_run_config(
        cfg, "in", "out", TraceFile(stem="O76_process", outcrop="O76")
    )

    assert run_cfg.output_prefix == "Custom"


def test_single_run_config_keeps_default_outcrop_prefix():
    cfg = base_config(process_all=False)
    run_cfg = dispatcher._build_run_config(
        cfg, "in", "out", TraceFile(stem="O76_process", outcrop="O76")
    )

    assert run_cfg.output_prefix == "O76"


def test_parallel_results_keep_target_order(monkeypatch):
    def fake_run_pipeline(run_cfg):
        if run_cfg.table_stem == "slow_process":
            time.sleep(0.02)
        return RunResult.success(run_cfg.table_stem, trace_count=1)

    monkeypatch.setattr(dispatcher, "run_pipeline", fake_run_pipeline)
    targets = [
        TraceFile(stem="slow_process", outcrop="slow"),
        TraceFile(stem="fast_process", outcrop="fast"),
    ]

    results = dispatcher.execute_targets(
        targets,
        base_config(process_all=True),
        "input",
        "output",
        workers=2,
        logger=logging.getLogger("test"),
    )

    assert [r.table_stem for r in results] == ["slow_process", "fast_process"]
