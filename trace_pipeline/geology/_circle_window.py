"""圆形取样窗核心 — 几何工具、迹线分型与窗口计数。"""
from __future__ import annotations

import math

import numpy as np

from ._geometry_utils import _EPS, cross_2d
from ._stat_types import CircleWindowDiagnostic, TraceStatisticsConfig

__all__ = [
    "classify_trace_types",
]


# ── 几何工具 ──────────────────────────────────────────────────────────


def _bbox_overlaps(p1: np.ndarray, p2: np.ndarray, q1: np.ndarray, q2: np.ndarray) -> bool:
    return (
        max(min(p1[0], p2[0]), min(q1[0], q2[0])) <= min(max(p1[0], p2[0]), max(q1[0], q2[0])) + _EPS
        and max(min(p1[1], p2[1]), min(q1[1], q2[1])) <= min(max(p1[1], p2[1]), max(q1[1], q2[1])) + _EPS
    )


def _segment_intersects_segment(
    p1: np.ndarray,
    p2: np.ndarray,
    q1: np.ndarray,
    q2: np.ndarray,
) -> bool:
    r = p2 - p1
    s = q2 - q1
    r_norm = float(np.linalg.norm(r))
    s_norm = float(np.linalg.norm(s))
    if r_norm <= _EPS or s_norm <= _EPS:
        return False

    denom = cross_2d(r, s)
    qp = q1 - p1
    if abs(denom) <= _EPS:
        if abs(cross_2d(qp, r)) > _EPS:
            return False
        return _bbox_overlaps(p1, p2, q1, q2)

    t = cross_2d(qp, s) / denom
    u = cross_2d(qp, r) / denom
    return -_EPS <= t <= 1.0 + _EPS and -_EPS <= u <= 1.0 + _EPS


def _line_intersects_scanline_segment(p1: np.ndarray, p2: np.ndarray, length: float) -> bool:
    if length <= _EPS:
        return False

    q1 = np.array([0.0, 0.0], dtype=float)
    q2 = np.array([length, 0.0], dtype=float)
    r = p2 - p1
    s = q2 - q1
    if float(np.linalg.norm(r)) <= _EPS:
        return False

    denom = cross_2d(r, s)
    qp = q1 - p1
    if abs(denom) <= _EPS:
        return abs(cross_2d(qp, r)) <= _EPS

    u = cross_2d(qp, r) / denom
    return -_EPS <= u <= 1.0 + _EPS


def classify_trace_types(local_segments: np.ndarray, scanline_length: float) -> tuple[str, ...]:
    """将迹线分为 I/II/III 型（向量化实现）。"""
    if local_segments.shape[0] == 0:
        return ()

    p1 = local_segments[:, 0:2]
    p2 = local_segments[:, 2:4]
    q1 = np.array([0.0, 0.0], dtype=float)
    q2 = np.array([scanline_length, 0.0], dtype=float)

    r = p2 - p1
    s = q2 - q1
    r_norm = np.linalg.norm(r, axis=1)
    s_norm = float(np.linalg.norm(s))
    qp = q1 - p1

    cross_r_s = r[:, 0] * s[1] - r[:, 1] * s[0]
    cross_qp_s = qp[:, 0] * s[1] - qp[:, 1] * s[0]
    cross_qp_r = qp[:, 0] * r[:, 1] - qp[:, 1] * r[:, 0]

    degenerate = (r_norm <= _EPS) | (s_norm <= _EPS)

    safe_denom = np.where(np.abs(cross_r_s) > _EPS, cross_r_s, 1.0)
    t = cross_qp_s / safe_denom
    u = cross_qp_r / safe_denom
    non_parallel_intersect = (
        (np.abs(cross_r_s) > _EPS)
        & (t >= -_EPS) & (t <= 1.0 + _EPS)
        & (u >= -_EPS) & (u <= 1.0 + _EPS)
    )

    collinear = (np.abs(cross_r_s) <= _EPS) & (np.abs(cross_qp_r) <= _EPS)
    seg_x_min = np.minimum(p1[:, 0], p2[:, 0])
    seg_x_max = np.maximum(p1[:, 0], p2[:, 0])
    scanline_x_min = min(q1[0], q2[0])
    scanline_x_max = max(q1[0], q2[0])
    seg_y_min = np.minimum(p1[:, 1], p2[:, 1])
    seg_y_max = np.maximum(p1[:, 1], p2[:, 1])
    bbox_overlap = (
        (np.maximum(seg_x_min, scanline_x_min) <= np.minimum(seg_x_max, scanline_x_max) + _EPS)
        & (np.maximum(seg_y_min, 0.0) <= np.minimum(seg_y_max, 0.0) + _EPS)
    )
    collinear_intersect = collinear & bbox_overlap

    is_type_i = (~degenerate) & (non_parallel_intersect | collinear_intersect)

    line_non_parallel = (np.abs(cross_r_s) > _EPS) & (u >= -_EPS) & (u <= 1.0 + _EPS)
    line_collinear = (np.abs(cross_r_s) <= _EPS) & (np.abs(cross_qp_r) <= _EPS)
    is_line_intersect = (~degenerate) & (line_non_parallel | line_collinear)
    is_type_ii = (~is_type_i) & is_line_intersect

    labels = np.where(is_type_i, "I", np.where(is_type_ii, "II", "III"))
    return tuple(labels.tolist())


