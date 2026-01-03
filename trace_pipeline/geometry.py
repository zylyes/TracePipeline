"""几何计算：迹线端点与走向转换。"""
from __future__ import annotations

import math
import numpy as np
import pandas as pd
from typing import Tuple


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
    """依据测线走向与左右/相交迹长计算节理端点坐标。"""

    # 将走向转为与三角函数匹配的角度体系
    if ang0 < 90:
        ang_0 = 90 - ang0
    else:
        ang_0 = 450 - ang0
    rad_0 = math.radians(ang_0)

    if ang < 270:
        ang1 = 360 - (ang + 90)
    else:
        ang1 = 720 - (90 + ang)

    # 根据左右侧/交叉情况确定旋转角
    rada = None
    rade = None
    if (r4 != 0) and (r6 == 0):
        if ang_0 <= 180:
            rada = math.radians(ang1 if (ang_0 < ang1) and (ang1 < (180 + ang_0)) else ang1 + 180)
        else:
            rada = math.radians(ang1 + 180 if ((ang_0 - 180) < ang1) and (ang1 < ang_0) else ang1)
    elif (r4 == 0) and (r6 != 0):
        if ang_0 <= 180:
            rade = math.radians(ang1 + 180 if (ang_0 < ang1) and (ang1 < (180 + ang_0)) else ang1)
        else:
            rade = math.radians(ang1 if ((ang_0 - 180) < ang1) and (ang1 < ang_0) else ang1 + 180)
    else:
        if ang_0 <= 180:
            rada = math.radians(ang1 if (ang_0 < ang1) and (ang1 < (180 + ang_0)) else ang1 + 180)
            rade = math.radians(ang1 + 180 if (ang_0 < ang1) and (ang1 < (180 + ang_0)) else ang1)
        else:
            rada = math.radians(ang1 + 180 if ((ang_0 - 180) < ang1) and (ang1 < ang_0) else ang1)
            rade = math.radians(ang1 if ((ang_0 - 180) < ang1) and (ang1 < ang_0) else ang1 + 180)

    # 依次把各段向量相加，得到两端点坐标
    z1 = complex(r1 * math.cos(rad_0), r1 * math.sin(rad_0))

    if (r4 != 0) and (r6 == 0):
        z2 = complex(r2 * math.cos(math.pi / 2 + rad_0), r2 * math.sin(math.pi / 2 + rad_0))
        z3 = complex(r3 * math.cos(rada), r3 * math.sin(rada))
        z4 = complex(r4 * math.cos(rada), r4 * math.sin(rada))
        s1 = z1 + z2 + z3
        s2 = s1 + z4
        a1, b1 = s1.real, s1.imag
        a2, b2 = s2.real, s2.imag
    elif (r4 == 0) and (r6 != 0):
        z2 = complex(r2 * math.cos(rad_0 - math.pi / 2), r2 * math.sin(rad_0 - math.pi / 2))
        z3 = complex(r5 * math.cos(rade), r5 * math.sin(rade))
        z4 = complex(r6 * math.cos(rade), r6 * math.sin(rade))
        s1 = z1 + z2 + z3
        s2 = s1 + z4
        a1, b1 = s1.real, s1.imag
        a2, b2 = s2.real, s2.imag
    else:
        y2 = complex(r2 * math.cos(math.pi / 2 + rad_0), r2 * math.sin(math.pi / 2 + rad_0))
        y3 = complex(r3 * math.cos(rada), r3 * math.sin(rada))
        y4 = complex(r4 * math.cos(rada), r4 * math.sin(rada))
        y5 = complex(r2 * math.cos(rad_0 - math.pi / 2), r2 * math.sin(rad_0 - math.pi / 2))
        y6 = complex(r5 * math.cos(rade), r5 * math.sin(rade))
        y7 = complex(r6 * math.cos(rade), r6 * math.sin(rade))

        s_left1 = z1 + y2 + y3
        s_left2 = s_left1 + y4
        s_right1 = z1 + y5 + y6
        s_right2 = s_right1 + y7

        a1, b1 = s_left2.real, s_left2.imag
        a2, b2 = s_right2.real, s_right2.imag

    return a1, b1, a2, b2


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

    # 表头：走向在 (1,8)，条数在 (1,9)
    ang0 = float(df.iloc[0, 7])
    n_raw = df.iloc[0, 8]
    n_num = pd.to_numeric([n_raw], errors="coerce")[0]
    if np.isnan(n_num):
        raise ValueError(f"Row 1 col 9 is not numeric: {n_raw!r}")
    n = int(n_num)

    M = df.iloc[:, 0:7].to_numpy(dtype=float)
    dd = df.iloc[:, 2].to_numpy(dtype=float)
    strike_angles = np.array([dip_to_strike(x) for x in dd])
    M[:, 2] = strike_angles[: M.shape[0]]

    # 按行计算每条迹线的两端点
    XY = np.zeros((n, 4), dtype=float)

    for m in range(n):
        X1, Y1, X2, Y2 = calc_joint_pts(
            ang0, M[m, 0], M[m, 1], M[m, 2], M[m, 3], M[m, 4], M[m, 5], M[m, 6]
        )
        XY[m, :] = [X1, Y1, X2, Y2]

    return ang0, n, XY
