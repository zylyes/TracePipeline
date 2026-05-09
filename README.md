# 岩体节理测线坐标计算与绘图工具

> **版本**: v0.1.0 | **语言**: Python >= 3.9 | **许可证**: MIT

基于 Python 的岩体节理测线法数据处理与可视化系统。以北山沙枣园花岗岩体 8 个露头（O76-O83）的 172 条节理迹线为数据基础，将 MATLAB 原型算法完整移植为工程化 Python 代码。适用于高放废物地质处置场址的节理几何特征分析。

**核心流水线**：综合法复数向量化端点计算 → 坐标平移与旋转标准化 → I/II/III 型自动分类 → 凸包露头面积 → 圆形取样窗法 4 策略自适应（tangent/hybrid/concentric + auto 6 因子加权评分）→ P10/P20/P21 密度统计 + Mauldon 迹长估计（实测优先三级回退）→ 四区 Excel 导出 → 迹线图（含比例尺、指北针、LaTeX 统计信息框）→ 玫瑰花瓣图。

> **毕业设计课题**: 26 届地球信息科学与技术专业 -- 周咏霖（学号 2022210162）
> **指导教师**: 霍亮（讲师），地球与行星科学学院
> **任务进度跟踪**: 见 [`reference/毕业设计任务流程与预期成果.md`](reference/毕业设计任务流程与预期成果.md)（v3.9）

---

## 研究背景

本项目服务于**甘肃北山高放废物地质处置**场址评价。北山沙枣园花岗岩体是我国高放废物处置库的候选场址，岩体结构面（节理）的几何特征——产状、迹长、密度——直接影响地下硐室稳定性评价与离散裂隙网络（DFN）建模的可靠性。野外采用**综合法（Scanline Method）**对 8 个花岗岩露头进行系统测量，记录 172 条节理迹线的 r1-r7 参数。传统 MATLAB 脚本逐条处理、缺乏统计与批量能力，本工具将其完整工程化为 Python。

> **参考资料**: 区域地质背景见 `reference/地质背景/`（董艳辉等、纪景仁等），统计理论来源见 `reference/文献/`（霍亮 4 篇、王贵宾、杨春和等），野外测量规范见 `reference/测量/`。

---

## 目录结构

```
.
├── config.json                         # 默认配置文件
├── pyproject.toml                      # 项目元数据与依赖（含 CLI 入口）
├── run_trace_pipeline.py               # CLI 入口脚本
├── constraints.txt                     # 依赖版本锁定
│
├── trace_pipeline/                     # 核心包
│   ├── __init__.py                     # 顶层公开 API（20 个导出，3 惰性导入）
│   ├── __main__.py                     # python -m trace_pipeline 入口
│   ├── models.py                       # TraceData / RunConfig / RunResult
│   ├── config.py                       # 配置加载、校验、路径解析
│   ├── validation.py                   # 校验与类型强制转换工具
│   ├── pipeline.py                     # 单目标全流程编排
│   ├── reporting.py                    # 结果格式化与汇总报告
│   │
│   ├── geology/                        # 地质/几何算法（纯函数，无 I/O）
│   │   ├── __init__.py                 # 子包导出
│   │   ├── angles.py                   # 倾向⇄走向、折叠、半平面
│   │   ├── endpoints.py                # 迹线端点向量化计算（复数运算）
│   │   ├── transforms.py               # 坐标平移与旋转变换
│   │   ├── statistics.py               # 统计编排层：P10/P20/P21 + 迹线分型
│   │   ├── _stat_types.py              #   └─ 统计数据类（TraceStatistics 等）
│   │   ├── _stat_format.py             #   └─ LaTeX 统计信息框格式化
│   │   ├── _circle_window.py           #   └─ 圆窗计数 + I/II/III 型分类
│   │   ├── _convex_hull.py             #   └─ 凸包面积（Andrew 单调链算法）
│   │   ├── _window_strategies.py       #   └─ tangent/hybrid/concentric 策略
│   │   ├── _window_scoring.py          #   └─ 6 因子加权评分与策略自动选择
│   │   └── _geometry_utils.py          #   └─ 几何常量与工具函数
│   │
│   ├── io/                             # I/O 层
│   │   ├── __init__.py                 # 子包导出（含 TraceFile、ExcelLayout）
│   │   ├── excel_reader.py             # Excel 读取（.xlsx/.xls 回退）
│   │   ├── excel_writer.py             # 四区布局写入
│   │   └── discovery.py                # 输入目录文件扫描与去重
│   │
│   ├── plotting/                       # 绘图层
│   │   ├── __init__.py                 # 子包导出（惰性加载 matplotlib）
│   │   ├── style.py                    # 全局样式 + CJK 字体多级回退
│   │   ├── trace_plot.py               # 迹线图（比例尺 + 指北针 + 统计框）
│   │   ├── rose_plot.py                # 玫瑰花瓣图
│   │   └── _helpers.py                 # Figure 工具（cm→inch、保存与关闭）
│   │
│   └── cli/                            # 命令行入口
│       ├── __init__.py                 # 子包导出
│       ├── main.py                     # 顶层编排（参数解析→配置加载→文件发现→目标决策→执行→汇总）
│       ├── args.py                     # argparse 参数解析
│       ├── interactive.py              # 交互式文件选择
│       ├── dispatcher.py               # 目标决策与串/并行执行
│       └── logging_setup.py            # 双通道日志（控制台 INFO / 文件 DEBUG）
│
├── input/                              # 输入目录（存放 *_process.xls*）
├── output/                             # 输出目录（Excel + 图片）
├── logs/                               # 运行日志（保留最近 7 份）
├── tests/                              # pytest 单元测试（17 个文件，覆盖全包）
│   ├── conftest.py                     # 共享夹具
│   └── test_*.py                       # 各模块测试
├── reference/                          # 研究资料（5 子目录，约 37 文件）
│   ├── matlab/                         # MATLAB 原版（3 .m + README，含 Bug 文档）
│   ├── 地质背景/                       # 区域地质 PDF x2（董艳辉、纪景仁）
│   ├── 文献/                           # 学术论文 7 篇（霍亮 x4、王贵宾、杨春和、许文涛，共 12 个文件）
│   ├── 测量/                           # 野外资料 x5（测量原理.docx、工具.docx、测线法说明.pptx、现场照片 x2）
│   └── 论文/                           # 论文相关 x13（任务书、开题报告、文献综述、初稿、外文翻译、模板等）
```

