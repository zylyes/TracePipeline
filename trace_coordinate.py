# 功能：根据测线与节理参数计算节理线段两端点的平面坐标。
import math
from typing import Tuple


def compute_joint_endpoints(ang0: float, r1: float, r2: float, ang: float, r3: float, r4: float, r5: float, r6: float) -> Tuple[float, float, float, float]:
    """
    依据测线走向、窗口位置、节理倾向/走向与左右/相交迹长，求出节理线段两端点坐标。
      - ang0: 测线走向角度（度）
      - r1: 测线起点到节理交点的距离
      - r2: 测线到节理的垂距（左/右模式都使用）
      - ang: 节理走向角度（度）
      - r3: 左侧起点到交点距离（或左侧部分）
      - r4: 左侧迹长
      - r5: 右侧起点到交点距离（或右侧部分）
      - r6: 右侧迹长

    返回:
      a1, b1, a2, b2: 节理线段两端点坐标 (x1, y1, x2, y2)
    """
    # 将测线方向角转换为计算角（维持与原 MATLAB 逻辑一致）
    if ang0 < 90:
        ang_0 = 90 - ang0
    else:
        ang_0 = 450 - ang0
    rad_0 = math.radians(ang_0)

    # 节理走向角转换为计算角，便于后续向量叠加
    if ang < 270:
        ang1 = 360 - (ang + 90)
    else:
        ang1 = 720 - (90 + ang)

    # 根据左右/相交迹长情况，分别确定左、右侧的旋转弧度
    rada = None
    rade = None
    if (r4 != 0) and (r6 == 0):
        # 左迹长
        if ang_0 <= 180:
            if (ang_0 < ang1) and (ang1 < (180 + ang_0)):
                rada = math.radians(ang1)
            else:
                rada = math.radians(ang1 + 180)
        else:
            if ((ang_0 - 180) < ang1) and (ang1 < ang_0):
                rada = math.radians(ang1 + 180)
            else:
                rada = math.radians(ang1)
    elif (r4 == 0) and (r6 != 0):
        # 右迹长
        if ang_0 <= 180:
            if (ang_0 < ang1) and (ang1 < (180 + ang_0)):
                rade = math.radians(ang1 + 180)
            else:
                rade = math.radians(ang1)
        else:
            if ((ang_0 - 180) < ang1) and (ang1 < ang_0):
                rade = math.radians(ang1)
            else:
                rade = math.radians(ang1 + 180)
    else:  # (r4 != 0) and (r6 != 0): 相交迹长：左右并存
        if ang_0 <= 180:
            if (ang_0 < ang1) and (ang1 < (180 + ang_0)):
                rada = math.radians(ang1)
                rade = math.radians(ang1 + 180)
            else:
                rada = math.radians(ang1 + 180)
                rade = math.radians(ang1)
        else:
            if ((ang_0 - 180) < ang1) and (ang1 < ang_0):
                rada = math.radians(ang1 + 180)
                rade = math.radians(ang1)
            else:
                rada = math.radians(ang1)
                rade = math.radians(ang1 + 180)

    # 复数向量叠加，先得到交点再延伸到两端点
    z1 = complex(r1 * math.cos(rad_0), r1 * math.sin(rad_0))

    if (r4 != 0) and (r6 == 0):
        # 左迹长
        z2 = complex(r2 * math.cos(math.pi / 2 + rad_0), r2 * math.sin(math.pi / 2 + rad_0))
        z3 = complex(r3 * math.cos(rada), r3 * math.sin(rada))
        z4 = complex(r4 * math.cos(rada), r4 * math.sin(rada))
        s1 = z1 + z2 + z3
        s2 = s1 + z4
        a1, b1 = s1.real, s1.imag
        a2, b2 = s2.real, s2.imag
    elif (r4 == 0) and (r6 != 0):
        # 右迹长
        z2 = complex(r2 * math.cos(rad_0 - math.pi / 2), r2 * math.sin(rad_0 - math.pi / 2))
        z3 = complex(r5 * math.cos(rade), r5 * math.sin(rade))
        z4 = complex(r6 * math.cos(rade), r6 * math.sin(rade))
        s1 = z1 + z2 + z3
        s2 = s1 + z4
        a1, b1 = s1.real, s1.imag
        a2, b2 = s2.real, s2.imag
    else:
        # 相交迹长：左右并行计算
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
