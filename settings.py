"""集中管理脚本运行所需的默认路径与参数配置。"""
import json
from pathlib import Path
from typing import Any, Dict

CONFIG_PATH = Path(__file__).with_name("config.json")

# 默认配置，供缺失字段回退。
DEFAULT_CONFIG: Dict[str, Any] = {
    "input_dir": r"D:\作业\毕业论文\周咏霖\input", # 输入目录
    "output_dir": r"D:\作业\毕业论文\周咏霖\output", # 输出目录
    "file_name": "Outcrop", # 测点名称
    "excel_base": "O76_process", # 迹线表基础名称
    "outcrop_name": "O76", # 测点名称
    "process_all": True, # 是否处理输入目录下所有发现的迹线表
}


def load_config(config_path: str | Path | None = None) -> Dict[str, Any]:
    """从 JSON 配置文件读取运行参数，缺失字段使用默认值。"""

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
