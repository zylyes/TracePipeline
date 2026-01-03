"""迹线处理脚本：读取 Excel、计算几何、导出表格与图片。"""
import json
import math
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Sequence, Tuple
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# 允许图形与控制台输出展示中文
plt.rcParams["font.sans-serif"] = [
    "SimHei",
    "Microsoft YaHei",
    "Arial Unicode MS",
]
plt.rcParams["axes.unicode_minus"] = False


# ------------------------ 配置与路径 ------------------------
CONFIG_PATH = Path(__file__).with_name("config.json")

DEFAULT_CONFIG: Dict[str, Any] = {
    "input_dir": r"D:\作业\毕业论文\周咏霖\input",
    "output_dir": r"D:\作业\毕业论文\周咏霖\output",
    "file_name": "Outcrop",
    "excel_base": "O76_process",
    "outcrop_name": "O76",
    "process_all": True,
}


def load_config(config_path: str | Path | None = None) -> Dict[str, Any]:
    """从 JSON 读取配置，缺失时使用默认值。"""

    path = Path(config_path) if config_path else CONFIG_PATH
    if not path.exists():
        return DEFAULT_CONFIG.copy()

    with path.open("r", encoding="utf-8") as fp:
        data = json.load(fp)
    if not isinstance(data, dict):
        raise ValueError(f"Config file {path} must contain a JSON object")

    merged = DEFAULT_CONFIG.copy()
    merged.update({k: v for k, v in data.items() if k in merged})
    return merged


def ensure_io_paths(input_dir: str, output_dir: str) -> Tuple[str, str]:
    """返回可用的输入/输出目录。"""

    cwd = os.getcwd()
    in_dir = input_dir if os.path.isdir(input_dir) else cwd
    out_dir = output_dir if os.path.isdir(output_dir) else cwd
    return in_dir, out_dir


def find_trace_tables(
    input_dir: str,
    suffix: str = "_process",
    extensions: Tuple[str, ...] = (".xlsx", ".xls"),
) -> list[Tuple[str, str]]:
    """在目录中查找符合命名规则的迹线表，返回 (excel_base, outcrop_name)。"""

    if not os.path.isdir(input_dir):
        return []

    matched: dict[str, Tuple[str, str]] = {}
    for name in sorted(os.listdir(input_dir)):
        base, ext = os.path.splitext(name)
        if ext.lower() not in extensions or not base.endswith(suffix):
            continue
        key = base.lower()
        if key not in matched:
            outcrop_name = base[: -len(suffix)]
            matched[key] = (base, outcrop_name)

    return list(matched.values())


def load_trace_table(base_path: str, excel_base: str, sheet: str) -> pd.DataFrame:
    """读取迹线 Excel 表，优先 .xlsx，缺失时回退 .xls。"""

    excel_path_xlsx = os.path.join(base_path, excel_base + ".xlsx")
    excel_path_xls = os.path.join(base_path, excel_base + ".xls")

    def read(path: str, engine: str) -> pd.DataFrame:
        try:
            return pd.read_excel(path, engine=engine, sheet_name=sheet, header=None)
        except ValueError:
            return pd.read_excel(path, engine=engine, sheet_name=0, header=None)

    if os.path.exists(excel_path_xlsx):
        return read(excel_path_xlsx, engine="openpyxl")
    if os.path.exists(excel_path_xls):
        return read(excel_path_xls, engine="xlrd")
    raise FileNotFoundError(f"Missing {excel_base}.xlsx or {excel_base}.xls under {base_path}")


