"""配置加载、校验、路径解析与文件发现。

职责：
  - 提供默认配置并支持 JSON 文件覆盖
  - 校验配置字段的类型与取值范围
  - 解析相对路径为绝对路径
  - 扫描输入目录发现迹线表文件
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Mapping, Tuple

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 路径常量
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = PROJECT_ROOT / "config.json"

_EXCEL_EXTENSIONS: Tuple[str, ...] = (".xlsx", ".xls")
_TRACE_SUFFIX = "_process"

# ---------------------------------------------------------------------------
# 配置键名
# ---------------------------------------------------------------------------

_KEY_INPUT_DIR = "input_dir"
_KEY_OUTPUT_DIR = "output_dir"
_KEY_FILE_NAME = "file_name"
_KEY_EXCEL_BASE = "excel_base"
_KEY_OUTCROP_NAME = "outcrop_name"
_KEY_PROCESS_ALL = "process_all"
_KEY_EXPORT_ROSE = "export_rose_plot"
_KEY_ROSE_BIN_WIDTH = "rose_bin_width"
_KEY_ROSE_DPI = "rose_dpi"

_REQUIRED_KEYS = (_KEY_INPUT_DIR, _KEY_OUTPUT_DIR, _KEY_EXCEL_BASE, _KEY_OUTCROP_NAME)

DEFAULT_CONFIG: Dict[str, Any] = {
    _KEY_INPUT_DIR: str(PROJECT_ROOT / "input"),
    _KEY_OUTPUT_DIR: str(PROJECT_ROOT / "output"),
    _KEY_FILE_NAME: "Outcrop",
    _KEY_EXCEL_BASE: "O76_process",
    _KEY_OUTCROP_NAME: "O76",
    _KEY_PROCESS_ALL: True,
    _KEY_EXPORT_ROSE: True,
    _KEY_ROSE_BIN_WIDTH: 10,
    _KEY_ROSE_DPI: 400,
}

__all__ = [
    "CONFIG_PATH",
    "DEFAULT_CONFIG",
    "PROJECT_ROOT",
    "find_trace_tables",
    "load_config",
    "resolve_config_base_dir",
    "resolve_io_paths",
    "validate_config",
]


# ---------------------------------------------------------------------------
# 校验
# ---------------------------------------------------------------------------

def validate_config(cfg: Mapping[str, Any]) -> Dict[str, Any]:
    """校验并返回规范化配置字典（仅保留已知键，缺失项用默认值填充）。"""
    # 合并：默认值为基础，用户配置覆盖
    merged = dict(DEFAULT_CONFIG)
    merged.update({k: v for k, v in cfg.items() if k in merged})

    # 必填项检查
    missing = [k for k in _REQUIRED_KEYS if str(merged.get(k, "")).strip() == ""]
    if missing:
        raise ValueError(f"缺少必要配置字段: {', '.join(missing)}")

    # 数值型校验
    try:
        merged[_KEY_ROSE_BIN_WIDTH] = float(merged[_KEY_ROSE_BIN_WIDTH])
    except (TypeError, ValueError) as exc:
        raise ValueError("rose_bin_width 必须为数值") from exc
    if not (0 < merged[_KEY_ROSE_BIN_WIDTH] <= 180):
        raise ValueError("rose_bin_width 必须在 (0, 180] 范围内")

    try:
        merged[_KEY_ROSE_DPI] = int(merged[_KEY_ROSE_DPI])
    except (TypeError, ValueError) as exc:
        raise ValueError("rose_dpi 必须为整数") from exc
    if merged[_KEY_ROSE_DPI] <= 0:
        raise ValueError("rose_dpi 必须为正整数")

    # 布尔型与字符串型规范化
    merged[_KEY_PROCESS_ALL] = bool(merged[_KEY_PROCESS_ALL])
    merged[_KEY_EXPORT_ROSE] = bool(merged[_KEY_EXPORT_ROSE])
    for key in _REQUIRED_KEYS + (_KEY_FILE_NAME,):
        merged[key] = str(merged[key]).strip()

    return merged


# ---------------------------------------------------------------------------
# 加载
# ---------------------------------------------------------------------------

def resolve_config_base_dir(config_path: str | Path | None = None) -> Path:
    """返回解析相对路径用的基准目录。

    优先级:
      1. config_path 指向存在的文件 → 文件所在目录
      2. config_path 的父目录存在 → 父目录
      3. 回退 → PROJECT_ROOT
    """
    if not config_path:
        return PROJECT_ROOT

    candidate = Path(config_path).expanduser().resolve()
    if candidate.is_file():
        return candidate.parent
    if candidate.parent.is_dir():
        logger.debug("配置文件 %s 不存在，使用其父目录作为基准", candidate)
        return candidate.parent

    logger.warning("配置路径 %s 无效，回退到项目根目录", candidate)
    return PROJECT_ROOT


def load_config(config_path: str | Path | None = None) -> Dict[str, Any]:
    """加载 JSON 配置文件，缺失则使用默认配置。

    Returns:
        校验后的配置字典。
    Raises:
        ValueError: JSON 格式无效或配置项不合法。
        OSError: 文件读取失败。
    """
    path = Path(config_path).expanduser().resolve() if config_path else CONFIG_PATH
    if not path.exists():
        logger.info("配置文件 %s 不存在，使用默认配置", path)
        return dict(DEFAULT_CONFIG)

    logger.info("加载配置文件: %s", path)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"配置文件 {path} 不是合法 JSON: {exc}") from exc
    except OSError as exc:
        raise OSError(f"无法读取配置文件 {path}: {exc}") from exc

    if not isinstance(data, dict):
        raise ValueError(f"配置文件 {path} 必须包含一个 JSON 对象")

    return validate_config(data)


# ---------------------------------------------------------------------------
# 路径解析
# ---------------------------------------------------------------------------

def _to_absolute(path_value: str, base_dir: Path) -> Path:
    """将路径转为绝对路径：绝对路径直接返回，相对路径以 base_dir 为基准。"""
    candidate = Path(path_value).expanduser()
    return candidate.resolve() if candidate.is_absolute() else (base_dir / candidate).resolve()


def resolve_io_paths(
    input_dir: str,
    output_dir: str,
    base_dir: str | Path | None = None,
) -> Tuple[str, str]:
    """将输入/输出目录解析为绝对路径并确保目录存在。

    Returns:
        (input_abs, output_abs) 绝对路径字符串。
    Raises:
        OSError: 目录创建失败。
    """
    resolved_base = Path(base_dir).expanduser().resolve() if base_dir else PROJECT_ROOT

    in_path = _to_absolute(input_dir, resolved_base)
    out_path = _to_absolute(output_dir, resolved_base)

    try:
        in_path.mkdir(parents=True, exist_ok=True)
        out_path.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        logger.error("无法创建目录: %s", exc)
        raise

    logger.debug("输入目录: %s", in_path)
    logger.debug("输出目录: %s", out_path)
    return str(in_path), str(out_path)


# ---------------------------------------------------------------------------
# 文件发现
# ---------------------------------------------------------------------------

def find_trace_tables(
    input_dir: str,
    suffix: str = _TRACE_SUFFIX,
    extensions: Tuple[str, ...] = _EXCEL_EXTENSIONS,
) -> List[Tuple[str, str]]:
    """扫描输入目录，返回匹配的迹线表列表 [(excel_base, outcrop_name), ...]。

    匹配规则：
      - 文件名以 suffix 结尾（不含扩展名）
      - 扩展名在 extensions 集合中
      - 同名文件（不同扩展名）按首次发现去重（大小写不敏感）

    Returns:
        按 outcrop_name 排序的列表；目录不存在或无匹配时返回空列表。
    """
    path = Path(input_dir)
    if not path.is_dir():
        logger.warning("输入目录不存在: %s", input_dir)
        return []

    matched: Dict[str, Tuple[str, str]] = {}
    for ext in extensions:
        for file_path in sorted(path.glob(f"*{suffix}{ext}")):
            base = file_path.stem
            key = base.lower()
            if key not in matched:
                outcrop_name = base[: -len(suffix)] if base.endswith(suffix) else base
                matched[key] = (base, outcrop_name)

    result = [matched[k] for k in sorted(matched)]
    if result:
        logger.info("发现 %d 个迹线表: %s", len(result), ", ".join(b for b, _ in result))
    else:
        logger.warning("在 %s 中未发现匹配的迹线表（后缀=%s）", input_dir, suffix)
    return result
