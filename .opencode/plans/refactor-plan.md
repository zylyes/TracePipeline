# 迹线处理流水线 — 代码重构方案

## 目标

审查并优化 `trace_pipeline` 包，按功能模块分类、合理命名、去除冗余。

---

## 当前文件结构

```
trace_pipeline/
├── __init__.py      — 公共 API 导出（118 行，导出过多内部常量）
├── angles.py        — 地质角度转换（120 行）
├── config.py        — 配置加载、校验、路径解析、CLI 覆盖、文件发现（299 行，职责过重）
├── display.py       — 终端结果展示（185 行，命名模糊）
├── geometry.py      — 迹线端点计算（235 行）
├── io.py            — Excel 读写（220 行）
├── models.py        — 数据模型（196 行，命名不规范 + 与 config 校验重复）
├── pipeline.py      — 流水线编排（143 行，接受 dict|RunConfig 双模式）
├── plotting.py      — 绘图 + 数据转换（278 行，职责混杂）
└── transforms.py    — 坐标变换（127 行）
```

外部文件：
```
run_trace_pipeline.py — CLI 入口（392 行）
config.json           — 配置文件（含旧键说明字段）
```

---

## 变更清单

### 1. 移除旧键兼容代码

**config.json** — 删除 `_comment`、`_usage`、`_note` 字段：
```json
{
  "input_dir": "input",
  "output_dir": "output",
  "output_prefix": "Outcrop",
  "table_stem": "O76_process",
  "outcrop": "O76",
  "process_all": true,
  "export_rose_plot": true,
  "rose_bin_width": 10,
  "rose_dpi": 400,
  "trace_dpi": 300,
  "rotated_trace_dpi": 600
}
```

**config.py** — 删除 `_normalize_legacy_keys` 函数及其在 `validate_config` 中的调用：
```python
# 删除整个 _normalize_legacy_keys 函数
# 删除 validate_config 中的调用行：
# raw_normalized = _normalize_legacy_keys(dict(cfg))
# 替换为：
# raw_cfg = dict(cfg)
```

**types.py（原 models.py）** — `RunConfig.from_mapping` 中删除旧键兼容分支：
```python
# 删除以下代码：
# for old_key, new_key in [
#     ("excel_base", "table_stem"),
#     ("outcrop_name", "outcrop"),
#     ("file_name", "output_prefix"),
# ]:
#     if old_key in normalized and new_key not in normalized:
#         normalized[new_key] = normalized.pop(old_key)
```

---

### 2. 统一校验到 `RunConfig.__post_init__`

**types.py** — `RunConfig` 添加 `__post_init__` 校验方法：
```python
def __post_init__(self):
    if not str(self.table_stem).strip():
        raise ValueError("table_stem 不能为空")
    if not str(self.outcrop).strip():
        raise ValueError("outcrop 不能为空")
    if not str(self.output_prefix).strip():
        raise ValueError("output_prefix 不能为空")
    if not str(self.input_dir).strip():
        raise ValueError("input_dir 不能为空")
    if not str(self.output_dir).strip():
        raise ValueError("output_dir 不能为空")
    _validate_rose_bin_width(self.rose_bin_width)
    _validate_dpi(self.rose_dpi)
    _validate_dpi(self.trace_dpi)
    _validate_dpi(self.rotated_trace_dpi)
```

校验函数 `_validate_rose_bin_width` 和 `_validate_dpi` 移到 `types.py`（从 `config.py` 迁移，去掉公开导出）。

`RunConfig.from_mapping` 简化为：
```python
@classmethod
def from_mapping(cls, cfg: Mapping[str, Any]) -> "RunConfig":
    return cls(
        input_dir=str(cfg["input_dir"]),
        output_dir=str(cfg["output_dir"]),
        output_prefix=str(cfg["output_prefix"]),
        table_stem=str(cfg["table_stem"]),
        outcrop=str(cfg["outcrop"]),
        export_rose=bool(cfg.get("export_rose_plot", True)),
        rose_bin_width=float(cfg.get("rose_bin_width", 10.0)),
        rose_dpi=int(cfg.get("rose_dpi", 400)),
        trace_dpi=int(cfg.get("trace_dpi", 300)),
        rotated_trace_dpi=int(cfg.get("rotated_trace_dpi", 600)),
    )
```

