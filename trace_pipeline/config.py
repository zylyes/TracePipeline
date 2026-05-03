"""配置加载、校验、路径解析与文件发现。

职责：
  - 提供默认配置并支持 JSON 覆盖
  - 校验字段类型与取值范围
  - 将相对路径解析为绝对路径
  - 合并 CLI 参数覆盖
  - 扫描输入目录发现迹线表文件
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Mapping, Tuple

logger = logging.getLogger(__name__)

# ===========================================================================
# 路径常量
# ===========================================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "config.json"

# ===========================================================================
# 文件发现常量
# ===========================================================================

EXCEL_EXTENSIONS: Tuple[str, ...] = (".xlsx", ".xls")
TRACE_SUFFIX = "_process"

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
# 校验函数
# ===========================================================================


def validate_rose_bin_width(value: Any) -> float:
    """校验 rose_bin_width：必须为数值且在 (0, 180] 范围内。"""
    try:
        width = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("rose_bin_width 必须为数值") from exc
    if not (0 < width <= 180):
        raise ValueError("rose_bin_width 必须在 (0, 180] 范围内")
    return width


def validate_dpi(value: Any) -> int:
    """校验 DPI 参数：必须为正整数（通用于 rose_dpi / trace_dpi 等）。"""
    try:
        dpi = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("DPI 必须为整数") from exc
    if dpi <= 0:
        raise ValueError("DPI 必须为正整数")
    return dpi


# 保留旧函数名以兼容外部引用
# ===========================================================================
# 配置加载
# ===========================================================================


def _normalize_legacy_keys(raw: Dict[str, Any]) -> Dict[str, Any]:
    """将旧版配置键名映射为新版键名（向后兼容）。

    旧 → 新:
      excel_base   → table_stem
      outcrop_name → outcrop
      file_name    → output_prefix
    """
    mapping = {
        "excel_base": "table_stem",
        "outcrop_name": "outcrop",
        "file_name": "output_prefix",
    }
    normalized = dict(raw)
    for old, new in mapping.items():
        if old in normalized and new not in normalized:
            normalized[new] = normalized.pop(old)
    return normalized


def load_config(config_path: str | Path | None = None) -> Dict[str, Any]:
    """加载 JSON 配置文件，缺失则使用默认配置。

    Returns:
        校验后的配置字典。

    Raises:
        ValueError: JSON 格式无效或配置项不合法。
        OSError: 文件读取失败。
    """
    path = Path(config_path).expanduser().resolve() if config_path else DEFAULT_CONFIG_PATH
    if not path.exists():
        logger.info("配置文件 %s 不存在，使用默认配置", path)
        return validate_config(dict(DEFAULT_CONFIG))

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


def validate_config(cfg: Mapping[str, Any]) -> Dict[str, Any]:
    """校验并返回规范化配置字典。

    合并顺序：默认值 → 旧键兼容 → 用户配置覆盖 → 类型校验。
    """
    merged = dict(DEFAULT_CONFIG)
    raw_normalized = _normalize_legacy_keys(dict(cfg))
    merged.update({k: v for k, v in raw_normalized.items() if k in merged})

    # 必填项检查
    missing = [k for k in _REQUIRED_KEYS if str(merged.get(k, "")).strip() == ""]
    if missing:
        raise ValueError(f"缺少必要配置字段: {', '.join(missing)}")

    # 数值校验
    merged["rose_bin_width"] = validate_rose_bin_width(merged["rose_bin_width"])
    merged["rose_dpi"] = validate_dpi(merged["rose_dpi"])
    merged["trace_dpi"] = validate_dpi(merged.get("trace_dpi", 300))
    merged["rotated_trace_dpi"] = validate_dpi(merged.get("rotated_trace_dpi", 600))

    # 类型规范化
    merged["process_all"] = bool(merged["process_all"])
    merged["export_rose_plot"] = bool(merged["export_rose_plot"])
    for key in _REQUIRED_KEYS + ("output_prefix",):
        if key in merged:
            merged[key] = str(merged[key]).strip()

    return merged


# ===========================================================================
# 路径解析
# ===========================================================================


def resolve_config_base_dir(config_path: str | Path | None = None) -> Path:
    """返回解析相对路径用的基准目录。

    优先级：
      1. config_path 指向存在的文件 → 该文件所在目录
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


def _to_absolute(path_value: str, base_dir: Path) -> Path:
    """将路径转为绝对路径。"""
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


# ===========================================================================
# CLI 覆盖合并
# ===========================================================================


def apply_cli_overrides(cfg: Dict[str, Any], **overrides: Any) -> Dict[str, Any]:
    """将 CLI 参数覆盖到配置字典中并重新校验。

    Args:
        cfg: 原始配置字典。
        **overrides: 要覆盖的键值对（仅非 None 值生效）。

    Returns:
        合并并校验后的新配置字典。
    """
    effective = {k: v for k, v in overrides.items() if v is not None}
    if not effective:
        return cfg

    merged = {**cfg, **effective}
    return validate_config(merged)


def find_trace_tables(
    input_dir: str,
    suffix: str = TRACE_SUFFIX,
    extensions: Tuple[str, ...] = EXCEL_EXTENSIONS,
) -> List[Tuple[str, str]]:
    """扫描输入目录，返回匹配的迹线表列表 [(table_stem, outcrop), ...]。

    匹配规则：
      - 文件名以 suffix 结尾（不含扩展名）
      - 扩展名在 extensions 集合中
      - 同名文件（不同扩展名）按首次发现去重（大小写不敏感）

    Returns:
        按 outcrop 排序的列表；目录不存在或无匹配时返回空列表。
    """
    path = Path(input_dir)
    if not path.is_dir():
        logger.warning("输入目录不存在: %s", input_dir)
        return []

    matched: Dict[str, Tuple[str, str]] = {}
    for ext in extensions:
        for file_path in sorted(path.glob(f"*{suffix}{ext}")):
            stem = file_path.stem
            key = stem.lower()
            if key not in matched:
                outcrop = stem[: -len(suffix)] if stem.endswith(suffix) else stem
                matched[key] = (stem, outcrop)

    result = [matched[k] for k in sorted(matched)]
    if result:
        logger.info("发现 %d 个迹线表: %s", len(result), ", ".join(b for b, _ in result))
    else:
        logger.warning("在 %s 中未发现匹配的迹线表（后缀=%s）", input_dir, suffix)
    return result


__all__ = [
    "DEFAULT_CONFIG",
    "DEFAULT_CONFIG_PATH",
    "EXCEL_EXTENSIONS",
    "PROJECT_ROOT",
    "TRACE_SUFFIX",
    "apply_cli_overrides",
    "find_trace_tables",
    "load_config",
    "resolve_config_base_dir",
    "resolve_io_paths",
    "validate_config",
    "validate_dpi",
    "validate_rose_bin_width",
]
