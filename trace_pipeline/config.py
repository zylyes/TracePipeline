"""配置加载与路径解析。

职责：
  - 提供默认配置并支持 JSON 覆盖
  - 将相对路径解析为绝对路径
  - 合并 CLI 参数覆盖
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, Mapping, Tuple

logger = logging.getLogger(__name__)

# ===========================================================================
# 路径常量
# ===========================================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "config.json"

# ===========================================================================
# 默认配置
# ===========================================================================

DEFAULT_CONFIG: Dict[str, Any] = {
    "input_dir": str(PROJECT_ROOT / "input"),
    "output_dir": str(PROJECT_ROOT / "output"),
    "output_prefix": "Outcrop",
    "table_stem": "O76_process",
    "outcrop": "O76",
    "process_all": True,
    "export_rose_plot": True,
    "rose_bin_width": 10,
    "rose_dpi": 400,
    "trace_dpi": 300,
    "rotated_trace_dpi": 600,
}

_REQUIRED_KEYS = ("input_dir", "output_dir", "table_stem", "outcrop")

# ===========================================================================
# 配置加载
# ===========================================================================


def load_config(config_path: str | Path | None = None) -> Dict[str, Any]:
    """加载 JSON 配置文件，缺失则使用默认配置。

    Returns:
        合并后的配置字典（键值类型已规范化）。

    Raises:
        ValueError: JSON 格式无效或配置项不合法。
        OSError: 文件读取失败。
    """
    explicit_path = config_path is not None
    path = Path(config_path).expanduser().resolve() if explicit_path else DEFAULT_CONFIG_PATH
    if not path.exists():
        if explicit_path:
            raise FileNotFoundError(f"指定的配置文件不存在: {path}")
        logger.info("配置文件 %s 不存在，使用默认配置", path)
        return validate_config(dict(DEFAULT_CONFIG))
    if not path.is_file():
        raise ValueError(f"配置路径 {path} 不是文件")

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


def coerce_bool(value: Any, name: str) -> bool:
    """将常见配置布尔写法规范化为 bool。"""
    if isinstance(value, bool):
        return value
    if isinstance(value, int) and value in (0, 1):
        return bool(value)
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "y", "on"}:
            return True
        if normalized in {"0", "false", "no", "n", "off"}:
            return False
    raise ValueError(f"{name} 必须为布尔值")


def coerce_positive_int(value: Any, name: str) -> int:
    """将 DPI 等正整数配置规范化为 int。"""
    try:
        number = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} 必须为正整数") from exc
    if number <= 0:
        raise ValueError(f"{name} 必须为正整数")
    return number


def coerce_rose_bin_width(value: Any) -> float:
    """规范化玫瑰图分箱宽度。"""
    try:
        width = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("rose_bin_width 必须为数值") from exc
    if not (0 < width <= 180):
        raise ValueError("rose_bin_width 必须在 (0, 180] 范围内")
    return width


def validate_config(cfg: Mapping[str, Any]) -> Dict[str, Any]:
    """合并默认值、规范化类型并检查必填项；对未知键发出警告。"""
    merged = dict(DEFAULT_CONFIG)
    unknown = [k for k in cfg.keys() if k not in merged]
    if unknown:
        logger.warning("忽略未知配置项: %s", ", ".join(sorted(unknown)))
    merged.update({k: v for k, v in cfg.items() if k in merged})

    missing = [k for k in _REQUIRED_KEYS if str(merged.get(k, "")).strip() == ""]
    if missing:
        raise ValueError(f"缺少必要配置字段: {', '.join(missing)}")

    merged["process_all"] = coerce_bool(merged["process_all"], "process_all")
    merged["export_rose_plot"] = coerce_bool(
        merged["export_rose_plot"], "export_rose_plot"
    )
    merged["rose_bin_width"] = coerce_rose_bin_width(merged["rose_bin_width"])
    for key in ("rose_dpi", "trace_dpi", "rotated_trace_dpi"):
        merged[key] = coerce_positive_int(merged[key], key)
    for key in _REQUIRED_KEYS + ("output_prefix",):
        if key in merged:
            merged[key] = str(merged[key]).strip()

    return merged


# ===========================================================================
# 路径解析
# ===========================================================================


def resolve_config_base_dir(config_path: str | Path | None = None) -> Path:
    """返回解析相对路径用的基准目录。"""
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


def _to_absolute(path_value: str, base_dir: Path) -> Path:
    """将路径转为绝对路径。"""
    candidate = Path(path_value).expanduser()
    return candidate.resolve() if candidate.is_absolute() else (base_dir / candidate).resolve()


def resolve_io_paths(
    input_dir: str,
    output_dir: str,
    base_dir: str | Path | None = None,
    *,
    create_dirs: bool = True,
) -> Tuple[str, str]:
    """将输入/输出目录解析为绝对路径，并按需确保目录存在。

    默认 `create_dirs=True` 保持历史兼容；CLI 的 `--list` / `--dry-run`
    会传入 False，避免只读命令意外创建空目录。
    """
    resolved_base = Path(base_dir).expanduser().resolve() if base_dir else PROJECT_ROOT

    in_path = _to_absolute(input_dir, resolved_base)
    out_path = _to_absolute(output_dir, resolved_base)

    if create_dirs:
        try:
            in_path.mkdir(parents=True, exist_ok=True)
            out_path.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            logger.error("无法创建目录: %s", exc)
            raise

    logger.debug("输入目录: %s", in_path)
    logger.debug("输出目录: %s", out_path)
    return str(in_path), str(out_path)


# ===========================================================================
# CLI 覆盖合并
# ===========================================================================


def apply_cli_overrides(cfg: Dict[str, Any], **overrides: Any) -> Dict[str, Any]:
    """将 CLI 参数覆盖到配置字典中并重新校验。"""
    effective = {k: v for k, v in overrides.items() if v is not None}
    if not effective:
        return cfg

    merged = {**cfg, **effective}
    return validate_config(merged)


__all__ = [
    "DEFAULT_CONFIG",
    "DEFAULT_CONFIG_PATH",
    "PROJECT_ROOT",
    "apply_cli_overrides",
    "coerce_bool",
    "coerce_positive_int",
    "coerce_rose_bin_width",
    "load_config",
    "resolve_config_base_dir",
    "resolve_io_paths",
    "validate_config",
]
