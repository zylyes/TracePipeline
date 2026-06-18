<p align="center">
  <img src="reference/favicon.ico" width="80" alt="TracePipeline Logo">
</p>

<h1 align="center">TracePipeline</h1>

<p align="center">
  <strong>岩体节理测线坐标计算与绘图工具</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.10_|_3.11_|_3.12-blue?logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/version-4.1.1-brightgreen" alt="Version">
  <img src="https://img.shields.io/badge/license-MIT-green" alt="License">
  <img src="https://img.shields.io/badge/platform-Windows-blue?logo=windows" alt="Platform">
</p>

<p align="center">
  基于 Python 的岩体节理测线法数据处理与可视化系统。<br>
  支持 <b>CLI 命令行</b>与<b>桌面 GUI</b> 双模式，将 MATLAB 原型算法完整移植为工程化 Python 代码。
</p>

---

## 📖 简介

TracePipeline 是一套面向岩体节理几何特征分析的专业工具。以北山沙枣园花岗岩体 8 个露头（O76-O83）的 172 条节理迹线为数据基础，实现了从原始测线记录到统计指标、可视化图表的全流程自动化处理。

**核心流水线**：综合法复数向量化端点计算 → 坐标平移与旋转标准化 → I/II/III 型自动分类 → 测线长度估算 → 凸包/缓冲凸包露头面积 → 圆形取样窗法 4 策略自适应 → P10/P20/P21 密度统计 → Mauldon 迹长估计 → 窗口一致性校验 → 节点识别（I/Y/X 拓扑分类）→ 多工作表 Excel 导出 → 迹线图与玫瑰图。

### ✨ 亮点

- 🎯 **双模式**：CLI 一键批量处理 + 桌面 GUI 交互式操作
- 🚀 **向量化计算**：NumPy 广播 + 复数运算，8 露头串行处理约 30-60 秒
- 🧪 **高精度**：与 MATLAB 原版端点坐标误差 < 1e-10 m（浮点精度级）
- 📊 **丰富统计**：P10/P20/P21 四级回退、4 策略圆窗自适应、Mauldon 迹长估计
- 🔬 **节点识别**：I/Y/X 型拓扑节点自动识别（空间网格聚类 + 并查集）
- 📦 **一键打包**：PyInstaller + Inno Setup + 7-Zip 生成 Windows 安装包
- 🛡️ **安全可靠**：输入校验、路径遍历防护、结构化日志全链路追踪

---

## 🏗 技术栈与系统架构

### 四层架构

系统采用分层架构设计，各层职责清晰、耦合度低：

| 层次 | 技术 | 职责 |
|------|------|------|
| **表示层** | Vue 3 + Element Plus + ECharts | 交互式桌面 GUI，6 页面视图，响应式仪表板 |
| **服务层** | pywebview JS Bridge + Python 服务 | 前后端通信、线程管理、缓存、安全校验 |
| **计算层** | NumPy + 纯函数模块 | 向量化端点计算、坐标变换、统计指标、节点识别 |
| **数据层** | pandas + openpyxl/xlrd | Excel 读写、文件发现、多工作表导出 |

### 技术选型

| 组件 | 选型 | 说明 |
|------|------|------|
| 桌面容器 | pywebview 5.x | Windows WebView2 嵌入，无 Electron 体积开销 |
| 前端框架 | Vue 3.4 + TypeScript 5.4 | Composition API, Pinia 状态管理 |
| UI 库 | Element Plus 2.x | 企业级 Vue 3 组件库 |
| 图表 | ECharts 5.x + vue-echarts | 直方图、饼图、柱状图对比 |
| 数值计算 | NumPy 1.24+ | 广播 + 复数向量化，8 露头串行 30-60s |
| 绘图 | matplotlib 3.7+ | 迹线图（600 DPI）、玫瑰图、LaTeX 统计框 |
| 打包 | PyInstaller + Inno Setup + 7-Zip | 安装版 + 便携版一链生成 |
| 日志 | 自定义 JSON Lines + contextvars | 按日轮转，30 天保留，request_id 全链路追踪 |

---

## 🚀 快速开始

### 安装

