# 岩体节理测线坐标计算与绘图工具

基于 Python 实现的岩体节理测线法数据处理与可视化系统。以北山沙枣园花岗岩体 8 个露头（O76–O83）的 172 条节理迹线为数据基础，将 MATLAB 原版算法完整移植为工程化 Python 代码，实现从原始测线记录到二维迹线图、玫瑰花瓣图的自动化流水线。

> **毕业设计课题**: 26 届地球信息科学与技术专业 — 周咏霖（学号 2022210162）
> **指导教师**: 霍亮（讲师），地球与行星科学学院
> **任务进度跟踪**: 见 [`reference/毕业设计任务流程与预期成果.md`](reference/毕业设计任务流程与预期成果.md)（v3.4）

---

## 目录结构

```
.
├── config.json                    # 默认配置文件
├── pyproject.toml                 # 项目元数据与依赖（含 CLI 入口）
├── run_trace_pipeline.py          # CLI 入口脚本
│
├── trace_pipeline/                # 核心包
│   ├── __init__.py                # 顶层公开 API
│   ├── __main__.py                # 支持 `python -m trace_pipeline`
│   ├── models.py                  # TraceData / RunConfig / RunResult
│   ├── config.py                  # 配置加载、校验、路径解析
│   ├── pipeline.py                # 单目标全流程编排
│   ├── reporting.py               # 结果格式化与汇总报告
│   │
│   ├── geology/                   # 地质/几何算法（纯函数，无 I/O）
│   │   ├── angles.py              # 倾向⇄走向、折叠、半平面
│   │   ├── endpoints.py           # 迹线端点向量化计算（复数运算）
│   │   ├── transforms.py          # 坐标平移与旋转变换
│   │   └── statistics.py          # P10/P20/P21 密度统计与迹线分型
│   │
│   ├── io/                        # I/O 层
│   │   ├── excel_reader.py        # Excel 读取
│   │   ├── excel_writer.py        # 四区布局写入
│   │   └── discovery.py           # 输入目录文件扫描
│   │
│   ├── plotting/                  # 绘图层
│   │   ├── style.py               # 全局样式 + CJK 字体检测
│   │   ├── trace_plot.py          # 迹线图（比例尺 + 指北针）
│   │   ├── rose_plot.py           # 玫瑰花瓣图
│   │   └── _helpers.py            # Figure 辅助工具
│   │
│   └── cli/                       # 命令行入口
│       ├── main.py                # 顶层编排
│       ├── args.py                # argparse 参数解析
│       ├── interactive.py         # 交互式文件选择
│       ├── dispatcher.py          # 目标决策与串/并行执行
│       └── logging_setup.py       # 日志初始化
│
├── input/                         # 输入目录（存放 *_process.xls*）
├── output/                        # 输出目录（Excel + 图片）
├── logs/                          # 运行日志
├── tests/                         # pytest 单元测试
└── reference/                     # 研究资料（含 MATLAB 原版参考代码）
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
| `tqdm` | 命令行进度条 |

### 快速开始

```bash
cd code
python -m venv .venv
.venv\Scripts\Activate.ps1    # Windows PowerShell
pip install -e .               # 安装（含 CLI 入口和所有依赖）
pip install -e .[dev]          # （可选）安装开发依赖
```

安装后可通过 `trace-pipeline` 命令直接调用，或使用 `python run_trace_pipeline.py`。

---

## 功能特性

| 功能 | 说明 |
|------|------|
| **数字化重构** | 从 r1–r7 测线记录通过复数法推导端点坐标，实现一维→二维空间还原 |
| **坐标变换** | 平移正象限 → 走向角旋转 → 再平移的规范化流水线 |
| **批量处理** | 自动扫描 `input/` 目录，支持 8 个露头一键处理（串行/并行） |
| **迹线图导出** | 原始迹线图（300 DPI）+ 旋转迹线图（600 DPI），含比例尺、指北针与统计信息框 |
| **玫瑰花瓣图** | 节理走向统计，可自定义分箱宽度与 DPI |
| **迹线统计指标** | I/II/III 型自动分类，实测优先的 P10/P20/P21 密度参数，圆形取样窗法作为缺失迹长的 Laslett 回退估算 |
| **Excel 四区输出** | A 基本信息 / B 原始坐标 / C 旋转坐标 / D 走向与长度 |
| **MATLAB 验证** | 与原版 `Coordinate.m` 端点坐标误差 < 1e-10 m |

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
  "rotated_trace_dpi":   600
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

所有配置项均可通过命令行参数覆盖。

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
| `--rose-bin` | — | 玫瑰图分箱宽度（度） |
| `--rose-dpi` | — | 玫瑰图 DPI |
| `--no-rose` | — | 跳过玫瑰图导出 |
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
```

