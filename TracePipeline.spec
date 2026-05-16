# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller 打包规格 — TracePipeline GUI 应用。

用法:
    pyinstaller TracePipeline.spec

输出: dist/TracePipeline/（独立文件夹）
"""
from __future__ import annotations

import sys
from pathlib import Path

# 读取版本号（与 app 版本同步）
_init_path = Path("trace_pipeline/__init__.py")
_version = "0.0.0"
if _init_path.exists():
    _content = _init_path.read_text(encoding="utf-8")
    for _line in _content.splitlines():
        _stripped = _line.strip()
        if _stripped.startswith('__version__'):
            _version = _stripped.split("=", 1)[1].strip().strip('"').strip("'")
            break

# ---------- Analysis ----------
a = Analysis(
    ["run_gui.py"],
    pathex=[],
    binaries=[],
    datas=[
        ("backend/static", "backend/static"),
        ("reference/ECUT.ico", "reference"),
    ],
    hiddenimports=[
        # matplotlib Agg 后端（run_gui.py 中 matplotlib.use('Agg') 显式设置）
        "matplotlib.backends.backend_agg",
        # pywebview Windows 平台后端
        "webview.platforms.winforms",
        "webview.platforms.win32",
        "webview.platforms.edgechromium",
        "webview.platforms.mshtml",
        "webview.guilib",
        # scipy 子模块（惰性加载，PyInstaller 可能遗漏）
        "scipy.spatial",
        "scipy.spatial._qhull",
        "scipy.stats",
        "scipy.stats._stats",
        "scipy.special",
        "scipy.special._ufuncs",
        # 惰性加载的 trace_pipeline 子包（通过 importlib.import_module 加载）
        "trace_pipeline.plotting.style",
        "trace_pipeline.plotting.trace_plot",
        "trace_pipeline.plotting.rose_plot",
        "trace_pipeline.plotting.overlays",
        "trace_pipeline.plotting.preview_plot",
        "trace_pipeline.plotting._helpers",
        "trace_pipeline.pipeline",
        "trace_pipeline.geology.statistics",
        "trace_pipeline.geology.transforms",
        "trace_pipeline.geology.angles",
        "trace_pipeline.geology.endpoints",
        "trace_pipeline.geology._stat_types",
        "trace_pipeline.geology._stat_format",
        "trace_pipeline.geology._circle_window",
        "trace_pipeline.geology._convex_hull",
        "trace_pipeline.geology._window_strategies",
        "trace_pipeline.geology._window_scoring",
        "trace_pipeline.analysis.models",
        "trace_pipeline.analysis.nodes",
        "trace_pipeline.geometry.segments",
        "trace_pipeline.io.excel_reader",
        "trace_pipeline.io.excel_writer",
        "trace_pipeline.io.discovery",
        "trace_pipeline.cli.main",
        "trace_pipeline.cli.args",
        "trace_pipeline.cli.dispatcher",
        "trace_pipeline.cli.interactive",
        "trace_pipeline.cli.logging_setup",
        "trace_pipeline.logging.core",
        "trace_pipeline.logging.context",
        "trace_pipeline.models",
        "trace_pipeline.config",
        "trace_pipeline.validation",
        "trace_pipeline.reporting",
        # 第三方依赖的动态子模块
        "shapely.geometry",
        "PIL._imaging",
        "openpyxl",
        "xlrd",
        "docx",
        "reportlab",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # 未使用的标准库模块（GUI 不需要）
        # 注意：distutils/setuptools/pydoc 被依赖库（tqdm 等）运行时引用，不能排除
        "tkinter",
        "turtle",
        "ensurepip",
        "idlelib",
        "lib2to3",
    ],
    noarchive=False,
)

# ---------- PYZ ----------
pyz = PYZ(a.pure)

# ---------- EXE ----------
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="TracePipeline",
    debug=False,
    bootloader_ignore_signals=False,
    strip=True,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon="reference/ECUT.ico",
)

# ---------- COLLECT ----------
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=True,
    upx=False,
    upx_exclude=[],
    name="TracePipeline",
)
