# v4.2.0

**2026-06-18**

> 基于 v4.0.0 以来的提交记录整理，涵盖 v4.1.0–v4.2.0 迭代周期。

## 高亮

- **报告导出实时进度反馈** — 后端逐阶段推送进度事件，前端进度条轮询展示，用户可清晰感知导出过程
- **前后端测试框架落地** — 引入 Vitest + jsdom 前端测试、pytest 后端冒烟测试，构建质量保障基础
- **绘图阶段解耦** — `run_pipeline` 中的绘图逻辑提取为独立 `_run_plot_stage` 函数，主函数复杂度显著降低
- **启动提速** — 非核心服务改为懒加载，延迟至 WebView2 检测后初始化，缩短冷启动时间
- **开源就绪** — 重写 README 技术架构文档，补充 LICENSE / CONTRIBUTING / CHANGELOG / CODE_OF_CONDUCT

---

## 新特性

- **报告导出进度反馈** — 后端 `generate` / `generate_reports_zip` 新增 `progress_callback`，通过线程安全 `deque` 队列逐阶段推送进度；前端 `DevPanel` / `StatisticsView` 新增 `ElProgress` 进度条及轮询逻辑 ([34c5a90](https://github.com/zylyes/TracePipeline/commit/34c5a90))
- **绘图阶段解耦** — 将 `run_pipeline` 中的绘图逻辑提取为独立 `_run_plot_stage`，降低主函数圈复杂度，提升可测试性 ([f32762f](https://github.com/zylyes/TracePipeline/commit/f32762f))

## 性能改进

- **服务启动优化** — `GuiApi` 非核心服务改为懒加载，延迟初始化至 WebView2 检测之后，缩短冷启动时间 ([f32762f](https://github.com/zylyes/TracePipeline/commit/f32762f))
- **缓存策略升级** — 统计缓存引入 LRU 淘汰机制，TTL 缓存采用批量驱逐策略，减少 `set` 操作锁竞争 ([f32762f](https://github.com/zylyes/TracePipeline/commit/f32762f))
- **全局异常处理优化** — 消除裸 `except:pass` 语句，统一替换为带日志的异常处理，提升可观测性 ([f32762f](https://github.com/zylyes/TracePipeline/commit/f32762f))

## 测试

- **前端测试** — 集成 Vitest + jsdom 环境，新增 cache / pipeline Store 单元测试、pywebview API 层及 Store 模块 JSDoc 类型文档 ([6afbf54](https://github.com/zylyes/TracePipeline/commit/6afbf54))
- **后端测试** — 新增绘图模块（trace_plot / rose_plot）冒烟测试与 ReportService 缓存逻辑测试 ([6afbf54](https://github.com/zylyes/TracePipeline/commit/6afbf54))

## 文档

- **README 全面重写** — 新增技术栈与系统架构、四层架构表、详细项目结构，v4.0.0 → v4.1.1 → v4.2.0 版本号同步更新 ([6cfb0aa](https://github.com/zylyes/TracePipeline/commit/6cfb0aa))
- **开源标准化** — 补充 LICENSE（MIT）、CONTRIBUTING、CHANGELOG、CODE_OF_CONDUCT，统一项目元数据 ([363c60c](https://github.com/zylyes/TracePipeline/commit/363c60c))

## 杂项

- 降低视图层重复调用日志级别 `warn` → `debug`，减少控制台噪音 ([6cfb0aa](https://github.com/zylyes/TracePipeline/commit/6cfb0aa))
- 补齐 `DevPanel` / `ImageModal` 缺失的用户错误提示 ([6cfb0aa](https://github.com/zylyes/TracePipeline/commit/6cfb0aa))
- `paths.py` 以 `@cache` 替代模块级全局变量，简化状态管理 ([6cfb0aa](https://github.com/zylyes/TracePipeline/commit/6cfb0aa))
- 修复超时任务 worker 进程未终止导致的资源泄漏 ([f32762f](https://github.com/zylyes/TracePipeline/commit/f32762f))
- 更新作者信息为 zylyes ([9c4e48a](https://github.com/zylyes/TracePipeline/commit/9c4e48a))

---

**完整提交历史**: [`v4.0.0...v4.2.0`](https://github.com/zylyes/TracePipeline/compare/v4.0.0...v4.2.0)
