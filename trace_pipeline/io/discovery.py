"""输入目录扫描 — 发现迹线表文件。"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import List, NamedTuple, Tuple

logger = logging.getLogger(__name__)

EXCEL_EXTENSIONS: Tuple[str, ...] = (".xlsx", ".xls")
TRACE_SUFFIX = "_process"

__all__ = ["TRACE_SUFFIX", "TraceFile", "find_trace_tables"]


class TraceFile(NamedTuple):
    """发现的迹线表文件描述。"""
    stem: str
    outcrop: str


def find_trace_tables(
    input_dir: str,
    suffix: str = TRACE_SUFFIX,
    extensions: Tuple[str, ...] = EXCEL_EXTENSIONS,
) -> List[TraceFile]:
    """扫描输入目录，返回匹配的迹线表列表。

    匹配规则：
      - 文件名以 suffix 结尾（不含扩展名）
      - 扩展名在 extensions 集合中
      - 同名文件（不同扩展名）按首次发现去重（大小写不敏感）

    Returns:
        按 outcrop 排序的 TraceFile 列表；目录不存在或无匹配时返回空列表。
    """
    path = Path(input_dir)
    if not path.is_dir():
        logger.warning("输入目录不存在: %s", input_dir)
        return []

    matched: dict = {}
    for ext in extensions:
        for file_path in sorted(path.glob(f"*{suffix}{ext}")):
            stem = file_path.stem
            key = stem.lower()
            if key not in matched:
                outcrop = stem[: -len(suffix)] if stem.endswith(suffix) else stem
                matched[key] = TraceFile(stem=stem, outcrop=outcrop)

    result = [matched[k] for k in sorted(matched)]
    if result:
        logger.info(
            "发现 %d 个迹线表: %s",
            len(result), ", ".join(tf.stem for tf in result),
        )
    else:
        logger.warning("在 %s 中未发现匹配的迹线表（后缀=%s）", input_dir, suffix)
    return result
