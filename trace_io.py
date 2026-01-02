"""路径发现与 Excel 读取的辅助函数。"""
from typing import Tuple, List
import os
import pandas as pd


def ensure_io_paths(input_dir: str, output_dir: str) -> Tuple[str, str, str]:
    """返回可用的输入/输出目录以及当前工作目录作为回退。"""
    cwd = os.getcwd()
    in_dir = input_dir if os.path.isdir(input_dir) else cwd
    out_dir = output_dir if os.path.isdir(output_dir) else cwd
    return in_dir, out_dir, cwd


def find_trace_tables(
    input_dir: str,
    suffix: str = "_process",
    extensions: Tuple[str, ...] = (".xlsx", ".xls"),
) -> List[Tuple[str, str]]:
    """
    在输入目录中查找符合命名规则的迹线表。
    返回 (excel_base, outcrop_name) 对列表。
    """
    if not os.path.isdir(input_dir):
        return []

    matched: dict[str, Tuple[str, str]] = {}
    files = sorted(os.listdir(input_dir))

    for ext in extensions:
        for name in files:
            if not name.lower().endswith(ext):
                continue

            base, _ = os.path.splitext(name)
            if not base.endswith(suffix):
                continue

            key = base.lower()
            if key in matched:
                continue

            outcrop_name = base[: -len(suffix)] if suffix and base.endswith(suffix) else base
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
