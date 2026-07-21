# MATLAB 参考代码

> 本目录仅作历史参照，不参与构建与运行。

## 来源与授权状态

本目录下的 `.m` 文件仅作为算法迁移和历史对照材料保留，**不参与 Python 包、
PyInstaller 分发目录、安装包或便携版构建**。

这些 MATLAB 文件目前没有独立的版权/许可证头。除非已经确认其为项目作者原创，
或已经取得原作者明确授权，否则不要将这些文件视为本项目 MIT 许可源码再分发。
后续应按实际情况二选一处理：

- 确认为原创或已获授权：在每个 `.m` 文件头补充版权、来源和许可证声明；
- 无法确认授权：从公开仓库中移除这些参考文件。

## 文件清单

| 文件 | 作用 |
|---|---|
| `A_outcrop_0map_coordinate.m` | 单露头处理：计算端点坐标 + 绘图 + 导出（不做旋转） |
| `A_outcrop_0map_rotate.m`     | 单露头处理：在前者基础上额外做走向旋转 |
| `Coordinate.m`                | 核心函数：按左/右/双侧三种情况计算单条迹线端点（复数向量法） |

## MATLAB ↔ Python 函数对应

| MATLAB | Python |
|---|---|
| `Coordinate(...)` switch 三分支 | `trace_pipeline.geology.endpoints._compute_left_only / _right_only / _bilateral`（向量化） |
| 倾向→走向 `if/elseif` 链 | `trace_pipeline.geology.angles.dip_to_strike` |
| `rada/rade` 半平面判定 | `trace_pipeline.geology.angles.fold_to_halfplane` |
| 平移到正象限 | `trace_pipeline.geology.transforms.shift_to_positive` |
| 旋转 + 平移 | `trace_pipeline.geology.transforms.rotate_and_shift` |
| 端点 → NaN 分隔绘图序列 | `trace_pipeline.plotting.trace_plot.segments_to_xy` |
| `xlsread` / `writematrix` | `trace_pipeline.io.excel_reader` / `excel_writer` |

## 已修正的 MATLAB Bug

### 旋转角 if 链不可达（`A_outcrop_0map_rotate.m:68-76`）

```matlab
if  ang0 <=360                            % ← 永远为真
    rotate_angle=-(360-ang0)*pi/180;
elseif ang0 <=270                         % 不可达
    rotate_angle=(ang0-180)*pi/180;
elseif ang0 <=180                         % 不可达
    rotate_angle=-(180-ang0)*pi/180;
else ang0<=90;                            % 不可达
    rotate_angle=ang0;
end
```

实际效果始终为 `rotate_angle = (ang0-360)·π/180`。

Python 版采用 `fold_strike_angle` 的正确语义（折叠到 [-90°, 90°]），使旋转后测线最贴近水平轴。详见 `trace_pipeline/geology/angles.py` 的 docstring。

## 迹线长度定义差异

- **MATLAB**：`traceLengths = M(:,5) + M(:,7)`，即 `r5 + r7`（沿测段累加）
- **Python**：默认输出**两列**，兼顾两种语义：
  - `端点距离` —— `hypot(dx, dy)`（端点间欧氏距离）
  - `测段长度(r5+r7)` —— 与 MATLAB 一致

## Python 版的新增能力

- 批量 / 并行处理（`-p N`）
- 玫瑰花瓣图（`render_rose_plot`）
- 交互式选择（`-I`）、试运行（`-n`）、列出文件（`-l`）
- 配置 JSON + CLI 覆盖
- 数据校验、类型注解、单元测试