```bash
# 克隆仓库
git clone https://github.com/zylyes/TracePipeline.git
cd TracePipeline

# 创建虚拟环境并安装
python -m venv .venv
.venv\Scripts\Activate.ps1    # Windows PowerShell
pip install -e .
```

### 运行

```bash
# CLI 模式 — 批量处理全部露头
python run_trace_pipeline.py
# 或使用注册的命令行入口
trace-pipeline
# 或通过模块运行
python -m trace_pipeline

# GUI 模式 — 桌面应用
python run_gui.py
```

> **CLI 模式**输出：`output/` 目录为每个露头生成迹线图（原始 + 旋转）+ 多工作表 Excel 文件；可选导出玫瑰图与节点覆盖层。输出数量因 `export_rose_plot` 和 `enable_node_recognition` 设置而异。加 `-p 4` 启用 4 线程并行。

---

## 🎨 功能特性

| 功能 | 说明 |
|------|------|
| 🔢 **数字化重构** | 从 r1-r7 测线记录通过复数法推导端点坐标，一维→二维空间还原 |
| 🔄 **坐标变换** | 平移正象限 → 走向角旋转 → 再平移的规范化流水线 |
| 📐 **迹线统计** | I/II/III 型自动分类、P10/P20/P21（实测优先四级回退）、Mauldon 平均迹长 |
| 🎯 **圆窗策略** | tangent/hybrid/concentric/auto 四策略，auto 模式 6 因子加权评分自动选择 |
| 🏔️ **面积估算** | 凸包（Andrew 单调链）→ 缓冲凸包 → 圆窗等效，四级回退 |
| 🔗 **节点识别** | I/Y/X 型拓扑节点自动识别，空间网格聚类 + 并查集 + 自适应合并容差 |
| 🖼️ **迹线图** | 600 DPI，含比例尺、指北针、LaTeX 统计信息框、凸包/圆窗/节点覆盖层、自动避让 |
| 🌹 **玫瑰图** | 节理走向统计，可自定义分箱宽度与 DPI |
| 📋 **Excel 导出** | 多工作表格式（6-9 sheet），含基本信息、裂隙情况、坐标、节点统计等 |
| 🖥️ **桌面 GUI** | pywebview + Vue 3 + Element Plus + ECharts，6 页面视图，4 级缓存 |
| 📄 **报告导出** | Word/PDF 一键生成，含统计汇总 + 图表内嵌 |
| 📦 **一键打包** | PyInstaller + Inno Setup + 7-Zip SFX，安装版 + 便携版 |
| 📝 **结构化日志** | JSON Lines 格式，按日轮转，request_id 全链路追踪，30 天保留 |

---

## 📦 安装指南

### 系统要求

- **Python** >= 3.10
- **Node.js** >= 18（仅 GUI 前端构建需要）
- **Windows WebView2 Runtime**（GUI 依赖，Windows 11 已内置）
- **pip** >= 21.0

### 依赖

**核心依赖**（CLI 模式必需）：

| 包 | 用途 |
|---|---|
| `numpy>=1.24` | 向量化数值计算 |
| `pandas>=2.0` | Excel 表格读写 |
| `matplotlib>=3.7` | 迹线图与玫瑰图绘制 |
| `openpyxl>=3.1` | .xlsx 读写引擎 |
| `xlrd>=2.0` | .xls 读写引擎 |
| `Pillow>=9.0` | 图像处理 |
| `tqdm>=4.67` | 命令行进度条 |

**GUI 依赖**（仅在桌面模式需要）：

| 包 | 用途 |
|---|---|
| `pywebview>=5.0` | 桌面 GUI 容器（WebView2 嵌入） |
| `python-docx>=1.0` | Word 报告导出 |
| `reportlab>=4.0` | PDF 报告导出 |

> `scipy>=1.10` 和 `shapely>=2.0` 为间接依赖/未来功能预留，当前核心计算（凸包、缓冲区、几何求交）均使用自定义纯 NumPy 实现。

### 安装方式