**单文件模式**：仅处理 `table_stem` 指定的文件。

```bash
python run_trace_pipeline.py -s                      # 仅处理 O76
python run_trace_pipeline.py -s -c my_config.json     # 自定义配置
```

---

## 数据处理流程

```text
加载配置 → 文件发现 → 逐目标处理 →
  1. 读取 Excel → 解析表头与数值矩阵
  2. 倾向 → 走向转换（dip_to_strike）
  3. 向量化端点坐标计算（三种情形复数运算）
  4. 坐标规范化：平移 → 走向旋转 → 再平移
  5. 迹线统计指标计算（I/II/III 型分类、P10/P20/P21、露头面积、圆形取样窗法迹长回退估算）
  6. 导出 Excel（四区布局写入）
  7. 绘制迹线图（原始 & 旋转后，含 LaTeX 统计信息框、比例尺、指北针）
  8. 绘制玫瑰花瓣图
```

### 核心模块

| 模块 | 职责 | 关键函数 |
|------|------|----------|
| `angles.py` | 倾向→走向、走向折叠、半平面折叠 | `dip_to_strike`, `fold_strike_angle`, `fold_to_halfplane` |
| `endpoints.py` | 向量化端点坐标计算、表头解析 | `compute_endpoints` |
| `transforms.py` | 坐标平移与旋转标准化流水线 | `normalize_coordinates` |
| `statistics.py` | P10/P20/P21 密度统计、I/II/III 型分类、露头面积估算、圆形取样窗法迹长回退估算 | `compute_trace_statistics` |
| `pipeline.py` | 单目标全流程编排 | `run_pipeline`, `load_trace_data` |
| `config.py` | 配置加载/校验、路径解析、CLI 覆盖 | `load_config`, `resolve_io_paths` |
| `io/` | Excel 读取、四区布局写入、文件发现 | `read_trace_excel`, `write_excel_sections` |
| `plotting/` | 迹线图、玫瑰图、全局样式（CJK 字体） | `render_trace_plot`, `render_rose_plot` |
| `reporting.py` | 结果格式化：详情、汇总表、统计摘要 | `print_pipeline_results` |
| `models.py` | 不可变数据类 | `TraceData`, `RunConfig`, `RunResult` |

---

## 数据格式

### 综合法测量原理

本项目采用**综合法**（Scanline Method 的扩展）进行野外节理调查。根据迹线与测线的相互关系，分为三种类型：

| 类型 | 名称 | 判定条件 | 特征 |
|------|------|----------|------|
| **Ⅰ型** | 相交型 | 迹线直接穿过测线 | 双侧均有迹线延伸 |
| **Ⅱ型** | 延长相交型 | 迹线延长线穿过测线 | 单侧迹线延伸 |
| **Ⅲ型** | 不相交型 | 迹线及延长线均不穿过测线 | 过迹线起点作测线垂线定位 |

> 仅记录迹长 > 30 cm 的结构面，短于 30 cm 的表层微裂隙不纳入统计。

### Excel 输入格式

`input/` 目录中的 `*_process.xls`（或 `.xlsx`）列布局：

