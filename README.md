# 岩体节理测线坐标计算与绘图工具

基于 Python 实现的岩体节理测线法数据处理与可视化系统。本项目是毕业设计《**基于 Python 的花岗岩露头节理网络数字化重构设计**》的核心代码库，以北山沙枣园花岗岩体 8 个露头（O76–O83）的 172 条节理迹线为数据基础，将 MATLAB 原版算法完整移植为工程化 Python 代码，实现了从原始测线记录到二维迹线图、玫瑰花瓣图的自动化流水线。

研究区域位于戈壁地区北山沙枣园花岗岩体，该岩体出露条件良好，节理发育充分，已被作为高放废物地质处置库的重点候选场址开展系列研究（霍亮等，2019, 2023, 2025）。

> **毕业设计课题**: 25 届地球信息科学与技术专业 — 周咏霖（学号 2022210162）  
> **指导教师**: 霍亮（讲师），地球与行星科学学院  
> **任务书与进度跟踪**: 见 [`杂项/毕业设计任务流程与预期成果.md`](杂项/毕业设计任务流程与预期成果.md)

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
│   ├── types.py                   # TraceData / RunConfig / RunResult 数据模型
│   ├── angles.py                  # 地质角度转换（倾向⇄走向、折叠、半平面）
│   ├── geometry.py                # 迹线端点向量化计算（复数运算）
│   ├── transforms.py              # 坐标平移与旋转变换
│   ├── io.py                      # Excel 读取与四区布局写入
│   ├── plotting.py                # 迹线图与玫瑰花瓣图绘制
│   ├── report.py                  # 结果格式化展示与汇总报告
│   └── pipeline.py                # 单目标全流程编排
│
├── input/                         # 输入目录（存放 *_process.xls*）
├── output/                        # 输出目录（Excel + 图片）
├── logs/                          # 运行日志
├── matlab参考/                     # MATLAB 原版参考代码
│   ├── A_outcrop_0map_coordinate.m
│   ├── A_outcrop_0map_rotate.m
│   └── Coordinate.m
│
├── 杂项/                          # 研究资料（毕业设计任务书、现场照片、测线法说明PPT等）
│   ├── 毕业设计任务流程与预期成果.md  # 论文写作 + 代码完善进度跟踪
│   ├── 25届...任务书_周咏霖.pdf      # 毕业设计任务书
│   ├── 测线法说明.pptx               # 测线法测量操作流程
│   ├── IMG_7311.JPG / 30MDJI_0662.JPG # 现场节理露头照片
│   └── ...
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

## 功能特性

### 已实现（核心流水线）

| 功能 | 说明 | 对应论文章节 |
|------|------|-------------|
| **数字化重构** | 从 r1–r7 测线记录复数法推导端点坐标，实现一维→二维空间还原 | §4.1–§4.3 |
| **坐标变换** | 平移正象限 → 走向角旋转 → 再平移的规范化流水线 | §4.4 |
| **批量处理** | 自动扫描 `input/` 目录，支持 8 个露头一键处理（串行/并行） | §5.3 |
| **迹线图导出** | 原始迹线图（300 DPI）+ 走向旋转迹线图（600 DPI） | §5.3 |
| **玫瑰花瓣图** | 节理走向统计，10° 分箱，支持自定义分箱宽度与 DPI | §5.3 |
| **Excel 四区输出** | A 基本信息 / B 原始坐标 / C 旋转坐标 / D 走向与长度 | §5.3 |
| **MATLAB 复现验证** | 与原版 `Coordinate.m` 端点坐标误差 < 1e-10 m | §4.6 |

### 论文扩展方向（待实现）

以下功能在论文 §1.3 中有规划，但当前代码尚未实现：

| 功能 | 说明 | 状态 |
|------|------|------|
| **节点识别** | I 型（端点终止）/ Y 型（一条终止于另一条）/ X 型（交叉贯穿） | 🔴 未实现 |
| **Terzaghi 修正** | 测线方向取样偏差的几何修正 | 🔴 未实现 |
| **密度参数统计** | P10（线密度）、P20（面密度中心数）、P21（面密度迹长） | 🔴 未实现 |
| **极点等值线图** | 节理产状的优势分组与等值线可视化 | 🔴 未实现 |
| **无人机影像对比** | 重构迹线图与正射影像的叠合对比分析 | 🔴 未实现 |

---

## 配置

配置文件 `config.json`（位于项目根目录）控制所有运行参数：

```json
{
  "input_dir":          "input",       // 输入目录（相对/绝对路径）
  "output_dir":         "output",      // 输出目录
  "output_prefix":      "Outcrop",     // 输出文件命名前缀
  "table_stem":         "O76_process", // 单文件模式下读取的 Excel 文件名（不含扩展名）
  "outcrop":            "O76",         // 露头名称（也是 Excel 工作表名）
  "process_all":        true,          // true=批量处理，false=仅处理 table_stem 指定的文件
  "export_rose_plot":    true,         // 是否导出玫瑰花瓣图
  "rose_bin_width":      10,          // 玫瑰图分箱宽度（度）
  "rose_dpi":            400,         // 玫瑰图分辨率
  "trace_dpi":           300,         // 原始迹线图分辨率
  "rotated_trace_dpi":   600          // 旋转迹线图分辨率
}
```

