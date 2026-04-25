"""配置加载与路径解析工具。

职责：
- 提供默认配置与 JSON 合并语义
- 校验配置字段的合法性
- 解析输入/输出路径（相对路径以配置文件或项目根为基准）
- 在输入目录中扫描符合命名规则的迹线表
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

# 合法的 Excel 后缀
_EXCEL_EXTENSIONS: Tuple[str, ...] = (".xlsx", ".xls")
# 迹线表文件名后缀标记
_TRACE_SUFFIX = "_process"

# ---------------------------------------------------------------------------
# 配置键名常量（避免字符串散落）
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
    "ensure_io_paths",
    "find_trace_tables",
    "load_config",
    "resolve_config_base_dir",
    "validate_config",
]


# ---------------------------------------------------------------------------
# 校验
# ---------------------------------------------------------------------------


def _validate_required(cfg: Mapping[str, Any]) -> None:
    missing = [k for k in _REQUIRED_KEYS if str(cfg.get(k, "")).strip() == ""]
    if missing:
        raise ValueError(f"缺少必要配置字段: {', '.join(missing)}")


def _validate_numeric(cfg: Dict[str, Any]) -> None:
    """就地校验并规范化数值型配置项。"""
    try:
        cfg[_KEY_ROSE_BIN_WIDTH] = float(cfg.get(_KEY_ROSE_BIN_WIDTH, DEFAULT_CONFIG[_KEY_ROSE_BIN_WIDTH]))
    except (TypeError, ValueError) as exc:
        raise ValueError("rose_bin_width 必须为数值") from exc
    if not (0 < cfg[_KEY_ROSE_BIN_WIDTH] <= 180):
        raise ValueError("rose_bin_width 必须在 (0, 180] 范围内")

    try:
        cfg[_KEY_ROSE_DPI] = int(cfg.get(_KEY_ROSE_DPI, DEFAULT_CONFIG[_KEY_ROSE_DPI]))
    except (TypeError, ValueError) as exc:
        raise ValueError("rose_dpi 必须为整数") from exc
    if cfg[_KEY_ROSE_DPI] <= 0:
        raise ValueError("rose_dpi 必须为正整数")


def validate_config(cfg: Mapping[str, Any]) -> Dict[str, Any]:
    """校验并返回规范化的配置字典（仅包含已知键）。"""
    merged = {k: v for k, v in DEFAULT_CONFIG.items()}
    merged.update({k: v for k, v in cfg.items() if k in merged})

    _validate_required(merged)
    _validate_numeric(merged)

    merged[_KEY_PROCESS_ALL] = bool(merged.get(_KEY_PROCESS_ALL, True))
    merged[_KEY_EXPORT_ROSE] = bool(merged.get(_KEY_EXPORT_ROSE, True))

    for key in _REQUIRED_KEYS + (_KEY_FILE_NAME,):
        merged[key] = str(merged[key]).strip()

    return merged


# ---------------------------------------------------------------------------
# 加载
# ---------------------------------------------------------------------------


def resolve_config_base_dir(config_path: str | Path | None = None) -> Path:
    """返回用于解析相对路径的基准目录。

    优先级:
    1. 若提供了 config_path 且对应文件存在 → 配置文件所在目录
    2. 若提供了 config_path 但文件不存在 → 配置路径的父目录（若存在）
    3. 以上均不满足 → PROJECT_ROOT
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
    """加载 JSON 配置，缺失时回退到默认值。

    Args:
        config_path: 配置文件路径。若为 None，使用默认 CONFIG_PATH。

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
# 路径工具
# ---------------------------------------------------------------------------


def _resolve_path(path_value: str, base_dir: Path) -> Path:
    """将路径解析为绝对路径。

    - 若为绝对路径 → 直接返回
    - 若为相对路径 → 以 base_dir 为基准解析
    """
    candidate = Path(path_value).expanduser()
    if candidate.is_absolute():
        return candidate.resolve()
    return (base_dir / candidate).resolve()


def ensure_io_paths(
    input_dir: str,
    output_dir: str,
    base_dir: str | Path | None = None,
) -> Tuple[str, str]:
    """解析并确保输入/输出目录存在，返回绝对路径字符串。

    Args:
        input_dir: 输入目录路径（绝对或相对）。
        output_dir: 输出目录路径（绝对或相对）。
        base_dir: 相对路径的基准目录，默认为 PROJECT_ROOT。

    Returns:
        (input_abs, output_abs) 绝对路径字符串元组。

    Raises:
        OSError: 目录创建失败时。
    """
    resolved_base = (
        Path(base_dir).expanduser().resolve() if base_dir else PROJECT_ROOT
    )

    in_path = _resolve_path(input_dir, resolved_base)
    out_path = _resolve_path(output_dir, resolved_base)

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
    """在输入目录中查找迹线表，返回 [(excel_base, outcrop_name), ...]。

    匹配规则：文件名以 `suffix` 结尾（不含扩展名），扩展名在 `extensions` 中。
    同名文件（不同扩展名）按首次发现原则去重（大小写不敏感）。

    Args:
        input_dir: 输入目录路径。
        suffix: 迹线表文件名后缀标记，默认 "_process"。
        extensions: 合法的 Excel 扩展名。

    Returns:
        按 outcrop_name 字母序排列的 (excel_base, outcrop_name) 列表。
        若目录不存在或无匹配文件，返回空列表。
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
        logger.info("发现 %d 个迹线表: %s", len(result),
                     ", ".join(b for b, _ in result))
    else:
        logger.warning("在 %s 中未发现匹配的迹线表（后缀=%s）", input_dir, suffix)
    return result
