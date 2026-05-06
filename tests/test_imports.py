"""单元测试：包级导入副作用。"""
import importlib
import sys


def test_import_trace_pipeline_does_not_import_pyplot():
    sys.modules.pop("trace_pipeline", None)
    sys.modules.pop("trace_pipeline.plotting", None)
    sys.modules.pop("matplotlib.pyplot", None)

    importlib.import_module("trace_pipeline")

    assert "matplotlib.pyplot" not in sys.modules
