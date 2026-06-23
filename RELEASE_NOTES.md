# TracePipeline v4.5.4 发布说明

**发布日期**：2026-06-23

## 本版本亮点

### 🧩 最终维护版稳定性收尾

v4.5.4 是 TracePipeline 最后一个计划内维护版本。本版本集中处理几个会影响长时间运行、批量导出和异常输入的边界问题，让当前功能集以更稳定的状态收尾。

后续我预计不会再持续投入这个项目；如果遇到问题或有功能需求，可以通过 GitHub Issue 或项目联系方式联系我。

### 📄 报告导出进度状态修复

- 批量报告 ZIP 打包失败时推送明确 `error` 事件
- 仅成功生成 ZIP 后推送 `complete` 事件，避免失败路径被前端误判为完成
- 报告服务返回业务错误时也会进入错误进度态，方便前端展示失败原因

### 🔒 并发与资源边界收敛

- `GuiApi` 懒加载服务增加线程安全双检锁，避免并发访问时重复创建服务实例
- `parallel_workers` 显式配置超过 CPU 核心数时自动裁剪；CPU 核心数不可识别时保守退回 1
- 流水线进度队列设置上限，避免长时间运行时消息无限积累
- TraceData 缓存容量从 64 调整为 16，降低批量处理时内存占用

### 📊 Excel 输入防护

- `read_trace_excel()` 在调用 pandas 前拒绝超过 50 MiB 的 Excel 文件
- 新增回归测试确认超大文件不会进入实际解析流程

## 变更文件

| 文件 | 变更类型 | 说明 |
|------|----------|------|
| `backend/gui_api.py` | 修复 | 报告 ZIP 错误/完成进度事件、懒加载服务线程安全 |
| `backend/services/pipeline_service.py` | 改进 | 进度队列上限、parallel_workers CPU 上限裁剪与兜底 |
| `trace_pipeline/io/excel_reader.py` | 修复 | Excel 文件 50 MiB 读取上限 |
| `trace_pipeline/pipeline.py` | 改进 | TraceData 缓存容量收敛 |
| `tests/test_gui_api.py` | 测试 | 报告 ZIP 失败路径和懒加载并发回归测试 |
| `tests/test_pipeline_service.py` | 测试 | 并行 worker 上限裁剪与 CPU 不可识别兜底测试 |
| `tests/test_excel_reader.py` | 测试 | Excel 大文件拒绝读取测试 |
| `trace_pipeline/__init__.py` / `frontend/package*.json` / `TracePipeline-setup.iss` | 版本 | 同步至 v4.5.4 |
| `README.md` / `CHANGELOG.md` / `RELEASE_NOTES.md` | 文档 | 同步 v4.5.4 最终维护版发布内容 |

## 验证状态

- Python `pytest`：通过（200 项）
- 前端 `npm.cmd run typecheck`：通过
- 前端 `npm.cmd run test`：通过（2 files / 21 tests）
- Windows 完整打包：通过（PyInstaller + Inno Setup + 7-Zip SFX）
- 程序目录：258.2 MB

## 发布注意

- 这是最后一个计划内维护版本。项目仍保留开源代码与发行产物，后续问题或功能需求请通过 GitHub Issue 或项目联系方式反馈。

## 发行版产物

- 安装版：`dist/TracePipeline-Setup-v4.5.4.exe`（128.9 MB）
- 便携版：`dist/TracePipeline-Portable-v4.5.4.exe`（123.1 MB）

---

# TracePipeline v4.5.3 发布说明

**发布日期**：2026-06-22

## 本版本亮点

### 🧭 GUI 交互稳定性修复

本版本聚焦桌面 GUI 的交互一致性与空态反馈：

- 开发者面板与对比视图中的 `el-radio-button` 改用 `value` 绑定，匹配新版 Element Plus 组件 API
- 前端按需注册补充 `ElRadio`，确保单选组组件依赖完整
- 折叠侧栏的导航项与目录快捷入口保留 tooltip，窄侧栏状态下也能识别功能入口

### 📊 对比视图体验补丁

- 无露头数据时展示“去处理数据”操作入口，减少空页面停顿
- 加载态与表格渲染拆分，避免加载中、空表格和数据表格状态混杂
- 图片筛选无结果时在图片区域内展示空态；处理完成但无结果图时展示明确提示
- 对比表格增加最小宽度与横向滚动，提升窄窗口下的可读性

