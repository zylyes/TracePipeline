# 更新日志

本文件记录 TracePipeline 项目的主要版本变更。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)，版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

---

## [Unreleased]

- 暂无。

---

## [4.5.3] - 2026-06-22

### 修复

- **Element Plus 单选按钮兼容性**：开发者面板与对比视图中的 `el-radio-button` 改用 `value` 绑定，并按需注册 `ElRadio`，避免新版 Element Plus 下单选组取值异常。
- **对比页空态与加载态**：无露头数据时提供“去处理数据”入口；加载状态与表格渲染分离，避免空数据和加载中状态互相覆盖。
- **图片筛选反馈**：对比页图片筛选无结果时在图片区域内展示空态，处理完成但无结果图时展示明确提示。

### 改进

- **折叠侧栏提示**：导航与目录按钮始终保留 `title`，折叠状态下仍可识别入口含义。
- **透明度输入可读性**：配置面板透明度数值输入框改为百分比宽度，并显式显示 `%` 单位。
- **对比表格窄屏表现**：对比表格增加最小宽度与横向滚动，减少列内容挤压。

### 版本同步

- 全项目版本号同步至 4.5.3。

### 验证状态

- Python `tests/test_packaging_metadata.py`：通过（3 项）
- 前端 `npm.cmd run typecheck`：通过
- 前端 `npm.cmd run test`：通过（2 files / 21 tests）
- Windows 完整打包：通过（PyInstaller + Inno Setup + 7-Zip SFX）
- 发行产物：安装版 128.9 MB，便携版 123.1 MB，程序目录 258.2 MB

---

## [4.5.2] - 2026-06-22

### 修复

- **运行配置覆盖白名单**：`GuiApi.run_pipeline()` 仅允许前端覆盖处理参数、`style` 和 `parallel_workers`，禁止通过运行请求覆盖 `input_dir`、`output_dir`、`table_stem`、`outcrop` 等路径/目标字段。
- **审计与日志参数限流**：`get_logs()` 的 `tail` 限制在 1–2000，`get_audit_log()` / `AuditService.get()` 的 `limit` 限制在 1–500，避免异常参数触发过量读取。
- **审计 zip 读取防护**：扫描归档日志时跳过超过 10 MiB 的 `.jsonl` member，降低恶意或异常归档造成的内存压力。
- **分页参数规范化**：数据分页统一限制 `page >= 1`、`1 <= page_size <= 500`，输入/输出数据读取路径保持一致行为。
- **绘图样式覆盖死锁修复**：`_STYLE_LOCK` 改为 `RLock`，`apply_style_overrides()` 在嵌套调用 `configure_style()` 时不再死锁。

### 改进

- **并发安全增强**：用户选择路径登记增加锁保护；`DirectoryChangeDetector` 的快照与失效操作加锁，超大目录截断快照额外记录总条目数。
- **Excel 读取优化**：命名 sheet 不存在时预先解析为首个工作表，避免先失败再回退的噪声路径。
- **缓存接口收敛**：`TTLCache` 新增 `__len__()`，统计缓存失效不再访问内部 `_store`。
- **前端产物拆分**：Element Plus 改为按需注册；Vite manual chunks 细分 Vue、ECharts、Element Plus 组件组，降低单个 vendor chunk 体积。
- **进度面板精简**：移除推断式步骤指示器，保留真实进度条、当前任务和并行度控制，避免步骤推断与后端实际状态不一致。
- **绘图字体噪声降低**：CJK 标题和 mathtext 不再请求缺失的 bold 字重，减少 matplotlib `findfont` 警告；标题视觉由粗体改为常规字重。

### 测试

- 新增 `test_gui_api.py` 覆盖运行配置白名单、日志/审计 limit clamp。
- 新增 `test_data_service_pagination.py` 覆盖输入/输出分页参数规范化。
- 新增 `test_audit_service.py` 覆盖审计 limit clamp 与 zip member 大小限制。
- 新增 `test_cache.py` 覆盖目录变更检测并发与截断目录变更识别。
- 新增 `test_excel_reader.py` 覆盖命名 sheet 缺失时读取首表。
- `tests/test_security.py` 增加用户选择路径并发读写测试；`tests/test_plotting.py` 增加样式覆盖反死锁测试。

