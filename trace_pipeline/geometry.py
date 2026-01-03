"""几何计算：迹线端点与走向转换。"""
from __future__ import annotations

import math
from typing import Tuple
import numpy as np
import pandas as pd


def _get_adjusted_angle(base_angle: float, target_angle: float, invert: bool = False) -> float:
    """
    根据基准角度调整目标角度，用于确定迹线延伸方向。
    
    Args:
        base_angle: 基准角度（通常为测线走向转换后的角度）
        target_angle: 目标角度（通常为节理走向转换后的角度）
        invert: 是否反转逻辑（用于区分左右侧）
        
    Returns:
        调整后的角度（弧度制）
    """
    if base_angle <= 180:
        cond = (base_angle < target_angle) and (target_angle < (180 + base_angle))
        # rada (invert=False): cond -> target, else -> target+180
        # rade (invert=True):  cond -> target+180, else -> target
        if not invert:
            res = target_angle if cond else target_angle + 180
        else:
            res = target_angle + 180 if cond else target_angle
    else:
        cond = ((base_angle - 180) < target_angle) and (target_angle < base_angle)
        # rada (invert=False): cond -> target+180, else -> target
        # rade (invert=True):  cond -> target, else -> target+180
        if not invert:
            res = target_angle + 180 if cond else target_angle
        else:
            res = target_angle if cond else target_angle + 180
            
    return math.radians(res)


def calc_joint_pts(
    ang0: float,
    r1: float,
    r2: float,
    ang: float,
    r3: float,
    r4: float,
    r5: float,
    r6: float,
) -> Tuple[float, float, float, float]:
    """
    依据测线走向与左右/相交迹长计算节理端点坐标。
    
    Args:
        ang0: 测线走向
        r1: 沿测线距离
        r2: 垂直测线偏移
        ang: 节理走向
        r3, r4: 左侧迹长参数
        r5, r6: 右侧迹长参数
        
    Returns:
        (x1, y1, x2, y2): 迹线两端点坐标
    """

    # 1. 角度预处理
    ang_0 = (90 - ang0) if ang0 < 90 else (450 - ang0)
    rad_0 = math.radians(ang_0)

    ang1 = (360 - (ang + 90)) if ang < 270 else (720 - (90 + ang))

    # 2. 确定左右侧逻辑
    has_left = (r4 != 0)
    has_right = (r6 != 0)
    
    rada = 0.0
    rade = 0.0

    if has_left:
        rada = _get_adjusted_angle(ang_0, ang1, invert=False)
    if has_right:
        rade = _get_adjusted_angle(ang_0, ang1, invert=True)

    # 3. 向量计算
    # z1: 沿测线位移
    z1 = complex(r1 * math.cos(rad_0), r1 * math.sin(rad_0))
    
    # 垂直方向单位向量
    vec_perp_left = complex(math.cos(rad_0 + math.pi/2), math.sin(rad_0 + math.pi/2))
    vec_perp_right = complex(math.cos(rad_0 - math.pi/2), math.sin(rad_0 - math.pi/2))
    
    # 倾斜方向单位向量
    vec_skew_a = complex(math.cos(rada), math.sin(rada))
    vec_skew_e = complex(math.cos(rade), math.sin(rade))

    # 4. 坐标合成
    if has_left and not has_right:
        # 仅左侧
        z2 = r2 * vec_perp_left
        z3 = r3 * vec_skew_a
        z4 = r4 * vec_skew_a
        s1 = z1 + z2 + z3
        s2 = s1 + z4
        return s1.real, s1.imag, s2.real, s2.imag
        
    elif not has_left and has_right:
        # 仅右侧
        z2 = r2 * vec_perp_right
        z3 = r5 * vec_skew_e
        z4 = r6 * vec_skew_e
        s1 = z1 + z2 + z3
        s2 = s1 + z4
        return s1.real, s1.imag, s2.real, s2.imag
        
    else:
        # 两侧都有（或都无，视为穿越？）
        # 左侧端点
        y2 = r2 * vec_perp_left
        y3 = r3 * vec_skew_a
        y4 = r4 * vec_skew_a
        s_left = z1 + y2 + y3 + y4
        
        # 右侧端点
        y5 = r2 * vec_perp_right
        y6 = r5 * vec_skew_e
        y7 = r6 * vec_skew_e
        s_right = z1 + y5 + y6 + y7
        
        return s_left.real, s_left.imag, s_right.real, s_right.imag


def dip_to_strike(dd: float) -> float:
    """倾向转走向。"""
    if dd >= 270:
        return dd + 90 - 360
    if dd >= 180:
        return dd - 90
    if dd >= 90:
        return dd - 90
    return dd + 90


def parse_trace_table(df: pd.DataFrame) -> Tuple[float, int, np.ndarray]:
    """从原始表格解析走向、条数与端点坐标。"""

    # 表头：走向在 (1,8)，条数在 (1,9) -> iloc[0, 7], iloc[0, 8]
    try:
        ang0 = float(df.iloc[0, 7])
        n_raw = df.iloc[0, 8]
        n = int(pd.to_numeric(n_raw))
    except (ValueError, IndexError) as e:
        raise ValueError(f"Failed to parse header info (strike/count) from Excel: {e}")

    # 提取数据矩阵
    # 假设前7列是参数: r1, r2, ang(dip), r3, r4, r5, r6
    # 注意：原始代码中 M[:, 2] 被替换为 strike
    M = df.iloc[:, 0:7].to_numpy(dtype=float)
    
    # 倾向转走向
    dd = df.iloc[:, 2].to_numpy(dtype=float)
    strike_angles = np.array([dip_to_strike(x) for x in dd])
    M[:, 2] = strike_angles[: M.shape[0]]

    # 计算坐标
    XY = np.zeros((n, 4), dtype=float)
    
    # 这里未来可以考虑向量化优化，但目前保持循环以确保逻辑正确
    for m in range(n):
        # 参数映射: r1=0, r2=1, ang=2, r3=3, r4=4, r5=5, r6=6
        args = M[m, :]
        X1, Y1, X2, Y2 = calc_joint_pts(ang0, *args)
        XY[m, :] = [X1, Y1, X2, Y2]

    return ang0, n, XY