```bash
# 方式一：venv（推荐）
python -m venv .venv
.venv\Scripts\Activate.ps1      # Windows PowerShell
# 或 source .venv/bin/activate  # Linux/macOS
pip install -e .

# 方式二：仅 CLI 模式（无需 GUI 依赖）
pip install -e . --no-deps      # 跳过所有依赖
pip install numpy pandas matplotlib openpyxl xlrd Pillow tqdm

# 方式三：含开发依赖
pip install -e ".[dev]"

# 方式四：conda / mamba
conda create -n trace python=3.11 -y
conda activate trace
pip install -e .

# 方式五：uv（快速）
uv sync
uv run trace-pipeline
```

### GUI 前端构建

```bash
cd frontend
npm install
npm run build
cd ..
python run_gui.py
```

---

## ⌨️ CLI 用法

### 基本命令

```bash
python run_trace_pipeline.py              # 批量处理全部露头
# 等效注册入口
trace-pipeline                            # 若已 pip install -e .
python -m trace_pipeline                  # 模块方式运行
python -m trace_pipeline.cli.main         # 直接调用 CLI 模块

python run_trace_pipeline.py -l           # 列出可用文件
python run_trace_pipeline.py -n           # 试运行（预览目标）
python run_trace_pipeline.py -I           # 交互式选择目标
python run_trace_pipeline.py -p 4         # 4 线程并行处理
```

### 完整参数

| 参数 | 简写 | 说明 |
|---|---|---|
| `--input` | `-i` | 输入目录（覆盖 `input_dir`） |
| `--output` | `-o` | 输出目录（覆盖 `output_dir`） |
| `--config` | `-c` | 自定义 JSON 配置文件路径 |
| `--single` | `-s` | 单文件模式 |
| `--parallel` | `-p` | 并行线程数（0=串行） |
| `--list` | `-l` | 列出发现的文件后退出 |
| `--interactive` | `-I` | 交互式选择处理目标 |
| `--dry-run` | `-n` | 试运行，不实际执行 |
| `--no-rose` | -- | 跳过玫瑰图导出 |
| `--rose-bin` | -- | 玫瑰图分箱宽度（度） |
| `--rose-dpi` | -- | 玫瑰图分辨率 |
| `--window-strategy` | -- | 圆窗策略：auto/tangent/hybrid/concentric |

### 使用示例

```bash
# 批量处理，跳过玫瑰图
python run_trace_pipeline.py --no-rose

# 单文件 + 自定义配置
python run_trace_pipeline.py -s -c my_config.json

# 指定圆窗策略 + 并行
python run_trace_pipeline.py --window-strategy hybrid -p 4
```

---

## 🖥️ GUI 桌面应用

基于 **pywebview** + **Vue 3 + Element Plus + ECharts** 的桌面应用：

```bash
python run_gui.py
```

### 界面架构

| 页面 | 路由 | 功能 |
|------|------|------|
| 🏠 首页 | `/` | 项目介绍、功能卡片、快速入门引导 |
| ⚙️ 处理 | `/processing` | 文件选择 → 参数配置 → 进度监控 → 结果查看 |
| 📊 统计 | `/statistics` | 单露头统计仪表板：卡片 + 直方图 + 饼图 + 迹线图 + 玫瑰图 |
| 📈 对比 | `/comparison` | 多露头对比表格 + 柱状图 + 图片网格 |
| 📋 数据 | `/data` | 原始数据浏览：输入/输出切换 + 9 区 Excel 分页 |
| 🔧 配置 | `/config` | 全局设置 + 样式预览 + 开发者面板 |

### 缓存架构

| 缓存项 | 前端 TTL | 后端 TTL | 说明 |
|--------|---------|---------|------|
| 文件扫描 | 30s | 30s | 目录变更检测 |
| 统计数据 | 5min | 5min | 含 SHA-256 配置指纹 |
| 对比数据 | 5min | — | 复用统计缓存 |
| 结果列表 | 5s | — | 轮询间隔 |
| 样式预览 | — | 配置 MD5 哈希 | 基于样式 dict 内容 |
| 图片 | 10min | — | 内存 Map 缓存 |
| Excel 数据 | 5min | 5min | 按切片分页缓存 |

---

## ⚙️ 配置

配置文件 `config.json`（本地生成，不提交 Git）。仓库提供 `config.example.json` 作为模板：

