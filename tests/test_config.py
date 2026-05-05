"""单元测试：配置加载、校验与路径解析。"""
from pathlib import Path

import pytest

from trace_pipeline.config import load_config, resolve_io_paths, validate_config


def test_explicit_missing_config_raises(tmp_path):
    missing = tmp_path / "missing.json"
    with pytest.raises(FileNotFoundError, match="指定的配置文件不存在"):
        load_config(missing)


def test_validate_config_coerces_bool_and_numbers():
    cfg = validate_config({
        "input_dir": " input ",
        "output_dir": " output ",
        "table_stem": " O76_process ",
        "outcrop": " O76 ",
        "process_all": "false",
        "export_rose_plot": "0",
        "rose_bin_width": "15",
        "rose_dpi": "600",
        "trace_dpi": "300",
        "rotated_trace_dpi": "900",
    })

    assert cfg["input_dir"] == "input"
    assert cfg["output_dir"] == "output"
    assert cfg["process_all"] is False
    assert cfg["export_rose_plot"] is False
    assert cfg["rose_bin_width"] == 15.0
    assert cfg["rose_dpi"] == 600


def test_validate_config_rejects_ambiguous_bool():
    with pytest.raises(ValueError, match="process_all 必须为布尔值"):
        validate_config({"process_all": "maybe"})


def test_resolve_io_paths_can_avoid_creating_dirs(tmp_path):
    input_dir, output_dir = resolve_io_paths(
        "not-yet-input",
        "not-yet-output",
        base_dir=tmp_path,
        create_dirs=False,
    )

    assert input_dir == str((tmp_path / "not-yet-input").resolve())
    assert output_dir == str((tmp_path / "not-yet-output").resolve())
    assert not Path(input_dir).exists()
    assert not Path(output_dir).exists()


def test_resolve_io_paths_default_creates_dirs(tmp_path):
    input_dir, output_dir = resolve_io_paths("input", "output", base_dir=tmp_path)

    assert Path(input_dir).is_dir()
    assert Path(output_dir).is_dir()