| 列号 | 符号 | 物理含义 | 约束 |
|------|------|----------|------|
| 0 | `r1` | 沿测线位移 | ≥0 |
| 1 | `r2` | 垂直测线偏移（左正右负） | — |
| 2 | `dip` | 节理倾向，自动转为走向 | [0°, 360°) |
| 3 | `r4` | 左侧迹线第一段长度 | ≥0 |
| 4 | `r5` | 左侧迹线第二段长度 | ≥0 |
| 5 | `r6` | 右侧迹线第一段长度 | ≥0 |
| 6 | `r7` | 右侧迹线第二段长度 | ≥0 |
| 7 | `ang0` | 测线走向角（**仅首行有效**） | [0°, 360°) |
| 8 | `n` | 迹线条数（**仅首行有效**） | ≥1 |
| 9–10 | — | 保留列，程序不读取 | — |
| 11 | `scanline_length` | 实测测线长度，m（**仅首行有效，可选**） | >0 |
| 12 | `outcrop_area` | 实测露头面积，m²（**仅首行有效，可选**） | >0 |

**关键规则**：
- 文件名需以 `_process` 结尾，批量模式下按此规则发现
- 工作表名 = 露头编号（如 `O76`），不存在时回退到第一张表
- 前 `n` 行的前 7 列必须为数值
- 第 12 列实测测线长度、第 13 列实测露头面积均按“实测优先”；缺失或非法时自动估算
- 迹线类型由 r5、r7 自动判定：`r5≠0, r7=0` → 左迹线；`r5=0, r7≠0` → 右迹线；`r5≠0, r7≠0` → 双侧迹线

### 倾向→走向转换公式

$$ \text{strike} = \begin{cases}
dd - 270 & dd \ge 270 \\
dd - 90 & 90 \le dd < 270 \\
dd + 90 & dd < 90
\end{cases} $$

走向角进一步折叠到 $[-90^\circ, 90^\circ]$ 用于坐标旋转。

### 迹线统计指标（P10/P20/P21）

> 理论参考：王贵宾、杨春和等《岩体节理平均迹长估计》及 Laslett C. (1982) 圆形取样窗法。实现：`statistics.py`。

| 指标 | 含义 | 计算方法 |
|------|------|----------|
| **P10** | 线密度（m⁻¹） | 迹线数 ÷ 测线长度；测线长度优先读取第 12 列实测值，缺失/非法时由 r1 间距估算 |
| **P20** | 面密度（m⁻²） | 迹线数 ÷ 露头面积；露头面积优先读取第 13 列实测值，缺失/非法时用“测线长度 × 测线法向总跨度”估算 |
| **P21** | 面累计长度密度（m⁻¹） | 迹线累计长度 ÷ 露头面积；累计长度优先端点欧氏长度总和，其次 r5+r7 总和，最后使用圆形取样窗 Laslett 平均迹长 × 迹线数 |

圆形取样窗策略仍保留为内部诊断与缺失迹长回退：3 切点（25%/50%/75%）× 2 侧（左/右）× 3 半径缩放比（1.0/0.75/0.50）= 最多 18 窗口，自动约束半径与交集数，无效窗口自动排除。Laslett 估计 $L_{\\mathrm{est}} = (\\pi R/2)\\cdot(q/m)$，$q = 2n_0+n_1$。

各露头统计结果随迹线图输出为 LaTeX 统计信息框（测线走向、迹线数量、平均迹线长度、分型数量、测线长度、露头面积与 P10/P20/P21），汇总表由终端表格生成。



---

## 输出

### Excel 文件

`{outcrop}_traces.xlsx`，单工作表四区布局：

| 区域 | 行位置 | 内容 |
|------|--------|------|
| **A** | 第1–3行 | 测线走向、迹线数量、平均迹线长度、I/II/III 型裂隙数、测线长度、露头面积、P10/P20/P21 |
| **B** | 第5行起 | 原始端点坐标（起点X/Y，终点X/Y） |
| **C** | 第5行起 | 旋转后端点坐标 |
| **D** | 第5行起 | 节理走向与迹线长度 |

