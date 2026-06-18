# 贡献指南

感谢你对 TracePipeline 的关注！本文档将帮助你了解如何参与项目开发。

## 目录

- [行为准则](#行为准则)
- [如何贡献](#如何贡献)
- [开发环境搭建](#开发环境搭建)
- [代码规范](#代码规范)
- [提交指南](#提交指南)
- [测试](#测试)
- [Issue 指南](#issue-指南)

## 行为准则

本项目遵循 [贡献者行为准则](CODE_OF_CONDUCT.md)。参与即表示你同意遵守其条款。

## 如何贡献

- **报告 Bug**：通过 GitHub Issues 提交，请使用 Bug 报告模板
- **功能建议**：通过 GitHub Issues 提交，请描述使用场景
- **代码贡献**：Fork 仓库 → 创建分支 → 提交 PR
- **文档改进**：文档同样欢迎贡献，包括 README、代码注释等

## 开发环境搭建

### 前置要求

- Python >= 3.10
- Node.js >= 18（仅 GUI 前端构建需要）
- Git

### 安装

```bash
# 克隆仓库
git clone https://github.com/zylyes/TracePipeline.git
cd TracePipeline

# 创建虚拟环境
python -m venv .venv
.venv\Scripts\Activate.ps1   # Windows PowerShell
# 或 source .venv/bin/activate  # Linux/macOS

# 安装依赖（含开发依赖）
pip install -e ".[dev]"

# 构建前端（GUI 模式需要）
cd frontend
npm install
npm run build
cd ..
```

### 运行

```bash
# CLI 模式
python run_trace_pipeline.py

# GUI 模式
python run_gui.py
```

## 代码规范

### Python

- 使用 [ruff](https://github.com/astral-sh/ruff) 进行代码检查：
  ```bash
  ruff check .
  ```
- 使用 [mypy](https://github.com/python/mypy) 进行类型检查：
  ```bash
  mypy trace_pipeline/
  ```
- 行宽限制：100 字符
- 目标 Python 版本：3.10
- 遵循项目现有的代码风格和模块组织方式

### 前端

- 使用 TypeScript
- 遵循 Vue 3 Composition API 风格
- 使用 ESLint + Prettier（配置在 `frontend/` 中）

## 提交指南

### 分支命名

- `feat/xxx` — 新功能
- `fix/xxx` — Bug 修复
- `docs/xxx` — 文档更新
- `refactor/xxx` — 重构
- `chore/xxx` — 构建/工具

### Commit Message

遵循约定式提交格式：

```
<type>(<scope>): <description>

[optional body]
```

类型包括：`feat`、`fix`、`docs`、`style`、`refactor`、`test`、`chore`、`perf`

### Pull Request 流程

1. Fork 本仓库
2. 创建你的特性分支 (`git checkout -b feat/amazing-feature`)
3. 提交你的更改 (`git commit -m 'feat: add amazing feature'`)
4. 推送到分支 (`git push origin feat/amazing-feature`)
5. 打开 Pull Request，描述变更内容和原因

PR 合并前需要：
- 通过 ruff 和 mypy 检查
- 通过所有测试
- 至少一位维护者审核通过

## 测试

```bash
# 运行全部测试
pytest

# 运行测试 + 覆盖率
pytest --cov --cov-report=term --cov-report=html

# 运行特定测试文件
pytest tests/test_angles.py
```

测试文件位于 `tests/` 目录，覆盖核心计算模块、I/O 层、GUI 服务等。

## Issue 指南

### 提交 Bug 报告时请包含：

- 操作系统和 Python 版本
- 复现步骤
- 期望行为 vs 实际行为
- 相关日志（`logs/` 目录下的 JSON Lines 文件）

### 提交功能建议时请说明：

- 使用场景
- 期望的交互方式
- 是否有参考实现

## 项目结构

参见 [README.md](README.md#目录结构) 中的完整目录说明。

## 许可证

贡献即表示你同意将代码以 [MIT 许可证](LICENSE) 授权。
