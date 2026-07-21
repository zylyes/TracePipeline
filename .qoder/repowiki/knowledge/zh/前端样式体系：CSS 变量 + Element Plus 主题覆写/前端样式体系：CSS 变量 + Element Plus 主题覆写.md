---
kind: frontend_style
name: 前端样式体系：CSS 变量 + Element Plus 主题覆写
category: frontend_style
scope:
    - '**'
source_files:
    - frontend/src/styles/tokens.css
    - frontend/src/styles/fonts.css
    - frontend/src/styles/element-global.css
    - frontend/src/main.ts
    - frontend/vite.config.ts
    - frontend/package.json
---

## 系统概述
TracePipeline 的前端基于 Vue 3 + Vite + Element Plus，采用「CSS 自定义属性（变量）+ 组件库主题覆写」的轻量级样式方案。所有视觉规范集中在 `frontend/src/styles/` 三个核心文件中，通过全局 CSS 变量形成统一的设计令牌（Design Tokens），并在此基础上覆盖 Element Plus 默认样式以达成一致的“地质科学”风格。

## 关键文件与包
- `frontend/src/styles/tokens.css` — 设计令牌中心：颜色、阴影、圆角、间距、动画、断点、图表色板等全部以 `--tp-*` 前缀的 CSS 变量声明，同时覆写 `--el-*` 变量使 Element Plus 自动继承。
- `frontend/src/styles/fonts.css` — 字体系统：定义中英文混排字体栈（Times New Roman + SimHei/SimSun），并通过 `.tp-font-*` 工具类统一标题、正文、数据、等宽四类排版。
- `frontend/src/styles/element-global.css` — Element Plus 全局样式覆写：按钮、表格、对话框、消息提示、分页、抽屉等组件均按 tokens 重新着色、加圆角与阴影。
- `frontend/src/main.ts` — 入口按顺序引入三套样式，确保变量先于组件样式生效。
- `frontend/vite.config.ts` — 构建配置：输出到 `backend/static`，对 Element Plus / ECharts / Vue 生态进行 manualChunks 拆分；启用 SCSS 预处理器。
- `frontend/package.json` — 依赖：Element Plus 2.6、ECharts 5.5、Pinia、Vue Router、Vitest、Sass 等。

## 架构与约定
1. **Token 优先**：所有颜色、尺寸、动效均以 `--tp-*` 变量集中管理，组件样式只引用变量，禁止硬编码色值或像素值。
2. **Element Plus 主题覆写**：在 `:root` 中直接覆写 `--el-color-*`、`--el-border-radius-*`、`--el-box-shadow-*` 等变量，配合 `element-global.css` 中的类选择器完成细节定制。
3. **命名空间**：项目级工具类统一使用 `tp-` 前缀（如 `.tp-card`、`.tp-glass`、`.tp-skeleton`、`.tp-fade-in`），避免与第三方库冲突。
4. **字体分层**：标题用黑体、正文用宋体、数据用 Times New Roman，通过 `font-family` 组合栈实现中英文混排自动回退，无需外部字体加载。
5. **动效与可访问性**：提供 `tp-pulse`、`tp-shimmer`、`tp-scale-in`、`tp-slide-left` 等通用动画；通过 `@media (prefers-reduced-motion)` 尊重系统减少动效偏好。
6. **构建产物**：Vite 将打包结果输出至 `backend/static/assets/`，由 Python 后端静态服务直接托管，无需独立 Web 服务器。

## 开发者应遵循的规则
- 新增颜色/尺寸/阴影时，先在 `tokens.css` 的 `:root` 中声明 `--tp-*` 变量，再在组件中使用，不要直接写十六进制值。
- 需要复用 UI 片段时，优先使用已有的 `tp-*` 工具类（卡片、骨架屏、扫描线、毛玻璃等），必要时扩展同类命名空间。
- 修改 Element Plus 组件外观时，在 `element-global.css` 中以类选择器覆写，保持与 token 变量的绑定。
- 字体相关样式一律走 `fonts.css` 定义的变量与工具类，不自行添加新的字体族。
- 动画统一使用 `--tp-duration-*` 和 `--tp-easing*` 变量，保证节奏一致；新动画需考虑 `prefers-reduced-motion` 降级。
- 图表配色使用 `--tp-chart-c1..c10` 系列变量，保持地质语义色的一致性。