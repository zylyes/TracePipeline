from __future__ import annotations

from backend.services import pipeline_service as pipeline_module
from backend.services.pipeline_service import PipelineService
from trace_pipeline.models import RunResult


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
