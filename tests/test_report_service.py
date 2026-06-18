"""ReportService 单元测试 — 缓存键生成与缓存行为。"""

from __future__ import annotations

import pytest
from backend.services.report_service import ReportService


class TestReportServiceCacheKey:
    """验证 _cache_key 的幂等性与区分度。"""

    def test_same_params_produce_same_key(self):
        cfg = {"input_dir": "in", "output_dir": "out", "window_strategy": "auto"}
        k1 = ReportService._cache_key("O76", "trace", "docx", cfg)
        k2 = ReportService._cache_key("O76", "trace", "docx", cfg)
        assert k1 == k2

    def test_different_outcrop_produce_different_keys(self):
        cfg = {"input_dir": "in", "output_dir": "out"}
        k1 = ReportService._cache_key("O76", "trace", "docx", cfg)
        k2 = ReportService._cache_key("O77", "trace", "docx", cfg)
        assert k1 != k2

    def test_different_format_produce_different_keys(self):
        cfg = {"input_dir": "in", "output_dir": "out"}
        k1 = ReportService._cache_key("O76", "trace", "docx", cfg)
        k2 = ReportService._cache_key("O76", "trace", "pdf", cfg)
        assert k1 != k2

    def test_different_report_type_produce_different_keys(self):
        cfg = {"input_dir": "in", "output_dir": "out"}
        k1 = ReportService._cache_key("O76", "trace", "docx", cfg)
        k2 = ReportService._cache_key("O76", "statistics", "docx", cfg)
        assert k1 != k2

    def test_irrelevant_config_keys_do_not_affect_key(self):
        """不相关的配置键不应影响缓存键。"""
        cfg1 = {"input_dir": "in", "output_dir": "out", "extra_field": "xyz"}
        cfg2 = {"input_dir": "in", "output_dir": "out", "extra_field": "abc"}
        k1 = ReportService._cache_key("O76", "trace", "docx", cfg1)
        k2 = ReportService._cache_key("O76", "trace", "docx", cfg2)
        assert k1 == k2

    def test_relevant_config_change_produces_different_key(self):
        """关键的配置变更应导致缓存键不同。"""
        cfg1 = {"input_dir": "in", "output_dir": "out", "window_strategy": "auto"}
        cfg2 = {"input_dir": "in", "output_dir": "out", "window_strategy": "tangent"}
        k1 = ReportService._cache_key("O76", "trace", "docx", cfg1)
        k2 = ReportService._cache_key("O76", "trace", "docx", cfg2)
        assert k1 != k2


class TestReportServiceInit:
    """验证 ReportService 初始化。"""

    def test_init_creates_cache(self):
        svc = ReportService()
        assert svc._result_cache is not None


class TestReportServiceImageMtimes:
    """验证 _image_mtimes 容错行为。"""

    def test_empty_list_returns_empty_dict(self):
        result = ReportService._image_mtimes([])
        assert result == {}

    def test_missing_files_return_zero(self):
        result = ReportService._image_mtimes(["/nonexistent/path.png"])
        assert result == {"/nonexistent/path.png": 0.0}

    def test_existing_files_return_mtime(self, tmp_path):
        f = tmp_path / "test.png"
        f.write_text("dummy")
        result = ReportService._image_mtimes([str(f)])
        assert str(f) in result
        assert result[str(f)] > 0.0
