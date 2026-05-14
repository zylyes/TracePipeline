"""Excel 四区数据读取服务。"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)

# 前端分区名 -> Excel 标题名 映射
SECTION_MAP = {
    "基本信息": "基本信息",
    "原始坐标": "原始端点坐标",
    "旋转坐标": "旋转后端点坐标",
    "走向与长度": "走向与长度",
}


class DataService:
    """读取 output/{outcrop}_traces.xlsx 并分页返回。"""

    def __init__(self, output_dir: str = "output") -> None:
        self._output_dir = Path(output_dir)

    def get_data(self, outcrop: str, section: str, page: int = 1, page_size: int = 20) -> dict[str, Any]:
        """读取指定露头 Excel 的指定分区。"""
        path = self._output_dir / f"{outcrop}_traces.xlsx"
        if not path.exists():
            return {"error": f"文件不存在: {path}"}

        try:
            df = pd.read_excel(path, sheet_name=outcrop, header=None)
        except Exception as exc:
            return {"error": str(exc)}

        sections = self._parse_sections(df)

        if section not in sections:
            return {"error": f"未知分区: {section}"}

        data = sections[section]
        total = len(data)
        start = (page - 1) * page_size
        end = start + page_size
        page_data = data[start:end]

        return {
            "outcrop": outcrop,
            "section": section,
            "page": page,
            "page_size": page_size,
            "total": total,
            "data": page_data,
            "columns": list(data[0].keys()) if data else [],
        }

    def _parse_sections(self, df: pd.DataFrame) -> dict[str, list[dict[str, Any]]]:
        """解析 Excel 为四区数据。"""
        sections: dict[str, list[dict[str, Any]]] = {
            "基本信息": [],
            "原始坐标": [],
            "旋转坐标": [],
            "走向与长度": [],
        }

        # 建立标题行索引：Excel标题 -> 行号
        excel_titles: dict[str, int] = {}
        for idx, row in df.iterrows():
            val = str(row.iloc[0]) if pd.notna(row.iloc[0]) else ""
            if val in SECTION_MAP.values():
                excel_titles[val] = idx

        # 基本信息
        if "基本信息" in excel_titles:
            idx = excel_titles["基本信息"]
            header_row = df.iloc[idx + 1]
            data_row = df.iloc[idx + 2] if idx + 2 < len(df) else None
            if data_row is not None:
                sections["基本信息"] = [
                    {
                        str(header_row.iloc[i]): str(data_row.iloc[i]) if pd.notna(data_row.iloc[i]) else ""
                        for i in range(len(header_row))
                        if pd.notna(header_row.iloc[i])
                    }
                ]

        # 原始坐标
        if "原始端点坐标" in excel_titles:
            idx = excel_titles["原始端点坐标"]
            sections["原始坐标"] = self._parse_data_block(df, idx)

        # 旋转坐标
        if "旋转后端点坐标" in excel_titles:
            idx = excel_titles["旋转后端点坐标"]
            sections["旋转坐标"] = self._parse_data_block(df, idx)

        # 走向与长度
        if "走向与长度" in excel_titles:
            idx = excel_titles["走向与长度"]
            sections["走向与长度"] = self._parse_data_block(df, idx)

        return sections

    def _parse_data_block(self, df: pd.DataFrame, title_idx: int) -> list[dict[str, Any]]:
        """解析标题下方的数据块。"""
        header_row = df.iloc[title_idx + 1]
        headers = [str(h) if pd.notna(h) else f"col_{i}" for i, h in enumerate(header_row)]
        results = []
        for i in range(title_idx + 2, len(df)):
            row = df.iloc[i]
            if row.isna().all():
                continue
            record = {}
            for j, h in enumerate(headers):
                if j >= len(row):
                    break
                val = row.iloc[j]
                record[h] = float(val) if pd.notna(val) and isinstance(val, (int, float)) else (str(val) if pd.notna(val) else "")
            if record:
                results.append(record)
        return results