**config.py** — `validate_config` 简化为仅合并默认值 + 类型规范化，不再做数值校验：
```python
def validate_config(cfg: Mapping[str, Any]) -> Dict[str, Any]:
    merged = dict(DEFAULT_CONFIG)
    merged.update({k: v for k, v in cfg.items() if k in merged})
    required = ("input_dir", "output_dir", "table_stem", "outcrop")
    missing = [k for k in required if str(merged.get(k, "")).strip() == ""]
    if missing:
        raise ValueError(f"缺少必要配置字段: {', '.join(missing)}")
    merged["process_all"] = bool(merged["process_all"])
    merged["export_rose_plot"] = bool(merged["export_rose_plot"])
    for key in required + ("output_prefix",):
        if key in merged:
            merged[key] = str(merged[key]).strip()
    return merged
```

删除 `validate_rose_bin_width` 和 `validate_dpi` 的公开导出（移到 types.py 内部）。

---

### 3. `run_pipeline` 只接受 `RunConfig`

**pipeline.py** — 简化 `run_pipeline` 签名和内部逻辑：
```python
def run_pipeline(cfg: RunConfig) -> RunResult:
    """处理单个迹线表：加载 → 变换 → 导出 Excel → 绘图。"""
    try:
        # ... 整个 try 块保持不变，只是不再需要 cfg 类型判断
    except ...
```

删除 `_safe_table_stem` 辅助函数。

**run_trace_pipeline.py** — 在主流程中将 dict 转为 RunConfig：
```python
from trace_pipeline.types import RunConfig

# 在 main() 中，配置加载后：
cfg = load_config(args.config)
cfg = apply_cli_overrides(cfg, **cli_overrides)
input_dir, output_dir = resolve_io_paths(...)
run_cfg = RunConfig.from_mapping({
    **cfg,
    "input_dir": input_dir,
    "output_dir": output_dir,
    "output_prefix": outcrop,  # 或根据 context
    "table_stem": table_stem,
    "outcrop": outcrop,
})
result = run_pipeline(run_cfg)
```

---

### 4. 函数迁移

#### 4a. `find_trace_tables` + 常量 → `io.py`

从 `config.py` 移到 `io.py`：
- `find_trace_tables()` 函数
- `EXCEL_EXTENSIONS` 常量
- `TRACE_SUFFIX` 常量

`io.py` 增加：
```python
from pathlib import Path
from typing import Dict, List, Tuple

EXCEL_EXTENSIONS: Tuple[str, ...] = (".xlsx", ".xls")
TRACE_SUFFIX = "_process"

def find_trace_tables(
    input_dir: str,
    suffix: str = TRACE_SUFFIX,
    extensions: Tuple[str, ...] = EXCEL_EXTENSIONS,
) -> List[Tuple[str, str]]:
    # ... 原逻辑不变
```

`config.py` 删除上述函数和常量，`from .config import find_trace_tables` 等导出移到 `io.py`。

#### 4b. `segments_to_plot_xy` → `transforms.py`（重命名为 `segments_to_xy`）

从 `plotting.py` 移到 `transforms.py`，重命名：
```python
def segments_to_xy(segments: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """将 (N, 4) 线段数组转为带 NaN 分隔的一维 X/Y 序列。"""
    # ... 原逻辑不变
```

`plotting.py` 内部改为导入：
```python
from .transforms import segments_to_xy
```

#### 4c. `_fold_strike_angles` → `angles.py`（公开为 `fold_strikes_to_semicircle`）

从 `plotting.py` 移到 `angles.py`：
```python
def fold_strikes_to_semicircle(strike_deg: np.ndarray) -> np.ndarray:
    """将走向角折叠到 [0°, 180°)，用于玫瑰图分箱（向量化）。"""
    folded = np.mod(np.asarray(strike_deg, dtype=float), 180.0)
    folded[np.isclose(folded, 180.0)] = 0.0
    return folded
```

`plotting.py` 中 `_compute_rose_histogram` 改为调用：
```python
from .angles import fold_strikes_to_semicircle as _fold_to_semicircle
# 在 _compute_rose_histogram 中：
folded = _fold_to_semicircle(strike_deg)
```

---

### 5. 文件重命名

| 旧名 | 新名 | 理由 |
|------|------|------|
| `models.py` | `types.py` | Python 惯例，types 更准确 |
| `display.py` | `report.py` | report 更贴切描述功能 |

