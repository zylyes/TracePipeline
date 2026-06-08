"""Excel 数据读取服务（支持多工作表格式）。"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from backend.utils.path_utils import resolve_path, error_response, validate_outcrop_name

logger = logging.getLogger(__name__)

# 前端分区名 -> Excel Sheet 名 映射
SECTION_MAP = {
    "基本信息": "基本信息",
    "原始坐标": "原始端点坐标",
    "旋转坐标": "旋转后端点坐标",
    "走向与长度": "走向与长度",
    "裂隙情况": "裂隙情况",
    "计算数据": "计算数据",
    "节点统计": "节点统计",
    "节点明细": "节点明细",
    "节点交点": "节点交点",
}

# 输入文件标准列名
INPUT_HEADERS = [
    "r1-沿测线位移",
    "r2-垂直测线位移",
    "倾向",
    "r4-左侧迹长1",
    "r5-左侧迹长2",
    "r6-右侧迹长1",
    "r7-右侧迹长2",
    "测线走向",
    "迹线条数",
]


class DataService:
    """读取 output/{outcrop}_traces.xlsx（多工作表）或 input/{outcrop}_process.xlsx 并分页返回。"""

    def __init__(self, output_dir: str = "output", input_dir: str = "input") -> None:
        self._output_dir = resolve_path(output_dir)
        self._input_dir = resolve_path(input_dir)

    @staticmethod
    def _paginate(data: list, page: int, page_size: int) -> tuple[list, int]:
        """按页切片,返回 (当前页数据, 总条数)。"""
        total = len(data)
        start = (page - 1) * page_size
        return data[start:start + page_size], total

    def get_data(
        self,
        outcrop: str,
        section: str,
        page: int = 1,
        page_size: int = 20,
        source: str = "output",
    ) -> dict[str, Any]:
        """读取指定露头 Excel 的指定分区。"""
        try:
            validate_outcrop_name(outcrop)
        except ValueError as exc:
            return error_response(str(exc))
        if source == "input":
            return self._get_input_data(outcrop, page, page_size)

        # 读取 output 目录下的多工作表处理结果
        path = self._output_dir / f"{outcrop}_traces.xlsx"
        if not path.exists():
            logger.warning(
                "get_data [%s/%s] 失败: 文件不存在", outcrop, section,
                extra={"stage": "data_get", "outcrop": outcrop, "section": section, "source": source, "path": str(path)},
            )
            return error_response(f"文件不存在: {path}")

        sheet_name = SECTION_MAP.get(section, section)
        try:
            # header=1: 跳过第1行标题，将第2行作为表头
            df = pd.read_excel(path, sheet_name=sheet_name, header=1)
        except ValueError:
            # Sheet 不存在（旧格式单工作表文件）
            logger.warning(
                "get_data [%s/%s] 失败: 工作表不存在", outcrop, section,
                extra={"stage": "data_get", "outcrop": outcrop, "section": section, "sheet": sheet_name},
            )
            return error_response(f"工作表 '{sheet_name}' 不存在，请重新处理该露头以生成新格式文件")
        except Exception as exc:
            logger.warning(
                "get_data [%s/%s] 失败: %s", outcrop, section, exc,
                extra={"stage": "data_get", "outcrop": outcrop, "section": section, "error": str(exc)},
            )
            return error_response(str(exc))

        data = df.to_dict("records")
        page_data, total = self._paginate(data, page, page_size)

        logger.debug(
            "get_data [%s/%s] page=%d: %d/%d 条",
            outcrop, section, page, len(page_data), total,
            extra={
                "stage": "data_get",
                "outcrop": outcrop,
                "section": section,
                "source": source,
                "page": page,
                "page_size": page_size,
                "total": total,
                "returned": len(page_data),
                "column_count": len(df.columns),
            },
        )
        return {
            "outcrop": outcrop,
            "section": section,
            "page": page,
            "page_size": page_size,
            "total": total,
            "data": page_data,
            "columns": list(df.columns),
        }

    def _get_input_data(self, outcrop: str, page: int, page_size: int) -> dict[str, Any]:
        """读取 input 目录下的原始输入 Excel。"""
        table_stem = f"{outcrop}_process"
        path = self._input_dir / f"{table_stem}.xls"
        if not path.exists():
            path = self._input_dir / f"{table_stem}.xlsx"
            if not path.exists():
                return error_response(f"输入文件不存在: {self._input_dir / table_stem}.xls/.xlsx")

        try:
            df = pd.read_excel(path, sheet_name=outcrop, header=None)
        except Exception:
            try:
                df = pd.read_excel(path, header=None)
            except Exception as exc:
                return error_response(str(exc))

        if len(df) < 1:
            return error_response("输入文件为空")

        headers = INPUT_HEADERS
        data = []
        for i in range(len(df)):
            row = df.iloc[i]
            if row.isna().all():
                continue
            record = {}
            for j, h in enumerate(headers):
                if j >= len(row):
                    break
                val = row.iloc[j]
                record[h] = float(val) if pd.notna(val) and isinstance(val, (int, float, np.integer)) else (str(val) if pd.notna(val) else "")
            if record:
                data.append(record)

        page_data, total = self._paginate(data, page, page_size)

        return {
            "outcrop": outcrop,
            "section": "原始输入",
            "page": page,
            "page_size": page_size,
            "total": total,
            "data": page_data,
            "columns": headers,
        }

    def set_input_dir(self, path: str) -> None:
        """动态更新输入目录。"""
        self._input_dir = resolve_path(path)

    def update_dirs(self, output_dir: str, input_dir: str) -> None:
        """同时更新输入/输出目录。"""
        self._output_dir = resolve_path(output_dir)
        self._input_dir = resolve_path(input_dir)
