"""预览服务单元测试 — 返回路径与结构化 images。"""
from __future__ import annotations

from unittest.mock import patch

from backend.services.preview_service import PreviewService


class TestPreviewService:
    def test_generate_returns_rotated_path(self):
        """PreviewService.generate 应返回包含 rotated 路径的结果。"""
        svc = PreviewService(sample_outcrop="O76")
        # 直接调用 generate，使用真实 demo 数据（完全解耦，无需 mock）
        result = svc.generate({
            "style": {},
            "show_hull": True,
            "show_circles": True,
            "show_nodes": True,
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

    def test_generate_respects_overlay_state(self):
        """generate 应区分不同的 overlay 状态生成不同缓存。"""
        svc = PreviewService()

        with patch.object(svc, "_generate_images") as mock_gen:
            mock_gen.return_value = {
                "raw": "/tmp/raw.png",
                "rotated": "/tmp/rot.png",
                "rose": "/tmp/rose.png",
            }

            # 状态 A：全部显示
            svc.generate({
                "style": {"trace_line_color": "#000000"},
                "show_hull": True,
                "show_circles": True,
                "show_nodes": True,
            })

            # 状态 B：隐藏凸包
            svc.generate({
                "style": {"trace_line_color": "#000000"},
                "show_hull": False,
                "show_circles": True,
                "show_nodes": True,
            })

            # 两次调用 _generate_images，因为缓存键不同
            assert mock_gen.call_count == 2