### ⚙️ 配置表单单位显示优化

- 凸包透明度、圆窗透明度输入框以百分比形式展示并显式补充 `%` 单位
- 输入框宽度收敛，滑块与数值输入组合更紧凑

## 变更文件

| 文件 | 变更类型 | 说明 |
|------|----------|------|
| `frontend/src/App.vue` | 改进 | 折叠侧栏导航与目录按钮 tooltip 优化 |
| `frontend/src/components/ConfigForm.vue` | 改进 | 透明度输入框百分比单位显示优化 |
| `frontend/src/components/DevPanel.vue` | 修复 | 单选按钮改用 `value` 绑定 |
| `frontend/src/main.ts` | 修复 | Element Plus 按需注册补充 `ElRadio` |
| `frontend/src/views/ComparisonView.vue` | 修复/改进 | 对比页空态、加载态、图片筛选空态、表格横向滚动优化 |
| `trace_pipeline/__init__.py` / `frontend/package*.json` / `TracePipeline-setup.iss` | 版本 | 同步至 v4.5.3 |
| `README.md` / `CHANGELOG.md` / `RELEASE_NOTES.md` | 文档 | 同步 v4.5.3 发布内容 |

## 验证状态

- Python `tests/test_packaging_metadata.py`：通过（3 项）
- 前端 `npm.cmd run typecheck`：通过
- 前端 `npm.cmd run test`：通过（2 files / 21 tests）
- Windows 完整打包：通过（PyInstaller + Inno Setup + 7-Zip SFX）
- 程序目录：258.2 MB

## 发布注意

- 本版本为 GUI patch 版本，重点验证对比视图、开发者面板单选项和配置面板透明度输入。

## 发行版产物

- 安装版：`dist/TracePipeline-Setup-v4.5.3.exe`（128.9 MB）
- 便携版：`dist/TracePipeline-Portable-v4.5.3.exe`（123.1 MB）

---

# TracePipeline v4.5.2 发布说明

**发布日期**：2026-06-22

## 本版本亮点

### 🛡️ 运行配置与日志读取边界加固

本版本收紧 GUI 运行入口与日志/审计读取参数：

- `GuiApi.run_pipeline()` 增加前端覆盖白名单，仅允许处理参数、`style` 和 `parallel_workers` 覆盖磁盘配置，禁止运行请求覆盖输入/输出目录、目标名等路径字段
- `get_logs()` 将 `tail` 限制在 1–2000；`get_audit_log()` 与 `AuditService.get()` 将 `limit` 限制在 1–500
- 审计归档扫描跳过超过 10 MiB 的 `.jsonl` zip member，避免异常归档造成内存压力
- 报告进度队列改为 `deque(maxlen=500)`，避免长期运行时进度消息无界增长

### 🔒 并发与缓存可靠性修复

- 用户通过系统对话框选择的外部路径集合增加锁保护，避免路径登记和校验并发读写风险
- `DirectoryChangeDetector` 的快照检测与失效操作加锁，并在超大目录截断时记录总条目数，新增/删除文件仍可触发变更检测
- `PipelineService.shutdown()` 对 `_running` 状态读取加锁，减少关闭期间状态竞争
- `TTLCache` 新增 `__len__()`，统计缓存失效不再直接访问内部 `_store`

### 📊 Excel 与绘图稳定性改进

- 命名工作表不存在时预先解析为首个 sheet，减少 `read_excel` 失败后再回退的噪声路径
- `read_trace_excel()` 的类型标注收敛为 `ExcelEngine` / `SheetArg`，并修复 pandas 数值检测的类型兼容性
- `apply_style_overrides()` 使用 `RLock`，修复样式覆盖期间再次配置 matplotlib 样式可能死锁的问题
- CJK 标题和 mathtext 不再请求缺失的 bold 字重，减少 `findfont` 警告；图表标题视觉由粗体改为常规字重

### ⚡ 前端打包与进度面板调整

- Element Plus 从全量 `app.use(ElementPlus)` 改为按需注册常用组件，降低运行时注册面
- Vite `manualChunks` 细分 Vue、ECharts、Element Plus 表单/数据/反馈组件等 chunk，并过滤 `@vueuse/core` 的无效注解警告
- `ProgressPanel` 移除推断式步骤指示器，保留真实进度条、当前文件/消息和并行度控制，避免前端推断步骤与后端实际阶段不一致

## 变更文件

