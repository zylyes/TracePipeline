---
kind: configuration_system
name: TracePipeline 配置系统：JSON 文件 + CLI 覆盖 + GUI 持久化
category: configuration_system
scope:
    - '**'
source_files:
    - trace_pipeline/config.py
    - config.example.json
    - backend/services/config_service.py
    - backend/gui_api.py
    - trace_pipeline/cli/args.py
    - frontend/src/stores/config.ts
    - pyproject.toml
---

## 1. 系统与架构概览
TracePipeline 采用「默认值 + JSON 配置文件 + CLI 参数覆盖 + GUI 持久化」的分层配置模型。核心由 trace_pipeline/config.py 提供加载/校验/路径解析能力，backend/services/config_service.ConfigService 作为 config.json 的唯一写入入口（线程安全、原子写回），CLI 通过 apply_cli_overrides 在运行时覆盖配置，GUI 前端通过 PyWebview API 调用后端服务读写配置。

## 2. 关键文件与职责
- trace_pipeline/config.py — 定义 DEFAULT_CONFIG、ConfigDict TypedDict、load_config、validate_config、resolve_io_paths、ensure_workspace_dirs、apply_cli_overrides 等核心函数；负责默认值合并、类型规范化、必填项校验、相对路径转绝对路径。
- config.example.json — 用户可复制为 config.json 的配置模板，字段与 DEFAULT_CONFIG 一一对应。
- backend/services/config_service.py — ConfigService 类封装 config.json 的 reload/get/set/reset/reset_processing/reset_style/_save，使用 threading.RLock 保证并发安全，_save 先写 .tmp 再 replace 实现原子落盘。
- backend/gui_api.py — GuiApi 持有 ConfigService 实例，暴露 get_config/set_config/reset_config/reset_processing_config/reset_style_config/run_pipeline 等 PyWebview 方法；对 run_pipeline 的前端覆盖仅允许白名单 _RUN_OVERRIDE_KEYS = PROCESSING_KEYS | {"style", "parallel_workers"}，禁止覆盖路径/目标字段。
- trace_pipeline/cli/args.py — 定义 CLI 参数并映射到 build_overrides 字典，供 apply_cli_overrides 合并。
- frontend/src/stores/config.ts — Pinia store 封装 loadConfig/saveConfig/resetConfig/resetProcessingConfig/resetStyleConfig/hydrateConfig，通过 api.get_config()/set_config() 与后端交互。
- pyproject.toml — 声明包名、依赖、entry point trace-pipeline = trace_pipeline.cli.main:main。

## 3. 配置分层与合并顺序
1) 默认值：DEFAULT_CONFIG（Python dict）提供所有字段的缺省值。
2) JSON 配置文件：load_config(config_path) 从项目根 config.json 或显式 -c/--config 指定路径加载；若不存在且未显式指定则直接返回默认配置。
3) CLI 覆盖：apply_cli_overrides(cfg, **overrides) 将非 None 的 CLI 参数覆盖进配置，再走 validate_config 重新校验。
4) GUI 运行时覆盖：run_pipeline(targets, config) 仅取白名单键与磁盘配置合并，不持久化到 config.json（除非显式调用 set_config）。
5) 路径解析：validate_config 中 resolve_paths=True 时把 input_dir / output_dir 转为绝对路径，基准目录为 PROJECT_ROOT 或配置文件所在父目录。
6) 工作目录保障：ensure_workspace_dirs 自动创建 input/output/logs 目录（权限异常仅警告）。

## 4. 设计决策与约定
- 单一 JSON 源：所有运行期配置最终落地到项目根 config.json，无环境变量、无 TOML/YAML 多格式支持。
- 严格白名单：validate_config 忽略未知键并告警；run_pipeline 前端覆盖仅限处理参数和样式/并行度。
- 原子持久化：ConfigService._save 使用 .tmp + Path.replace 避免中断损坏配置文件。
- 线程安全：ConfigService 内部用 RLock 保护内存状态，get 返回深拷贝防止外部修改。
- 类型规范：ConfigDict TypedDict + coerce_bool / coerce_scalar_config_fields 统一类型转换。
- GUI 同步：配置变更后 GuiApi._sync_services_from_config 同步 FileService/DataService 路径，并失效相关缓存。

## 5. 开发者应遵循的规则
- 新增配置字段需同时更新 DEFAULT_CONFIG、ConfigDict、config.example.json，并在 validate_config 中补充类型/校验逻辑。
- 通过 ConfigService 读写配置，不要直接操作 config.json 文件。
- GUI 前端如需临时覆盖配置，应在调用 run_pipeline 时传入白名单内字段，而非直接修改持久化配置。
- CLI 新增参数需在 args.py 的 parse_args 与 build_overrides 中成对添加，确保能落入 apply_cli_overrides 的合并流程。
- 涉及路径的字段一律保持字符串形式，交由 validate_config 解析为绝对路径，避免下游模块自行拼接。