```json
{
  "input_dir":                "input",
  "output_dir":               "output",
  "output_prefix":            "Outcrop",
  "table_stem":               "O76_process",
  "outcrop":                  "O76",
  "process_all":              true,
  "export_rose_plot":         false,
  "rose_bin_width":           10.0,
  "rose_dpi":                 600,
  "trace_dpi":                600,
  "rotated_trace_dpi":        600,
  "window_strategy":          "auto",
  "auto_density_threshold":   5.0,
  "tangent_window_count":     3,
  "min_intersections":        5,
  "style":                    {},
  "enable_node_recognition":  false,
  "node_merge_tolerance":     0.01,
  "show_node_overlay":        true,
  "node_label_mode":          "type",
  "is_dev_mode":              false
}
```

| 配置键 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `input_dir` | string | `"input"` | 输入目录（含 `*_process.xls*`） |
| `output_dir` | string | `"output"` | 输出目录 |
| `output_prefix` | string | `"Outcrop"` | 输出文件名前缀 |
| `table_stem` | string | `"O76_process"` | 单文件模式下的表名主干 |
| `outcrop` | string | `"O76"` | 单文件模式下的露头名 |
| `process_all` | bool | `true` | 是否批量处理全部露头 |
| `window_strategy` | string | `"auto"` | 圆窗策略：`auto`/`tangent`/`hybrid`/`concentric` |
| `auto_density_threshold` | float | `5.0` | auto 策略的密度阈值 |
| `tangent_window_count` | int | `3` | tangent 策略窗口数 |
| `min_intersections` | int | `5` | 圆窗最小交切数（低于此值窗口无效） |
| `enable_node_recognition` | bool | `false` | 是否启用节点识别 |
| `node_merge_tolerance` | float | `0.01` | 节点合并容差（m） |
| `show_node_overlay` | bool | `true` | 是否在迹线图上绘制节点覆盖层 |
| `node_label_mode` | string | `"type"` | 节点标注模式：`none`/`type`/`id` |
| `export_rose_plot` | bool | `false` | 是否导出玫瑰图 |
| `rose_bin_width` | float | `10.0` | 玫瑰图分箱宽度（度） |
| `rose_dpi` | int | `600` | 玫瑰图分辨率 |
| `trace_dpi` | int | `600` | 迹线图分辨率 |
| `rotated_trace_dpi` | int | `600` | 旋转迹线图分辨率 |
| `style` | dict | `{}` | 自定义绘图样式覆盖 |
| `is_dev_mode` | bool | `false` | GUI 开发者模式 |

---

## 🐍 Python API

除 CLI 和 GUI 外，`trace_pipeline` 可作为 Python 库在代码中调用：

```python
from trace_pipeline import (
    run_pipeline,             # 核心流水线
    load_trace_data,          # 数据加载
    TraceData,                # 数据模型
    RunConfig,                # 运行配置
    RunResult,                # 运行结果
    compute_trace_statistics, # 统计计算
    TraceStatistics,          # 统计结果
    find_trace_tables,        # 文件发现
)
```

### 完整流水线

```python
from trace_pipeline import load_config, RunConfig, run_pipeline

cfg_dict = load_config("config.json")
config = RunConfig(
    input_dir="input",
    output_dir="output",
    output_prefix="Outcrop",
    table_stem="O76_process",
    outcrop="O76",
    window_strategy="auto",
)

result = run_pipeline(config)
print(result.status)          # PipelineStatus.SUCCESS
print(result.excel_path)      # Excel 输出路径
print(result.raw_plot_path)   # 迹线图路径
```

### 单独统计计算

```python
from trace_pipeline import load_trace_data, compute_trace_statistics, TraceStatisticsConfig

trace = load_trace_data("input", "O76_process", "O76")
stats_config = TraceStatisticsConfig(window_strategy="hybrid")
stats = compute_trace_statistics(trace, stats_config)

print(f"P10 = {stats.p10:.4f} m⁻¹")
print(f"P20 = {stats.p20:.4f} m⁻²")
print(f"P21 = {stats.p21:.4f} m⁻¹")
```

