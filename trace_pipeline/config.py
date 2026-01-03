"""配置加载与输入输出路径工具。

包含默认配置、从 JSON 文件读取并与默认值合并的逻辑，
以及对输入/输出目录进行基本容错处理和在目录中查找符合命名规则的迹线表。
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, Tuple, List

# 默认配置与配置文件位置
# 项目根目录（trace_pipeline 的上级目录），用于推导默认的 input/output 路径
PROJECT_ROOT = Path(__file__).resolve().parent.parent
# 默认配置文件位置（项目根目录下的 config.json）
CONFIG_PATH = PROJECT_ROOT / "config.json"

DEFAULT_CONFIG: Dict[str, Any] = {
    "input_dir": str(PROJECT_ROOT / "input"),
    "output_dir": str(PROJECT_ROOT / "output"),
    "file_name": "Outcrop",
    "excel_base": "O76_process",
    "outcrop_name": "O76",
    "process_all": True,
}


def load_config(config_path: str | Path | None = None) -> Dict[str, Any]:
    """从 JSON 读取配置，缺失时使用默认值。"""

    # 优先使用传入的路径，否则使用默认的 CONFIG_PATH
    path = Path(config_path) if config_path else CONFIG_PATH
    # 若配置文件不存在，则返回默认配置的拷贝，避免修改全局常量
    if not path.exists():
        return DEFAULT_CONFIG.copy()

    # 读取 JSON 并校验其为对象（字典）格式，非字典则抛错
    with path.open("r", encoding="utf-8") as fp:
        data = json.load(fp)
    if not isinstance(data, dict):
        raise ValueError(f"Config file {path} must contain a JSON object")

    # 仅合并已定义的默认键，忽略未知键以防止配置文件包含不相关字段
    merged = DEFAULT_CONFIG.copy()
    merged.update({k: v for k, v in data.items() if k in merged})
    return merged


def ensure_io_paths(input_dir: str, output_dir: str) -> Tuple[str, str]:
    """返回可用的输入/输出目录。"""

    # 路径不存在则回退到当前工作目录，避免因路径问题导致程序崩溃
    cwd = Path.cwd()

    in_path = Path(input_dir)
    out_path = Path(output_dir)

    final_in = str(in_path) if in_path.is_dir() else str(cwd)
    final_out = str(out_path) if out_path.is_dir() else str(cwd)

    return final_in, final_out


def find_trace_tables(
    input_dir: str,
    suffix: str = "_process",
    extensions: Tuple[str, ...] = (".xlsx", ".xls"),
) -> List[Tuple[str, str]]:
    """在目录中查找符合命名规则的迹线表，返回 (excel_base, outcrop_name)。"""

    path = Path(input_dir)
    if not path.is_dir():
        return []

    matched: Dict[str, Tuple[str, str]] = {}

    # 遍历目录下的文件，筛选后缀并检查文件名是否以指定后缀结束
    for file_path in path.iterdir():
        if not file_path.is_file():
            continue

        # 仅处理指定的 Excel 后缀
        if file_path.suffix.lower() not in extensions:
            continue

        base = file_path.stem
        if not base.endswith(suffix):
            continue

        # 使用不区分大小写的 key 防止重复（例如 .XLSX/.xlsx 同名文件）
        key = base.lower()
        if key not in matched:
            # 从文件名去掉后缀片段以得到岩相/出露名
            outcrop_name = base[: -len(suffix)]
            matched[key] = (base, outcrop_name)

    return list(matched.values())
