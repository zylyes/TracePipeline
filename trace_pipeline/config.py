"""配置加载与路径解析工具。

职责：
- 提供默认配置与 JSON 合并语义
- 校验配置字段的合法性
- 解析输入/输出路径（相对路径以配置文件或项目根为基准）
- 在输入目录中扫描符合命名规则的迹线表
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Mapping, Tuple

# ---------------------------------------------------------------------------
# 默认值
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
    """返回用于解析相对路径的基准目录。"""
    if not config_path:
        return PROJECT_ROOT
    candidate = Path(config_path).expanduser()
    if candidate.exists():
        return candidate.resolve().parent
    if candidate.parent.exists():
        return candidate.resolve().parent
    return PROJECT_ROOT


def load_config(config_path: str | Path | None = None) -> Dict[str, Any]:
    """加载 JSON 配置，缺失时回退到默认值。"""
    path = Path(config_path).expanduser() if config_path else CONFIG_PATH
    if not path.exists():
        return dict(DEFAULT_CONFIG)

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"配置文件 {path} 不是合法 JSON: {exc}") from exc

    if not isinstance(data, dict):
        raise ValueError(f"配置文件 {path} 必须包含一个 JSON 对象")

    return validate_config(data)


# ---------------------------------------------------------------------------
# 路径工具
# ---------------------------------------------------------------------------


def _resolve_path(path_value: str, base_dir: Path) -> Path:
    """将路径解析为绝对路径。"""
    candidate = Path(path_value).expanduser()
    return candidate if candidate.is_absolute() else (base_dir / candidate).resolve()


def ensure_io_paths(
    input_dir: str,
    output_dir: str,
    base_dir: str | Path | None = None,
) -> Tuple[str, str]:
    """解析并确保输入/输出目录存在，返回绝对路径字符串。"""
    resolved_base = Path(base_dir).expanduser().resolve() if base_dir else PROJECT_ROOT

    in_path = _resolve_path(input_dir, resolved_base)
    out_path = _resolve_path(output_dir, resolved_base)

    in_path.mkdir(parents=True, exist_ok=True)
    out_path.mkdir(parents=True, exist_ok=True)
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
    """
    path = Path(input_dir)
    if not path.is_dir():
        return []

    matched: Dict[str, Tuple[str, str]] = {}
    for ext in extensions:
        for file_path in path.glob(f"*{suffix}{ext}"):
            base = file_path.stem
            key = base.lower()
            if key not in matched:
                outcrop_name = base[: -len(suffix)] if base.endswith(suffix) else base
                matched[key] = (base, outcrop_name)

    return [matched[k] for k in sorted(matched)]