### 节点识别

```python
from trace_pipeline.analysis.models import NodeRecognitionConfig
from trace_pipeline.analysis.nodes import recognize_trace_nodes

config = NodeRecognitionConfig(
    enabled=True,
    merge_tolerance=0.01,
    show_overlay=True,
    label_mode="type",  # "none" | "type" | "id"
)
analysis = recognize_trace_nodes(trace.endpoints, config)

print(f"节点总数: {analysis.node_count}")
print(f"I 型节点: {analysis.node_i_count}")
print(f"Y 型节点: {analysis.node_y_count}")
print(f"X 型节点: {analysis.node_x_count}")
print(f"交点总数: {analysis.intersection_count}")

# 遍历所有节点
for node in analysis.nodes:
    print(f"  节点 {node.node_id}: 类型={node.node_type}, "
          f"度数={node.degree}, 坐标=({node.x:.3f}, {node.y:.3f})")

# 节点密度（需传入露头面积）
density = analysis.node_density(area=150.0)
print(f"节点密度: {density:.4f} 个/m²")
```

---

## 🔬 数据处理原理

### 综合法测量原理

根据迹线与测线的相互关系，分为三种类型：

| 类型 | 名称 | 判定条件 | 特征 |
|------|------|----------|------|
| **I 型** | 相交型 | 迹线直接穿过测线 | 双侧均有迹线延伸 |
| **II 型** | 延长相交型 | 迹线延长线穿过测线 | 单侧迹线延伸 |
| **III 型** | 不相交型 | 迹线及延长线均不穿过测线 | 过迹线起点作测线垂线定位 |

> 仅记录迹长 > 30 cm 的结构面。

### 复平面端点坐标算法

在复平面中构建测线局部坐标系。设测线方位角为 α，笛卡尔角 θ = 90° − α（当 α < 90°）或 θ = 450° − α（当 α ≥ 90°），测线方向单位向量 **v** = e^{iθ}。

根据综合法参数 r₅, r₇ 的取值自动判别三种计算情形：

| 情形 | 条件 | 计算方式 |
|------|------|----------|
| 仅左侧 | r₅ ≠ 0, r₇ = 0 | Z₀ + r₂**v**_L + r₄**v**_s → 起点 + r₅**v**_s |
| 仅右侧 | r₅ = 0, r₇ ≠ 0 | Z₀ + r₂**v**_R + r₆**v**_s → 起点 + r₇**v**_s |
| 双侧 | r₅ ≠ 0, r₇ ≠ 0 | 分开计算左右端点 |

全部计算通过 NumPy 复数向量化一次性完成 N 条迹线的转换，时间复杂度 O(N)。

### 迹线统计指标

| 指标 | 含义 | 计算方法 |
|------|------|----------|
| **P10** | 线密度（m⁻¹） | 迹线数 / 测线长度 |
| **P20** | 面密度（m⁻²） | 迹线数 / 有效面积；面积回退链：实测 → 凸包 → 缓冲凸包 → 圆窗等效 |
| **P21** | 面累计长度密度（m⁻¹） | 累计迹长 / 有效面积 |
| **平均迹长** | 平均迹线长度（m） | 三级回退：测段(r₅+r₇) → 端点欧氏距离 → 圆窗 Mauldon L_est |

> 来源标注：(M) 实测、(W) 圆窗、(W_eq) 圆窗等效、(E) 估算。

### 圆形取样窗法

| 策略 | 窗口布置 | 适用场景 |
|------|----------|----------|
| **tangent** | 沿测线均布 k 个相切圆 | 大间距、稀疏迹线 |
| **hybrid** | 3 切点 × 2 侧 × 3 半径缩放比，最多 18 窗口 | 中等密度 |
| **concentric** | 测线中点同心圆，多半径 | 高密度 |
| **auto** | 三种策略 6 因子加权评分，自动选择最优 | 默认推荐 |

### 节点识别

启用 `enable_node_recognition: true` 后，通过空间网格聚类 + 并查集算法，自动识别 I/Y/X 型拓扑节点。合并容差自适应于数据尺度。

---

## 📦 打包分发

`scripts/package.py` 提供一键打包流水线：