def _distance_point_to_segment(point: np.ndarray, p1: np.ndarray, p2: np.ndarray) -> float:
    segment = p2 - p1
    length_sq = float(segment @ segment)
    if length_sq <= _EPS:
        return float(np.linalg.norm(point - p1))
    t = float(((point - p1) @ segment) / length_sq)
    t = min(1.0, max(0.0, t))
    closest = p1 + t * segment
    return float(np.linalg.norm(point - closest))


def _segment_intersects_circle(segment: np.ndarray, center: np.ndarray, radius: float) -> bool:
    p1 = segment[0:2]
    p2 = segment[2:4]
    if np.linalg.norm(p1 - center) <= radius + _EPS:
        return True
    if np.linalg.norm(p2 - center) <= radius + _EPS:
        return True
    return _distance_point_to_segment(center, p1, p2) <= radius + _EPS


# ── 圆窗计数 ─────────────────────────────────────────────────────────


def _count_circle_windows_batch(
    local_segments: np.ndarray,
    centers: np.ndarray,
    radii: np.ndarray,
    min_intersections: int,
    cut_positions: np.ndarray,
    sides: list[str],
    strategies: list[str],
    group_keys: list[str],
) -> list[CircleWindowDiagnostic]:
    """批量计算多个圆窗的相交统计（向量化）。

    利用 broadcasting 一次计算所有线段到所有圆心的距离矩阵，
    避免多次 Python 函数调用开销。

    Args:
        local_segments: (N, 4) 线段端点坐标
        centers: (M, 2) 各窗口圆心
        radii: (M,) 各窗口半径
        min_intersections: 最少相交迹线数
        cut_positions: (M,) 各窗口切割位置
        sides: 长度 M 的侧向列表
        strategies: 长度 M 的策略列表
        group_keys: 长度 M 的分组键列表

    Returns:
        M 个 CircleWindowDiagnostic 对象的列表
    """
    n_segs = local_segments.shape[0]
    m_windows = centers.shape[0]

    if n_segs == 0:
        return [
            _invalid_window(
                float(cut_positions[i]), sides[i], "无迹线数据",
                strategy=strategies[i], group_key=group_keys[i],
                center_x=float(centers[i, 0]), center_y=float(centers[i, 1]),
                radius=float(radii[i]),
            )
            for i in range(m_windows)
        ]

    # p1: (N, 2), p2: (N, 2)
    p1 = local_segments[:, 0:2]
    p2 = local_segments[:, 2:4]

    # centers: (M, 2) → 广播到 (N, M, 2)
    # d1[n, m] = ||p1[n] - center[m]||
    d1 = np.linalg.norm(p1[:, np.newaxis, :] - centers[np.newaxis, :, :], axis=2)  # (N, M)
    d2 = np.linalg.norm(p2[:, np.newaxis, :] - centers[np.newaxis, :, :], axis=2)  # (N, M)

    # 线段向量与到圆心的最近点距离
    seg_vec = p2 - p1  # (N, 2)
    length_sq = np.sum(seg_vec * seg_vec, axis=1)  # (N,)
    safe_length_sq = np.where(length_sq > _EPS, length_sq, 1.0)  # (N,)

    # t[n, m] = clamp(dot(center[m] - p1[n], seg_vec[n]) / |seg_vec[n]|^2, 0, 1)
    diff = centers[np.newaxis, :, :] - p1[:, np.newaxis, :]  # (N, M, 2)
    dot_val = np.sum(diff * seg_vec[:, np.newaxis, :], axis=2)  # (N, M)
    t = dot_val / safe_length_sq[:, np.newaxis]  # (N, M)
    t = np.clip(t, 0.0, 1.0)
    t = np.where(length_sq[:, np.newaxis] > _EPS, t, 0.0)

    # closest[n, m] = p1[n] + t[n, m] * seg_vec[n]
    closest = p1[:, np.newaxis, :] + t[:, :, np.newaxis] * seg_vec[:, np.newaxis, :]  # (N, M, 2)
    dist_to_seg = np.linalg.norm(
        centers[np.newaxis, :, :] - closest, axis=2
    )  # (N, M)

    # threshold[m] = radii[m] + _EPS
    thresholds = radii[np.newaxis, :] + _EPS  # (1, M) 广播到 (N, M)

    # intersects[n, m]: 线段 n 是否与窗口 m 相交
    intersects = (d1 <= thresholds) | (d2 <= thresholds) | (dist_to_seg <= thresholds)  # (N, M)

    # 逐窗口统计
    intersection_counts = intersects.sum(axis=0)  # (M,)

    # inside1[n, m], inside2[n, m]: 端点是否在圆内
    inside1 = d1 <= thresholds  # (N, M)
    inside2 = d2 <= thresholds  # (N, M)

    # 仅统计相交的线段
    inside_count = inside1.astype(int) + inside2.astype(int)  # (N, M): 0/1/2
    # 只计入与窗口相交的线段
    masked_inside = np.where(intersects, inside_count, -1)

    results = []
    for i in range(m_windows):
        ic = int(intersection_counts[i])
        col = masked_inside[:, i]
        valid_col = col[col >= 0]
        n0 = int(np.sum(valid_col == 0))
        n1 = int(np.sum(valid_col == 1))
        n2 = int(np.sum(valid_col == 2))

        m_val = n1 + 2 * n2
        q_val = 2 * n0 + n1
        p20 = math.nan
        p21 = math.nan
        l_est = math.nan
        reason = ""
        valid = True
        r = float(radii[i])

        if ic < min_intersections:
            valid = False
            reason = f"相交迹线数不足: {ic} < {min_intersections}"
        elif m_val <= 0:
            valid = False
            reason = "m <= 0"
        else:
            p20 = m_val / (2.0 * math.pi * r * r)
            p21 = q_val / (4.0 * r)
            l_est = (math.pi * r / 2.0) * (q_val / m_val)

        results.append(CircleWindowDiagnostic(
            cut_position=float(cut_positions[i]),
            side=sides[i],
            center_x=float(centers[i, 0]),
            center_y=float(centers[i, 1]),
            radius=r,
            intersection_count=ic,
            n0=n0,
            n1=n1,
            n2=n2,
            m=m_val,
            q=q_val,
            p20=float(p20),
            p21=float(p21),
            l_est=float(l_est),
            strategy=strategies[i],
            group_key=group_keys[i],
            valid=valid,
            reason=reason,
        ))

    return results


