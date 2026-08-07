# Orchestrator 专属记忆

## 2026-08-07 v4.5.6 发布任务记录
- **版本判断**：patch 级小版本更新（4.5.5 → 4.5.6），因变更仅含打包脚本构建修复、gitignore 整理与文档，无功能/API 变更
- **执行**：自己完成版本号同步（5 文件 10 处）+ 文档更新（README/CHANGELOG/RELEASE_NOTES），委派 @fast-generic 提交推送（commit e2e9df0，21 文件 +279/-58，含 .qoder 重命名与 docs/memory/ 新文件）
- **经验**：package-lock.json 顶部有两处独立缩进的 version 字段（2 空格 + 6 空格），replaceAll 需分别处理；README 版本历史表 v4.5.5 漏更新，本次一并补齐
- **注意**：TracePipeline-setup.iss 被 git 忽略未跟踪，但需手动同步版本号（发行流程约定）

## 2026-08-07 系统性清理任务记录- **用户决策**（后续同类任务直接引用）：
  - `.venv/` 保留；历史发行版 exe 移入 `dist/archive/` 而非删除
  - `.qoder/` 完全保留（含 git 跟踪状态，不加入 .gitignore）
  - 删除：`output/`、`logs/2026-06-23/`、`.slim/deepwork/`、全部 cache/preview 预览图、全部 __pycache__、.pytest_cache/.ruff_cache、build/、egg-info、backend/static（重建）、.codeartsdoer 冗余
  - `dist/TracePipeline/` 运行目录用户保留（但打包 rmtree 会重建，属脚本预期行为）
  - 产物布局：保持根目录 dist/build/output/reports 现状，不做大重构
- **已验证**：pytest 200 passed；vite build 成功；package.py 全流程打包成功（Setup 130.3MB / Portable 124.4MB）

## 经验教训
1. PowerShell `Remove-Item -LiteralPath` **不支持通配符**（`cache/preview/*` 静默失败，需先 `Get-ChildItem` 枚举再逐个删）
2. PyInstaller onedir 模式打包会在 dist/ 根目录残留无版本号 `TracePipeline.exe`（EXE 阶段中间产物，COLLECT 后根目录副本不清理）——已在 package.py run_pyinstaller() 修复（打包后 unlink）
3. 打包流程会重新生成 build/、__pycache__、.pytest_cache——验证完需收尾清理以保持整洁
4. explorer 子代理无 shell 权限时拿不到文件大小/时间戳，需在 prompt 中允许其用 PowerShell（本次给了 bash 权限但 explorer 受限，后续直接自己用 bash 复核关键条目）

## 待办提示
- .qoder/repowiki 的 git D/M 状态（用户选择保留未处理），如未来用户决定清理需 `git rm -r --cached .qoder` 并加入 .gitignore（git 写操作走 @fast-generic）
