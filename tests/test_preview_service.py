"""预览服务单元测试 — 返回路径与结构化 images。"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from backend.services.preview_service import PreviewService


class TestPreviewService:
    def test_generate_returns_rotated_path(self):
        """PreviewService.generate 应返回包含 rotated 路径的结果。"""
        svc = PreviewService(sample_outcrop="O76")
        # 直接调用 _generate_images 绕过缓存，避免需要真实数据
        with patch("backend.services.preview_service.load_trace_data") as mock_load:
            mock_trace = MagicMock()
            mock_trace.endpoints = MagicMock()
            mock_trace.endpoints.__getitem__ = MagicMock(return_value=MagicMock())
            mock_trace.joint_strikes = MagicMock()
            mock_trace.joint_strikes.size = 0
            mock_trace.count = 0
            mock_trace.scanline_azimuth = 298.0
            mock_trace.lengths = MagicMock()
            mock_trace.lengths.mean = MagicMock(return_value=0.0)
            mock_trace.lengths.size = 0
            mock_load.return_value = mock_trace

            with patch("backend.services.preview_service.compute_trace_statistics") as mock_stats:
                mock_stat = MagicMock()
                mock_stat.mean_trace_length = 1.0
                mock_stat.p10 = 1.0
                mock_stat.p20 = 1.0
                mock_stat.p21 = 1.0
                mock_stat.type_i_count = 0
                mock_stat.type_ii_count = 0
                mock_stat.type_iii_count = 0
                mock_stat.scanline_length = 10.0
                mock_stat.outcrop_area = 5.0
                mock_stat.outcrop_area_source = "hull"
                mock_stat.window_strategy = "auto"
                mock_stat.window_validation_warning = ""
                mock_stat.diagnostics = []
                mock_stats.return_value = mock_stat

                with patch("backend.services.preview_service.render_trace_plot") as mock_render:
                    with patch("backend.services.preview_service.render_rose_plot") as mock_rose:
                        with patch("backend.services.preview_service.configure_style"):
                            with patch("backend.services.preview_service.build_raw_circle_overlays", return_value=[]):
                                with patch("backend.services.preview_service.build_rotated_circle_overlays", return_value=[]):
                                    with patch("backend.services.preview_service.build_selected_hull_overlays", return_value=(None, None)):
                                        with patch("trace_pipeline.geology.statistics.format_statistics_box_lines", return_value=[]):
                                            with patch("backend.services.preview_service.normalize_coordinates", return_value=MagicMock()):
                                                with patch("backend.services.preview_service.fold_strike_angle", return_value=0.0):
                                                    with patch("backend.services.preview_service.build_node_overlays", return_value=()):
                                                        with patch("backend.services.preview_service.build_rotated_node_overlays", return_value=()):
                                                            with patch("backend.services.preview_service.recognize_trace_nodes"):
                                                                result = svc.generate({
                                                                    "style": {},
                                                                    "window_strategy": "auto",
                                                                    "auto_density_threshold": 5.0,
                                                                    "tangent_window_count": 3,
                                                                    "enable_node_recognition": True,
                                                                    "node_merge_tolerance": 1e-6,
                                                                    "show_node_overlay": True,
                                                                    "node_label_mode": "type",
                                                                    "export_rose_plot": True,
                                                                    "rose_bin_width": 10.0,
                                                                })

        assert result["status"] == "ready"
        assert "paths" in result
        assert "raw" in result["paths"]
        assert "rotated" in result["paths"]
        assert "rose" in result["paths"]
        assert "images" in result
        images = result["images"]
        keys = [img["key"] for img in images]
        assert "raw" in keys
        assert "rotated" in keys

    def test_to_images_filters_empty_paths(self):
        """_to_images 应过滤掉空路径。"""
        svc = PreviewService()
        paths = {"raw": "/tmp/raw.png", "rotated": "/tmp/rotated.png", "rose": ""}
        images = svc._to_images(paths)
        keys = [img["key"] for img in images]
        assert "raw" in keys
        assert "rotated" in keys
        assert "rose" not in keys
