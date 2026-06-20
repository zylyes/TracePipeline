# 更新日志

本文件记录 TracePipeline 项目的主要版本变更。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)，版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

---

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
