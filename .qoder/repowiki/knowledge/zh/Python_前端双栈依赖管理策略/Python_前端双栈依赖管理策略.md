---
kind: dependency_management
name: Python/前端双栈依赖管理策略
category: dependency_management
scope:
    - '**'
source_files:
    - pyproject.toml
    - requirements.txt
    - TracePipeline.spec
    - frontend/package.json
    - frontend/package-lock.json
    - .codeartsdoer/package.json
---

TracePipeline 采用 Python + Vue 3 双栈架构，分别使用不同的依赖管理系统：

## Python 后端依赖管理
- **主声明文件**：`pyproject.toml`（PEP 621 规范），使用 setuptools 作为构建后端
- **运行时依赖**：通过 `[project].dependencies` 声明，要求 Python >=3.10，核心依赖包括 numpy、pandas、matplotlib、scipy、shapely、pywebview 等科学计算与 GUI 库
- **可选依赖组**：`[project.optional-dependencies]` 中定义 `dev` 组，包含 ruff、mypy、pytest 等开发工具
- **入口点**：通过 `[project.scripts]` 暴露 `trace-pipeline` CLI 命令
- **requirements.txt**：由 pyproject.toml 自动生成（文件头注释明确标注 DO NOT EDIT MANUALLY），用于兼容传统 pip install -r 场景
- **版本锁定**：未发现 .lock 文件，依赖使用宽松版本约束（>=X.Y）
- **虚拟环境**：项目根目录存在 `.venv`，但未被 git 跟踪
- **打包集成**：`TracePipeline.spec`（PyInstaller 规格）显式列出所有动态导入的模块，确保打包时包含 scipy、shapely、openpyxl 等第三方库的子模块

## 前端依赖管理
- **声明文件**：`frontend/package.json`，使用 npm/yarn/pnpm 生态
- **生产依赖**：Vue 3、Element Plus、ECharts、Pinia、Vue Router 等 UI 与可视化库
- **开发依赖**：Vite、TypeScript、vitest、vue-tsc 等构建与测试工具
- **版本锁定**：`frontend/package-lock.json` 已提交到版本控制，确保构建一致性（package.json 中有注释强调）
- **私有包**：`.codeartsdoer/package.json` 单独管理 CodeArtsDoer 插件依赖

## 构建与打包流程
- PyInstaller 通过 `TracePipeline.spec` 将 Python 应用打包为独立 Windows 可执行文件
- 前端静态资源经 Vite 构建后输出到 `backend/static/assets/`，被 PyInstaller 一并打包
- README.md 提供多种安装方式：pip、conda/mamba、uv sync 等

## 开发者约定
- 修改 Python 依赖应更新 `pyproject.toml`，而非直接编辑 `requirements.txt`
- 前端依赖变更需提交 `package-lock.json` 以保证可重复构建
- 新增动态导入的第三方子模块需在 `TracePipeline.spec` 的 `hiddenimports` 中补充