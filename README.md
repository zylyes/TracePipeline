# 岩体节理测线坐标与绘图说明

本项目包含 MATLAB 代码的 Python 复现，用于根据测线几何参数与节理数据计算节理端点坐标并绘制裂缝示意图。

## 目录结构
- a_outcrop_0map_coordinate.py：主流程，读取 Excel、转换角度、计算端点、绘制并导出结果。
- coordinate.py：几何计算核心，将测线/节理角度与左右迹长转换为端点坐标。
- A_outcrop_0map_coordinate.m、Coordinate.m：MATLAB 原版参考。

## 运行环境
- Python 3.9+（已在 venv 下验证）
- 依赖：pandas、numpy、matplotlib、openpyxl（读写 xlsx）、xlrd（可选，读 xls）

## 数据要求
- 默认 Excel 文件：`O76_process.xlsx`（同目录下），若缺失则回退 `O76_process.xls`。
- 默认工作表名：`O76`，若不存在则自动使用首个工作表。
- 数据格式（与 MATLAB 一致，行列为 1 基描述）：
  - 第 1 行第 8 列：测线走向角度 `ang0`。
  - 第 1 行第 9 列：节理条目数 `n`。
  - 前 7 列（各行）：位置、倾向/走向、迹长等参数；第 3 列为节理倾向，运行时转换为走向。

## 角度转换
- 倾向转走向规则（与 MATLAB 一致）：
  - 若 $dd \ge 270$, $strike = dd + 90 - 360$。
  - 若 $dd \ge 180$, $strike = dd - 90$。
  - 若 $dd \ge 90$, $strike = dd - 90$。
  - 否则 $strike = dd + 90$。

## 输出
- Excel：`Outcrop.xlsx`，在工作表 `O76` 的 A1 写入节理数量 `n`。
- 图片：`O76(n).png`，裂缝示意图，白底、300 dpi。
- 输出目录：优先 `D:\作业\毕业论文\周咏霖`，若不存在则使用当前工作目录。

## 运行步骤
1. 将 `O76_process.xlsx`（或 `.xls`）放在工作目录，确保含有表 `O76` 且数据格式符合要求。
2. 打开终端进入工作目录，执行：
   ```bash
   python a_outcrop_0map_coordinate.py
   ```
3. 完成后在同目录查看 `Outcrop.xlsx` 和 `O76(n).png`。

## 可配置项
- 更改工作表或文件前缀：修改 `outcrop_name`、`excel_base`。
- 调整输入/输出目录：修改 `path1`、`path3`，脚本会在目录不存在时退回当前工作目录。
- 绘图样式：在绘图段调整颜色、线宽、图幅尺寸、dpi。

## 测试建议
- 使用小型测试 Excel（n=3~5）验证：
  - Excel 读写无报错。
  - 输出图坐标比例正确（轴等比例，线段数量为 n）。
  - 倾向→走向转换符合预期（可用已知样例核对）。
