# 岩体节理测线坐标计算与绘图工具

基于 Python 实现的岩体节理测线数据处理流水线。根据现场测量的测线几何参数与节理数据，自动计算节理端点坐标、进行坐标旋转（按走向标定），并生成迹线长度图与产状玫瑰花瓣图。

本项目是对 MATLAB 原版程序（见 `matlab参考/`）的完整 Python 复现，采用模块化流水线架构，支持批量处理。

---

## 目录结构

```
.
├── config.json                    # 默认配置文件
├── pyproject.toml                 # 项目元数据与依赖
├── requirements.txt               # pip 依赖锁定
├── run_trace_pipeline.py          # CLI 入口脚本
│
├── trace_pipeline/                # 核心包
│   ├── __init__.py                # 包导出
│   ├── config.py                  # 配置加载、校验、路径解析、文件发现
│   ├── data_loader.py             # Excel 读取与 ParsedTraceData 封装
│   ├── geometry.py                # 迹线端点向量化计算（复数运算）
│   ├── transforms.py              # 坐标平移与旋转
│   ├── excel_export.py            # Excel 输出构建与写入
│   ├── plotting.py                # 迹线图与玫瑰花瓣图绘制
│   └── pipeline.py                # 单目标全流程编排
│
├── input/                         # 输入目录（存放 *_process.xlsx）
├── output/                        # 输出目录（Excel + 图片）
├── logs/                          # 运行日志
├── matlab参考/                     # MATLAB 原版参考代码
│   ├── A_outcrop_0map_coordinate.m
│   ├── A_outcrop_0map_rotate.m
│   └── Coordinate.m
│
└── 杂项/                          # 其他研究资料
```

---

## 安装与环境配置

### 系统要求

- **Python** ≥ 3.9
- **pip** ≥ 21.0

### 依赖

| 包 | 用途 |
|---|---|
| `numpy` | 向量化数值计算 |
| `pandas` | Excel 表格读写 |
| `matplotlib` | 迹线图与玫瑰图绘制 |
| `openpyxl` | .xlsx 读写引擎 |
| `xlrd` | .xls 回退读取引擎 |
| `pytest` | 单元测试（开发用） |

### 快速开始

```bash
# 克隆 / 进入项目目录
cd code

# 创建虚拟环境（推荐）
python -m venv .venv

# Windows PowerShell：
.venv\Scripts\Activate.ps1

# 安装依赖
pip install -r requirements.txt

# 或通过 pyproject.toml 安装（含 CLI 入口）
pip install -e .
```

安装后可通过 `trace-pipeline` 命令直接调用（若使用 `pip install -e .`）。

---

## 配置

配置文件 `config.json`（位于项目根目录）控制所有运行参数：

```json
{
  "input_dir":       "input",       // 输入目录（相对/绝对路径）
  "output_dir":      "output",      // 输出目录
  "file_name":       "Outcrop",     // 输出文件命名前缀
  "excel_base":      "O76_process", // 单文件模式下读取的 Excel 文件名（不含扩展名）
  "outcrop_name":    "O76",         // 露头名称（也是 Excel 工作表名）
  "process_all":     true,          // true=批量处理，false=仅处理 excel_base 指定的文件
  "export_rose_plot": true,         // 是否导出玫瑰花瓣图
  "rose_bin_width":  10,           // 玫瑰图分箱宽度（度）
  "rose_dpi":        400           // 玫瑰图分辨率
}
```

所有配置项均可通过命令行参数覆盖（见下文）。

---

## 命令行用法

### 基本运行

```bash
# 使用 config.json 配置运行
python run_trace_pipeline.py

# 指定自定义配置文件
python run_trace_pipeline.py -c my_config.json

# 指定输入/输出目录
python run_trace_pipeline.py -i ./data -o ./results
```

### 完整 CLI 选项

| 参数 | 简写 | 说明 |
|---|---|---|
| `--input` | `-i` | 输入目录（覆盖 `config.json` 中的 `input_dir`） |
| `--output` | `-o` | 输出目录（覆盖 `config.json` 中的 `output_dir`） |
| `--config` | `-c` | 自定义 JSON 配置文件路径 |
| `--single` | `-s` | **单文件模式**：仅处理配置中 `excel_base` 指定的文件（忽略目录扫描） |
| `--rose-bin` | — | 玫瑰图分箱宽度（度），如 `--rose-bin 15` |
| `--rose-dpi` | — | 玫瑰图 DPI，如 `--rose-dpi 600` |
| `--no-rose` | — | 跳过玫瑰图导出 |

### 运行模式

**批量模式**（默认）：扫描输入目录下所有命名类似 `*_process.xlsx`（或 `*.xls`）的文件，逐个处理。

```bash
python run_trace_pipeline.py                    # 批量处理 input/ 下所有 *_process.xlsx
```

**单文件模式**：仅处理 `config.json` 中 `excel_base` 指定的文件。

```bash
python run_trace_pipeline.py -s                 # 仅处理 O76_process.xlsx
python run_trace_pipeline.py -s -c my_conf.json # 使用自定义配置的单文件模式
```

---

## 数据处理流程

整个流水线按以下阶段串联：

```
加载配置 → 文件发现 → 逐目标处理 →
  1. 读取 Excel（data_loader）
  2. 解析表头与数值矩阵（geometry）
  3. 倾向 → 走向转换（geometry）
  4. 向量化端点坐标计算（geometry）
  5. 坐标规范化：平移 → 走向旋转 → 再平移（transforms）
  6. 导出 Excel（excel_export）
  7. 绘制迹线图（原始 & 旋转后）（plotting）
  8. 绘制玫瑰花瓣图（plotting）
```

### 核心模块说明