### 图片文件

| 命名模式 | 说明 | DPI |
|----------|------|-----|
| `{outcrop}_raw(n={count}).png` | 原始迹线图（含比例尺 + 指北针 + LaTeX 统计信息框） | 300 |
| `{outcrop}_rotated(strike={deg}).png` | 走向旋转后迹线图（含比例尺 + 指北针 + LaTeX 统计信息框） | 600 |
| `{outcrop}_rose(bin={width}).png` | 玫瑰花瓣图 | 400 |

### 输出示例

```
output/
├── O76_raw(n=19).png
├── O76_rotated(strike=298).png
├── O76_rose(bin=10).png
├── O76_traces.xlsx
├── ...（O77–O83 同理，共 32 个文件）
└── O83_rotated(strike=265).png
```

为保持旧结果兼容，批量处理和默认单文件处理仍按露头名生成 `{outcrop}_traces.xlsx`；只有在单文件模式中把 `output_prefix` 显式改为非默认值时，Excel 文件才使用该自定义前缀。

---

## 使用示例

```bash
# 列出可用文件
python run_trace_pipeline.py -l

# 试运行
python run_trace_pipeline.py -n

# 批量处理
python run_trace_pipeline.py

# 自定义玫瑰图参数
python run_trace_pipeline.py --rose-bin 15 --rose-dpi 600

# 指定输入输出目录
python run_trace_pipeline.py -i ./field_data -o ./figures

# 交互式选择
python run_trace_pipeline.py -I

# 4 线程并行 + 跳过玫瑰图
python run_trace_pipeline.py -p 4 --no-rose
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
| 迹线统计 | 无 | I/II/III 型分类 + 实测优先 P10/P20/P21 + 露头面积 + 圆形取样窗法迹长回退估算 |
| 迹线图信息 | 无 | LaTeX 统计信息框（P10/P20/P21/迹长/分型/露头面积）内置 |
| 精度 | 基准 | 端点坐标误差 < 1e-10 m |

### 迁移要点

- **向量化**：逐条 `for` 循环改为 NumPy mask 三分支，角度/半平面改为数组广播
- **修正 MATLAB Bug**：`A_outcrop_0map_rotate.m:68-76` 中 `if ang0<=360` 永远为真，导致分支不可达；Python 版 `fold_strike_angle` 正确折叠到 `[-90°, 90°]`
- **双定义输出**：Excel 同时输出端点距离（欧氏距离）与测段长度（r5+r7）
- **统计增强**：新增 I/II/III 型自动分类、露头面积与实测优先 P10/P20/P21 密度参数，圆形取样窗法（3 切点 × 2 侧 × 3 半径 = 18 窗口）保留为内部诊断与迹长回退估算
- **自动导出**：迹线图含比例尺、指北针与统计信息框，玫瑰图支持自定义分箱，CJK 字体自动回退

### 验证

```bash
python run_trace_pipeline.py -s    # 处理 O76
# Excel 区域 B（原始坐标）与 MATLAB XY 变量逐行对比
# 最大绝对误差 < 1e-10 m ✅
```

---

## 开发

### 测试

```bash
pip install pytest
pytest
```

测试模块覆盖 `angles`、`endpoints`、`transforms`、`statistics`、`discovery`、`config`、`models`、`plotting`、`excel_reader`、`dispatcher`、`logging_setup`。

### 日志

双通道输出：控制台（INFO 级别）+ 文件（DEBUG 级别，`logs/pipeline_YYYYMMDD_HHMMSS.log`）。

### 扩展

新增模块在 `trace_pipeline/` 下创建，在 `__init__.py` 中导出。流水线编排在 `pipeline.py:run_pipeline()` 中，可按需插入或替换阶段。顶层包导出 15 个常用入口，底层函数可直接导入：

```python
from trace_pipeline import run_pipeline, TraceData
from trace_pipeline.geology.angles import fold_strike_angle
```