| 文件 | 变更类型 | 说明 |
|------|----------|------|
| `backend/gui_api.py` | 修复 | 运行配置覆盖白名单、路径登记锁、日志/审计 limit clamp、报告进度队列上限 |
| `backend/services/audit_service.py` | 修复 | 审计 limit clamp、zip member 10 MiB 大小限制 |
| `backend/services/data_service.py` | 修复 | 分页参数统一规范化 |
| `backend/services/pipeline_service.py` | 修复 | shutdown 状态读取加锁 |
| `backend/services/stats_service.py` | 改进 | 通过 `len(TTLCache)` 获取缓存条数 |
| `backend/utils/cache.py` | 修复 | `TTLCache.__len__()`、目录变更检测并发锁、截断目录总数快照 |
| `trace_pipeline/io/excel_reader.py` | 改进 | sheet 缺失预解析回退首表、类型标注收敛 |
| `trace_pipeline/plotting/style.py` | 修复 | RLock 反死锁、CJK/mathtext 字重降噪 |
| `frontend/src/main.ts` | 改进 | Element Plus 按需注册 |
| `frontend/vite.config.ts` | 改进 | 细分 manual chunks、过滤 @vueuse 注解警告 |
| `frontend/src/components/ProgressPanel.vue` | 变更 | 移除推断式步骤指示器 |
| `tests/*.py` | 测试 | 新增安全、分页、缓存、Excel、绘图并发/回归测试 |
| `README.md` / `CHANGELOG.md` / `RELEASE_NOTES.md` | 文档 | 同步 v4.5.2 发布内容 |

## 验证状态

- Python 发布相关测试：通过（57 项，覆盖 GUI API、审计、缓存、分页、Excel、路径安全、绘图与打包元数据）
- 前端 `npm.cmd run typecheck`：通过
- 前端 `npm.cmd run test`：通过（2 files / 21 tests）
- Windows 完整打包：通过（PyInstaller + Inno Setup + 7-Zip SFX）
- 程序目录：258.2 MB

## 发布注意

- 前端 chunk 文件名已调整，部署或试运行时需清理旧静态资源缓存。
- 图表标题不再强制 bold，若论文排版模板依赖粗体标题，请重新预览导出图。

## 发行版产物

- 安装版：`dist/TracePipeline-Setup-v4.5.2.exe`（128.9 MB）
- 便携版：`dist/TracePipeline-Portable-v4.5.2.exe`（123.1 MB）

---

# TracePipeline v4.5.1 发布说明

**发布日期**：2026-06-21

## 本版本亮点

### 📝 全项目代码注释规范化

本次版本对 40+ 源文件进行了系统性注释清理与规范化：

- **删除冗余装饰性注释框**：移除 `# ---- ... ----`、`# ==== ... ====` 等长分隔线，统一为短标题分区风格
- **中文化注释**：将英文及中英混杂注释改为中文（如 `# success should have None error` → `# 成功时应无错误`）
- **保留高价值注释**：MATLAB 算法参考、安全校验逻辑（路径遍历防护/域名白名单）、跨版本兼容性说明、工具抑制标记（ruff/mypy/pylint）

覆盖范围：`trace_pipeline/` 核心计算包（angles/endpoints/transforms/statistics/nodes/config/models/pipeline/reporting/validation 等）、`backend/` GUI 服务层（gui_api/main_gui/report_service/stats_service/cache）、`frontend/src/` 前端视图层（App.vue 及 6 个视图组件、3 个样式文件、DevPanel/ProgressPanel）、`tests/` 测试文件、`scripts/package.py` 打包脚本。

### 🚀 SplashScreen 启动页视觉增强

启动引导界面进行了用户体验改进（75+ 行变更）：

- **加载点动画**：进度文本后增加动态 `...` 指示器（`loading-dots` CSS keyframe），缓解等待焦虑
- **重试机制**：连接失败时显示「重试连接」按钮，点击触发 `retryBootSequence()` 重新执行引导序列
- **错误状态展示**：错误消息区域化展示，背景/边框/文字颜色语义强化（半透明红色、`#fca5a5` 文字）
- **移动端适配**：安全边距（40px→24px）、雷达图 `min(80vw, 280px)`、低价值装饰标签在窄屏隐藏
- **进度条可读性提升**：轨道背景对比度增强（`rgba(255,255,255,0.08)`→`0.15`）、填充中心加亮（`#7dd3fc`）、发光效果增强（`0 0 12px rgba(56,189,248,0.8)`）、文字明度提升（`rgba(255,255,255,0.6)`→`0.85`）

