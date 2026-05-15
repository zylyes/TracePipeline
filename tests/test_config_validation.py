"""配置校验单元测试 — 节点字段保留与类型强制转换。"""
from __future__ import annotations

import pytest

from trace_pipeline.config import DEFAULT_CONFIG, validate_config


class TestConfigValidation:
    def test_validate_config_preserves_node_fields(self):
        """节点配置字段不应被 validate_config 丢弃。"""
        cfg = {
            "input_dir": "input",
            "output_dir": "output",
            "table_stem": "O76_process",
            "outcrop": "O76",
            "enable_node_recognition": False,
            "node_merge_tolerance": 1e-4,
            "show_node_overlay": False,
            "node_label_mode": "id",
        }
        result = validate_config(cfg)
        assert result["enable_node_recognition"] is False
        assert result["node_merge_tolerance"] == 1e-4
        assert result["show_node_overlay"] is False
        assert result["node_label_mode"] == "id"

    def test_validate_config_node_field_defaults(self):
        """未提供节点字段时应使用默认值。"""
        cfg = {
            "input_dir": "input",
            "output_dir": "output",
            "table_stem": "O76_process",
            "outcrop": "O76",
        }
        result = validate_config(cfg)
        assert result["enable_node_recognition"] is True
        assert result["node_merge_tolerance"] == 1e-6
        assert result["show_node_overlay"] is True
        assert result["node_label_mode"] == "type"

    def test_validate_config_coerces_node_bool_from_string(self):
        """节点布尔字段应支持字符串形式的 true/false。"""
        cfg = {
            "input_dir": "input",
            "output_dir": "output",
            "table_stem": "O76_process",
            "outcrop": "O76",
            "enable_node_recognition": "false",
            "show_node_overlay": "0",
        }
        result = validate_config(cfg)
        assert result["enable_node_recognition"] is False
        assert result["show_node_overlay"] is False

    def test_validate_config_rejects_invalid_node_label_mode(self):
        """非法的 node_label_mode 应抛出 ValueError。"""
        cfg = {
            "input_dir": "input",
            "output_dir": "output",
            "table_stem": "O76_process",
            "outcrop": "O76",
            "node_label_mode": "invalid",
        }
        with pytest.raises(ValueError, match="node_label_mode"):
            validate_config(cfg)

    def test_validate_config_rejects_non_positive_node_merge_tolerance(self):
        """node_merge_tolerance 必须为正数。"""
        cfg = {
            "input_dir": "input",
            "output_dir": "output",
            "table_stem": "O76_process",
            "outcrop": "O76",
            "node_merge_tolerance": 0,
        }
        with pytest.raises(ValueError, match="node_merge_tolerance"):
            validate_config(cfg)