def _count_circle_window(
    local_segments: np.ndarray,
    cut_position: float,
    side: str,
    center: np.ndarray,
    radius: float,
    min_intersections: int,
    strategy: str,
    group_key: str,
) -> CircleWindowDiagnostic:
    n_segs = local_segments.shape[0]
    if n_segs == 0:
        return _invalid_window(
            cut_position, side, "无迹线数据",
            strategy=strategy, group_key=group_key,
            center_x=float(center[0]), center_y=float(center[1]), radius=radius,
        )

    p1 = local_segments[:, 0:2]
    p2 = local_segments[:, 2:4]
    d1 = np.linalg.norm(p1 - center, axis=1)
    d2 = np.linalg.norm(p2 - center, axis=1)

    seg_vec = p2 - p1
    length_sq = np.sum(seg_vec * seg_vec, axis=1)
    safe_length_sq = np.where(length_sq > _EPS, length_sq, 1.0)
    t = np.sum((center - p1) * seg_vec, axis=1) / safe_length_sq
    t = np.clip(t, 0.0, 1.0)
    t = np.where(length_sq > _EPS, t, 0.0)
    closest = p1 + t[:, np.newaxis] * seg_vec
    dist_to_seg = np.linalg.norm(center - closest, axis=1)

    threshold = radius + _EPS
    intersects = (d1 <= threshold) | (d2 <= threshold) | (dist_to_seg <= threshold)

    intersection_count = int(np.sum(intersects))

    inside1 = d1[intersects] <= threshold
    inside2 = d2[intersects] <= threshold
    inside_count = inside1.astype(int) + inside2.astype(int)
    n0 = int(np.sum(inside_count == 0))
    n1 = int(np.sum(inside_count == 1))
    n2 = int(np.sum(inside_count == 2))

    m = n1 + 2 * n2
    q = 2 * n0 + n1
    p20 = math.nan
    p21 = math.nan
    l_est = math.nan
    reason = ""
    valid = True
    if intersection_count < min_intersections:
        valid = False
        reason = f"相交迹线数不足: {intersection_count} < {min_intersections}"
    elif m <= 0:
        valid = False
        reason = "m <= 0"
    else:
        p20 = m / (2.0 * math.pi * radius * radius)
        p21 = q / (4.0 * radius)
        l_est = (math.pi * radius / 2.0) * (q / m)

    return CircleWindowDiagnostic(
        cut_position=cut_position,
        side=side,
        center_x=float(center[0]),
        center_y=float(center[1]),
        radius=float(radius),
        intersection_count=intersection_count,
        n0=n0,
        n1=n1,
        n2=n2,
        m=m,
        q=q,
        p20=float(p20),
        p21=float(p21),
        l_est=float(l_est),
        strategy=strategy,
        group_key=group_key,
        valid=valid,
        reason=reason,
    )