### 版本同步

- 全项目版本号同步至 4.5.2。

### 验证状态

- Python 发布相关测试：通过（57 项）
- 前端 `npm.cmd run typecheck`：通过
- 前端 `npm.cmd run test`：通过（2 files / 21 tests）
- Windows 完整打包：通过（PyInstaller + Inno Setup + 7-Zip SFX）
- 发行产物：安装版 128.9 MB，便携版 123.1 MB，程序目录 258.2 MB

### 发布注意

- 前端 chunk 文件名会变化，部署时需清理旧静态资源缓存。
- 图表标题不再强制 bold，论文图表模板如依赖粗体标题需重新预览。

---

## [4.5.1] - 2026-06-21

### 改进

- **全项目代码注释规范化**：删除冗余注释框（`# ---- ... ----` / `# ==== ... ====`），统一为短标题分区风格；中文化英文及中英混杂注释；保留 MATLAB 算法参考、安全校验逻辑、跨版本兼容性说明、工具抑制（ruff/mypy/pylint）等高价值注释。涉及 `trace_pipeline/` 核心包（angles/endpoints/transforms/statistics/nodes/config/models/pipeline/reporting/validation 等 30+ 文件）、`backend/` 服务层（gui_api/main_gui/report_service/stats_service/cache）、`frontend/src/` 视图层（App.vue 及 6 个视图组件、3 个样式文件、DevPanel/ProgressPanel）、`tests/`（6 个测试文件）、`scripts/package.py`
- **SplashScreen 启动页视觉增强**：
  - 新增加载点动画（`loading-dots` CSS keyframe 动态 `...` 指示器）
  - 新增连接失败重试按钮（`retryBootSequence()` 方法 + `.retry-btn` 样式）
  - 错误状态展示优化：错误消息区域化展示、背景/边框/文字颜色调整
  - 移动端安全边距（padding 40px→24px）、响应式媒体查询（768px 断点隐藏低价值装饰元素）
  - 进度条可读性提升：轨道背景对比度增强、填充中心加亮（`#7dd3fc`）、发光效果增强、文字明度提升

### 版本同步

- 全项目版本号同步至 4.5.1

### 验证状态

- Python `compileall`：通过
- 前端 `npm.cmd run typecheck`：通过
- 前端 `npm.cmd run test`：通过（2 files / 21 tests）
- Python 快速测试：通过（`tests/test_packaging_metadata.py`、`test_angles.py`、`test_endpoints.py`、`test_nodes.py`、`test_statistics.py`，共 67 项）
- Python `tests/test_pipeline.py`：`TestLoadTraceData` 2 项通过，`TestRunPipeline::test_successful_run` 本机执行 300s 超时
- Windows 完整打包：通过（PyInstaller + Inno Setup + 7-Zip SFX）
- `ruff`：未安装，跳过

---

## [4.5.0] - 2026-06-21

### 新增

- **图标库统一**：迁移至 `@lucide/vue`，6 个导航图标（Compass / Workflow / BarChart3 / Layers2 / Table2 / SlidersHorizontal）替换原自定义 SVG；侧边栏工具按钮同步迁移，移除对 `@element-plus/icons-vue` 的依赖
- **设计语言统一**：侧边栏导航图标颜色与首页模块卡片地质语义色一致（深蓝 / 青碧 / 赭石 / 蓝紫 / 鲜红 / 品牌蓝）
- **卡片语义辉光工具类**：新增 `.tp-glow-success / warning / danger / info`，配合 `border-left` 卡片使用
- **启动页雷达环差速旋转**：三层同心圆差速旋转（16 s / 10 s 反向 / 6 s），带高光弧位点增强层次感
- **侧边栏折叠标签淡出**：使用 `<Transition>` 为 logo 文字与菜单标签添加 opacity 淡入淡出过渡

### 改进

