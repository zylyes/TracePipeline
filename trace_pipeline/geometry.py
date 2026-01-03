"""几何计算：迹线端点与走向转换。

该模块包含向量化实现，用于根据 Excel 中给定的测线/节理参数计算迹线的两个端点坐标。
主要功能：
- 将倾向（dip）转换为走向（strike）向量
- 根据测线基准角度和节理角度关系调整角度以获得正确方向
- 使用复数向量运算批量计算二维坐标，减少显式三角运算带来的复杂性
"""
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
    # 确保输入为 ndarray 以便进行向量化操作
    targets = np.asarray(target_angles)

    # 逻辑说明：根据基准角 base_angle 的取值区域来判断哪些 target_angles
    # 需要加上 180 度以确保方向指向期望的一侧。
    # invert 参数用于交换加/不加 180 的逻辑（用于左右侧区分）。
    if base_angle <= 180:
        # 当 base_angle 在 [0,180] 区间时，判断 targets 是否落在 (base, base+180)
        cond = (base_angle < targets) & (targets < (180 + base_angle))
        if not invert:
            # rada (invert=False): 若条件成立则保持 targets，否则加 180
            res = np.where(cond, targets, targets + 180)
        else:
            # rade (invert=True): 若条件成立则加 180，否则保持 targets
            res = np.where(cond, targets + 180, targets)
    else:
        # 当 base_angle 在 (180,360] 区间时，对应区间判断反向
        cond = ((base_angle - 180) < targets) & (targets < base_angle)
        if not invert:
            # rada (invert=False): 若条件成立则加 180，否则保持
            res = np.where(cond, targets + 180, targets)
        else:
            # rade (invert=True): 若条件成立则保持，否则加 180
            res = np.where(cond, targets, targets + 180)

    # 返回弧度制数组，供后续复数向量运算使用
    return np.radians(res)


def dip_to_strike_vec(dd: np.ndarray) -> np.ndarray:
    """
    倾向转走向（向量化）。
    
    逻辑:
    >= 270: dd - 270
    90 <= dd < 270: dd - 90
    < 90: dd + 90
    """
    # 根据给定规则将倾向角（dip）转换为走向角（strike）
    # 使用向量化掩码比循环更高效
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
    # 从表头尝试解析测线走向（ang0）和迹线数量 n
    try:
        ang0 = float(df.iloc[0, 7])
        n_raw = df.iloc[0, 8]
        # 使用 pandas.to_numeric 处理可能的字符串或异常格式
        n = int(pd.to_numeric(n_raw))
    except (ValueError, IndexError) as e:
        raise ValueError(f"Failed to parse header info (strike/count) from Excel: {e}")

    # 2. 提取数据矩阵
    # 列索引映射: 0:r1, 1:r2, 2:ang(dip), 3:r3, 4:r4, 5:r5, 6:r6
    # 确保只取前 n 行（如果 DataFrame 有多余行）
    # 读取前 n 行、前 7 列作为参数矩阵，列含义在文件顶部有注释
    M = df.iloc[:n, 0:7].to_numpy(dtype=float)
    
    # 3. 倾向转走向
    # 第三列为倾向（dip），先将其转为走向（strike）以便后续角度计算
    dd = M[:, 2]
    M[:, 2] = dip_to_strike_vec(dd)

    # 提取各列参数
    # 将矩阵列拆解为命名变量便于阅读
    r1 = M[:, 0]
    r2 = M[:, 1]
    ang = M[:, 2]
    r3 = M[:, 3]
    r4 = M[:, 4]
    r5 = M[:, 5]
    r6 = M[:, 6]

    # 4. 角度预处理
    # 计算测线基准角 ang_0（用于将测线方向转为数学角度系），并转换为弧度
    ang_0 = (90 - ang0) if ang0 < 90 else (450 - ang0)
    rad_0 = math.radians(ang_0)

    # ang1 calculation: (270 - ang) % 360
    # ang1 的计算用于将节理走向角按特定规则映射到 0-360 区间，便于后续调整
    ang1 = np.where(ang < 270, 360 - (ang + 90), 720 - (90 + ang))

    # 5. 确定左右侧逻辑
    # 判断左侧/右侧数据是否存在（通过 r4, r6 是否为 0 判定）
    has_left = (r4 != 0)
    has_right = (r6 != 0)

    # 计算用于倾斜方向的两个角度向量（弧度制），分别对应左右两侧的方向调整
    rada = _get_adjusted_angle_vec(ang_0, ang1, invert=False)
    rade = _get_adjusted_angle_vec(ang_0, ang1, invert=True)

    # 6. 向量计算
    # z1: 沿测线位移 (复数表示)
    # z1 表示沿测线方向的位移（复数表示法：实部为 x，虚部为 y）
    z1 = r1 * np.exp(1j * rad_0)

    # 垂直方向单位向量（左/右）用于将 r2 投影到垂直测线的方向
    vec_perp_left = np.exp(1j * (rad_0 + math.pi/2))
    vec_perp_right = np.exp(1j * (rad_0 - math.pi/2))

    # 倾斜方向单位向量（节理方向经过角度调整后的向量）
    vec_skew_a = np.exp(1j * rada)
    vec_skew_e = np.exp(1j * rade)

    # 初始化结果数组
    # 初始化结果数组
    X1, Y1, X2, Y2 = np.zeros(n), np.zeros(n), np.zeros(n), np.zeros(n)

    # Case 1: Left Only (has_left & !has_right)
    mask_l = has_left & (~has_right)
    if np.any(mask_l):
        # 左侧只有数据的情况（has_left & !has_right）
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
        # 右侧只有数据的情况（!has_left & has_right）
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
        # 两侧都有数据的情况（has_left & has_right）
        # 左侧的端点和右侧的端点分别按各自的倾斜方向计算
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
    # 将结果组合为 (N,4) 数组并返回原始测线走向与数量
    XY = np.column_stack((X1, Y1, X2, Y2))
    return ang0, n, XY
