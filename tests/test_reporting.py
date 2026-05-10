"""单元测试：结果格式化。"""
from trace_pipeline.models import RunResult
from trace_pipeline.reporting import format_results_table, format_summary


def test_format_results_table_empty():
    assert format_results_table([]) == "（无结果）"


def test_format_results_table_mixed_success_and_failure():
    results = [
        RunResult.success(
            "O76_process",
            trace_count=2,
            mean_length=3.5,
            scanline_azimuth=90.0,
            rose_plot_path="O76_rose.png",
            window_strategy="hybrid",
            area_source="window_equivalent",
        ),
        RunResult.failure("O77_process", "bad input"),
    ]

    table = format_results_table(results)

    assert "O76_process" in table
    assert "O77_process" in table
    assert "成功 1 个" in table
    assert "迹线总数 2" in table
    assert "玫瑰图 1 张" in table
    assert "混合圆窗" in table
    assert "FAIL" in table


def test_format_summary_truncates_failure_error():
    long_error = "x" * 100
    summary = format_summary([RunResult.failure("O77_process", long_error)])

    assert "失败:        1" in summary
    assert f"O77_process: {'x' * 80}" in summary
    assert "x" * 81 not in summary
