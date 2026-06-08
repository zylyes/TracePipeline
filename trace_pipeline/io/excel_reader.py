"""Excel 迹线表读取 — 候选扩展名 + 工作表回退 + 格式校验。"""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)

EXCEL_ENGINES: tuple[tuple[str, str], ...] = (
    (".xlsx", "openpyxl"),
    (".xls", "xlrd"),
)

_MIN_COLUMNS = 4
_MAX_SKIP_ROWS = 2

__all__ = ["read_trace_excel", "TraceValidationError"]


class TraceValidationError(ValueError):
    """迹线表格式校验失败。

    继承 ValueError 以兼容现有调用方,但作为独立类型,使读取逻辑
    能区分"数据格式错误"(应直接上抛)与"工作表不存在"(可回退首表)。
    """


def read_trace_excel(
    base_path: str,
    table_stem: str,
    sheet: str | int | None = None,
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
        raise FileNotFoundError(f"在 {base_path} 下未找到 {table_stem}.xlsx 或 {table_stem}.xls")

    last_error: Exception | None = None
    errors: list[str] = []
    for path, engine, sheet_arg in attempts:
        logger.debug("读取文件: %s (引擎=%s, sheet=%r)", path, engine, sheet_arg)
        try:
            df = pd.read_excel(path, engine=engine, sheet_name=sheet_arg, header=None)
            _validate_trace_dataframe(df, path)
            return df
        except TraceValidationError:
            # 数据格式错误(列数不足/NaN/Inf):直接上抛,不回退首表,避免掩盖真实错误
            raise
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
        f"找到 {found}，但读取失败" + (f": {detail}" if detail else "")
    ) from last_error


def _validate_trace_dataframe(df: pd.DataFrame, path: Path) -> None:
    """校验迹线 DataFrame 的基本格式：最少列数和数值有效性。

    Args:
        df: 读取的原始 DataFrame（无表头）。
        path: 数据文件路径（仅用于日志）。

    Raises:
        ValueError: 列数不足或前4列包含非数值数据。
    """
    if df.shape[1] < _MIN_COLUMNS:
        raise TraceValidationError(
            f"迹线表 {path.name} 至少需要 {_MIN_COLUMNS} 列 (x1, y1, x2, y2)，"
            f"实际仅有 {df.shape[1]} 列"
        )

    first_rows = df.head(_MAX_SKIP_ROWS)
    numeric_count = 0
    for col in range(min(_MIN_COLUMNS, df.shape[1])):
        try:
            vals = pd.to_numeric(first_rows.iloc[:, col], errors="coerce")
            numeric_count += vals.notna().sum()
        except Exception:
            pass

    total_cells = min(len(first_rows), _MAX_SKIP_ROWS) * _MIN_COLUMNS
    if total_cells > 0 and numeric_count / total_cells < 0.5:
        logger.warning(
            "迹线表 %s 前%d行中数值占比过低 (%d/%d)，可能包含非数据行",
            path.name,
            _MAX_SKIP_ROWS,
            numeric_count,
            total_cells,
            extra={
                "stage": "validate_trace",
                "path": str(path),
                "numeric_ratio": numeric_count / total_cells,
            },
        )