操作步骤：
1. 创建 `types.py`（内容来自 `models.py` + 校验函数迁移）
2. 创建 `report.py`（内容来自 `display.py`）
3. 删除旧文件 `models.py` 和 `display.py`

---

### 6. 精简 `__init__.py`

移除以下导出：
- `COL_DIP`, `COL_HEADER_AZIMUTH`, `COL_HEADER_COUNT`, `COL_LEFT_LEN1/2`, `COL_RIGHT_LEN1/2`, `COL_SHIFT_ALONG`, `COL_SHIFT_ACROSS` — Excel 列布局内部常量
- `EXCEL_EXTENSIONS`, `TRACE_SUFFIX` — 迁移到 io.py 内部
- `validate_config`, `validate_dpi`, `validate_rose_bin_width` — 内部校验函数
- `DEFAULT_CONFIG`, `DEFAULT_CONFIG_PATH`, `PROJECT_ROOT` — 保留（配置 API 需要）

保留的导出：
```python
# 数据类型
"TraceData", "RunConfig", "RunResult",
# 配置
"load_config", "apply_cli_overrides",
"resolve_config_base_dir", "resolve_io_paths",
# 角度
"dip_to_strike", "fold_strike_angle", "fold_to_halfplane",
"folds_strikes_to_semicircle",
# 几何计算
"compute_endpoints",
# 坐标变换
"normalize_coordinates", "rotate_and_shift",
"shift_to_positive", "segments_to_xy",
# Excel I/O
"build_excel_sections", "parse_trace_file",
"read_trace_excel", "write_excel_sections",
"find_trace_tables",
# 绘图
"configure_style", "render_rose_plot",
"render_trace_plot",
# 报告
"format_result_detail", "format_results_table",
"format_summary", "print_pipeline_results",
# 流水线
"run_pipeline",
```

---

### 7. 更新所有导入引用

**涉及文件：**
- `run_trace_pipeline.py`: 更新所有 `from trace_pipeline import ...` 和 `from trace_pipeline.models import RunResult` → `from trace_pipeline.types import RunResult`
- `pipeline.py`: `from .models import ...` → `from .types import ...`
- `__init__.py`: 全面重写导入
- `io.py`: 内部 `from .models import TraceData` → `from .types import TraceData`
- `plotting.py`: 添加 `from .transforms import segments_to_xy`，移除本地定义
- `config.py`: 移除 `find_trace_tables`、`EXCEL_EXTENSIONS`、`TRACE_SUFFIX`、`validate_dpi`、`validate_rose_bin_width`

---

## 变更后的文件结构

```
trace_pipeline/
├── __init__.py      — 精简公共 API（~60 行）
├── angles.py        — 增加 fold_strikes_to_semicircle（~135 行）
├── config.py        — 简化：配置加载+路径+CLI覆盖（~180 行）
├── report.py        — 原 display.py 重命名（185 行）
├── geometry.py      — 不变（235 行）
├── io.py            — 增加 find_trace_tables（~280 行）
├── types.py         — 原 models.py，合并校验逻辑（~180 行）
├── pipeline.py      — 简化，只接受 RunConfig（~100 行）
├── plotting.py      — 移除 segments_to_plot_xy 和 _fold_strike_angles（~220 行）
└── transforms.py    — 增加 segments_to_xy（~145 行）
```

外部文件：
- `run_trace_pipeline.py` — 更新导入，改用 RunConfig
- `config.json` — 删除旧键说明字段

---

## 执行顺序

1. 创建 `types.py`（合并 models.py 内容 + 校验函数）
2. 创建 `report.py`（拷贝 display.py 内容）
3. 更新 `angles.py`（增加 fold_strikes_to_semicircle）
4. 更新 `transforms.py`（增加 segments_to_xy）
5. 更新 `io.py`（增加 find_trace_tables + 常量）
6. 更新 `config.py`（移除已迁移内容，简化 validate_config）
7. 更新 `plotting.py`（移除已迁移内容，改用导入）
8. 更新 `pipeline.py`（只接受 RunConfig）
9. 重写 `__init__.py`（精简导出）
10. 更新 `run_trace_pipeline.py`（改用新导入）
11. 更新 `config.json`（删除旧字段）
12. 删除 `models.py` 和 `display.py`
13. 运行验证