def _invalid_window(
    cut_position: float,
    side: str,
    reason: str,
    *,
    strategy: str,
    group_key: str,
    center_x: float | None = None,
    center_y: float | None = None,
    radius: float | None = None,
) -> CircleWindowDiagnostic:
    return CircleWindowDiagnostic(
        cut_position=cut_position,
        side=side,
        center_x=float(cut_position if center_x is None else center_x),
        center_y=float(math.nan if center_y is None else center_y),
        radius=float(math.nan if radius is None else radius),
        intersection_count=0,
        n0=0,
        n1=0,
        n2=0,
        m=0,
        q=0,
        p20=math.nan,
        p21=math.nan,
        l_est=math.nan,
        strategy=strategy,
        group_key=group_key,
        valid=False,
        reason=reason,
    )


# ── 辅助度量 ─────────────────────────────────────────────────────────


def _side_height(local_segments: np.ndarray, sign: float) -> float:
    y_values = local_segments[:, [1, 3]].ravel()
    side_values = y_values[y_values * sign > _EPS]
    if side_values.size == 0:
        return 0.0
    return float(np.max(np.abs(side_values)))


def _max_abs_y(local_segments: np.ndarray) -> float:
    if local_segments.size == 0:
        return 0.0
    y_values = np.asarray(local_segments[:, [1, 3]].ravel(), dtype=float)
    if y_values.size == 0:
        return 0.0
    return float(np.max(np.abs(y_values)))


def _tangent_radius(scanline_length: float, config: TraceStatisticsConfig) -> float:
    if not math.isfinite(float(scanline_length)) or scanline_length <= _EPS:
        return math.nan
    return float(scanline_length) / (2.0 * config.tangent_window_count)
