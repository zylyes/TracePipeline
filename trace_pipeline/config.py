"""配置加载与输入输出路径工具。"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, Tuple

# 默认配置与配置文件位置
PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = PROJECT_ROOT / "config.json"

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

    # 路径不存在则回退到当前工作目录，避免崩溃
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
        # 使用不区分大小写的 key 防止重复
        key = base.lower()
        if key not in matched:
            outcrop_name = base[: -len(suffix)]
            matched[key] = (base, outcrop_name)

    return list(matched.values())