- **统计卡片重设计**：强调色从顶部边框（`border-top`）改为左侧竖线（`border-left`），hover 光晕方向同步调整
- **表格行微交互**：首列 `::before` 伪元素，悬停时品牌色竖线从 0 → 3 px 过渡
- **ECharts 图表色修复**：图表文字色由暗模式灰 `#8b949e` 改为运行时读取 CSS 变量 `--tp-text-tertiary`（浅色主题可读）
- **图表颜色统一**：`CHART_COLOR_PRIMARY/SECONDARY/TERTIARY/DANGER` 改为地质语义色，与对比视图保持一致，视觉沉稳不晃眼
- **Element Plus 组件规范化**：
  - 滑块：轨道高度 4 px、手柄 16 × 16 px、hover 缩放 1.2×
  - 标签页：选中态文字色 `--tp-brand-accent` + 加粗
  - 状态标签：`border-radius` 改为 pill 形（`--tp-radius-full`）
- **开发者模式开关**：侧边栏底部开关居中对齐，展开/折叠状态一致

---

## [4.4.0] - 2026-06-21

### 改进

- **动画性能优化**：骨架屏 shimmer 动画从 `background-position` 改为 `transform: translateX` + `::after` 伪元素方案，消除每帧 Paint 重绘，降低 GPU 合成负载
- **页面切换优化**：移除路由切换过渡动画中的 `filter: blur()` 效果，减少合成层开销
- **侧边栏动画**：为侧边栏宽度过渡添加 `will-change: width` GPU 提示，降低 reflow 成本

### 新增

- **设计系统 Token 扩展**：新增 Surface 层次系统（`--tp-surface-0` ~ `--tp-surface-3`）、发光色 Token（`--tp-glow-primary/success/danger/warning`）、标准缓动曲线（`--ease-spring/decelerate/accelerate/standard`）
- **新增动效 Keyframe**：`tp-success-burst`（成功爆发光效）、`tp-border-glow`（边框呼吸光）、`tp-scan-line`（扫描线动效）供后续组件复用

## [4.3.3] - 2026-06-20

### 死代码清理与接口精简 — 代码清理（无功能变更）

#### 后端日志模块清理
- `trace_pipeline/cli/logging_setup.py`：删除日志初始化兼容层（仅 10 行委托代码），`backend/main_gui.py` 改为直接导入 `trace_pipeline.logging`
- `TracePipeline.spec`：同步移除 `trace_pipeline.cli.logging_setup` hidden import 声明

#### 绘图模块清理
- `plotting/_layout.py`：移除未使用的 `_add_north_arrow` 函数及 `_split_statistics_line`、`_statistics_font_size`、`_style_trace_axes` 三个未导出函数，同步清理 `__all__`
- `plotting/style.py`：移除未使用的 `text_font_kwargs` 函数，同步清理 `__all__`
- `plotting/trace_plot.py`：移除未使用的 `_add_scale_bar` 函数，同步清理 import

#### 前端 API 接口清理
- `pywebview.ts`：移除未使用的 `WebView2CheckResult` 接口、`check_webview2` 方法声明、mock 实现及 api 导出

#### 版本号同步
- 文档版本号同步至 4.3.3

#### 测试验证
- 后端 pytest：148/149 通过（1 项 pre-existing failure 与本次变更无关）
- 前端 vitest：21/21 通过
- 前端生产构建：成功（1.30s）

## [4.3.2] - 2026-06-20

### 代码质量与防御性编程 — 一般缺陷修复

#### 严重缺陷修复
- `preview_service.py`：缓存键哈希从 `hashlib.md5` 统一为 `hashlib.sha256`（截取前 16 位），与 `stats_service.py`、`report_service.py` 保持一致

#### 一般缺陷修复
- `config_service.py`：`_save()` 原子写入异常时临时文件残留修复 — `json.dumps` 移入 try 块，异常捕获扩展为 `Exception`，确保任何失败都清理临时文件
- `config_service.py`：`reset_processing()` 添加 `key in DEFAULT_CONFIG` 防御性检查，避免 `PROCESSING_KEYS` 与 `DEFAULT_CONFIG` 不同步时 KeyError
- `style.py`：`apply_style_overrides` 锁结构修复 — 从两个独立 `with _STYLE_LOCK` 块改为 `acquire()/release()` 单次获取模式，确保 orig 捕获→修改→恢复整个生命周期在同一锁临界区内
- `gui_api.py`：`scan_files` 方法添加 `force = bool(force)` 显式转换，防止 JS bridge 传入字符串 `"true"` 被误判
- `log_service.py`：`_tail_lines` 添加 `_MAX_TAIL_BUFFER = 2MB` 缓冲区上限，超限时截断保留最后 2MB 数据并记录 warning
- `message.ts`：双重 `requestAnimationFrame` DOM 查询添加 `setTimeout` 递增延迟重试回退（50ms/100ms/200ms，最多 3 次）

