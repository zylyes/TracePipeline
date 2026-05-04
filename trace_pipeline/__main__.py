"""支持 `python -m trace_pipeline` 调用方式。"""
import matplotlib as _mpl

_mpl.use("Agg")

from .cli import main

if __name__ == "__main__":
    main()