---

## 设计理念

```mermaid
graph TD
    CLI[用户接口层 cli/] --> PIPE[流水线层 pipeline.py / config.py / reporting.py]
    PIPE --> GEOL[核心计算层 geology/]
    PIPE --> IO[I/O 层 io/]
    PIPE --> PLOT[绘图层 plotting/]
    GEOL --> MODEL[数据模型层 models.py / validation.py]
    IO --> MODEL
    PLOT --> MODEL
```

| 原则 | 说明 |
|------|------|
| **不可变数据模型** | 6 个核心 `frozen=True` 数据类（`models.py`: `TraceData`、`RunConfig`、`RunResult`；`_stat_types.py`: `TraceStatistics`、`TraceStatisticsConfig`、`CircleWindowDiagnostic`），NumPy 数组深拷贝后设为 read-only |
| **纯函数计算层** | `geology/` 子包全部为纯函数——接收数组，返回数组，无 I/O 无副作用 |
| **向量化优先** | NumPy 广播 + 复数运算替代 `for` 循环；布尔 mask 索引替代多级 `if-else` |
| **惰性导入** | `__init__.py` 通过 `__getattr__` 延迟加载 matplotlib 依赖，`import trace_pipeline` 不触发绘图初始化 |
| **实测优先三级回退** | P10/P20/P21 各有独立回退链（measured -> window -> hull），全链路来源标注 (M)/(W)/(E) |
| **私有模块拆分** | `statistics.py` 作为编排层，委托 7 个 `_*.py` 单一职责模块（`_stat_types`、`_stat_format`、`_circle_window`、`_convex_hull`、`_window_strategies`、`_window_scoring`、`_geometry_utils`），每个模块 50-300 行 |

---

## 安装与环境配置

### 系统要求

- **Python** >= 3.9
- **pip** >= 21.0

### 依赖

| 包 | 用途 |
|---|---|
| `numpy` | 向量化数值计算 |
| `pandas` | Excel 表格读写 |
| `matplotlib` | 迹线图与玫瑰图绘制 |
| `openpyxl` | .xlsx 读写引擎 |
| `xlrd` | .xls 回退读取引擎 |
| `tqdm` | 命令行进度条 |

> 精确版本锁定见 `constraints.txt`。

### 快速开始

```bash
cd code

# 方式一：venv（推荐）
python -m venv .venv
.venv\Scripts\Activate.ps1    # Windows PowerShell
# 或 source .venv/bin/activate   # Linux/macOS
pip install -e .
pip install -e .[dev]         # 可选：安装开发依赖

# 方式二：conda / mamba
conda create -n trace python=3.11 -y
conda activate trace
pip install -e .

# 方式三：uv（快速）
uv sync
uv run trace-pipeline
```

安装后可通过 `trace-pipeline` 命令直接调用，或使用 `python run_trace_pipeline.py`。

### 运行效果

安装后一行命令即可生成全部成果，终端输出汇总表，`output/` 目录生成 32 个文件：

```bash
uv run trace-pipeline
```

| 产物 | 示例 | 数量 |
|------|------|------|
| 旋转迹线图（600 DPI，含 LaTeX 统计框） | `O76_rotated(strike=298.0).png` | 8 |
| 原始迹线图（300 DPI） | `O76_raw(n=19).png` | 8 |
| 玫瑰花瓣图（400 DPI） | `O76_rose(bin=10.0).png` | 8 |
| 四区 Excel | `O76_traces.xlsx` | 8 |

