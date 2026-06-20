"""迹线处理入口脚本 — 调用 trace_pipeline.cli.main。

命令行参数与使用方式详见:
    python run_trace_pipeline.py --help
"""

import logging
import sys
import traceback

from trace_pipeline.cli import main
from trace_pipeline.config import ensure_workspace_dirs

if __name__ == "__main__":
    try:
        ensure_workspace_dirs()
        main()
    except KeyboardInterrupt:
        sys.exit(130)
    except Exception:
        try:
            logging.exception("迹线处理启动失败")
        except Exception:
            print(traceback.format_exc(), file=sys.stderr)
        print(
            "错误：迹线处理启动失败，请检查配置或环境。详细信息见上方日志。",
            file=sys.stderr,
        )
        sys.exit(1)