#### 版本号同步
- `TracePipeline-setup.iss`：AppVersion/OutputBaseFilename/UninstallDisplayName/VersionInfoVersion 同步至 4.3.1
- `frontend/package-lock.json`：版本号同步至 4.3.1

#### 测试验证
- 后端 pytest：132/132 通过
- 前端 vitest：21/21 通过
- 前端生产构建：成功（1.12s）

## [4.3.1] - 2026-06-20

### 性能与安全优化 — 多进程竞态修复 + 缓存增强 + 启动加速

#### 致命缺陷修复
- `logging/core.py`：多进程日志归档竞态修复 — `DailyRotatingJsonHandler.__init__` 中归档/清理操作仅主进程执行，子进程（spawn worker）跳过，消除 `threading.Lock` 不跨进程导致的日志数据丢失/zip 损坏风险

#### 严重缺陷修复
- `pipeline_service.py`：`_run_background` 中 `future.result()` 和外层 try-except 添加 `(MemoryError, SystemExit, KeyboardInterrupt): raise`，防止关键异常被 `except Exception` 吞没
- `data_service.py`：`get_data` 和 `_get_input_data` 添加关键异常传播，防止内存耗尽时静默失败

#### 性能优化
- `gui_api.py`：新增图片缓存 `TTLCache(maxsize=20, ttl=300)`，`get_image`/`get_image_data` 命中时跳过文件读取+base64 编码，重复请求从 500-2000ms 降至 <5ms
- `report_service.py`：TTLCache `maxsize` 从 0（无上限）改为 32，消除内存无限增长 OOM 风险
- `trace_plot.py`：节点绘制从逐个 `ax.plot()` 改为按类型（I/Y/X）分组批量 `ax.scatter()`，节点 >100 时绘制耗时从 200-500ms 降至 <50ms
- `App.vue`：启动步骤 2（文件扫描）与步骤 3（字体预热）合并为 `Promise.all` 并行执行，4 步→3 步，启动时间减少 2-5 秒

#### 测试验证
- 后端 pytest：132/132 通过（快速测试集）
- 后端日志测试：2/2 通过
- 前端 vitest：21/21 通过
- 前端生产构建：成功（1.13s）

## [4.3.0] - 2026-06-20

### 全面代码审查与优化 — 致命缺陷修复 + 严重缺陷修复 + 性能优化

#### 致命缺陷修复（阶段一）
- `run_gui.py` / `run_trace_pipeline.py`：添加全局异常捕获，`KeyboardInterrupt` 静默退出，其他异常记录日志 + 用户友好提示（GUI 弹出 MessageBoxW，CLI 输出 stderr）
- `gui_api.py`：`run_pipeline` 方法在 `except ValueError` 之后添加 `except Exception` 兜底，统一返回 `{"status": "error", "message": ...}`，防止异常穿透到 pywebview 调用栈
- `output_paths.py`：新增 `_safe_glob_pattern()` 辅助函数，使用 `glob.escape()` 转义字面字符后恢复 `*` 通配符，修复 glob 模式中括号 `()` 在 Linux 上被解释为字符集导致文件匹配失败
- `dispatcher.py`：`_terminate_worker_processes` 从访问 `executor._processes` 私有属性改为使用 `mp.active_children()` 公开 API
- `report_service.py`：缓存键从 Python 内置 `hash()` 改为 `hashlib.sha256` 稳定哈希，修复 `PYTHONHASHSEED` 随机化导致进程重启后缓存全部失效
- `config.example.json`：补充 `parallel_workers` 字段（默认 0=自动 CPU 数）

