"""集中管理脚本运行所需的默认路径与参数配置。"""
from dataclasses import dataclass


@dataclass
class RunConfig:
    """脚本运行时的统一配置。

    Attributes:
        input_dir: 源 Excel 文件所在目录。
        output_dir: 导出图片和表格的目录。
        file_name: 导出 Excel 的基础文件名。
        excel_base: 输入目录中待读取的 Excel 文件名（不含扩展名）。
        outcrop_name: 工作表名称，同时用于图件标签。
        process_all: 发现多个相同命名规则的表时，是否批量处理全部。
    """

    input_dir: str = r"D:\作业\毕业论文\周咏霖\input"
    output_dir: str = r"D:\作业\毕业论文\周咏霖\output"
    file_name: str = "Outcrop"
    excel_base: str = "O76_process"
    outcrop_name: str = "O76"
    process_all: bool = True


def default_config() -> RunConfig:
    """返回两个脚本共用的默认配置。"""
    return RunConfig()
