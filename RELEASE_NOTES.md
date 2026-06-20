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