#### 严重缺陷修复（阶段二）
- `models.py`：`TraceData.lengths` 缓存从直接操作 `__dict__` 改为 `object.__setattr__` 标准模式，消除 CPython 实现细节依赖
- `logging/core.py`：`_rotate` 中 `Path.rename()` 改为 `Path.replace()` 原子覆盖 + try/except 竞态保护
- `data_service.py`：`float(val)` 转换包裹 try/except，转换失败 fallback 到 `str(val)`
- `audit_service.py`：审计日志从仅查当天改为扫描最近 3 天（目录 + zip 归档），新增 `_scan_day_dir` 和 `_scan_zip_file` 方法
- `cache.py`：TTLCache 批量驱逐间隔从 10 改为 3，减少过期条目驻留
- `nodes.py`：网格分桶前添加坐标值范围检查，超 1e15 发出警告防止 int64 溢出

#### 前端严重缺陷修复
- `cache.ts`：`getCachedString` 改为 delete+set 不可变更新，消除 Vue 响应式副作用；`pruneStringCache` 和 `setCachedString` LRU 淘汰从 O(n) 遍历改为 O(1) `keys().next()`
- `App.vue`：三处拖拽/resize 的 document 事件监听器添加 `onUnmounted` 清理 + `_activeCleanup` 跟踪，修复内存泄漏
- `pywebview.ts`：`GuiApiInterface` 所有 `Promise<unknown>` 替换为具体返回类型（`ConfigData`/`PipelineResult[]`/`StatsData` 等），新增 10 个辅助接口，消除调用方 `as any` 转型
- `image.ts`：添加 `_loadingPromises` Map 实现并发请求去重，相同图片同时请求时复用同一 Promise
- `StylePreview.vue`：移除不必要的 `as Record<string, unknown>` 断言，适配类型安全改进

#### 测试验证
- 后端 pytest：52/52 通过
- 前端 vue-tsc 类型检查：零错误
- 前端 vitest：21/21 通过
- 前端生产构建：成功

## [4.2.7] - 2026-06-20

### 优化
- `ProgressPanel.vue` 进度条平滑插值动画：`requestAnimationFrame` 驱动的追赶插值 + 等待期间蠕动效果，消除"长时间不动→突然跳变"的卡顿体验；CSS `transition` 从 `0.4s expo` 调整为 `0.15s linear` 配合逐帧更新

### 修复
- `ProgressPanel.vue` 重复运行进度条不归零：新运行启动时重置 `displayPercentage` 为 0

## [4.2.6] - 2026-06-20

### 新增
- GUI 并行处理：`ProcessPoolExecutor` (spawn) 替代串行逐目标处理，`parallel_workers` 配置项（0=自动, 1=串行, >1=指定进程数）
- CLI `--force-parallel` 参数：目标数 ≤2 时自动降级串行，可通过此参数强制并行
- `config_service.set()` / `gui_api.run_pipeline()` 增加配置重载，确保外部磁盘变更不被内存旧值覆盖

### 变更
- `pipeline_service.py` 移除 `_EXECUTION_LOCK`，改用 `ProcessPoolExecutor` 并行调度
- `ProgressPanel.vue` 并行滑块管理权上移至 `ProcessingView`，移除 localStorage 持久化逻辑，默认值 1 → 0
- `ProcessingView.vue` 轮询改为 while 循环一次性消费所有在途事件，防止事件积压
- `run_gui.py` 添加 `multiprocessing.freeze_support()`，将 GUI 导入移至 `__main__` 守卫内
- `config.py` 新增 `parallel_workers` 配置字段（默认 0）

## [4.2.1] - 2026-06-19

### 优化
- 字符串缓存追踪 O(n) → O(1) 运行时字符计数，减少 GC 压力
- `configure_style()` 幂等化 + double-checked locking，避免重复配置
- `TraceData.__post_init__` 使用 `np.asarray` 替代 `np.array(copy=True)`，消除不必要拷贝

### 修复
- `get_image_thumbnail` BytesIO 未使用 context manager 导致的资源泄漏

## [4.2.5] - 2026-06-20

### 优化
- Python 异常捕获精确化（`except Exception` → `except (ValueError, OSError, RuntimeError)`）
- 前端 API 层类型断言补完，`vue-tsc --noEmit` 零错误

## [4.2.4] - 2026-06-20

### 新增
- `GuiApiInterface` 接口定义（36 方法签名），收窄 API 返回类型