| 模块 | 职责 |
|---|---|
| `config.py` | 加载/校验 JSON 配置；输入目录文件发现（`find_trace_tables`）；路径解析 |
| `data_loader.py` | 读取 Excel（优先 .xlsx，回退 .xls）；封装 `ParsedTraceData` 数据类 |
| `geometry.py` | **纯向量化**复数运算计算迹线端点；倾向→走向转换 |
| `transforms.py` | 坐标平移（正象限留白）→ 走向旋转 → 再次平移的规范化流水线 |
| `excel_export.py` | 将结果拆分为四个区域（基本信息、原始坐标、旋转坐标、走向与长度）写入 Excel |
| `plotting.py` | matplotlib 绘图：迹线长度图（原始/旋转后）、节理走向玫瑰花瓣图 |
| `pipeline.py` | 单目标全流程编排，异常包装与日志 |

---

## 数据格式

### Excel 输入

每张迹线表需遵循以下列布局（与 MATLAB 原版约定一致）：

| 列号（0基） | 字段 | 说明 |
|---|---|---|
| 0 | `r1` | 沿测线位移 |
| 1 | `r2` | 垂直测线位移（正=左侧，负=右侧） |
| 2 | `倾向` | **节理倾向**（度），运行时会自动转为走向 |
| 3 | `r4` | 左侧迹长 1 |
| 4 | `r5` | 左侧迹长 2 |
| 5 | `r6` | 右侧迹长 1 |
| 6 | `r7` | 右侧迹长 2 |
| 7 | `ang0` | 测线走向角（度），**仅首行有效** |
| 8 | `n` | 迹线条数，**仅首行有效** |

**重要规则：**
- 文件名需以 `_process` 结尾（如 `O76_process.xlsx`），批量模式下按此规则发现文件。
- 工作表名使用 `outcrop_name`（如 `O76`）；若不存在，自动回退到第一个工作表。
- 前 `n` 行的前 7 列必须为数值，不可包含空值或文本。
- 迹线类型由 `r5` 和 `r7` 是否为 0 自动判定：
  - **左迹线**（`r5 ≠ 0, r7 = 0`）：仅左侧有迹长数据
  - **右迹线**（`r5 = 0, r7 ≠ 0`）：仅右侧有迹长数据
  - **双侧迹线**（`r5 ≠ 0, r7 ≠ 0`）：两侧均有迹长数据

### 角度转换规则

**倾向 → 走向**（与 MATLAB 一致）：

$$ \text{strike} = \begin{cases}
dd - 270 & dd \ge 270 \\
dd - 90 & 90 \le dd < 270 \\
dd + 90 & dd < 90
\end{cases} $$

**走向 → 绘图弧度**（用于坐标旋转）：

将 $0^\circ$–$360^\circ$ 走向角折叠到 $[-90^\circ, 90^\circ]$ 范围内：
- $(0, 90]$ → 正值，与走向一致
- $(90, 180]$ → $\text{ang} - 180^\circ$（负值）
- $(180, 270]$ → $\text{ang} - 180^\circ$（正值）
- $(270, 360)$ → $\text{ang} - 360^\circ$（负值）

---

## 输出

### 1. Excel 文件

`{file_name}_traces.xlsx`，单个工作表，包含四个区域：

| 区域 | 内容 |
|---|---|
| **A**（第1行） | 测线走向、迹线数量、平均迹线长度 |
| **B**（第4行起） | 原始端点坐标（起点X/Y，终点X/Y） |
| **C**（第4行起） | 旋转后端点坐标 |
| **D**（第4行起） | 每条迹线的节理走向与迹线长度 |

### 2. 图片文件

| 文件命名 | 说明 |
|---|---|
| `{outcrop}_raw(n={count}).png` | 原始迹线长度图，300 DPI |
| `{outcrop}_rotated(strike={deg}).png` | 按走向旋转后的迹线长度图，600 DPI |
| `{outcrop}_rose(bin={width}).png` | 节理走向玫瑰花瓣图（可选），400 DPI |

所有图片均为白底，迹线图为等比例无刻度坐标轴。

---

## 典型示例

```bash
# 1. 批量处理 input/ 下所有迹线表
python run_trace_pipeline.py

# 2. 单文件处理，自定义配置
python run_trace_pipeline.py -s -c my_config.json

# 3. 指定输入输出 + 自定义玫瑰图参数
python run_trace_pipeline.py -i ./field_data -o ./figures --rose-bin 15 --rose-dpi 600

# 4. 批量处理但跳过玫瑰图
python run_trace_pipeline.py --no-rose
```

---

## MATLAB 参考

原版 MATLAB 代码位于 `matlab参考/`：

| 文件 | 对应 Python 模块 |
|---|---|
| `A_outcrop_0map_coordinate.m` | 旧版主流程 → 现由 `pipeline.py` + `run_trace_pipeline.py` 替代 |
| `A_outcrop_0map_rotate.m` | 坐标旋转 → `transforms.py` |
| `Coordinate.m` | 几何计算 → `geometry.py` |

Python 实现采用向量化复数运算替代 MATLAB 的逐行循环，计算效率更高，且输出结果与原版一致。

---

## 开发

### 运行测试

```bash
# 安装开发依赖
pip install pytest

# 运行测试
pytest
```

测试文件位于 `tests/` 目录，命名格式 `test_*.py`。

### 日志

日志同时输出到控制台（INFO 级别）和文件（DEBUG 级别，位于 `logs/pipeline_YYYYMMDD_HHMMSS.log`），便于排查问题。

### 扩展

新增模块只需在 `trace_pipeline/` 下创建文件，并在 `__init__.py` 中导出即可。流水线编排在 `pipeline.py` 的 `process_target()` 函数中，可按需插入或替换阶段。
