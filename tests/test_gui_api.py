from __future__ import annotations

import sys
from types import SimpleNamespace

sys.modules.setdefault(
    "webview",
    SimpleNamespace(FileDialog=SimpleNamespace(SAVE="save", FOLDER="folder")),
)

import pytest
from backend.gui_api import GuiApi, _RUN_OVERRIDE_KEYS


# ── _RUN_OVERRIDE_KEYS 白名单验证 ──────────────────────────────────


class TestRunOverrideKeys:
    def test_excludes_path_fields(self) -> None:
        assert "input_dir" not in _RUN_OVERRIDE_KEYS
        assert "output_dir" not in _RUN_OVERRIDE_KEYS
        assert "table_stem" not in _RUN_OVERRIDE_KEYS
        assert "outcrop" not in _RUN_OVERRIDE_KEYS
        assert "output_prefix" not in _RUN_OVERRIDE_KEYS

    def test_includes_processing_keys(self) -> None:
        assert "process_all" in _RUN_OVERRIDE_KEYS
        assert "window_strategy" in _RUN_OVERRIDE_KEYS
        assert "enable_node_recognition" in _RUN_OVERRIDE_KEYS

    def test_includes_style_and_parallel_workers(self) -> None:
        assert "style" in _RUN_OVERRIDE_KEYS
        assert "parallel_workers" in _RUN_OVERRIDE_KEYS


# ── run_pipeline 前端覆盖白名单行为 ────────────────────────────────


class TestRunPipelineOverride:
    """验证 run_pipeline 不允许前端覆盖 input_dir/output_dir 等路径字段，
    但允许 style/parallel_workers 覆盖。"""

    def test_prevents_input_dir_override(self, monkeypatch) -> None:
        """前端传入 input_dir 不应覆盖磁盘配置中的 input_dir。"""
        api = object.__new__(GuiApi)

        original_input_dir = "/safe/input"
        disk_cfg = {
            "input_dir": original_input_dir,
            "output_dir": "/safe/output",
            "style": {},
            "parallel_workers": 2,
            "process_all": True,
        }

        # 模拟 ConfigService
        class FakeConfig:
            def reload(self):
                pass
            def get(self):
                return dict(disk_cfg)
            def set(self, cfg):
                # 验证 input_dir 没有被前端覆盖
                assert cfg["input_dir"] == original_input_dir, \
                    "input_dir 不应被前端覆盖"
                # 验证 style 可以被覆盖
                assert cfg.get("style") == {"font_size": 14}, \
                    "style 应允许被覆盖"
                # 验证 parallel_workers 可以被覆盖
                assert cfg.get("parallel_workers") == 4, \
                    "parallel_workers 应允许被覆盖"
                return cfg

        api._config = FakeConfig()
        api._audit = SimpleNamespace(log=lambda *a, **kw: None)
        api._file = SimpleNamespace(invalidate_cache=lambda: None)
        api._stats = SimpleNamespace(invalidate_cache=lambda: None)
        api._pipeline = SimpleNamespace(run=lambda *a, **kw: {"status": "started"})
        api._sync_services_from_config = lambda *a, **kw: None

        frontend_config = {
            "input_dir": "/evil/path",
            "output_dir": "/evil/output",
            "style": {"font_size": 14},
            "parallel_workers": 4,
            "process_all": True,
        }
        result = api.run_pipeline(["O76"], frontend_config)
        assert result["status"] == "started"

    def test_prevents_output_dir_override(self, monkeypatch) -> None:
        """前端传入 output_dir 不应覆盖磁盘配置中的 output_dir。"""
        api = object.__new__(GuiApi)

        disk_cfg = {
            "input_dir": "/safe/input",
            "output_dir": "/safe/output",
            "style": {},
            "parallel_workers": 2,
        }

        captured = {}

        class FakeConfig:
            def reload(self):
                pass
            def get(self):
                return dict(disk_cfg)
            def set(self, cfg):
                captured["output_dir"] = cfg.get("output_dir")
                captured["input_dir"] = cfg.get("input_dir")
                return cfg

        api._config = FakeConfig()
        api._audit = SimpleNamespace(log=lambda *a, **kw: None)
        api._file = SimpleNamespace(invalidate_cache=lambda: None)
        api._stats = SimpleNamespace(invalidate_cache=lambda: None)
        api._pipeline = SimpleNamespace(run=lambda *a, **kw: {"status": "started"})
        api._sync_services_from_config = lambda *a, **kw: None

        frontend_config = {
            "input_dir": "/malicious/input",
            "output_dir": "/malicious/output",
            "style": {"font_size": 12},
        }
        api.run_pipeline(["O76"], frontend_config)
        assert captured["input_dir"] == "/safe/input"
        assert captured["output_dir"] == "/safe/output"