```bash
python scripts/package.py                # 完整打包（安装版 + 便携版）
python scripts/package.py --skip-portable # 仅安装版
python scripts/package.py --skip-frontend # 跳过前端构建
```

### 打包工具链

| 工具 | 用途 | 发现方式 |
|------|------|----------|
| PyInstaller | Python 应用打包 | `.venv/Scripts/pyinstaller.exe` |
| Inno Setup 6 | 生成 Windows 安装程序 | 环境变量 `ISCC_EXE` 或系统 PATH |
| 7-Zip | 生成自解压便携版 | 环境变量 `SEVEN_ZIP` 或系统 PATH |

### 打包流程

| 步骤 | 工具 | 产物 |
|------|------|------|
| 前端构建 | `npm run build` | `backend/static/` |
| 应用打包 | PyInstaller | `dist/TracePipeline/` |
| 安装程序 | Inno Setup 6 | `dist/TracePipeline-Setup-v{version}.exe` |
| 便携版 | 7-Zip SFX | `dist/TracePipeline-Portable-v{version}.exe` |

---

## 🧪 开发

### 开发工具

```bash
pip install -e ".[dev]"

# 代码检查
ruff check .

# 类型检查
mypy trace_pipeline/

# 测试
pytest

# 测试 + 覆盖率
pytest --cov --cov-report=term --cov-report=html
```

| 工具 | 配置位置 | 要点 |
|------|----------|------|
| ruff | `pyproject.toml [tool.ruff]` | Python 3.10, 100 列行宽 |
| mypy | `pyproject.toml [tool.mypy]` | Python 3.10, warn_return_any |
| pytest | `pyproject.toml [tool.pytest]` | testpaths = `tests/` |

### 项目结构

