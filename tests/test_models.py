"""单元测试 — models.py 数据模型校验。"""

from __future__ import annotations

import numpy as np
import pytest

from trace_pipeline.models import RunConfig, TraceData


class TestTraceData:
    """TraceData 不可变数据类校验。"""

    def test_basic_construction(self) -> None:
        endpoints = np.array([[0.0, 0.0, 1.0, 1.0]])
        td = TraceData(
            scanline_azimuth=298.0,
            count=1,
            endpoints=endpoints,
            joint_strikes=np.array([28.0]),
            segment_lengths=np.array([1.0]),
            scanline_positions=np.array([0.5]),
        )
        assert td.scanline_azimuth == 298.0
        assert td.count == 1
        assert np.array_equal(td.endpoints, endpoints)

    def test_negative_count(self) -> None:
        with pytest.raises(ValueError, match="count 不能为负数"):
            TraceData(
                scanline_azimuth=0.0,
                count=-1,
                endpoints=np.array([[0, 0, 1, 1]]),
                joint_strikes=np.array([0.0]),
                segment_lengths=np.array([1.0]),
                scanline_positions=np.array([0.0]),
            )

    def test_shape_mismatch(self) -> None:
        with pytest.raises(ValueError, match="endpoints 形状"):
            TraceData(
                scanline_azimuth=0.0,
                count=2,
                endpoints=np.array([[0, 0, 1, 1]]),  # 只有 1 行
                joint_strikes=np.array([0.0, 1.0]),
                segment_lengths=np.array([1.0, 1.0]),
                scanline_positions=np.array([0.0, 1.0]),
            )

    def test_nan_in_endpoints(self) -> None:
        with pytest.raises(ValueError, match="endpoints 包含 NaN 或 inf"):
            TraceData(
                scanline_azimuth=0.0,
                count=1,
                endpoints=np.array([[0, np.nan, 1, 1]]),
                joint_strikes=np.array([0.0]),
                segment_lengths=np.array([1.0]),
                scanline_positions=np.array([0.0]),
            )

    def test_optional_positive_validation(self) -> None:
        with pytest.raises(ValueError, match="measured_scanline_length"):
            TraceData(
                scanline_azimuth=0.0,
                count=1,
                endpoints=np.array([[0, 0, 1, 1]]),
                joint_strikes=np.array([0.0]),
                segment_lengths=np.array([1.0]),
                scanline_positions=np.array([0.0]),
                measured_scanline_length=-1.0,
            )

    def test_arrays_are_readonly(self) -> None:
        td = TraceData(
            scanline_azimuth=0.0,
            count=1,
            endpoints=np.array([[0, 0, 1, 1]]),
            joint_strikes=np.array([0.0]),
            segment_lengths=np.array([1.0]),
            scanline_positions=np.array([0.0]),
        )
        assert not td.endpoints.flags.writeable
        assert not td.joint_strikes.flags.writeable

    def test_lengths_property(self) -> None:
        td = TraceData(
            scanline_azimuth=0.0,
            count=2,
            endpoints=np.array([[0, 0, 3, 4], [0, 0, 0, 10]]),
            joint_strikes=np.array([0.0, 90.0]),
            segment_lengths=np.array([5.0, 10.0]),
            scanline_positions=np.array([0.0, 1.0]),
        )
        lengths = td.lengths
        assert lengths[0] == pytest.approx(5.0)
        assert lengths[1] == pytest.approx(10.0)
        assert not lengths.flags.writeable


class TestRunConfig:
    """RunConfig 校验。"""

    def test_basic_construction(self) -> None:
        cfg = RunConfig(
            input_dir="input",
            output_dir="output",
            output_prefix="Outcrop",
            table_stem="O76_process",
            outcrop="O76",
        )
        assert cfg.outcrop == "O76"

    def test_empty_field(self) -> None:
        with pytest.raises(ValueError, match="不能为空"):
            RunConfig(
                input_dir="",
                output_dir="output",
                output_prefix="Outcrop",
                table_stem="O76_process",
                outcrop="O76",
            )

    def test_from_mapping(self) -> None:
        cfg = RunConfig.from_mapping(
            {
                "input_dir": "./data",
                "output_dir": "./results",
                "output_prefix": "Test",
                "table_stem": "O77_process",
                "outcrop": "O77",
                "export_rose_plot": True,
            }
        )
        assert cfg.outcrop == "O77"
        assert cfg.export_rose_plot is True
        # 未知键应被忽略
        assert not hasattr(cfg, "unknown_key")
