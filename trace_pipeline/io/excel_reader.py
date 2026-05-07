"""Excel 迹线表读取 — 候选扩展名 + 工作表回退。"""
from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)

EXCEL_ENGINES: tuple[tuple[str, str], ...] = (
    (".xlsx", "openpyxl"),
    (".xls", "xlrd"),
)

__all__ = ["read_trace_excel"]


def read_trace_excel(
    base_path: str,
    table_stem: str,
    sheet: str | None = None,
) -> pd.DataFrame:
    """读取迹线 Excel 表，优先 .xlsx，缺失则回退 .xls；sheet 不存在时回退首表。

    Args:
        base_path: 输入目录路径。
        table_stem: 不含扩展名的文件名。
        sheet: 工作表名；为 None 或不存在时回退到第一个 sheet。

    Returns:
        无表头的原始 DataFrame。

    Raises:
        FileNotFoundError: .xlsx 与 .xls 均不存在。
        ValueError: 文件存在但无法读取。
    """
    base = Path(base_path)
    # 候选：(path, engine, sheet_arg)，每个文件尝试两次（指定 sheet / 第一个 sheet）
    attempts: list[tuple[Path, str, object]] = []
    found_paths: list[Path] = []
    for ext, engine in EXCEL_ENGINES:
        path = base / f"{table_stem}{ext}"
        if not path.is_file():
            continue
        found_paths.append(path)
        attempts.append((path, engine, sheet if sheet else 0))
        if sheet:
            attempts.append((path, engine, 0))

    if not found_paths:
        raise FileNotFoundError(
            f"在 {base_path} 下未找到 {table_stem}.xlsx 或 {table_stem}.xls"
        )

    last_error: Exception | None = None
    errors: list[str] = []
    for path, engine, sheet_arg in attempts:
        logger.debug("读取文件: %s (引擎=%s, sheet=%r)", path, engine, sheet_arg)
        try:
            return pd.read_excel(path, engine=engine, sheet_name=sheet_arg, header=None)
        except ValueError as exc:
            # 工作表名不存在 → 会被下一个 attempt (sheet_arg=0) 覆盖
            logger.debug("读取 %s 失败（将尝试回退）: %s", path, exc)
            last_error = exc
            errors.append(f"{path.name} sheet={sheet_arg!r}: {exc}")
        except Exception as exc:
            logger.warning("读取 %s 失败 (%s)", path, exc)
            last_error = exc
            errors.append(f"{path.name} sheet={sheet_arg!r}: {exc}")

    found = ", ".join(p.name for p in found_paths)
    detail = "; ".join(errors[-3:])
    raise ValueError(
        f"找到 {found}，但读取失败"
        + (f": {detail}" if detail else "")
    ) from last_error
