---
kind: logging_system
name: TracePipeline 结构化日志系统
category: logging_system
scope:
    - '**'
source_files:
    - trace_pipeline/logging/__init__.py
    - trace_pipeline/logging/core.py
    - trace_pipeline/logging/context.py
    - backend/main_gui.py
    - backend/gui_api.py
    - backend/services/pipeline_service.py
    - trace_pipeline/pipeline.py
---

## 1. 系统概述
TracePipeline 基于 Python 标准库 `logging` 构建统一结构化日志系统，核心位于 `trace_pipeline/logging/` 包。提供 JSON Lines 文件输出、按天目录归档与 zip 打包、跨线程/协程的 request_id 追踪、计时装饰器以及多进程安全写入能力。

## 2. 关键组件
- **JsonFormatter** (`core.py`)：将 LogRecord 序列化为单行 JSON，固定字段包括 `timestamp`(ISO 8601)、`level`、`logger`、`module`、`funcName`、`lineno`、`message`、`request_id`、`exc_info`，并通过 `extra=` 透传扩展字段；内置 `_json_sanitize` 递归清洗 NaN/inf 并调用 `numpy_compat.to_native` 处理 numpy 类型。
- **DailyRotatingJsonHandler** (`core.py`)：继承 `FileHandler`，按 UTC 日期创建子目录（`logs/YYYY-MM-DD/`），主日志文件命名 `run_XXX.jsonl`，worker 子进程使用 `worker_{pid}.jsonl`；支持按大小（默认 50MB）分片（`_part_N.jsonl`），启动时仅主进程执行旧日目录 zip 归档与超过 30 天的清理，通过类级 `threading.Lock` 防止竞态。
- **setup_logging / setup_worker_logging** (`core.py`)：幂等初始化入口。前者为主进程配置 ConsoleHandler + DailyRotatingJsonHandler，并将 `backend` logger 合并到同一套 handler；后者为 `ProcessPoolExecutor` worker 专用，跳过归档逻辑并附带 stderr 精简输出。
- **LogContext / timed / timed_ctx** (`context.py`)：基于 `contextvars.ContextVar` 实现 request_id 传播，`timed` 装饰器与上下文管理器自动记录耗时与异常，额外字段包含 `duration_ms`、`error`、`func`、`module`。

## 3. 架构与约定
- **目录结构**：`logs/<YYYY-MM-DD>/run_001.jsonl`、`logs/<YYYY-MM-DD>/worker_{pid}.jsonl`，历史目录在次日被打包为 `logs/<YYYY-MM-DD>.zip` 后删除。
- **多进程策略**：仅 `MainProcess` 执行归档与清理；子进程通过独立的 `worker_{pid}.jsonl` 写入同一天目录，避免跨进程锁竞争。
- **后端集成**：`backend` logger 被显式合并到 `trace_pipeline` 的 handler 集合，使 GUI 层日志与 CLI 日志共享同一份 run 文件。
- **CLI 兼容层**：`trace_pipeline/cli/main.py` 仍从 `.logging_setup` 导入 `setup_logging`，但根据发布说明该兼容层已被移除，实际应直接导入 `trace_pipeline.logging.setup_logging`。

## 4. 开发者规范
- 模块内获取 logger：`logger = logging.getLogger(__name__)`，级别由 `setup_logging` 全局控制。
- 使用 `LogContext(request_id=...)` 包裹请求作用域，所有日志自动携带 `request_id`。
- 对耗时操作使用 `@timed(logging.INFO, name="xxx")` 装饰器或 `with timed_ctx(logger, ...)` 上下文。
- 通过 `extra={...}` 传递业务字段，避免拼接字符串消息；数值字段需保证可 JSON 序列化。
- 不要在子进程中手动调用归档相关 API，交由 `DailyRotatingJsonHandler.__init__` 中的进程名判断自动处理。
- 控制台输出人类可读格式（`asctime [LEVEL] name: message`），文件输出始终为 JSON Lines，便于后续解析与聚合分析。