> 全部 8 露头串行处理约 30-60 秒，加 `-p 4` 启用 4 线程并行。详细输出格式见[输出](#输出)章节。

---

## 参考资料

`reference/` 包含 5 个子目录：`matlab/`（MATLAB 原版算法及对照文档）、`地质背景/`（区域地质文献）、`文献/`（学术论文 7 篇）、`测量/`（野外资料）、`论文/`（论文相关文档）。各资料与论文章节的对应关系见 [`reference/毕业设计任务流程与预期成果.md`](reference/毕业设计任务流程与预期成果.md)。

---

## 功能特性

| 功能 | 说明 |
|------|------|
| **数字化重构** | 从 r1-r7 测线记录通过复数法推导端点坐标，实现一维->二维空间还原 |
| **坐标变换** | 平移正象限 -> 走向角旋转 -> 再平移的规范化流水线 |
| **批量处理** | 自动扫描 `input/` 目录，支持 8 个露头一键处理（串行/并行） |
| **迹线图导出** | 原始迹线图（300 DPI）+ 旋转迹线图（600 DPI），含比例尺、指北针与统计信息框 |
| **玫瑰花瓣图** | 节理走向统计，可自定义分箱宽度与 DPI |
| **迹线统计指标** | I/II/III 型自动分类，P10/P20/P21 密度参数（实测优先三级回退），圆形取样窗法 4 策略自适应，Mauldon 平均迹长估计 |
| **Excel 四区输出** | A 基本信息 / B 原始坐标 / C 旋转坐标 / D 走向与长度 |
| **MATLAB 验证** | 与原版 `Coordinate.m` 端点坐标理论误差 < 1e-10 m（浮点精度级） |

---

## 配置

配置文件 `config.json`（项目根目录）控制所有运行参数：

```json
{
  "input_dir":          "input",
  "output_dir":         "output",
  "output_prefix":      "Outcrop",
  "table_stem":         "O76_process",
  "outcrop":            "O76",
  "process_all":        true,
  "export_rose_plot":    true,
  "rose_bin_width":      10,
  "rose_dpi":            400,
  "trace_dpi":           300,
  "rotated_trace_dpi":   600,
  "window_strategy":     "auto",
  "auto_density_threshold": 5.0,
  "tangent_window_count":   3
}
```

| 配置键 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `input_dir` | string | `"input"` | 输入目录（含 `*_process.xls*` 迹线表），支持相对/绝对路径 |
| `output_dir` | string | `"output"` | 输出目录（Excel + 图片将写入此目录） |
| `output_prefix` | string | `"Outcrop"` | 输出 Excel 命名前缀；批量模式按露头名输出，单文件模式下显式改为非默认值时生效 |
| `table_stem` | string | `"O76_process"` | 单文件模式下读取的 Excel 文件名（不含扩展名） |
| `outcrop` | string | `"O76"` | 露头名称（也是 Excel 工作表名） |
| `process_all` | bool | `true` | `true`=批量处理；`false`=仅处理 `table_stem` 指定文件 |
| `export_rose_plot` | bool | `true` | 是否导出玫瑰花瓣图 |
| `rose_bin_width` | float | `10` | 玫瑰图分箱宽度（度），范围 (0, 180]，运行时校验 |
| `rose_dpi` | int | `400` | 玫瑰图分辨率 |
| `trace_dpi` | int | `300` | 原始迹线图分辨率 |
| `rotated_trace_dpi` | int | `600` | 旋转迹线图分辨率 |
| `window_strategy` | string | `"auto"` | 圆形取样窗策略：`auto`（自适应）/ `tangent`（沿测线均布相切圆）/ `hybrid`（3切点x左右x3半径）/ `concentric`（同心圆） |
| `auto_density_threshold` | float | `5.0` | `auto` 策略下切换 hybrid->concentric 的粗估面密度阈值 |
| `tangent_window_count` | int | `3` | `tangent` 策略下每侧布置的切圆数量 |

常用配置项可通过命令行参数覆盖（`-i/-o`、`--rose-bin/--rose-dpi`、`--no-rose`、`--window-strategy`、`-s` 等）；`trace_dpi`、`rotated_trace_dpi` 等其余项通过 `-c` 指定自定义 JSON 配置文件来覆盖。

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

显式通过 `-c/--config` 指定配置文件时，路径必须存在；默认不传 `-c` 时才会回退到项目根目录的 `config.json` 或内置默认配置。

### 完整 CLI 选项

| 参数 | 简写 | 说明 |
|---|---|---|
| `--input` | `-i` | 输入目录（覆盖 `input_dir`） |
| `--output` | `-o` | 输出目录（覆盖 `output_dir`） |
| `--config` | `-c` | 自定义 JSON 配置文件路径 |
| `--single` | `-s` | 单文件模式：仅处理 `table_stem` 指定文件 |
| `--rose-bin` | -- | 玫瑰图分箱宽度（度） |
| `--rose-dpi` | -- | 玫瑰图 DPI |
| `--no-rose` | -- | 跳过玫瑰图导出 |
| `--window-strategy` | -- | 圆窗策略：auto/tangent/hybrid/concentric |
| `--parallel` | `-p` | 并行处理线程数（默认 0=串行） |
| `--list` | `-l` | 列出发现的迹线表文件后退出 |
| `--interactive` | `-I` | 交互模式：由用户选择处理目标 |
| `--dry-run` | `-n` | 试运行：打印待处理目标但不执行 |

### 运行模式

**批量模式**（默认）：扫描 `input/` 下所有 `*_process.xlsx`（或 `*.xls`）文件。

```bash
python run_trace_pipeline.py              # 批量处理
python run_trace_pipeline.py --no-rose    # 批量处理，跳过玫瑰图
python run_trace_pipeline.py -p 4          # 4 线程并行
python run_trace_pipeline.py --window-strategy hybrid  # 指定圆窗策略
```

**单文件模式**：仅处理 `table_stem` 指定的文件。

```bash
python run_trace_pipeline.py -s                      # 仅处理 O76
python run_trace_pipeline.py -s -c my_config.json     # 自定义配置
```

---

## 数据处理流程

```text
加载配置 -> 文件发现 -> 逐目标处理 ->
  1. 读取 Excel -> 解析表头与数值矩阵
  2. 倾向 -> 走向转换（dip_to_strike）
  3. 向量化端点坐标计算（三种情形复数运算）
  4. 坐标规范化：平移 -> 走向旋转 -> 再平移
  5. 迹线统计指标计算（I/II/III 型分类、P10/P20/P21、露头面积、圆形取样窗法迹长回退估算）
  6. 导出 Excel（四区布局写入）
  7. 绘制迹线图（原始 & 旋转后，含 LaTeX 统计信息框、比例尺、指北针）
  8. 绘制玫瑰花瓣图
```

### 核心模块

| 模块 | 职责 | 关键函数 |
|------|------|----------|
| `geology/angles.py` | 倾向->走向、走向折叠、半平面折叠 | `dip_to_strike`, `fold_strike_angle`, `fold_to_halfplane` |
| `geology/endpoints.py` | 向量化端点坐标计算、表头解析 | `compute_endpoints` |
| `geology/transforms.py` | 坐标平移与旋转标准化流水线 | `normalize_coordinates` |
| `geology/statistics.py` | 统计编排层：P10/P20/P21 + I/II/III 分类（委托 7 个私有模块） | `compute_trace_statistics` |
| `pipeline.py` | 单目标全流程编排 | `run_pipeline`, `load_trace_data` |
| `config.py` | 配置加载/校验、路径解析、CLI 覆盖 | `load_config`, `resolve_io_paths`, `apply_cli_overrides` |
| `io/excel_reader.py` | Excel 迹线表读取（.xlsx/.xls 回退） | `read_trace_excel` |
| `io/excel_writer.py` | 四区布局写入（A/B/C/D 区） | `build_excel_sections`, `write_excel_sections` |
| `io/discovery.py` | 输入目录文件扫描与去重 | `find_trace_tables` |
| `plotting/trace_plot.py` | 迹线图（比例尺 + 指北针 + LaTeX 统计信息框） | `render_trace_plot` |
| `plotting/rose_plot.py` | 玫瑰花瓣图 | `render_rose_plot` |
| `plotting/style.py` | 全局样式配置 + CJK 字体多级回退 | `configure_style` |
| `reporting.py` | 结果格式化：详情、汇总表、统计摘要 | `print_pipeline_results`, `format_results_table` |
| `models.py` | 不可变数据类（含校验） | `TraceData`, `RunConfig`, `RunResult` |
| `cli/` | 命令行入口：args/dispatcher/interactive/logging_setup/main | `parse_args`, `execute_targets`, `select_targets_interactive` |

### 内部子模块（geology/ 统计实现）

`statistics.py` 将统计流程委托给以下 7 个私有模块，各自承担单一职责：

| 模块 | 职责 | 关键函数/类 |
|------|------|------------|
| `_stat_types.py` | 统计数据类定义 | `TraceStatistics`, `TraceStatisticsConfig`, `CircleWindowDiagnostic` |
| `_circle_window.py` | 圆窗计数与 I/II/III 型分类 | `classify_trace_types`, `_count_circle_window` |
| `_convex_hull.py` | 凸包面积估算 | `convex_hull_area`（Andrew 单调链算法 + Shoelace 公式） |
| `_window_strategies.py` | 三种圆窗策略实现 | `compute_circle_windows`（调度 tangent/hybrid/concentric） |
| `_window_scoring.py` | auto 策略 6 因子评分与选择 | `select_window_diagnostics`, `aggregate_window_metric` |
| `_stat_format.py` | LaTeX 统计信息框文本 | `format_statistics_box_lines`（10 行指标，含来源标注） |
| `_geometry_utils.py` | 几何常量与工具 | `cross_2d`, `_EPS`（浮点容差 1e-9） |

此外，`plotting/_helpers.py` 提供 `new_figure`（cm->inch 转换）与 `save_figure`（保存+关闭）工具函数。

---

## 数据格式

### 综合法测量原理

本项目采用**综合法**（Scanline Method 的扩展）进行野外节理调查。根据迹线与测线的相互关系，分为三种类型：

| 类型 | 名称 | 判定条件 | 特征 |
|------|------|----------|------|
| **I型** | 相交型 | 迹线直接穿过测线 | 双侧均有迹线延伸 |
| **II型** | 延长相交型 | 迹线延长线穿过测线 | 单侧迹线延伸 |
| **III型** | 不相交型 | 迹线及延长线均不穿过测线 | 过迹线起点作测线垂线定位 |

> 仅记录迹长 > 30 cm 的结构面，短于 30 cm 的表层微裂隙不纳入统计。

### Excel 输入格式

`input/` 目录中的 `*_process.xls`（或 `.xlsx`）列布局（下表为 0-based 编程索引，对应 Excel 实际列号 = 索引 + 1）：

| 列号 | 符号 | 物理含义 | 约束 |
|------|------|----------|------|
| 0 | `r1` | 沿测线位移 | >=0 |
| 1 | `r2` | 垂直测线偏移（左正右负） | -- |
| 2 | `dip` | 节理倾向，自动转为走向 | [0, 360) |
| 3 | `r4` | 左侧迹线第一段长度 | >=0 |
| 4 | `r5` | 左侧迹线第二段长度 | >=0 |
| 5 | `r6` | 右侧迹线第一段长度 | >=0 |
| 6 | `r7` | 右侧迹线第二段长度 | >=0 |
| 7 | `ang0` | 测线走向角（**仅首行有效**） | [0, 360) |
| 8 | `n` | 迹线条数（**仅首行有效**） | >=1 |
| 9-10 | -- | 保留列，程序不读取 | -- |
| 11 | `scanline_length` | 实测测线长度，m（**仅首行有效，可选**） | >0 |
| 12 | `outcrop_area` | 实测露头面积，m2（**仅首行有效，可选**） | >0 |

**关键规则**：
- 文件名需以 `_process` 结尾，批量模式下按此规则发现
- 工作表名 = 露头编号（如 `O76`），不存在时回退到第一张表
- 前 `n` 行的前 7 列必须为数值
- 列 11（Excel 第 12 列）实测测线长度、列 12（Excel 第 13 列）实测露头面积均按"实测优先"；缺失或非法时自动估算
- 迹线类型由 r5、r7 自动判定：`r5!=0, r7=0` -> 左迹线；`r5=0, r7!=0` -> 右迹线；`r5!=0, r7!=0` -> 双侧迹线

### 倾向->走向转换公式

$$ \text{strike} = \begin{cases}
dd - 270 & dd \ge 270 \\
dd - 90 & 90 \le dd < 270 \\
dd + 90 & dd < 90
\end{cases} $$

走向角进一步折叠到 $[-90^\circ, 90^\circ]$ 用于坐标旋转。

### 迹线统计指标

> 理论参考：王贵宾、杨春和等《岩体节理平均迹长估计》；Laslett C. (1982) 圆形取样窗法；Mauldon M. (1998) 平均迹长闭式估计。实现：`statistics.py` + 7 个私有子模块。

#### 密度参数定义

| 指标 | 含义 | 计算方法 |
|------|------|----------|
| **P10** | 线密度（m^-1） | 迹线数 / 测线长度；测线长度优先读取列 11 实测值，缺失/非法时由 r1 间距估算 |
| **P20** | 面密度（m^-2） | `trace_count / effective_area`；面积优先链：实测 → 凸包 → 圆窗等效；面积不可用时回退圆窗 P20 |
| **P21** | 面累计长度密度（m^-1） | `observed_total / effective_area`；observed 优先：测段(r5+r7) → 端点欧氏距离 → 圆窗 L_est；面积不可用时回退圆窗 P21 |
| **平均迹长** | 平均迹线长度（m） | 三级回退：(1) 测段(r5+r7) 现场观测 → (2) 端点欧氏距离校验 → (3) 圆窗 Mauldon L_est 兜底 |
| **露头面积** | 露头有效面积（m2） | 三层回退：实测 → 凸包 → 圆窗等效(`trace_count / P20_window`)；凸包退化或与圆窗差异 >40% 时自动降级 |

来源标注：**(M)** 实测、**(W)** 圆窗、**(W_eq)** 圆窗等效、**(E)** 估算/凸包/端点/测段。

#### 圆形取样窗法（4 策略）

| 策略 | 窗口布置 | 适用场景 |
|------|----------|----------|
| **tangent** | 沿测线均布 k 个相切圆（每侧 `tangent_window_count` 个） | 大间距、稀疏迹线 |
| **hybrid** | 3 切点（25%/50%/75%）x 2 侧 x 3 半径缩放比（1.0/0.75/0.50），最多 18 窗口 | 中等密度 |
| **concentric** | 测线中点同心圆，按 `radius_fractions` 生成多个半径 | 高密度 |
| **auto** | 分别试算 tangent/hybrid/concentric，按 6 因子加权评分选择最优策略 | 默认推荐 |

各窗口统计量：n_0（两端点均在圆外但线段穿过圆）、n_1（一端在圆内）、n_2（两端均在圆内）。聚合指标：m = n_1 + 2*n_2、q = 2*n_0 + n_1。指标按 group_key 分组取均值后再聚合，无效窗口（交集数 < `min_intersections` 或 m <= 0）自动排除。

#### auto 策略评分机制

对 tangent/hybrid/concentric 三种候选策略分别计算加权总分，最高分胜出：

| 因子 | 权重 | 计算方式 |
|------|------|----------|
| 有效组数 | x1.45 | 有效分组数 / 策略最大可能分组数 |
| 有效组比例 | x1.00 | 有效分组 / 该策略全部分组 |
| 空间覆盖 | x1.35 | 双侧平衡度（0-0.85 分）+ 沿测线三分区覆盖率，取均值 |
| 指标稳定性 | x1.10 | 1/(1+CV) 对 P20/P21/L_est 三指标取均值 |
| 半径尺度 | x1.00 | median_radius / max_radius |
| 样本充足率 | x1.10 | mean(min(1, count / (2 * min_intersections))) |

若最高分与粗估密度偏好策略的分差 <= 12% 容差，回退到密度偏好；无有效候选时按粗估面密度降级（tangent -> hybrid -> concentric）。

#### 窗口一致性校验

圆窗诊断**始终计算**，不再只在兜底时使用。主结果选定后，系统自动对比主结果与圆窗结果：

| 对比项 | 判定方式 | 阈值 | 动作 |
|--------|----------|------|------|
| 面积差异 | `abs(hull - window_eq) / max(...)` | 40% | 凸包无效/差异过大时降级到圆窗等效面积 |
| P20 差异 | `abs(P20_main - P20_window) / max(...)` | 50% | 记录密度校验告警 |
| P21 差异 | `abs(P21_main - P21_window) / max(...)` | 50% | 记录密度校验告警 |

有实测面积时，面积来源不被圆窗覆盖，但仍记录密度差异告警。圆窗等效面积是统计等效值，不等同于现场 GPS 多边形实测面积。

### 各露头统计汇总

| 露头 | 迹线数 | 测线走向 | 平均迹长 (m) | I/II/III | P10 (m⁻¹) | P20 (m⁻²) | P21 (m⁻¹) | 策略 | 有效窗 |
|------|--------|----------|-------------|----------|-----------|-----------|-----------|------|--------|
| O76 | 19 | 298 | 10.07 | 13/6/0 | 1.0671 | 0.0530 (W) | 0.5180 (W) | concentric | 6 |
| O77 | 19 | 280 | 9.06 | 12/7/0 | 0.8064 | 0.0338 (W) | 0.3065 (W) | concentric | 6 |
| O78 | 26 | 165 | 3.45 | 21/5/0 | 1.0033 | 0.0607 (W) | 0.2167 (W) | concentric | 6 |
| O79 | 20 | 212 | 6.67 | 20/0/0 | 0.5672 | 0.0225 (W) | 0.1560 (W) | concentric | 6 |
| O80 | 29 | 334 | 6.57 | 29/0/0 | 1.1959 | 0.0585 (W) | 0.3757 (W) | concentric | 6 |
| O81 | 19 | 75 | 14.27 | 17/2/0 | 2.2042 | 0.1362 (W) | 1.8798 (W) | hybrid | 18 |
| O82 | 20 | 273 | 4.99 | 18/2/0 | 1.6632 | 0.1430 (W) | 0.6884 (W) | concentric | 6 |
| O83 | 20 | 265 | 4.15 | 18/2/0 | 2.1769 | 0.2383 (W) | 0.9856 (W) | concentric | 6 |

> 上表由 `auto` 策略生成。来源标注：(M) 实测、(W) 圆窗、(W_eq) 圆窗等效、(E) 估算/凸包/端点/测段。当前 8 个输入表缺少实测测线长度和实测露头面积，因此主要使用凸包面积与圆窗校验；有现场观测测段长度(r5+r7)时优先使用。详细数据参见各露头迹线图内置 LaTeX 统计信息框。

---

## 输出

### Excel 文件

`{outcrop}_traces.xlsx`，单工作表，包含 3 个汇总 Section + 3 个数据 Section（共 6 个区段）：

| Section | 列位置 | 内容 |
|--------|--------|------|
| **基本信息** | 左 | 测线走向、测线长度、平均迹长、露头面积 |
| **裂隙情况** | 中 | 迹线数量、I/II/III 型裂隙数 |
| **计算数据** | 右 | P10/P20/P21（含来源标注）、有效取样窗数量 |
| **原始端点坐标** | 左 | 起点(X,Y)、终点(X,Y) |
| **旋转后端点坐标** | 中 | 旋转后起点(X,Y)、旋转后终点(X,Y) |
| **走向与长度** | 右 | 节理走向(°)、端点距离、测段长度(r5+r7)、迹线类型 |

### 图片文件

| 命名模式 | 说明 | DPI |
|----------|------|-----|
| `{outcrop}_raw(n={count}).png` | 原始迹线图（含比例尺 + 指北针 + LaTeX 统计信息框） | 300 |
| `{outcrop}_rotated(strike={azimuth}).png` | 走向旋转后迹线图（含比例尺 + 指北针 + LaTeX 统计信息框） | 600 |
| `{outcrop}_rose(bin={width}).png` | 玫瑰花瓣图 | 400 |

> 注：`azimuth` 和 `width` 为浮点数（如 `strike=298.0`、`bin=10.0`），`count` 为整数。

### 输出示例

```
output/
├── O76_raw(n=19).png
├── O76_rotated(strike=298.0).png
├── O76_rose(bin=10.0).png
├── O76_traces.xlsx
├── ...（O77-O83 同理，共 32 个文件）
└── O83_rotated(strike=265.0).png
```

---

## 使用示例

### 日常使用

```bash
python run_trace_pipeline.py           # 批量处理全部 8 露头
python run_trace_pipeline.py -l        # 列出可用文件
python run_trace_pipeline.py -n        # 试运行，预览目标不实际处理
```

### 自定义输出

```bash
python run_trace_pipeline.py --rose-bin 15 --rose-dpi 600
python run_trace_pipeline.py --window-strategy hybrid
python run_trace_pipeline.py -o ./results --no-rose
```

### 高级用法

```bash
python run_trace_pipeline.py -I                    # 交互式选择目标
python run_trace_pipeline.py -p 4                  # 4 线程并行
python run_trace_pipeline.py -s -c my_config.json  # 单文件 + 自定义配置
```

---

## MATLAB 参考

原版 MATLAB 代码位于 `reference/matlab/`：

| 文件 | Python 对应模块 |
|---|---|
| `Coordinate.m` | `endpoints.py` + `angles.py`（核心几何算法） |
| `A_outcrop_0map_coordinate.m` | `pipeline.py`（主流程） |
| `A_outcrop_0map_rotate.m` | `transforms.py`（坐标旋转） |

### MATLAB vs Python 对比

| 功能区 | MATLAB 原版 | Python 版 |
|------|-------------|-----------|
| 计算模式 | `for` 循环逐条处理 | NumPy 向量化批量运算 |
| 角度转换 | 硬编码 `if-else` | `numpy.select` 向量化分段映射 |
| 坐标变换 | 逐行循环旋转 | 矩阵广播一次性旋转 |
| I/O | `xlsread`/`writematrix` 单文件 | `pandas`+`openpyxl` 四区布局 |
| 绘图 | `plot` + 手动导图 | `matplotlib` 自动排版 + 多 DPI + CJK 多字体回退 |
| 批量处理 | 手动改文件名逐张运行 | 自动扫描 + 可选并行 + 进度条 |
| 迹线统计 | 无 | I/II/III 型分类 + P10/P20/P21（三级回退）+ 凸包面积 + 圆形取样窗法 4 策略 + Mauldon 迹长 |
| 迹线图信息 | 无 | LaTeX 统计信息框（P10/P20/P21/迹长/分型/露头面积）内置 |
| 精度 | 基准 | 端点坐标误差 < 1e-10 m |

### 迁移要点

- **向量化**：逐条 `for` 循环改为 NumPy mask 三分支，角度/半平面改为数组广播
- **修正 MATLAB Bug**：`A_outcrop_0map_rotate.m:68-76` 中 `if ang0<=360` 永远为真，导致分支不可达；Python 版 `fold_strike_angle` 正确折叠到 `[-90, 90]`
- **双定义输出**：Excel 同时输出端点距离（欧氏距离）与测段长度（r5+r7）
- **统计增强**：新增 I/II/III 型自动分类、凸包露头面积、P10/P20/P21 密度参数（三级回退），圆形取样窗法 4 策略自适应 + Mauldon 平均迹长，来源标注 (M)/(W)/(E)
- **自动导出**：迹线图含比例尺、指北针与统计信息框，玫瑰图支持自定义分箱，CJK 字体自动回退

### 验证

端点坐标算法与 MATLAB 原版 `Coordinate.m` 公式完全一致（均使用双精度浮点），理论误差 < 1e-10 m。完整的自动化基准测试脚本待补充。

```bash
python run_trace_pipeline.py -s    # 处理 O76
# Excel 区域 B（原始坐标）与 MATLAB XY 变量逐行对比
# 最大绝对误差 < 1e-10 m
```

---

## 开发

### 开发工具

```bash
# 安装开发依赖
pip install -e .[dev]

# 代码检查（ruff）
ruff check .

# 类型检查（mypy）
mypy trace_pipeline/

# 运行测试
pytest

# 运行测试 + 覆盖率
pytest --cov --cov-report=term --cov-report=html
```

| 工具 | 配置位置 | 要点 |
|------|----------|------|
| ruff | `pyproject.toml [tool.ruff]` | Python 3.9 target, 100 列行宽, 规则集 E/F/I/N/UP/B/SIM |
| mypy | `pyproject.toml [tool.mypy]` | Python 3.10 target, `warn_return_any=true` |
| pytest | `pyproject.toml [tool.pytest]` | testpaths = `tests/`, 文件匹配 `test_*.py` |
| coverage | `pyproject.toml [tool.coverage]` | 源 = `trace_pipeline/`, 排除 `tests/` |

### 测试

测试套件共 17 个文件（`tests/` 目录），覆盖全部公开模块：

| 测试文件 | 被测模块 |
|----------|----------|
| `test_angles.py` | `geology/angles.py` -- 倾向走向转换、折叠逻辑 |
| `test_endpoints.py` | `geology/endpoints.py` -- 端点计算三分支、可选测量值 |
| `test_transforms.py` | `geology/transforms.py` -- 坐标变换流水线 |
| `test_statistics.py` | `geology/statistics.py` — P10/P20/P21、I/II/III 分型、圆窗计数与策略选择、凸包面积、Mauldon 迹长 |
| `test_excel_reader.py` | `io/excel_reader.py` -- Excel 读取与回退 |
| `test_excel_writer.py` | `io/excel_writer.py` -- 四区布局与样式 |
| `test_discovery.py` | `io/discovery.py` -- 文件扫描与去重 |
| `test_plotting.py` | `plotting/` -- 迹线图与玫瑰图生成 |
| `test_models.py` | `models.py` -- 数据类校验 |
| `test_config.py` | `config.py` -- 配置加载与校验 |
| `test_cli_main.py` | `cli/main.py` -- CLI 入口编排 |
| `test_dispatcher.py` | `cli/dispatcher.py` -- 目标决策与执行 |
| `test_interactive.py` | `cli/interactive.py` -- 交互模式 |
| `test_logging_setup.py` | `cli/logging_setup.py` -- 日志初始化 |
| `test_reporting.py` | `reporting.py` -- 结果格式化 |
| `test_integration.py` | `pipeline.py` -- 端到端集成 |
| `test_imports.py` | `__init__.py` -- 包导入与惰性加载 |

### 日志

双通道输出：控制台（INFO 级别）+ 文件（DEBUG 级别，`logs/pipeline_YYYYMMDD_HHMMSS.log`，保留最近 7 份）。

### 扩展

新增模块在 `trace_pipeline/` 下创建，在 `__init__.py` 中导出。流水线编排在 `pipeline.py:run_pipeline()` 中，可按需插入或替换阶段。顶层包导出 20 个公开入口（含 `TraceStatisticsConfig`、`compute_trace_statistics` 等统计接口），底层函数可直接导入：

```python
from trace_pipeline import run_pipeline, TraceData, compute_trace_statistics
from trace_pipeline.geology.angles import fold_strike_angle
from trace_pipeline.geology.statistics import TraceStatisticsConfig
```

### 常见问题

| 现象 | 原因 | 解决 |
|------|------|------|
| 迹线图中文字符显示为方块 | 系统缺少 CJK 字体 | 安装宋体/黑体，或配置 `matplotlib` 字体目录；程序已内置衬线回退链 SimSun → Noto Serif SC → STSong → FangSong，无衬线回退链 SimHei → Microsoft YaHei → Noto Sans CJK SC 等多级自动检测 |
| `ModuleNotFoundError: openpyxl` | 未安装依赖 | `pip install -e .` |
| 发现 0 个迹线表文件 | 文件名不以 `_process` 结尾 | 重命名为 `{露头}_process.xls(x)` 并放入 `input/` |
| "工作表不存在" 错误 | Sheet 名与露头编号不一致 | 确保 Sheet 名为 `O76`/`O77`…与文件名露头部分一致 |
| P20/P21 显示 NaN | 迹线数过少（< 3）导致凸包退化 | 检查输入数据；此为正常兜底行为，论文中标注 N/A |
| 迹线图统计框内数值与论文预期不符 | 圆窗策略不同导致估计值差异 | 尝试 `--window-strategy tangent` 或 `hybrid` 对比 |