所有配置项均可通过命令行参数覆盖（见下文）。完整配置 schema 说明见 `CONFIG_SCHEMA.md`（待编写）。

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
| `--single` | `-s` | **单文件模式**：仅处理配置中 `table_stem` 指定的文件（忽略目录扫描） |
| `--rose-bin` | — | 玫瑰图分箱宽度（度），如 `--rose-bin 15` |
| `--rose-dpi` | — | 玫瑰图 DPI，如 `--rose-dpi 600` |
| `--no-rose` | — | 跳过玫瑰图导出 |
| `--parallel` | `-p` | 并行处理线程数（默认 0=串行），如 `-p 4` |
| `--list` | `-l` | 列出发现的迹线表文件后退出 |
| `--interactive` | `-I` | 交互模式：列出文件后由用户选择处理目标 |
| `--dry-run` | `-n` | 试运行：打印待处理目标但不实际执行 |

### 运行模式

**批量模式**（默认）：扫描输入目录下所有命名类似 `*_process.xlsx`（或 `*.xls`）的文件，逐个处理。

```bash
python run_trace_pipeline.py                    # 批量处理 input/ 下所有 *_process.xlsx
```

**单文件模式**：仅处理 `config.json` 中 `table_stem` 指定的文件。

```bash
python run_trace_pipeline.py -s                 # 仅处理 O76_process.xlsx
python run_trace_pipeline.py -s -c my_conf.json # 使用自定义配置的单文件模式
```

---

## 数据处理流程

整个流水线按以下阶段串联：

```
加载配置 → 文件发现 → 逐目标处理 →
  1. 读取 Excel（io.parse_trace_file）
  2. 解析表头与数值矩阵（geometry.compute_endpoints）
  3. 倾向 → 走向转换（angles.dip_to_strike）
  4. 向量化端点坐标计算（geometry）
  5. 坐标规范化：平移 → 走向旋转 → 再平移（transforms.normalize_coordinates）
  6. 导出 Excel（io.build_excel_sections + io.write_excel_sections）
  7. 绘制迹线图（原始 & 旋转后）（plotting.render_trace_plot）
  8. 绘制玫瑰花瓣图（plotting.render_rose_plot）
```

### 核心模块说明

| 模块 | 职责 |
|---|---|
| `config.py` | 加载/校验 JSON 配置；输入目录文件发现（`find_trace_tables`）；路径解析与 CLI 覆盖合并 |
| `types.py` | 不可变数据类：`TraceData`（解析结果）、`RunConfig`（运行参数）、`RunResult`（运行结果） |
| `angles.py` | 纯函数角度工具：倾向→走向转换、走向角折叠、半平面折叠 |
| `geometry.py` | **纯向量化**复数运算计算迹线端点；表头解析与数值提取 |
| `transforms.py` | 坐标平移（正象限留白）→ 走向旋转 → 再次平移的规范化流水线 |
| `io.py` | 统一 Excel I/O：读取（优先 .xlsx，回退 .xls）、四区布局写入 |
| `plotting.py` | matplotlib 绘图：迹线长度图（原始/旋转后）、节理走向玫瑰花瓣图 |
| `report.py` | 结果格式化展示：单结果详情、批量汇总表、统计摘要 |
| `pipeline.py` | 单目标全流程编排，异常包装与日志 |

---

## 数据格式

### 综合法测量原理

本项目采用**综合法**（Scanline Method 的扩展）进行野外节理调查。根据测线与节理迹线的相互关系，将迹线分为三种类型：

| 类型 | 名称 | 判定条件 | 特征 |
|------|------|----------|------|
| **Ⅰ型** | 相交型 | 迹线直接穿过测线 | 双侧均有迹线延伸 |
| **Ⅱ型** | 延长相交型 | 迹线延长线穿过测线 | 单侧迹线延伸 |
| **Ⅲ型** | 不相交型 | 迹线及延长线均不穿过测线 | 过迹线起点作测线垂线定位 |

> **迹长下限**：仅记录迹长 > 30 cm 的结构面，短于 30 cm 的表层微裂隙不纳入统计。

### Excel 输入格式

`input/` 目录中的 `*_process.xls`（或 `.xlsx`）为野外测线数据的数字化录入结果。每张表遵循以下列布局：

| 列号（0基） | 符号 | 物理含义 | 对应综合法参数 |
|-------------|------|----------|----------------|
| 0 | `r1` | 沿测线位移（从测线起点量起） | L₀（交点/垂足位置） |
| 1 | `r2` | 垂直测线偏移（左正右负） | L₁（垂线段长度） |
| 2 | `dip` | 节理倾向（度），自动转为走向 | — |
| 3 | `r4` | 左侧迹线第一段长度 | L₂（左段） |
| 4 | `r5` | 左侧迹线第二段长度 | L₃（左延伸） |
| 5 | `r6` | 右侧迹线第一段长度 | L₂（右段） |
| 6 | `r7` | 右侧迹线第二段长度 | L₃（右延伸） |
| 7 | `ang0` | 测线走向角（度），**仅首行有效** | — |
| 8 | `n` | 迹线条数，**仅首行有效** | — |

