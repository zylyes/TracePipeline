from __future__ import annotations

from trace_pipeline.models import RunConfig


def test_node_label_mode_from_mapping() -> None:
    base = {
        "input_dir": "./data",
        "output_dir": "./results",
        "output_prefix": "Test",
        "table_stem": "O77_process",
        "outcrop": "O77",
    }

    assert RunConfig.from_mapping({**base, "node_label_mode": "id"}).node_label_mode == "id"
    assert (
        RunConfig.from_mapping({**base, "style": {"node_label_mode": "none"}}).node_label_mode
        == "none"
    )
