from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

from backend.services import pipeline_service as pipeline_module
from backend.services.pipeline_service import PipelineService
from trace_pipeline.models import RunResult


class _ThreadPoolExecutor(ThreadPoolExecutor):
    """适配 ProcessPoolExecutor 接口，忽略 mp_context 参数。"""
    def __init__(self, max_workers=None, mp_context=None, **kwargs):
        super().__init__(max_workers=max_workers, **kwargs)


def test_run_rejects_invalid_target(tmp_path) -> None:
    service = PipelineService()

    result = service.run(["../secret"], {"input_dir": str(tmp_path), "output_dir": str(tmp_path)})

    assert result["status"] == "error"
    assert "非法的露头名" in result["message"]
    assert not service.is_running()


def test_background_result_uses_frontend_image_fields(tmp_path, monkeypatch) -> None:
    service = PipelineService()

    def fake_run_pipeline(_cfg):
        return RunResult.success(
            table_stem="O76_process",
            trace_count=1,
            raw_plot_path="raw.png",
            rotated_plot_path="rotated.png",
            rose_plot_path="rose.png",
        )

    monkeypatch.setattr(pipeline_module, "ProcessPoolExecutor", _ThreadPoolExecutor)
    monkeypatch.setattr(pipeline_module, "run_pipeline", fake_run_pipeline)

    service._run_background(["O76"], {"input_dir": str(tmp_path), "output_dir": str(tmp_path)})

    events = []
    while True:
        event = service.poll_progress()
        if event is None:
            break
        events.append(event)

    file_complete = next(event for event in events if event["type"] == "file_complete")
    result = file_complete["result"]
    assert result["raw_plot"] == "raw.png"
    assert result["rotated_plot"] == "rotated.png"
    assert result["rose_plot"] == "rose.png"
    assert "raw_plot_path" not in result


def test_workers_capped_by_cpu_count(tmp_path, monkeypatch) -> None:
    """parallel_workers > 1 时提交给 executor 的 workers 不应超过 cpu_count。"""
    monkeypatch.setattr(pipeline_module.mp, "cpu_count", lambda: 4)
    service = PipelineService()
    captured = {}

    class CapturingExecutor(_ThreadPoolExecutor):
        def __init__(self, max_workers=None, mp_context=None, **kwargs):
            captured["max_workers"] = max_workers
            super().__init__(max_workers=max_workers, mp_context=mp_context, **kwargs)

    def fake_run_pipeline(_cfg):
        return RunResult.success(table_stem="O76_process", trace_count=1)

    monkeypatch.setattr(pipeline_module, "ProcessPoolExecutor", CapturingExecutor)
    monkeypatch.setattr(pipeline_module, "run_pipeline", fake_run_pipeline)

    service._run_background(
        [f"O{i}" for i in range(10)],
        {
            "input_dir": str(tmp_path / "input"),
            "output_dir": str(tmp_path / "output"),
            "parallel_workers": 8,
        },
    )

    assert captured["max_workers"] == 4


def test_workers_auto_also_capped_by_cpu_count(tmp_path, monkeypatch) -> None:
    """parallel_workers=0 时提交给 executor 的 workers 不应超过 cpu_count。"""
    monkeypatch.setattr(pipeline_module.mp, "cpu_count", lambda: 2)
    service = PipelineService()
    captured = {}

    class CapturingExecutor(_ThreadPoolExecutor):
        def __init__(self, max_workers=None, mp_context=None, **kwargs):
            captured["max_workers"] = max_workers
            super().__init__(max_workers=max_workers, mp_context=mp_context, **kwargs)

    def fake_run_pipeline(_cfg):
        return RunResult.success(table_stem="O76_process", trace_count=1)

    monkeypatch.setattr(pipeline_module, "ProcessPoolExecutor", CapturingExecutor)
    monkeypatch.setattr(pipeline_module, "run_pipeline", fake_run_pipeline)

    service._run_background(
        [f"O{i}" for i in range(10)],
        {
            "input_dir": str(tmp_path / "input"),
            "output_dir": str(tmp_path / "output"),
            "parallel_workers": 0,
        },
    )

    assert captured["max_workers"] == 2


def test_workers_fall_back_when_cpu_count_unavailable(tmp_path, monkeypatch) -> None:
    """无法识别 CPU 核心数时应保守退回 1 个 worker。"""
    monkeypatch.setattr(pipeline_module.mp, "cpu_count", lambda: None)
    service = PipelineService()
    captured = {}

    class CapturingExecutor(_ThreadPoolExecutor):
        def __init__(self, max_workers=None, mp_context=None, **kwargs):
            captured["max_workers"] = max_workers
            super().__init__(max_workers=max_workers, mp_context=mp_context, **kwargs)

    def fake_run_pipeline(_cfg):
        return RunResult.success(table_stem="O76_process", trace_count=1)

    monkeypatch.setattr(pipeline_module, "ProcessPoolExecutor", CapturingExecutor)
    monkeypatch.setattr(pipeline_module, "run_pipeline", fake_run_pipeline)

    service._run_background(
        ["O76", "O77"],
        {
            "input_dir": str(tmp_path / "input"),
            "output_dir": str(tmp_path / "output"),
            "parallel_workers": 0,
        },
    )

    assert captured["max_workers"] == 1