```
.
├── trace_pipeline/          # 核心计算包（51 .py 文件）
│   ├── __init__.py          # 包入口，延迟导入，__all__ 定义
│   ├── models.py            # 数据模型（TraceData, RunConfig, RunResult）
│   ├── config.py            # 配置加载、路径解析、CLI 覆盖合并
│   ├── pipeline.py          # 单目标全流程编排（5 阶段）
│   ├── reporting.py         # 终端结果表格与摘要输出
│   ├── validation.py        # 标量类型强制转换
│   ├── geology/             # 地质/几何算法（纯函数）
│   │   ├── angles.py        # 角度转换（倾向→走向、方位角→笛卡尔）
│   │   ├── endpoints.py     # 综合法复数向量化端点计算
│   │   ├── statistics.py    # P10/P20/P21 密度统计、迹线分类
│   │   ├── transforms.py    # 坐标平移、旋转与标准化
│   │   ├── _convex_hull.py  # Andrew 单调链凸包、鞋带公式面积
│   │   ├── _circle_window.py# 圆窗交切计数（批量向量化）
│   │   ├── _window_strategies.py  # tangent/hybrid/concentric 布局
│   │   ├── _window_scoring.py     # auto 策略 6 因子加权评分
│   │   ├── _stat_types.py   # TraceStatisticsConfig, TraceStatistics
│   │   └── _stat_format.py  # 统计信息格式化
│   ├── analysis/            # 节点识别分析
│   │   ├── models.py        # NodeRecognitionConfig, NodeAnalysis
│   │   └── nodes.py         # recognize_trace_nodes (网格聚类+并查集)
│   ├── geometry/            # 几何原语
│   │   └── segments.py      # 线段求交、共线、点到线距离
│   ├── io/                  # I/O 层
│   │   ├── discovery.py     # find_trace_tables（文件发现）
│   │   ├── excel_reader.py  # read_trace_excel（引擎/表名回退）
│   │   └── excel_writer.py  # write_excel_multi_sheets（多工作表导出）
│   ├── plotting/            # 绘图层
│   │   ├── style.py         # matplotlib 全局样式 + CJK 字体配置
│   │   ├── trace_plot.py    # render_trace_plot（迹线图）
│   │   ├── rose_plot.py     # render_rose_plot（玫瑰图）
│   │   ├── preview_plot.py  # render_preview_*（样式预览）
│   │   ├── overlays.py      # 凸包/圆窗/节点覆盖层
│   │   ├── _helpers.py      # 图形创建、指北针、边界计算
│   │   └── _layout.py       # 布局、统计框、图例、比例尺
│   ├── logging/             # 结构化日志系统
│   │   ├── core.py          # JsonFormatter, DailyRotatingJsonHandler
│   │   └── context.py       # LogContext, request_id 传播, timed 装饰器
│   ├── cli/                 # 命令行入口
│   │   ├── main.py          # CLI 入口（配置→发现→调度→报告）
│   │   ├── args.py          # argparse 参数定义
│   │   ├── dispatcher.py    # 批量/单文件目标选择与串行/并行执行
│   │   ├── interactive.py   # 交互式文件选择（范围解析）
│   │   └── logging_setup.py # 日志兼容层
│   └── utils/               # 工具函数
│       ├── paths.py         # PyInstaller 感知的路径解析
│       ├── output_paths.py  # 输出图片查找
│       ├── numpy_compat.py  # NumPy → Python 原生类型转换
│       ├── mpl_init.py      # 强制非交互式 backend
│       ├── fonts.py         # CJK 字符检测
│       └── formatting.py    # 文件大小格式化
├── backend/                 # GUI 后端（pywebview）
│   ├── main_gui.py          # pywebview 启动器、窗口管理
│   ├── gui_api.py           # JS Bridge API（38 个方法）
│   ├── webview2_checker.py  # WebView2 Runtime 检测
│   ├── services/            # 9 个后端服务
│   │   ├── config_service.py   # 配置读写（原子保存）
│   │   ├── file_service.py     # 文件扫描（TTLCache 30s）
│   │   ├── pipeline_service.py # 后台流水线执行（线程+队列）
│   │   ├── stats_service.py    # 统计计算（TTLCache 5min）
│   │   ├── data_service.py     # Excel 数据分页读取
│   │   ├── preview_service.py  # 样式预览生成（MD5 缓存）
│   │   ├── report_service.py   # Word/PDF 报告导出
│   │   ├── audit_service.py    # 用户操作审计日志
│   │   └── log_service.py      # 结构化日志读取
│   └── utils/               # 后端工具
│       ├── cache.py         # TTLCache + 目录变更检测
│       ├── security.py      # 路径遍历防护、Windows 设备名拦截
│       └── path_utils.py    # 露头名校验、错误响应格式化
├── frontend/                # Vue 3 前端（TypeScript）
│   └── src/
│       ├── App.vue          # 根组件（侧边栏 + 标题栏 + 状态栏）
│       ├── views/           # 6 页面视图
│       │   ├── IntroView.vue       # 首页引导
│       │   ├── ProcessingView.vue  # 文件选择 + 流水线处理
│       │   ├── StatisticsView.vue  # 单露头统计仪表板
│       │   ├── ComparisonView.vue  # 多露头对比
│       │   ├── DataView.vue        # 原始数据浏览
│       │   └── ConfigView.vue      # 全局配置 + 样式预览
│       ├── components/      # 13 个功能组件 + 6 个图标组件
│       │   ├── SplashScreen.vue, FileList.vue, ProgressPanel.vue
│       │   ├── StatCards.vue, HistogramChart.vue, PieChart.vue
│       │   ├── ImageViewer.vue, ImageModal.vue, StylePreview.vue
│       │   ├── ConfigForm.vue, DevPanel.vue, DataTable.vue, GeoIcon.vue
│       │   └── icons/ (HomeIcon, ProcessIcon, StatsIcon, CompareIcon, DataIcon, ConfigIcon)
│       ├── stores/          # Pinia 状态管理（app, config, cache, pipeline）
│       ├── api/             # pywebview JS Bridge 封装
│       ├── utils/           # 前端工具（消息、图片、格式化、ECharts 主题）
│       └── styles/          # 设计令牌、字体、Element Plus 覆盖
├── tests/                   # pytest 单元测试（20 个文件）
├── scripts/
│   └── package.py           # 一键打包流水线（reqs → 前端 → PyInstaller → Inno Setup → 7-Zip）
├── reference/               # 参考资料
│   ├── matlab/              # MATLAB 原版算法代码
│   ├── 论文/                # 毕业设计文档
│   ├── 文献/                # 学术参考论文
│   ├── 图件/                # 论文插图
│   └── 地质背景/            # 地质数据与背景资料
├── config.example.json      # 配置模板
├── pyproject.toml           # 项目元数据与构建配置
├── requirements.txt         # 依赖声明（自动生成）
├── run_trace_pipeline.py    # CLI 入口脚本
├── run_gui.py               # GUI 入口脚本
├── TracePipeline.spec       # PyInstaller 打包配置
└── TracePipeline-setup.iss  # Inno Setup 安装程序模板
```

