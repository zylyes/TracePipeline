"""pytest 共享 fixture 与辅助函数。"""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")

import numpy as np
import pandas as pd

from trace_pipeline.config import DEFAULT_CONFIG
from trace_pipeline.models import TraceData


def make_trace_df(rows):
    """构造 compute_endpoints 期望的 DataFrame。

    rows: [[r1,r2,dip,r4,r5,r6,r7, ang0_or_nan, n_or_nan], ...]
    """
    return pd.DataFrame(rows)


def make_trace(
    endpoints,
    scanline_positions,
    *,
    segment_lengths=None,
    joint_strikes=None,
    scanline_azimuth=90.0,
    measured_scanline_length=None,
    measured_outcrop_area=None,
):
    """构造 TraceData 实例的通用辅助函数。"""
    arr = np.asarray(endpoints, dtype=float)
    n = arr.shape[0]
    if segment_lengths is None:
        segment_lengths = np.ones(n)
    if joint_strikes is None:
        joint_strikes = np.zeros(n)
    return TraceData(
        scanline_azimuth=scanline_azimuth,
        count=n,
        endpoints=arr,
        joint_strikes=np.asarray(joint_strikes, dtype=float),
        segment_lengths=np.asarray(segment_lengths, dtype=float),
        scanline_positions=np.asarray(scanline_positions, dtype=float),
        measured_scanline_length=measured_scanline_length,
        measured_outcrop_area=measured_outcrop_area,
    )


def base_config(**overrides):
    """构造基础配置字典。"""
    cfg = dict(DEFAULT_CONFIG)
    cfg.update({
        'input_dir': 'input',
        'output_dir': 'output',
        'table_stem': 'O76_process',
        'outcrop': 'O76',
    })
    cfg.update(overrides)
    return cfg