### 🔢 版本同步

全项目版本号同步至 4.5.1，涉及 `trace_pipeline/__init__.py`、`frontend/package.json`、`frontend/package-lock.json`、`TracePipeline-setup.iss`。

## 变更文件

| 文件 | 变更类型 | 说明 |
|------|----------|------|
| `trace_pipeline/*.py`（30+文件） | 改进 | 注释规范化：删除冗余框/中文化/统一短标题分区 |
| `backend/gui_api.py` | 改进 | 注释规范化（11处分区标题） |
| `backend/main_gui.py` | 改进 | 注释中文化 |
| `backend/services/report_service.py` | 改进 | 注释规范化（4处分区标题） |
| `backend/services/stats_service.py` | 改进 | 注释中文化 |
| `backend/utils/cache.py` | 改进 | 注释中文化 |
| `frontend/src/components/SplashScreen.vue` | 改进 | 加载点动画、重试按钮、错误状态、移动端优化、进度条可读性 |
| `frontend/src/components/DevPanel.vue` | 改进 | 注释中文化 |
| `frontend/src/components/ProgressPanel.vue` | 改进 | 注释规范化 |
| `frontend/src/App.vue` | 改进 | 注释规范化（10处分区标题/冗余注释删除） |
| `frontend/src/views/*.vue`（6文件） | 改进 | 注释规范化（CSS 分区标题统一） |
| `frontend/src/styles/*.css`（3文件） | 改进 | 注释规范化（120+行头部/分区注释简化） |
| `frontend/tests/stores/cache.test.ts` | 改进 | 注释中文化 |
| `scripts/package.py` | 改进 | 注释规范化（所有分区标题） |
| `tests/*.py`（6文件） | 改进 | 注释中文化/规范化 |
| `trace_pipeline/__init__.py` | 版本 | 4.5.0 → 4.5.1 |
| `frontend/package.json` | 版本 | 4.5.0 → 4.5.1 |
| `frontend/package-lock.json` | 版本 | 4.5.0 → 4.5.1 |
| `TracePipeline-setup.iss` | 版本 | 4.5.0 → 4.5.1 |
| `README.md` | 文档 | 版本徽章与版本历史同步 |
| `CHANGELOG.md` | 文档 | 新增 v4.5.1 条目 |
| `RELEASE_NOTES.md` | 文档 | 同步至 v4.5.1 |

## 验证状态

- Python `compileall`：通过
- 前端 `npm.cmd run typecheck`：通过
- 前端 `npm.cmd run test`：通过（2 files / 21 tests）
- Python 快速测试：通过（`tests/test_packaging_metadata.py`、`test_angles.py`、`test_endpoints.py`、`test_nodes.py`、`test_statistics.py`，共 67 项）
- Python `tests/test_pipeline.py`：`TestLoadTraceData` 2 项通过，`TestRunPipeline::test_successful_run` 本机执行 300s 超时
- Windows 完整打包：通过
- `ruff`：未安装，跳过

## 发行版产物

- 安装版：`dist/TracePipeline-Setup-v4.5.1.exe`（129.2 MB）
- 便携版：`dist/TracePipeline-Portable-v4.5.1.exe`（123.4 MB）

---

# TracePipeline v4.5.0 发布说明

**发布日期**：2026-06-21

## 本版本亮点

### 🎨 界面视觉全面升级（P0 → P2 三阶段重构）

本版本完成了软件界面的系统性视觉重构：

**P0 — 设计一致性基础**：统一图标库迁移至 `@lucide/vue`，移除混用的 Element Plus 图标；修复 ECharts 图表文字色（暗色主题灰 → 浅色语义变量）；规范化滑块、标签页、状态标签的 Element Plus 组件样式。

**P1 — 体验提升**：统计卡片强调色从顶部边框改为左侧竖线，与现代数据卡片设计规范对齐；表格行悬停新增品牌色左侧指示器动效。

**P2 — 品牌感与沉浸感**：启动页三层同心圆差速旋转（16 s / 10 s反向 / 6 s）营造层次感；新增卡片语义辉光工具类；侧边栏折叠时标签淡出过渡。

### 🗺️ 地质语义色系统统一

