---
kind: build_system
name: Python + PyInstaller 桌面应用打包体系
category: build_system
scope:
    - '**'
source_files:
    - pyproject.toml
    - TracePipeline.spec
    - scripts/package.py
    - frontend/package.json
    - run_gui.py
    - trace_pipeline/__init__.py
    - requirements.txt
---

## 构建系统概览

TracePipeline 采用 **Python setuptools + PyInstaller** 的桌面应用打包方案，前端基于 Vue3 + Vite 独立构建，最终通过 Inno Setup 生成 Windows 安装程序、7-Zip SFX 生成便携版。整个流程由 `scripts/package.py` 统一编排。

### 1. 核心工具链与依赖

- **Python 包管理**: `pyproject.toml` 使用 setuptools 后端，声明 Python ≥3.10，依赖通过 `[project.dependencies]` 集中管理
- **前端构建**: `frontend/` 目录使用 Vite + Vue3 + TypeScript，`package.json` 中 `build` 脚本执行 `vue-tsc --noEmit && vite build`
- **桌面打包**: PyInstaller 通过 `TracePipeline.spec` 规格文件将 GUI 入口 `run_gui.py` 打包为独立可执行文件
- **安装包生成**: Inno Setup 6（ISCC.exe）编译 .iss 脚本生成标准安装器
- **便携版生成**: 7-Zip SFX 模块拼接自解压 EXE

### 2. 关键文件与职责

| 文件 | 作用 |
|------|------|
| `pyproject.toml` | Python 包元数据、依赖声明、动态版本读取（从 `trace_pipeline.__version__`） |
| `TracePipeline.spec` | PyInstaller 打包规格，显式声明 hiddenimports 以覆盖所有惰性加载的子模块 |
| `scripts/package.py` | 主打包脚本，串联前端构建 → PyInstaller → Inno Setup → 7-Zip 四步流水线 |
| `frontend/package.json` | 前端依赖与构建脚本定义 |
| `run_gui.py` | GUI 入口，设置 DPI 感知、强制 matplotlib Agg 后端、启动 pywebview |
| `requirements.txt` | 自动生成，由 package.py 从 pyproject.toml 解析生成，供 pip 环境安装 |

### 3. 构建流水线

```
python scripts/package.py
├── [步骤 0.5] generate_requirements() — 从 pyproject.toml 提取 dependencies 生成 requirements.txt
├── [步骤 0]   build_frontend()         — npm install && npm run build → backend/static/
├── [步骤 1]   run_pyinstaller()        — PyInstaller -m TracePipeline.spec → dist/TracePipeline/
├── [步骤 2]   generate_iss() + run_inno_setup() → dist/TracePipeline-Setup-v{ver}.exe
└── [步骤 3]   build_portable_sfx()     — 7z 压缩 + SFX 拼接 → dist/TracePipeline-Portable-v{ver}.exe
```

支持 `--skip-frontend`、`--skip-installer`、`--skip-portable`、`--gen-requirements` 等参数选择性跳过步骤。

### 4. 版本管理策略

版本号单一来源：`trace_pipeline/__init__.py` 中的 `__version__ = "4.5.5"`。PyInstaller spec 和打包脚本均通过正则解析该文件获取版本号，确保 Python 包、GUI 应用、安装包三者版本一致。

### 5. 设计决策与约定

- **惰性导入**: `trace_pipeline` 包使用 `__getattr__` 实现按需加载子模块，避免导入时触发 matplotlib/pywebview 等重型依赖；这要求 PyInstaller spec 必须显式声明所有可能被 `importlib.import_module` 加载的隐藏导入
- **前端产物内嵌**: Vite 构建输出到 `backend/static/`，被 PyInstaller 作为 data 文件打包进 EXE，运行时由 pywebview 本地加载
- **Windows 平台优先**: 打包目标明确限定为 Windows（`Operating System: Microsoft :: Windows`），DPI 感知、Inno Setup、7-Zip 均为 Windows 生态工具
- **虚拟环境约束**: 打包脚本硬编码 `.venv/Scripts/python.exe`，要求开发者在仓库根目录创建并激活 venv

### 6. 开发者注意事项

- 修改 `pyproject.toml` 的 dependencies 后需运行 `python scripts/package.py --gen-requirements` 同步 `requirements.txt`
- 新增 `trace_pipeline` 子模块若通过 `importlib.import_module` 动态导入，必须在 `TracePipeline.spec` 的 `hiddenimports` 中补充，否则 PyInstaller 会遗漏
- 前端资源变更需先执行 `npm run build` 或让打包脚本自动构建，否则 GUI 无法加载新页面
- Inno Setup 和 7-Zip 路径可通过环境变量 `ISCC_EXE`、`SEVEN_ZIP` 或命令行参数覆盖默认查找逻辑