# ── get_logs / get_audit_log 参数合规 ─────────────────────────────


class TestGetLogsClamp:
    def test_clamps_tail_above_2000(self) -> None:
        api = object.__new__(GuiApi)
        captured = {}

        class FakeLog:
            def get_logs(self, tail, level):
                captured["tail"] = tail
                return []
        api._log = FakeLog()

        api.get_logs(tail=9999)
        assert captured["tail"] == 2000

    def test_clamps_tail_below_1(self) -> None:
        api = object.__new__(GuiApi)
        captured = {}

        class FakeLog:
            def get_logs(self, tail, level):
                captured["tail"] = tail
                return []
        api._log = FakeLog()

        api.get_logs(tail=0)
        assert captured["tail"] == 1

    def test_clamps_tail_negative(self) -> None:
        api = object.__new__(GuiApi)
        captured = {}

        class FakeLog:
            def get_logs(self, tail, level):
                captured["tail"] = tail
                return []
        api._log = FakeLog()

        api.get_logs(tail=-5)
        assert captured["tail"] == 1

    def test_passes_valid_tail_through(self) -> None:
        api = object.__new__(GuiApi)
        captured = {}

        class FakeLog:
            def get_logs(self, tail, level):
                captured["tail"] = tail
                return []
        api._log = FakeLog()

        api.get_logs(tail=150)
        assert captured["tail"] == 150

    def test_fallback_on_invalid_type(self) -> None:
        api = object.__new__(GuiApi)
        captured = {}

        class FakeLog:
            def get_logs(self, tail, level):
                captured["tail"] = tail
                return []
        api._log = FakeLog()

        api.get_logs(tail="abc")
        assert 1 <= captured["tail"] <= 2000


class TestGetAuditLogClamp:
    def test_clamps_limit_above_500(self) -> None:
        api = object.__new__(GuiApi)
        captured = {}

        class FakeAudit:
            def get(self, limit):
                captured["limit"] = limit
                return []
        api._audit = FakeAudit()

        api.get_audit_log(limit=9999)
        assert captured["limit"] == 500

    def test_clamps_limit_below_1(self) -> None:
        api = object.__new__(GuiApi)
        captured = {}

        class FakeAudit:
            def get(self, limit):
                captured["limit"] = limit
                return []
        api._audit = FakeAudit()

        api.get_audit_log(limit=0)
        assert captured["limit"] == 1

    def test_clamps_limit_negative(self) -> None:
        api = object.__new__(GuiApi)
        captured = {}

        class FakeAudit:
            def get(self, limit):
                captured["limit"] = limit
                return []
        api._audit = FakeAudit()

        api.get_audit_log(limit=-10)
        assert captured["limit"] == 1

    def test_passes_valid_limit_through(self) -> None:
        api = object.__new__(GuiApi)
        captured = {}

        class FakeAudit:
            def get(self, limit):
                captured["limit"] = limit
                return []
        api._audit = FakeAudit()

        api.get_audit_log(limit=100)
        assert captured["limit"] == 100

    def test_fallback_on_invalid_type(self) -> None:
        api = object.__new__(GuiApi)
        captured = {}

        class FakeAudit:
            def get(self, limit):
                captured["limit"] = limit
                return []
        api._audit = FakeAudit()

        api.get_audit_log(limit="xyz")
        assert 1 <= captured["limit"] <= 500
