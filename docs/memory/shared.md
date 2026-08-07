# TracePipeline 项目共享记忆

## 项目概况
- TracePipeline v4.5.6（2026-08-07 维护补丁）：Windows 桌面应用，Python（PyInstaller 打包）+ Vue 3（Vite）前端 + Python.NET 桌面壳
- 版本号唯一来源：`trace_pipeline/__init__.py` 的 `__version__`
- 测试：`pytest tests/`（当前 200 个用例全部通过）；前端测试：vitest（frontend/tests/）

## 版本发布同步清单（v4.5.6 确认）
- 版本号同步文件：`trace_pipeline/__init__.py`、`frontend/package.json`、`frontend/package-lock.json`（2 处）、`TracePipeline-setup.iss`（4 处：AppVersion/OutputBaseFilename/UninstallDisplayName/VersionInfoVersion）、`README.md`（徽章/维护状态/版本历史表）
- **`TracePipeline-setup.iss` 被 .gitignore 忽略且未被 git 跟踪**，但磁盘上仍手动同步版本号（历史一致）
- 文档同步：README.md、CHANGELOG.md（Keep a Changelog）、RELEASE_NOTES.md（顶部插入新段）
- 提交风格：`🔖 release: vX.Y.Z ...`；发行版发布流程：版本同步 → 文档 → git add -A + commit + push（git 写操作走 @fast-generic）
- 历史坑：README 版本历史表最高行曾在 v4.5.5 发布时漏更新，v4.5.6 时补上（更新时注意检查表头是否含最新版）

## 构建与产物布局（2026-08-07 清理后确认的约定）
- **构建链路**：`frontend npm run build` → `backend/static/`（vite outDir）→ `scripts/package.py` PyInstaller → `dist/TracePipeline/` → Inno Setup（`TracePipeline-Setup-vX.Y.Z.exe`）/ 7-Zip SFX（`TracePipeline-Portable-vX.Y.Z.exe`）
- **目录边界**：源码（backend、frontend、trace_pipeline、tests、scripts）｜数据（input、output、reference、reports、logs、cache）｜构建产物（build、dist），全部产物目录已被 .gitignore 忽略
- **dist/ 规则**：根目录只放最新版本产物；历史发行版 exe 移入 `dist/archive/`（27 个 v4.0.0~v4.5.5 备份）；`dist/TracePipeline/` 是 onedir 运行目录
- **package.py 已有清理逻辑**：打包前 rmtree 旧 `dist/TracePipeline/`、清理 `*.7z`/`*.sfxcfg`；2026-08-07 补充：打包后自动清理 PyInstaller EXE 中间产物 `dist/TracePipeline.exe`（根目录副本）
- **logs/ 归档策略**：按日期 zip 并删除源文件；`reports/` 目前为空占位

## 工具辅助目录状态（2026-08-07 确认）
- `.venv/`、`frontend/node_modules/`：保留（开发必需）
- `.arts/settings.json`、`.codeartsdoer` 配置（AGENTS.md/package.json/mcp）、`.opencode/playbooks/`：保留
- `.qoder/repowiki/`：AI 自动生成文档，**被 git 跟踪**（用户决定保留，不处理）；其 git status 的 D/M 状态属预期，勿擅动
- `.slim/`：历史会话记录已清空（deepwork 产物），目录本身被 .gitignore 忽略

## 用户偏好
- 中文交流；破坏性操作前先出清单并确认
- 代码风格：ruff（py310、line-length 100），行内直接回答不奉承
