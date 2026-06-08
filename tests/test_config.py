from __future__ import annotations

import json

from trace_pipeline.config import load_config


def test_load_config_resolves_relative_paths_from_config_file(tmp_path) -> None:
    config_dir = tmp_path / "case"
    config_dir.mkdir()
    config_path = config_dir / "config.json"
    config_path.write_text(
        json.dumps({"input_dir": "input", "output_dir": "output", "outcrop": "O76"}),
        encoding="utf-8",
    )

    cfg = load_config(config_path)

    assert cfg["input_dir"] == str((config_dir / "input").resolve())
    assert cfg["output_dir"] == str((config_dir / "output").resolve())