侧边栏导航图标颜色与首页模块卡片完全对齐，使用同一套地质语义配色：深蓝（处理）/ 青碧（统计）/ 赭石（对比）/ 蓝紫（数据）/ 鲜红（配置）。对比视图、饼图、直方图的图表系列色同步统一，视觉沉稳不晃眼。

## 变更文件

| 文件 | 变更类型 | 说明 |
|------|----------|------|
| `frontend/src/components/icons/*.vue` | 重构 | 6 个图标组件迁移至 @lucide/vue |
| `frontend/src/App.vue` | 改进 | 图标颜色传值、侧边栏标签过渡、dev-toggle 居中 |
| `frontend/src/components/StatCards.vue` | 改进 | border-top → border-left，光晕方向调整 |
| `frontend/src/components/SplashScreen.vue` | 改进 | 雷达环差速旋转动画 |
| `frontend/src/utils/echarts-theme.ts` | 修复+改进 | 图表文字色、系列色统一为地质语义色 |
| `frontend/src/components/PieChart.vue` | 修复 | 图表文字色修复 |
| `frontend/src/components/HistogramChart.vue` | 修复 | 图表文字色修复 |
| `frontend/src/styles/element-global.css` | 改进 | 滑块/标签页/标签/表格行微交互规范化 |
| `frontend/src/styles/tokens.css` | 新增 | 卡片语义辉光工具类 |
| `frontend/package.json` | 版本 | 4.4.0 → 4.5.0 |
| `trace_pipeline/__init__.py` | 版本 | 4.4.0 → 4.5.0 |

---

# TracePipeline v4.4.0 发布说明

**发布日期**：2026-06-21

## 本版本亮点

### 🎨 UI 动效性能全面提升

本版本对前端动画渲染层进行了系统性优化，所有骨架屏闪光动画改用 GPU Composite-only 方案（`transform: translateX`），消除了 Paint 阶段的帧间重绘；页面路由切换动画移除了开销较高的 `filter: blur()` 效果。

### 🎯 设计系统 Token 扩展

新增 Surface 层次色彩系统、发光色 Token 和标准缓动曲线变量，为后续组件视觉升级奠定基础。同时预置了三类可复用动效 Keyframe，供下阶段 UI 改造直接引用。

## 变更文件

| 文件 | 变更类型 | 说明 |
|------|----------|------|
| `frontend/src/styles/tokens.css` | 改进+新增 | shimmer 性能修复；新增 Surface/glow/easing token 和3个 keyframe |
| `frontend/src/styles/element-global.css` | 改进 | Element Plus 骨架屏样式更新为 ::after 伪元素方案 |
| `frontend/src/App.vue` | 改进 | 页面切换动画去 blur；侧边栏添加 will-change |

---

# v4.3.3

**2026-06-20**

> 死代码清理与接口精简 — 6 项清理，删除约 112 行代码，无功能变更。

## 高亮

- **日志兼容层移除** — 删除 `trace_pipeline/cli/logging_setup.py`，GUI 入口改为直接导入 `trace_pipeline.logging`
- **绘图死代码清理** — 移除 `_add_north_arrow`、`_add_scale_bar` 及 3 个未导出辅助函数，同步清理 `__all__` 与 import
- **样式辅助函数精简** — 删除未使用的 `text_font_kwargs`，降低公开接口噪音
- **前端 API 接口收敛** — 移除未使用的 WebView2 检测接口、mock 实现及 api 导出
- **打包配置同步** — 移除废弃 logging setup hidden import，避免保留无效依赖

## 变更摘要

### 后端日志模块清理（2 项）
- `trace_pipeline/cli/logging_setup.py`：删除日志初始化兼容层
- `TracePipeline.spec`：移除 `trace_pipeline.cli.logging_setup` hidden import

### 绘图模块清理（3 项）
- `plotting/_layout.py`：移除 `_add_north_arrow` 与 3 个未导出辅助函数
- `plotting/style.py`：移除 `text_font_kwargs`
- `plotting/trace_plot.py`：移除 `_add_scale_bar` 并清理 import

### 前端 API 接口清理（1 项）
- `pywebview.ts`：移除未使用的 WebView2 检测接口、方法声明、mock 实现及导出

### 测试验证
- 后端 pytest：148/149 通过（1 项 pre-existing failure 与本次变更无关）
- 前端 vitest：21/21 通过
- 前端构建：成功（1.30s）

---

# v4.3.2

**2026-06-20**

> 代码质量与防御性编程 — 7 项一般缺陷修复。