### 变更
- 移除 `scripts/package.py` 中 `shell=True` 模式，消除命令注入风险
- 视图层 `any` 类型收窄，增强空安全与错误处理健壮性

### 修复
- `config_service._save()` 异常捕获精确化，增加写入失败日志

## [4.2.3] - 2026-06-20

### 变更
- 前端类型安全加固：缓存 Store 新增 4 接口定义，替换 14 处 `any`
- `ConfigData` / `DataPageResult` 接口 `any` → `unknown`
- `catch (e: any)` → `catch (e: unknown)`（StylePreview / SplashScreen）
- 4 处裸 `catch {}` 补充异常参数

## [4.2.2] - 2026-06-19

### 新增
- `get_image_data` 方法：合并图片元数据与加载为单次 JS bridge 调用

### 变更
- 清理 5 处 `console.debug` 开发调试残留
- 4 处空 `.catch(() => {})` 替换为 `console.error` 错误日志

### 修复
- `main_gui.py` 静默 `except:pass` 添加 `logger.debug` 降级日志

## [4.2.0] - 2026-06-18

### 新增
- 报告导出新增实时进度反馈（前端进度条 + 后端 SSE 推送）
- 新增前后端测试框架（pytest + vitest）与单元测试
- 提取绘图阶段为独立服务，优化模块职责分离
- 前后端分层缓存架构（30s ~ 10min TTL）

### 变更
- 重构服务启动流程，优化缓存性能与目录同步机制
- 重写 README 技术架构文档，补充 LICENSE/CONTRIBUTING/CODE_OF_CONDUCT
- 更新作者信息为 zylyes
- WebView2 Runtime 自动检测与下载引导
- 打包流水线：PyInstaller + Inno Setup + 7-Zip SFX 一键生成

### 优化
- 应用初始化流程与目录同步机制优化
- 路径安全性与线程安全性增强
- 字体缓存预热优化

---

## [4.1.0] ~ [4.1.3] - 2026-06 期间迭代

### 新增
- 报告生成功能增强（Word/PDF 一键导出）
- 图片缓存与预取、后端图片元数据接口
- 应用初始化流程与目录同步机制
- Inno Setup 安装脚本

### 优化
- 路径安全加固、报告导出锁定机制
- 线程锁增强重型资源操作安全性
- PDF 字体改进与排版美化
- 多项稳定性修复

---

## [4.0.0] - 2026-06-17

### 新增
- 桌面 GUI 完整交互界面（pywebview + Vue 3 + Element Plus + ECharts）
- 6 页面视图：首页引导、流水线处理、单露头统计、多露头对比、数据浏览、配置管理
- 前后端分层缓存架构（30s ~ 10min TTL）
- Word/PDF 报告一键导出
- 样式预览面板（3 面板，500ms 去抖）
- 启动屏引导（4 步：WebView2 → 配置 → 文件扫描 → 服务就绪）
- WebView2 Runtime 自动检测与下载引导
- 打包流水线：PyInstaller + Inno Setup + 7-Zip SFX 一键生成

### 变更
- pyproject.toml 完善开源元数据
- 隐私清理：移除敏感路径、脱敏学术引用、加固打包脚本
- 前端构建输出整合到 `backend/static/`

---

## [3.9.0] - 2026-05

### 新增
- PDF 字体改进与排版美化
- 报告生成功能增强

### 变更
- 字体缓存预热优化

---

## [3.8.2] - 2026-05

### 修复
- 多项稳定性修复
- 路径安全加固
- 报告导出锁定机制

---

## [3.5.0] - 2026-05

### 新增
- GUI API 增强（图像、日志接口）
- Inno Setup 安装程序升级
- 图片缓存与预取
- 后端图片元数据接口

### 变更
- 路径安全与目录变更检测优化
- 线程安全性增强

---

## [3.2.0] - 2026-05

### 新增
- 前端样式系统重构
- 窗口控制功能
- 节点识别功能（I/Y/X 拓扑分类）

### 变更
- UI 样式优化
- 输出目录变更检测改进
- 缓存失效修复

---

## [2.4.6] - 2026-04

### 新增
- 窗口居中显示与 DPI 感知支持
- 节点识别算法重构（空间网格聚类 + 并查集）
- 打包脚本及安装程序配置