**重要规则：**
- 文件名需以 `_process` 结尾（如 `O76_process.xls`），批量模式下按此规则发现文件。
- 工作表名使用 `outcrop`（如 `O76`）；若不存在，自动回退到第一个工作表。
- 前 `n` 行的前 7 列必须为数值，不可包含空值或文本。
- 迹线类型由 `r5`（列4）和 `r7`（列6）是否为 0 自动判定：
  - **左迹线**（`r5 ≠ 0, r7 = 0`）：仅左侧有迹长数据（常见于Ⅱ型、Ⅲ型）
  - **右迹线**（`r5 = 0, r7 ≠ 0`）：仅右侧有迹长数据（常见于Ⅱ型、Ⅲ型）
  - **双侧迹线**（`r5 ≠ 0, r7 ≠ 0`）：两侧均有迹长数据（常见于Ⅰ型）

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

`{output_prefix}_traces.xlsx`，单个工作表，包含四个区域：

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

### 实际输出样例（output/ 目录）

运行完成后 `output/` 目录包含 8 组露头的处理结果（每组 4 个文件）：

```
output/
├── O76_raw(n=19).png           # 原始迹线图
├── O76_rotated(strike=298).png # 走向旋转后迹线图
├── O76_rose(bin=10).png        # 节理走向玫瑰图
├── O76_traces.xlsx             # 四区布局 Excel 结果
├── O77_* ...                   # O77–O83 同理
└── O83_rotated(strike=265).png
```


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

# 5. 列出所有可用迹线表
python run_trace_pipeline.py -l

# 6. 交互式选择处理目标
python run_trace_pipeline.py -I

# 7. 试运行（不产生输出）
python run_trace_pipeline.py -n

# 8. 4 线程并行处理
python run_trace_pipeline.py -p 4
```

---

## MATLAB 参考

原版 MATLAB 代码位于 `matlab参考/`：

| 文件 | 对应 Python 模块 |
|---|---|
| `A_outcrop_0map_coordinate.m` | 旧版主流程 → 现由 `pipeline.py` + `run_trace_pipeline.py` 替代 |
| `A_outcrop_0map_rotate.m` | 坐标旋转 → `transforms.py` |
| `Coordinate.m` | **核心几何计算函数** → `geometry.py` + `angles.py` |

### MATLAB vs Python 对比

| 维度 | MATLAB 原版 | Python 版 |
|------|-------------|-----------|
| **计算模式** | `for` 循环逐条处理（串行） | NumPy 向量化批量运算 |
| **复数运算** | 逐元素实部/虚部拼接 | 原生 `complex128` 数组广播 |
| **角度转换** | 硬编码三区间 `if-else` | `numpy.select` 向量化分段映射 |
| **坐标变换** | 逐行循环旋转 | 矩阵广播 `@` 一次性旋转 |
| **I/O** | `xlsread` / `writematrix` 单文件 | `pandas` + `openpyxl` 四区布局 |
| **绘图** | `plot` + 手动导图 | `matplotlib` 自动排版 + 多 DPI 导出 |
| **批量处理** | 需手动改文件名逐张运行 | 自动扫描 `input/` + 可选并行 |
| **误差** | 基准 | **位置偏差 < 1e-10 m**（双精度浮点误差，见下方验证） |

### 对比验证方法

以 O76 为基准，逐条对比 Python 与 MATLAB 版 `Coordinate.m` 计算的端点坐标：

```bash
python run_trace_pipeline.py -s        # 处理 O76，产出 output/O76_traces.xlsx
# 将 Excel 区域 B（原始坐标）与 MATLAB 工作区变量 XY 逐行对比
# 最大绝对误差应 < 1e-10 m（双精度浮点舍入误差量级）
```

**验证结论**：Python 向量化实现与 MATLAB 逐行循环实现计算结果一致，向量化版本在保持精度的同时大幅提升了批量处理效率。

---

## 开发

### 运行测试

```bash
# 安装开发依赖
pip install pytest

# 运行测试
pytest
```

> ⚠️ **当前状态**：`tests/` 目录尚未编写正式测试文件（仅含 `__pycache__`）。根据毕业设计计划，需补充以下测试模块：
> - `test_angles.py` — 倾向→走向转换、半平面折叠
> - `test_geometry.py` — 三种情形端点计算
> - `test_transforms.py` — 平移、旋转流水线
> - `test_pipeline_integration.py` — 端到端集成测试（以 O76 真实数据验证）

### 日志

日志同时输出到控制台（INFO 级别）和文件（DEBUG 级别，位于 `logs/pipeline_YYYYMMDD_HHMMSS.log`），便于排查问题。

### 扩展

新增模块只需在 `trace_pipeline/` 下创建文件，并在 `__init__.py` 中导出即可。流水线编排在 `pipeline.py` 的 `run_pipeline()` 函数中，可按需插入或替换阶段。