## 高亮

- **配置保存临时文件残留修复** — `config_service._save()` 任何异常都清理临时文件，防止磁盘残留
- **样式覆盖锁一致性** — `apply_style_overlays` orig 捕获→修改→恢复整个生命周期在同一锁临界区内
- **哈希算法统一** — `preview_service.py` 从 MD5 改为 SHA-256，与全项目一致
- **日志 tail 内存限制** — `_tail_lines` 缓冲区上限 2MB，超限截断并告警
- **消息 badge DOM 查询回退** — 双重 rAF 后追加 setTimeout 递增延迟重试

## 变更摘要

### 严重缺陷修复（1 项）
- `preview_service.py`：MD5 → SHA-256 哈希统一

### 一般缺陷修复（6 项）
- `config_service.py`：临时文件清理 + 配置重置防御性检查
- `style.py`：apply_style_overrides 锁结构修复
- `gui_api.py`：force 参数 bool() 转换
- `log_service.py`：tail 缓冲区 2MB 上限
- `message.ts`：DOM 查询 setTimeout 回退

### 测试验证
- 后端 pytest：132/132 通过
- 前端 vitest：21/21 通过
- 前端构建：成功（1.12s）

---

# v4.3.1

**2026-06-20**

> 性能与安全优化 — 多进程日志竞态修复 + 图片缓存 + 节点批量绘制 + 启动并行化。

## 高亮

- **多进程日志归档竞态修复** — `logging/core.py` 归档/清理操作仅主进程执行，子进程跳过，消除 `threading.Lock` 不跨进程导致的日志数据丢失/zip 损坏风险
- **图片缓存 TTLCache** — `gui_api.py` 新增 `TTLCache(maxsize=20, ttl=300)`，重复请求同一图片从 500-2000ms 降至 <5ms
- **节点批量 scatter 绘制** — `trace_plot.py` 从逐个 `ax.plot()` 改为按类型分组批量 `ax.scatter()`，节点 >100 时绘制提速 5-10x
- **启动步骤并行化** — `App.vue` 文件扫描与字体预热合并为 `Promise.all` 并行执行，启动时间减少 2-5 秒
- **关键异常传播** — `pipeline_service.py` / `data_service.py` 添加 `(MemoryError, SystemExit, KeyboardInterrupt): raise`，防止内存耗尽时静默失败
- **ReportService 缓存上限** — `maxsize` 从 0（无上限）改为 32，消除 OOM 风险

## 变更摘要

### 致命缺陷修复（1 项）
- `logging/core.py`：多进程日志归档竞态修复

### 严重缺陷修复（2 项）
- `pipeline_service.py`：关键异常传播（2 处）
- `data_service.py`：关键异常传播（2 处）

### 性能优化（4 项）
- `gui_api.py`：图片缓存 TTLCache
- `report_service.py`：maxsize 0→32
- `trace_plot.py`：节点批量 scatter
- `App.vue`：启动步骤并行化

### 测试验证
- 后端 pytest：132/132 通过
- 前端 vitest：21/21 通过
- 前端构建：成功（1.13s）

---

# v4.3.0

**2026-06-20**

> 全面代码审查与优化 — 6 项致命缺陷修复 + 12 项严重缺陷修复 + 前端性能优化。

## 高亮

- **入口脚本全局异常捕获** — `run_gui.py` / `run_trace_pipeline.py` 添加 try/except 兜底，GUI 模式弹出 Windows MessageBoxW 错误对话框，CLI 模式输出 stderr 友好提示，杜绝静默崩溃
- **JS Bridge 异常穿透修复** — `gui_api.run_pipeline` 添加 `except Exception` 兜底，统一返回错误响应，防止 `PermissionError`/`OSError` 穿透到 pywebview 调用栈
- **glob 括号跨平台修复** — `output_paths.py` 新增 `_safe_glob_pattern()` 辅助函数，使用 `glob.escape()` + 通配符恢复，修复 `()` 在 Linux 上被解释为字符集导致文件匹配失败
- **报告缓存键稳定化** — `report_service.py` 从 Python 内置 `hash()` 改为 `hashlib.sha256`，修复 `PYTHONHASHSEED` 随机化导致进程重启后缓存全部失效
- **前端图片缓存 LRU O(1)** — `cache.ts` 从 O(n) 遍历查找最旧条目改为 `Map.keys().next()` O(1) 淘汰，50 条目淘汰操作提速 ~100x
- **JS Bridge 类型安全** — `pywebview.ts` 所有 `Promise<unknown>` 替换为具体返回类型，新增 10 个辅助接口，`vue-tsc` 零错误
- **图片加载并发去重** — `image.ts` 添加 `_loadingPromises` Map，相同图片并发请求时复用同一 Promise，减少 50%+ 重复请求
- **App.vue 事件泄漏修复** — 三处拖拽/resize 的 document 事件监听器添加 `onUnmounted` 清理