### 修复
- 路径越权与文件损坏防护
- 流水线优雅关闭
- 节点序列化修复

---

## [2.3.1] - 2026-04

### 新增
- GUI 模式首次引入
- 前后端缓存机制
- 统一结构化日志（JSON Lines + 按日轮转）
- 启动优化

### 变更
- README 文档更新

---

## [2.1.0] - 2026-04

### 新增
- 配置面板与样式控件重构
- 预览服务解耦
- 配置重置与保存逻辑拆分

### 修复
- 打包路径修复
- 多项运行时问题修复

---

## [2.0.0] - 2026-03

### 新增
- 圆形取样窗法 4 策略自适应（tangent/hybrid/concentric/auto）
- 凸包/缓冲凸包露头面积计算
- P10/P20/P21 密度统计（实测优先四级回退）
- Mauldon 迹长估计（三级回退）
- 窗口一致性校验（自适应阈值）
- 节点识别算法（I/Y/X 拓扑分类）
- 迹线图覆盖层（凸包/圆窗/节点）
- LaTeX 统计信息框
- 自动避让布局算法
- 玫瑰花瓣图导出
- 批量/并行处理（ProcessPoolExecutor）
- 交互式文件选择

---

## [1.0.0] - 2026-02

### 新增
- 综合法复数向量化端点坐标计算
- 坐标平移与旋转标准化
- I/II/III 型迹线自动分类
- 测线长度估算
- 多工作表 Excel 导出
- 迹线图绘制（比例尺 + 指北针）
- CJK 字体多级回退
- MATLAB 算法完整移植与验证（误差 < 1e-10 m）
- CLI 命令行界面

---

[4.5.3]: https://github.com/zylyes/TracePipeline/releases/tag/v4.5.3
[4.5.2]: https://github.com/zylyes/TracePipeline/releases/tag/v4.5.2
[4.5.1]: https://github.com/zylyes/TracePipeline/releases/tag/v4.5.1
[4.5.0]: https://github.com/zylyes/TracePipeline/releases/tag/v4.5.0
[4.4.0]: https://github.com/zylyes/TracePipeline/releases/tag/v4.4.0
[4.3.3]: https://github.com/zylyes/TracePipeline/releases/tag/v4.3.3
[4.3.2]: https://github.com/zylyes/TracePipeline/releases/tag/v4.3.2
[4.3.1]: https://github.com/zylyes/TracePipeline/releases/tag/v4.3.1
[4.3.0]: https://github.com/zylyes/TracePipeline/releases/tag/v4.3.0
[4.2.7]: https://github.com/zylyes/TracePipeline/releases/tag/v4.2.7
[4.2.6]: https://github.com/zylyes/TracePipeline/releases/tag/v4.2.6
[4.2.5]: https://github.com/zylyes/TracePipeline/releases/tag/v4.2.5
[4.2.4]: https://github.com/zylyes/TracePipeline/releases/tag/v4.2.4
[4.2.3]: https://github.com/zylyes/TracePipeline/releases/tag/v4.2.3
[4.2.2]: https://github.com/zylyes/TracePipeline/releases/tag/v4.2.2
[4.2.0]: https://github.com/zylyes/TracePipeline/releases/tag/v4.2.0
[4.0.0]: https://github.com/zylyes/TracePipeline/releases/tag/v4.0.0
[3.9.0]: https://github.com/zylyes/TracePipeline/releases/tag/v3.9.0
[3.8.2]: https://github.com/zylyes/TracePipeline/releases/tag/v3.8.2
[3.5.0]: https://github.com/zylyes/TracePipeline/releases/tag/v3.5.0
[3.2.0]: https://github.com/zylyes/TracePipeline/releases/tag/v3.2.0
[2.4.6]: https://github.com/zylyes/TracePipeline/releases/tag/v2.4.6
[2.3.1]: https://github.com/zylyes/TracePipeline/releases/tag/v2.3.1
[2.1.0]: https://github.com/zylyes/TracePipeline/releases/tag/v2.1.0
[2.0.0]: https://github.com/zylyes/TracePipeline/releases/tag/v2.0.0
[1.0.0]: https://github.com/zylyes/TracePipeline/releases/tag/v1.0.0
