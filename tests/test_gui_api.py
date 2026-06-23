from __future__ import annotations

# 该测试必须先 stub webview，再导入 backend.gui_api。
# ruff: noqa: E402,I001

import sys
from types import SimpleNamespace

sys.modules.setdefault(
    "webview",
    SimpleNamespace(FileDialog=SimpleNamespace(SAVE="save", FOLDER="folder")),
)

from backend.gui_api import GuiApi, _RUN_OVERRIDE_KEYS  # noqa: E402


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


# ── generate_reports_zip 进度推送行为 ──────────────────────────────


class TestGenerateReportsZipProgress:
    """验证 generate_reports_zip 成功/失败路径的进度推送。"""

    def test_failure_does_not_push_complete(self, monkeypatch) -> None:
        """异常路径应推送 error 而非 complete。"""
        import threading
        from collections import deque

        api = object.__new__(GuiApi)
        api._report_lock = threading.Lock()
        api._report_progress_lock = threading.Lock()
        api._report_progress_queue = deque(maxlen=500)
        api._config = SimpleNamespace(get=lambda: {"input_dir": "/tmp", "output_dir": "/tmp"})
        api._audit = SimpleNamespace(log=lambda *a, **kw: None)
        api._safe_known_path = lambda p: None
        api._safe_user_selected_path = lambda p, **kw: None

        # 让 generate 抛出异常 — 设置 backing field 而非 property
        class BrokenReportSvc:
            def generate(self, *a, **kw):
                raise RuntimeError("模拟失败")
        api._report = BrokenReportSvc()

        result = api.generate_reports_zip(["O76"], "standard", "docx")
        assert "error" in result
        # 验证没有 complete 事件
        with api._report_progress_lock:
            events = list(api._report_progress_queue)
        assert not any(e.get("type") == "complete" for e in events)

    def test_report_error_pushes_error_not_complete(self) -> None:
        """报告服务返回业务错误时应推送 error，而不是静默停在进度态。"""
        import threading
        from collections import deque

        api = object.__new__(GuiApi)
        api._report_lock = threading.Lock()
        api._report_progress_lock = threading.Lock()
        api._report_progress_queue = deque(maxlen=500)
        api._config = SimpleNamespace(get=lambda: {"input_dir": "/tmp", "output_dir": "/tmp"})
        api._audit = SimpleNamespace(log=lambda *a, **kw: None)
        api._safe_known_path = lambda p: None
        api._safe_user_selected_path = lambda p, **kw: None
        api._report = SimpleNamespace(generate=lambda *a, **kw: {"error": "生成失败"})

        result = api.generate_reports_zip(["O76"], "standard", "docx")

        assert result == {"error": "没有生成任何报告: O76: 生成失败"}
        with api._report_progress_lock:
            events = list(api._report_progress_queue)
        assert any(e.get("type") == "error" for e in events)
        assert not any(e.get("type") == "complete" for e in events)


# ── 懒加载线程安全 ────────────────────────────────────────────────


class TestLazyLoadingThreadSafety:
    """验证懒加载属性在并发访问时只创建一个实例。"""

    def test_concurrent_access_creates_single_instance(self, monkeypatch) -> None:
        import threading
        import time

        api = object.__new__(GuiApi)
        api._service_lock = threading.RLock()
        api._pipeline = None
        api._preview = None
        api._stats = None
        api._data = None
        api._report = None
        api._audit = None

        created = {"count": 0}
        create_lock = threading.Lock()
        barrier = threading.Barrier(10)

        class CountingPipelineService:
            def __init__(self):
                with create_lock:
                    created["count"] += 1
                time.sleep(0.01)

        import backend.gui_api as gui_api_module
        monkeypatch.setattr(gui_api_module, "PipelineService", CountingPipelineService)

        def access_pipeline_service() -> None:
            barrier.wait()
            _ = api._pipeline_svc

        threads = [threading.Thread(target=access_pipeline_service) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert created["count"] == 1, (
            f"期望只创建 1 个 PipelineService 实例，实际创建了 {created['count']}"
        )