## 变更摘要

### 致命缺陷修复（6 项）
- `run_gui.py` / `run_trace_pipeline.py`：全局异常捕获 + 用户友好提示
- `gui_api.py`：`run_pipeline` 添加 `except Exception` 兜底
- `output_paths.py`：`_safe_glob_pattern()` glob 括号转义
- `dispatcher.py`：`mp.active_children()` 替代 `executor._processes` 私有属性
- `report_service.py`：`hash()` → `hashlib.sha256` 稳定哈希
- `config.example.json`：补充 `parallel_workers` 字段

### 严重缺陷修复（12 项）
- `models.py`：`TraceData.lengths` 缓存改用 `object.__setattr__`
- `logging/core.py`：`_rotate` 竞态保护（`replace()` + try/except）
- `data_service.py`：`float()` 转换异常保护
- `audit_service.py`：跨天审计追溯（3 天 + zip 归档）
- `cache.py`：TTLCache 驱逐间隔 10 → 3
- `nodes.py`：int64 溢出保护
- `cache.ts`：不可变更新 + LRU O(1) 淘汰
- `App.vue`：document 事件 `onUnmounted` 清理
- `pywebview.ts`：完整类型安全（10 个辅助接口）
- `image.ts`：并发请求去重
- `StylePreview.vue`：适配类型安全改进

### 测试验证
- 后端 pytest：52/52 通过
- 前端 vue-tsc：零错误
- 前端 vitest：21/21 通过
- 前端构建：成功（1.03s）

---

# v4.2.7

**2026-06-20**

> 进度条体验优化。

## 高亮

- **进度条平滑动画** — `requestAnimationFrame` 驱动的追赶插值 + 蠕动效果，消除文件级粒度上报导致的"长时间不动→突然跳变"卡顿
- **重复运行修复** — 新运行启动时重置显示进度，避免残留上次的 100%

## 变更摘要

- `ProgressPanel.vue`：新增 `displayPercentage` 插值动画（追赶比例 0.12/帧 + 蠕动 0.015%/帧），CSS `transition` 调整为 `0.15s linear`；`watch(running)` 中重置 `displayPercentage` 为 0

---

# v4.2.6

**2026-06-20**

> GUI/CLI 双端并行处理支持，性能与用户体验双提升。

## 高亮

- **GUI 并行处理** — `ProcessPoolExecutor` (spawn) 替代逐目标串行执行，新增 `parallel_workers` 配置项（0=自动/cpu_count, 1=单进程串行, >1=自定义），多目标场景提速显著
- **CLI `--force-parallel`** — 目标数 ≤2 时自动切换串行（避免进程创建开销），可通过此参数强制并行
- **配置一致性增强** — `config_service.set()` 与 `gui_api.run_pipeline()` 增加 `reload()` 刷新，确保外部修改不被内存旧值覆盖
- **前端事件消费优化** — 轮询改为 while 循环一次性消费所有在途事件，防止进度条卡顿和事件积压

## 变更摘要

- `pipeline_service.py`：移除 `_EXECUTION_LOCK`，改用 `ProcessPoolExecutor`，支持关闭信号提前中止、`cancel_futures` 子进程清理
- `ProgressPanel.vue`：并行滑块控制权上移至父组件，移除 localStorage 持久化逻辑
- `ProcessingView.vue`：`parallelWorkers` 与 `configStore` 双向同步，轮询消费改为 while 循环
- `run_gui.py`：`multiprocessing.freeze_support()` 确保子进程不重复执行 GUI 初始化
- `config.py`：`parallel_workers` 字段加入 `DEFAULT_CONFIG` / `ConfigDict`
- `cli/args.py` + `cli/dispatcher.py`：新增 `--force-parallel` 参数与 `_should_use_serial()` 启发式判断

---

# v4.2.5

**2026-06-20**

> 类型安全加固与打包工具链完善。

## 高亮

