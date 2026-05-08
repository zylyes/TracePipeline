"""单元测试：CLI 顶层入口。"""
import argparse
import importlib
import logging

import pytest

from trace_pipeline.cli.args import build_overrides
from trace_pipeline.config import DEFAULT_CONFIG
from trace_pipeline.io.discovery import TraceFile

main_module = importlib.import_module("trace_pipeline.cli.main")


class _NonTty:
    def isatty(self):
        return False


def test_build_overrides_includes_window_strategy():
    args = argparse.Namespace(
        input=None,
        output=None,
        single=False,
        rose_bin=None,
        rose_dpi=None,
        no_rose=False,
        window_strategy="tangent",
    )

    assert build_overrides(args) == {"window_strategy": "tangent"}


def test_interactive_requires_tty(monkeypatch, tmp_path):
    args = argparse.Namespace(
        config=None,
        list=False,
        dry_run=False,
        interactive=True,
        parallel=0,
    )

    called = {"decide": False, "execute": False}

    def fail_decide_targets(*args, **kwargs):
        called["decide"] = True
        raise AssertionError("decide_targets should not be called")

    def fail_execute_targets(*args, **kwargs):
        called["execute"] = True
        raise AssertionError("execute_targets should not be called")

    cfg = dict(DEFAULT_CONFIG)
    cfg.update({"input_dir": "input", "output_dir": "output"})

    monkeypatch.setattr(main_module, "parse_args", lambda: args)
    monkeypatch.setattr(main_module, "setup_logging", lambda: logging.getLogger("test"))
    monkeypatch.setattr(main_module, "load_config", lambda path: cfg)
    monkeypatch.setattr(main_module, "build_overrides", lambda args: {})

    monkeypatch.setattr(main_module, "resolve_config_base_dir", lambda path: tmp_path)
    monkeypatch.setattr(
        main_module,
        "resolve_io_paths",
        lambda input_dir, output_dir, base_dir=None, create_dirs=True: (
            str(tmp_path / "input"),
            str(tmp_path / "output"),
        ),
    )
    monkeypatch.setattr(
        main_module,
        "find_trace_tables",
        lambda input_dir: [TraceFile(stem="O76_process", outcrop="O76")],
    )
    monkeypatch.setattr(main_module, "decide_targets", fail_decide_targets)
    monkeypatch.setattr(main_module, "execute_targets", fail_execute_targets)
    monkeypatch.setattr(main_module.sys, "stdin", _NonTty())

    with pytest.raises(SystemExit) as excinfo:
        main_module.main()

    assert excinfo.value.code == 2
    assert called == {"decide": False, "execute": False}


def test_list_mode_prints_discovered_files(monkeypatch, tmp_path, capsys):
    args = argparse.Namespace(
        config=None,
        list=True,
        dry_run=False,
        interactive=False,
        parallel=0,
    )

    monkeypatch.setattr(main_module, "parse_args", lambda: args)
    monkeypatch.setattr(main_module, "setup_logging", lambda: logging.getLogger("test"))
    monkeypatch.setattr(main_module, "load_config", lambda path: dict(DEFAULT_CONFIG))
    monkeypatch.setattr(main_module, "build_overrides", lambda args: {})

    monkeypatch.setattr(main_module, "resolve_config_base_dir", lambda path: tmp_path)
    monkeypatch.setattr(
        main_module,
        "resolve_io_paths",
        lambda input_dir, output_dir, base_dir=None, create_dirs=True: (
            str(tmp_path),
            str(tmp_path),
        ),
    )
    monkeypatch.setattr(
        main_module,
        "find_trace_tables",
        lambda input_dir: [TraceFile(stem="O76_process", outcrop="O76")],
    )

    main_module.main()
    captured = capsys.readouterr().out

    assert "O76_process" in captured


def test_list_mode_shows_none_found(monkeypatch, tmp_path, capsys):
    args = argparse.Namespace(
        config=None,
        list=True,
        dry_run=False,
        interactive=False,
        parallel=0,
    )

    monkeypatch.setattr(main_module, "parse_args", lambda: args)
    monkeypatch.setattr(main_module, "setup_logging", lambda: logging.getLogger("test"))
    monkeypatch.setattr(main_module, "load_config", lambda path: dict(DEFAULT_CONFIG))
    monkeypatch.setattr(main_module, "build_overrides", lambda args: {})

    monkeypatch.setattr(main_module, "resolve_config_base_dir", lambda path: tmp_path)
    monkeypatch.setattr(
        main_module,
        "resolve_io_paths",
        lambda input_dir, output_dir, base_dir=None, create_dirs=True: (
            str(tmp_path),
            str(tmp_path),
        ),
    )
    monkeypatch.setattr(main_module, "find_trace_tables", lambda input_dir: [])

    main_module.main()
    captured = capsys.readouterr().out

    assert "未发现" in captured


def test_dry_run_mode_prints_targets_without_executing(monkeypatch, tmp_path, capsys):
    args = argparse.Namespace(
        config=None,
        list=False,
        dry_run=True,
        interactive=False,
        parallel=0,
    )

    called = {"execute": False}

    def fail_execute_targets(*args, **kwargs):
        called["execute"] = True
        raise AssertionError("execute_targets should not be called")

    cfg = dict(DEFAULT_CONFIG)
    cfg.update({"input_dir": "input", "output_dir": "output"})

    monkeypatch.setattr(main_module, "parse_args", lambda: args)
    monkeypatch.setattr(main_module, "setup_logging", lambda: logging.getLogger("test"))
    monkeypatch.setattr(main_module, "load_config", lambda path: cfg)
    monkeypatch.setattr(main_module, "build_overrides", lambda args: {})

    monkeypatch.setattr(main_module, "resolve_config_base_dir", lambda path: tmp_path)
    monkeypatch.setattr(
        main_module,
        "resolve_io_paths",
        lambda input_dir, output_dir, base_dir=None, create_dirs=True: (
            str(tmp_path / "input"),
            str(tmp_path / "output"),
        ),
    )
    monkeypatch.setattr(
        main_module,
        "find_trace_tables",
        lambda input_dir: [TraceFile(stem="O76_process", outcrop="O76")],
    )
    monkeypatch.setattr(main_module, "execute_targets", fail_execute_targets)

    main_module.main()
    captured = capsys.readouterr().out

    assert "试运行" in captured
    assert "O76_process" in captured
    assert "未执行任何操作" in captured
    assert called == {"execute": False}
