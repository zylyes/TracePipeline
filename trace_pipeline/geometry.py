"""几何计算：迹线端点与走向转换。"""
from __future__ import annotations

import math
from typing import Tuple
import numpy as np
import pandas as pd


def _get_adjusted_angle_vec(base_angle: float, target_angles: np.ndarray, invert: bool = False) -> np.ndarray:
    """
    根据基准角度调整目标角度（向量化版本）。
    
    Args:
        base_angle: 基准角度（通常为测线走向转换后的角度）
        target_angles: 目标角度数组（通常为节理走向转换后的角度）
        invert: 是否反转逻辑（用于区分左右侧）
        
    Returns:
        调整后的角度数组（弧度制）
    """
    targets = np.asarray(target_angles)
    
    if base_angle <= 180:
        cond = (base_angle < targets) & (targets < (180 + base_angle))
        if not invert:
            # rada (invert=False): cond -> target, else -> target+180
            res = np.where(cond, targets, targets + 180)
        else:
            # rade (invert=True):  cond -> target+180, else -> target
            res = np.where(cond, targets + 180, targets)
    else:
        cond = ((base_angle - 180) < targets) & (targets < base_angle)
        if not invert:
            # rada (invert=False): cond -> target+180, else -> target
            res = np.where(cond, targets + 180, targets)
        else:
            # rade (invert=True):  cond -> target, else -> target+180
            res = np.where(cond, targets, targets + 180)
            
    return np.radians(res)


def dip_to_strike_vec(dd: np.ndarray) -> np.ndarray:
    """
    倾向转走向（向量化）。
    
    逻辑:
    >= 270: dd - 270
    90 <= dd < 270: dd - 90
    < 90: dd + 90
    """
    res = np.zeros_like(dd)
    mask1 = dd >= 270
    mask2 = (dd >= 90) & (dd < 270)
    mask3 = dd < 90
    
    res[mask1] = dd[mask1] - 270
    res[mask2] = dd[mask2] - 90
    res[mask3] = dd[mask3] + 90
    return res


def parse_trace_table(df: pd.DataFrame) -> Tuple[float, int, np.ndarray]:
    """
    从原始表格解析走向、条数与端点坐标（向量化）。
    
    Args:
        df: 包含迹线数据的 DataFrame
        
    Returns:
        (ang0, n, XY): 测线走向, 迹线数量, 坐标数组 (N, 4)
    """

    # 1. 解析表头信息
    try:
        ang0 = float(df.iloc[0, 7])
        n_raw = df.iloc[0, 8]
        n = int(pd.to_numeric(n_raw))
    except (ValueError, IndexError) as e:
        raise ValueError(f"Failed to parse header info (strike/count) from Excel: {e}")

    # 2. 提取数据矩阵
    # 列索引映射: 0:r1, 1:r2, 2:ang(dip), 3:r3, 4:r4, 5:r5, 6:r6
    # 确保只取前 n 行（如果 DataFrame 有多余行）
    M = df.iloc[:n, 0:7].to_numpy(dtype=float)
    
    # 3. 倾向转走向
    dd = M[:, 2]
    M[:, 2] = dip_to_strike_vec(dd)

    # 提取各列参数
    r1 = M[:, 0]
    r2 = M[:, 1]
    ang = M[:, 2]
    r3 = M[:, 3]
    r4 = M[:, 4]
    r5 = M[:, 5]
    r6 = M[:, 6]

    # 4. 角度预处理
    ang_0 = (90 - ang0) if ang0 < 90 else (450 - ang0)
    rad_0 = math.radians(ang_0)

    # ang1 calculation: (270 - ang) % 360
    ang1 = np.where(ang < 270, 360 - (ang + 90), 720 - (90 + ang))

    # 5. 确定左右侧逻辑
    has_left = (r4 != 0)
    has_right = (r6 != 0)
    
    # 计算 rada, rade
    rada = _get_adjusted_angle_vec(ang_0, ang1, invert=False)
    rade = _get_adjusted_angle_vec(ang_0, ang1, invert=True)

    # 6. 向量计算
    # z1: 沿测线位移 (复数表示)
    z1 = r1 * np.exp(1j * rad_0)
    
    # 垂直方向单位向量
    vec_perp_left = np.exp(1j * (rad_0 + math.pi/2))
    vec_perp_right = np.exp(1j * (rad_0 - math.pi/2))
    
    # 倾斜方向单位向量
    vec_skew_a = np.exp(1j * rada)
    vec_skew_e = np.exp(1j * rade)

    # 初始化结果数组
    X1, Y1, X2, Y2 = np.zeros(n), np.zeros(n), np.zeros(n), np.zeros(n)

    # Case 1: Left Only (has_left & !has_right)
    mask_l = has_left & (~has_right)
    if np.any(mask_l):
        # s1 = z1 + r2*L_perp + r3*L_skew
        # s2 = s1 + r4*L_skew
        _z1 = z1[mask_l]
        _r2 = r2[mask_l]
        _r3 = r3[mask_l]
        _r4 = r4[mask_l]
        _v_skew = vec_skew_a[mask_l]
        
        s1 = _z1 + _r2 * vec_perp_left + _r3 * _v_skew
        s2 = s1 + _r4 * _v_skew
        
        X1[mask_l] = s1.real
        Y1[mask_l] = s1.imag
        X2[mask_l] = s2.real
        Y2[mask_l] = s2.imag

    # Case 2: Right Only (!has_left & has_right)
    mask_r = (~has_left) & has_right
    if np.any(mask_r):
        # s1 = z1 + r2*R_perp + r5*R_skew
        # s2 = s1 + r6*R_skew
        _z1 = z1[mask_r]
        _r2 = r2[mask_r]
        _r5 = r5[mask_r]
        _r6 = r6[mask_r]
        _v_skew = vec_skew_e[mask_r]
        
        s1 = _z1 + _r2 * vec_perp_right + _r5 * _v_skew
        s2 = s1 + _r6 * _v_skew
        
        X1[mask_r] = s1.real
        Y1[mask_r] = s1.imag
        X2[mask_r] = s2.real
        Y2[mask_r] = s2.imag

    # Case 3: Both (has_left & has_right)
    mask_b = has_left & has_right
    if np.any(mask_b):
        # s_left = z1 + r2*L_perp + (r3+r4)*L_skew
        # s_right = z1 + r2*R_perp + (r5+r6)*R_skew
        _z1 = z1[mask_b]
        _r2 = r2[mask_b]
        _r3 = r3[mask_b]
        _r4 = r4[mask_b]
        _r5 = r5[mask_b]
        _r6 = r6[mask_b]
        
        s_left = _z1 + _r2 * vec_perp_left + (_r3 + _r4) * vec_skew_a[mask_b]
        s_right = _z1 + _r2 * vec_perp_right + (_r5 + _r6) * vec_skew_e[mask_b]
        
        X1[mask_b] = s_left.real
        Y1[mask_b] = s_left.imag
        X2[mask_b] = s_right.real
        Y2[mask_b] = s_right.imag

    # 组合结果
    XY = np.column_stack((X1, Y1, X2, Y2))
    return ang0, n, XY