# ------------------------ 几何计算 ------------------------
def compute_joint_endpoints(
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

    if ang0 < 90:
        ang_0 = 90 - ang0
    else:
        ang_0 = 450 - ang0
    rad_0 = math.radians(ang_0)

    if ang < 270:
        ang1 = 360 - (ang + 90)
    else:
        ang1 = 720 - (90 + ang)

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


def convert_dip_to_strike(dd: float) -> float:
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

    ang0 = float(df.iloc[0, 7])
    n_raw = df.iloc[0, 8]
    n_num = pd.to_numeric([n_raw], errors="coerce")[0]
    if np.isnan(n_num):
        raise ValueError(f"Row 1 col 9 is not numeric: {n_raw!r}")
    n = int(n_num)

    M = df.iloc[:, 0:7].to_numpy(dtype=float)
    dd = df.iloc[:, 2].to_numpy(dtype=float)
    strike_angles = np.array([convert_dip_to_strike(x) for x in dd])
    M[:, 2] = strike_angles[: M.shape[0]]

    XY = np.zeros((n, 4), dtype=float)

    for m in range(n):
        X1, Y1, X2, Y2 = compute_joint_endpoints(
            ang0, M[m, 0], M[m, 1], M[m, 2], M[m, 3], M[m, 4], M[m, 5], M[m, 6]
        )
        XY[m, :] = [X1, Y1, X2, Y2]

    return ang0, n, XY


# ------------------------ 数据包装与 Excel 输出 ------------------------
@dataclass
class TraceData:
    strike_deg: float
    trace_count: int
    xy: np.ndarray


def load_trace_data(cfg: dict) -> TraceData:
    """读取 Excel 表并封装 TraceData。"""

    df = load_trace_table(cfg["input_dir"], cfg["excel_base"], cfg["outcrop_name"])
    ang0, n, XY = parse_trace_table(df)

    return TraceData(
        strike_deg=ang0,
        trace_count=n,
        xy=XY,
    )


def write_excel_sections(
    excel_path: str,
    sheet_name: str,
    sections: Sequence[Tuple[pd.DataFrame, int, int, bool]],
):
    """将多个 DataFrame 写入同一工作表的不同区域。"""

    os.makedirs(os.path.dirname(excel_path) or ".", exist_ok=True)
    with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:
        for df, startrow, startcol, header in sections:
            df.to_excel(
                writer,
                sheet_name=sheet_name,
                index=False,
                header=header,
                startrow=startrow,
                startcol=startcol,
            )


def build_excel_sections(trace: TraceData, rotated_xy: np.ndarray) -> Sequence[Tuple[pd.DataFrame, int, int, bool]]:
    """组装 Excel 写入所需的分块信息。"""

    base_info = pd.DataFrame({"测线走向(°)": [trace.strike_deg], "迹线数量": [trace.trace_count]})
    raw_df = pd.DataFrame(trace.xy, columns=["起点X", "起点Y", "终点X", "终点Y"])
    rot_df = pd.DataFrame(rotated_xy, columns=["旋转后起点X", "旋转后起点Y", "旋转后终点X", "旋转后终点Y"])
    return [
        (base_info, 0, 0, True),
        (raw_df, 3, 0, True),
        (rot_df, 3, 6, True),
    ]


def export_figure(fig, output_dir: str, filename: str, dpi: int = 300) -> str:
    """导出图片到输出目录并返回完整路径。"""

    os.makedirs(output_dir, exist_ok=True)
    full_path = os.path.join(output_dir, filename)
    fig.tight_layout()
    fig.savefig(full_path, dpi=dpi, facecolor="white")
    return full_path


# ------------------------ 坐标平移与旋转 ------------------------
def strike_to_rotation_rad(ang0: float) -> float:
    if ang0 > 270:
        return -(360 - ang0) * math.pi / 180.0
    if ang0 > 180:
        return (ang0 - 180) * math.pi / 180.0
    if ang0 > 90:
        return -(180 - ang0) * math.pi / 180.0
    return ang0 * math.pi / 180.0


def shift_lines_to_positive(XY: np.ndarray, padding: float = 1.0) -> np.ndarray:
    min_x = abs(np.round(np.min(XY[:, [0, 2]]))) + padding
    min_y = abs(np.round(np.min(XY[:, [1, 3]]))) + padding
    return XY + np.array([min_x, min_y, min_x, min_y])


def rotate_lines_and_shift(lines: np.ndarray, ang0: float) -> np.ndarray:
    angle = strike_to_rotation_rad(ang0)
    rot_mat = np.array([
        [math.cos(angle), -math.sin(angle)],
        [math.sin(angle), math.cos(angle)],
    ])
    rot_lines = (lines.reshape(-1, 2) @ rot_mat.T).reshape(lines.shape)

    min_rot_x = abs(np.round(np.min(rot_lines[:, [0, 2]])))
    min_rot_y = abs(np.round(np.min(rot_lines[:, [1, 3]])))
    return rot_lines + np.array([min_rot_x, min_rot_y, min_rot_x, min_rot_y])


def normalize_and_rotate_lines(XY: np.ndarray, ang0: float, padding: float = 1.0) -> np.ndarray:
    shifted = shift_lines_to_positive(XY, padding=padding)
    return rotate_lines_and_shift(shifted, ang0)


# ------------------------ 绘图工具 ------------------------
def build_nan_separated_lines(XY: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    n = XY.shape[0]
    X_plot = np.column_stack([XY[:, 0], XY[:, 2], np.full((n,), np.nan)]).ravel()
    Y_plot = np.column_stack([XY[:, 1], XY[:, 3], np.full((n,), np.nan)]).ravel()
    return X_plot, Y_plot


def style_trace_axes(ax: plt.Axes) -> plt.Axes:
    ax.set_aspect("equal")
    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_linewidth(1)
    ax.tick_params(labelsize=14)
    ax.set_facecolor("white")
    ax.get_figure().patch.set_facecolor("white")
    return ax


def render_trace_plot(X_plot, Y_plot, title: str, output_dir: str, filename: str, dpi: int = 300):
    """绘制单张迹线图并导出到指定目录。"""

    fig, ax = plt.subplots(figsize=(24 / 2.54, 12 / 2.54), dpi=dpi)
    ax.plot(X_plot, Y_plot, "-", color=(0, 0, 0), linewidth=1)
    style_trace_axes(ax)
    ax.set_title(title, fontsize=12)
    export_figure(fig, output_dir, filename, dpi=dpi)
    plt.close(fig)


# ------------------------ 主流程 ------------------------
def main(cfg: dict | None = None):
    cfg = cfg or load_config()

    input_dir, output_dir = ensure_io_paths(cfg["input_dir"], cfg["output_dir"])
    discovered = find_trace_tables(input_dir)
    targets = discovered if (cfg.get("process_all") and discovered) else [(cfg["excel_base"], cfg["outcrop_name"])]

    print(f"输入目录：{input_dir}", flush=True)
    print(f"输出目录：{output_dir}", flush=True)
    print(f"待处理文件数：{len(targets)}", flush=True)

    run_summaries: list[dict] = []

    for idx, (excel_base, outcrop_name) in enumerate(targets, start=1):
        run_cfg = {
            **cfg,
            "input_dir": input_dir,
            "output_dir": output_dir,
            "file_name": outcrop_name,
            "excel_base": excel_base,
            "outcrop_name": outcrop_name,
        }

        trace = load_trace_data(run_cfg)

        rotated = normalize_and_rotate_lines(trace.xy, trace.strike_deg)
        X_raw, Y_raw = build_nan_separated_lines(trace.xy)
        X_rot, Y_rot = build_nan_separated_lines(rotated)

        excel_out = os.path.join(output_dir, f"{run_cfg['file_name']}_traces.xlsx")
        sections = build_excel_sections(trace, rotated)
        write_excel_sections(excel_out, run_cfg["outcrop_name"], sections)

        raw_title = f"迹线长度图（数量={trace.trace_count}）"
        raw_name = f"{run_cfg['outcrop_name']}_raw(n={trace.trace_count}).png"
        render_trace_plot(X_raw, Y_raw, raw_title, output_dir, raw_name, dpi=300)

        rot_title = f"迹线长度图（数量={trace.trace_count}）\n标尺（走向={trace.strike_deg}）"
        rot_name = f"{run_cfg['outcrop_name']}_rotated(strike={trace.strike_deg}).png"
        render_trace_plot(X_rot, Y_rot, rot_title, output_dir, rot_name, dpi=600)

        run_summaries.append(
            {
                "excel_base": excel_base,
                "excel_out": excel_out,
                "trace_count": trace.trace_count,
            }
        )

        print(
            f"[{idx}/{len(targets)}] 已处理 {excel_base} -> {excel_out} (迹线数={trace.trace_count})",
            flush=True,
        )

    if not run_summaries:
        print(f"未找到可处理的文件，请检查输入目录：{input_dir}", flush=True)
        return

    lines = [f"处理完成，文件数：{len(run_summaries)}"]

    print("\n".join(lines), flush=True) #输出总结
    
if __name__ == "__main__":
    main()
