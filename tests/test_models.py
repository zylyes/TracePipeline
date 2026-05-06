"""单元测试：数据模型校验。"""
import numpy as np
import pytest

from trace_pipeline.models import RunConfig, TraceData


def test_trace_data_accepts_empty_with_strict_shapes():
    trace = TraceData(
        scanline_azimuth=0.0,
        count=0,
        endpoints=np.zeros((0, 4)),
        joint_strikes=np.array([]),
        segment_lengths=np.array([]),
        scanline_positions=np.array([]),
    )

    assert trace.mean_length == 0.0


def test_trace_data_rejects_empty_wrong_endpoint_shape():
    with pytest.raises(ValueError, match="endpoints 形状"):
        TraceData(
            scanline_azimuth=0.0,
            count=0,
            endpoints=np.array([]),
            joint_strikes=np.array([]),
            segment_lengths=np.array([]),
            scanline_positions=np.array([]),
        )


def test_trace_data_rejects_nonfinite_values():
    with pytest.raises(ValueError, match="endpoints 包含"):
        TraceData(
            scanline_azimuth=0.0,
            count=1,
            endpoints=np.array([[0.0, 0.0, np.nan, 1.0]]),
            joint_strikes=np.array([10.0]),
            segment_lengths=np.array([1.0]),
            scanline_positions=np.array([0.0]),
        )


def test_trace_data_rejects_wrong_scanline_position_shape():
    with pytest.raises(ValueError, match="scanline_positions 形状"):
        TraceData(
            scanline_azimuth=0.0,
            count=1,
            endpoints=np.array([[0.0, 0.0, 1.0, 1.0]]),
            joint_strikes=np.array([10.0]),
            segment_lengths=np.array([1.0]),
            scanline_positions=np.array([]),
        )


def test_trace_data_accepts_optional_measured_length_and_area():
    trace = TraceData(
        scanline_azimuth=0.0,
        count=1,
        endpoints=np.array([[0.0, 0.0, 1.0, 1.0]]),
        joint_strikes=np.array([10.0]),
        segment_lengths=np.array([1.0]),
        scanline_positions=np.array([0.0]),
        measured_scanline_length=12.5,
        measured_outcrop_area=34.5,
    )

    assert trace.measured_scanline_length == pytest.approx(12.5)
    assert trace.measured_outcrop_area == pytest.approx(34.5)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("measured_scanline_length", 0.0),
        ("measured_scanline_length", np.inf),
        ("measured_outcrop_area", -1.0),
        ("measured_outcrop_area", np.nan),
    ],
)
def test_trace_data_rejects_invalid_optional_measured_values(field, value):
    kwargs = {
        "scanline_azimuth": 0.0,
        "count": 1,
        "endpoints": np.array([[0.0, 0.0, 1.0, 1.0]]),
        "joint_strikes": np.array([10.0]),
        "segment_lengths": np.array([1.0]),
        "scanline_positions": np.array([0.0]),
        field: value,
    }

    with pytest.raises(ValueError, match=f"{field} 必须为正的有限浮点数"):
        TraceData(**kwargs)


def test_run_config_normalizes_values():
    cfg = RunConfig(
        input_dir=" input ",
        output_dir=" output ",
        output_prefix=" O76 ",
        table_stem=" O76_process ",
        outcrop=" O76 ",
        export_rose_plot="false",
        rose_bin_width="15",
        rose_dpi="600",
        trace_dpi="300",
        rotated_trace_dpi="900",
    )

    assert cfg.input_dir == "input"
    assert cfg.export_rose_plot is False
    assert cfg.rose_bin_width == 15.0
    assert cfg.rose_dpi == 600