### 设计理念

系统遵循 **不可变数据模型 — 纯函数计算 — 向量化优先** 三项核心原则：

| 原则 | 说明 |
|------|------|
| **不可变数据模型** | 核心数据类使用 `frozen=True`，NumPy 数组设为只读 |
| **纯函数计算** | `geology/` 子包全部为纯函数，接收数组返回数组 |
| **向量化优先** | NumPy 广播 + 复数运算替代 for 循环；布尔 mask 替代 if-else |
| **惰性导入** | matplotlib 延迟加载，`import trace_pipeline` 不触发绘图初始化 |
| **私有模块拆分** | 大模块委托 6 个 `_*.py` 单一职责模块，每个 50-350 行 |
| **结构化日志** | JSON Lines + 按日轮转 + contextvars 传播 request_id |

---

## ❓ 常见问题

| 现象 | 原因 | 解决 |
|------|------|------|
| 迹线图中文字符显示为方块 | 系统缺少 CJK 字体 | 安装宋体/黑体；程序已内置多级回退链 |
| `ModuleNotFoundError: openpyxl` | 未安装依赖 | `pip install -e .` |
| 发现 0 个迹线表文件 | 文件名不以 `_process` 结尾 | 重命名为 `{露头}_process.xls(x)` |
| "工作表不存在" 错误 | Sheet 名与露头编号不一致 | 确保 Sheet 名为 O76/O77… |
| P20/P21 显示 NaN | 迹线数过少（< 3）导致凸包退化 | 正常兜底行为 |
| GUI 启动白屏 | 前端未构建 | `cd frontend && npm install && npm run build` |
| GUI 提示 WebView2 缺失 | 系统未安装 WebView2 Runtime | 点击提示链接下载安装 |
| 仅需 CLI 功能，不想装 GUI 依赖 | `pyproject.toml` 统一声明了全部依赖 | 使用 `pip install --no-deps` 后手动安装核心依赖（见安装方式二） |
| `.xls` 文件读取报错或不完整 | `xlrd>=2.0` 仅支持 `.xls`，不支持 `.xlsx` | 将 `.xlsx` 文件另存为 `.xls` 格式，或确保 `openpyxl` 已安装 |
| 并行处理时内存占用过高 | `ProcessPoolExecutor` 每个子进程独立加载依赖 | 降低 `-p` 线程数；串行模式（`-p 0`）内存占用最低 |
| 打包后运行提示找不到字体 | PyInstaller 未打包系统字体 | 确保目标系统已安装宋体/黑体等 CJK 字体 |
| 节点识别未生成覆盖层 | `show_node_overlay` 为 `false` 或 `enable_node_recognition` 未开启 | 检查 `config.json` 中两项均设为 `true` |

---

## 🤝 贡献

欢迎各种形式的贡献！请查阅 [CONTRIBUTING.md](CONTRIBUTING.md) 了解开发环境搭建、代码规范和提交流程。

本项目遵循 [贡献者行为准则](CODE_OF_CONDUCT.md)。

---

## 📄 许可证

本项目基于 [MIT 许可证](LICENSE) 开源。

---

## 🙏 致谢

- MATLAB 原版算法为本项目的理论基础
- [Mauldon (1998)](https://doi.org/10.1016/S0148-9062(98)00007-2) 圆形取样窗平均迹长估计
- [Laslett (1982)](https://doi.org/10.1007/BF01032939) 圆形取样窗法
- 北山沙枣园花岗岩体野外数据采集团队