- **类型安全加固** — 前端 25+ 处 `any` 替换为具体接口类型（`ScanEntry`/`StatsResult`/`ComparisonEntry`/`ResultEntry`），新增 `GuiApiInterface`（36 方法签名），`vue-tsc --noEmit` 零错误
- **异常捕获精确化** — Python 端 `except Exception` 收窄为 `except (ValueError, OSError, RuntimeError)` 等具体类型
- **打包工具链完善** — 移除 `shell=True`，改用 `shutil.which` 解析可执行文件全路径；添加 D 盘回退路径检测

## 变更摘要

- 前端类型系统重构：14 处 `any` → 具体接口、`catch (e: any)` → `catch (e: unknown)`、裸 `catch {}` 补充参数
- Python 异常精确化：`data_service.py` / `report_service.py` / `config_service.py` 收窄异常类型
- 打包脚本安全加固：`shell=True` → `shutil.which` + `is_file()` 检测
- 文档更新：README 版本历史补全、Mermaid 架构图、类型安全桥接说明

---

# v4.2.4

**2026-06-20**

> 安全重构与架构类型化。

## 高亮

- **GuiApiInterface** — 36 方法签名的 TypeScript 接口，替换 `getApi()` 和 `mockApi()` 的 `any` 返回类型
- **shell=True 消除** — `scripts/package.py` 移除 `shell=True` 模式，消除命令注入风险
- **前端类型断言补完** — 11 个视图/组件/Store 文件添加 API 调用类型断言

---

# v4.2.3

**2026-06-20**

> 前端类型安全全面加固。

## 高亮

- **缓存 Store 类型化** — 新增 4 个接口（`ScanEntry`/`StatsResult`/`ComparisonEntry`/`ResultEntry`），替换 14 处 `any`
- **核心类型收窄** — `ConfigData` / `DataPageResult` 中 `any` → `unknown`
- **异常处理规范化** — `catch (e: any)` → `catch (e: unknown)`，4 处裸 `catch {}` 补充异常参数

---

# v4.2.2

**2026-06-19**

> 错误处理强化与开发体验优化。

## 高亮

- **图片调用合并** — 新增 `get_image_data` 方法，缓存未命中时单次 JS bridge 调用替代原先的 meta+image 双调用
- **调试残留清理** — 移除 5 处 `console.debug` 开发期残留
- **静默错误消除** — 4 处空 `.catch(() => {})` 替换为 `console.error` 错误日志

---

# v4.2.1

**2026-06-19**

> 性能优化与缺陷修复。

## 高亮

- **字符串缓存优化** — 引入运行中字符计数器，图片淘汰从 O(n²) 降至 O(1) 摊销
- **幂等样式配置** — `configure_style()` 添加 double-checked locking，消除每次绘图的冗余调用
- **内存优化** — `TraceData.__post_init__` 使用 `np.asarray` 替代 `np.array(copy=True)`

## 修复

- `get_image_thumbnail` BytesIO 未使用 context manager 导致的资源泄漏

---

# v4.2.0

**2026-06-18**

> 基于 v4.0.0 以来的提交记录整理，涵盖 v4.1.0–v4.2.0 迭代周期。

## 高亮

- **报告导出实时进度反馈** — 后端逐阶段推送进度事件，前端进度条轮询展示
- **前后端测试框架落地** — 引入 Vitest + jsdom 前端测试、pytest 后端冒烟测试
- **绘图阶段解耦** — `run_pipeline` 中的绘图逻辑提取为独立 `_run_plot_stage` 函数
- **启动提速** — 非核心服务改为懒加载，延迟至 WebView2 检测后初始化
- **开源就绪** — 重写 README 技术架构文档，补充 LICENSE / CONTRIBUTING / CHANGELOG / CODE_OF_CONDUCT

## 新特性

- **报告导出进度反馈** — 后端 `generate` / `generate_reports_zip` 新增 `progress_callback`
- **绘图阶段解耦** — 主函数复杂度显著降低，提升可测试性

## 性能改进

- **服务启动优化** — 非核心服务懒加载，缩短冷启动时间
- **缓存策略升级** — 统计缓存引入 LRU 淘汰机制，TTL 缓存批量驱逐
- **全局异常处理优化** — 消除裸 `except:pass` 语句

---

**完整对比**: [`v4.2.0...v4.2.5`](https://github.com/zylyes/TracePipeline/compare/v4.2.0...v4.2.5)
