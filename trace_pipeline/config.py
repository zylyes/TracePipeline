"""配置加载与路径解析。

职责：
  - 提供默认配置并支持 JSON 覆盖
  - 将相对路径解析为绝对路径
  - 合并 CLI 参数覆盖
"""
from __future__ import annotations

import json
import logging
from collections.abc import Mapping
from pathlib import Path
from typing import Any, TypedDict

from .validation import coerce_bool, coerce_scalar_config_fields

logger = logging.getLogger(__name__)

# ===========================================================================
# 路径常量
# ===========================================================================

try:
    PROJECT_ROOT = Path(__file__).resolve().parent.parent
except (AttributeError, TypeError):
    PROJECT_ROOT = Path.cwd()
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "config.json"

# ===========================================================================
# 默认配置
# ===========================================================================


class ConfigDict(TypedDict, total=False):
    """配置字典类型定义，用于类型检查。"""

    input_dir: str
    output_dir: str
    output_prefix: str
    table_stem: str
    outcrop: str
    process_all: bool
    export_rose_plot: bool
    rose_bin_width: float
    rose_dpi: int
    trace_dpi: int
    rotated_trace_dpi: int
    window_strategy: str
    auto_density_threshold: float
    tangent_window_count: int


DEFAULT_CONFIG: dict[str, Any] = {
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
    "window_strategy": "auto",
    "auto_density_threshold": 5.0,
    "tangent_window_count": 3,
}

_REQUIRED_KEYS = ("input_dir", "output_dir", "table_stem", "outcrop")

# ===========================================================================
# 配置加载
# ===========================================================================


def load_config(config_path: str | Path | None = None) -> dict[str, Any]:
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


def validate_config(cfg: Mapping[str, Any]) -> dict[str, Any]:
    """合并默认值、规范化类型并检查必填项；对未知键发出警告。"""
    merged = dict(DEFAULT_CONFIG)
    unknown = [k for k in cfg if k not in merged]
    if unknown:
        logger.warning("忽略未知配置项: %s", ", ".join(sorted(unknown)))
    merged.update({k: v for k, v in cfg.items() if k in merged})

    missing = [
        k for k in _REQUIRED_KEYS
        if merged.get(k) is None or str(merged[k]).strip() == ""
    ]
    if missing:
        raise ValueError(f"缺少必要配置字段: {', '.join(missing)}")

    merged["process_all"] = coerce_bool(merged["process_all"], "process_all")
    coerce_scalar_config_fields(merged)
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
) -> tuple[str, str]:
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


def apply_cli_overrides(cfg: dict[str, Any], **overrides: Any) -> dict[str, Any]:
    """将 CLI 参数覆盖到配置字典中并重新校验。"""
    effective = {k: v for k, v in overrides.items() if v is not None}
    if not effective:
        return cfg

    merged = {**cfg, **effective}
    return validate_config(merged)


__all__ = [
    "ConfigDict",
    "DEFAULT_CONFIG",
    "DEFAULT_CONFIG_PATH",
    "PROJECT_ROOT",
    "apply_cli_overrides",
    "load_config",
    "resolve_config_base_dir",
    "resolve_io_paths",
    "validate_config",
]
