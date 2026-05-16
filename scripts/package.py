"""TracePipeline 应用打包脚本。

三步流程:
  1. PyInstaller → dist/TracePipeline/（独立程序文件夹）
  2. Inno Setup 6 → dist/TracePipeline-Setup-v{version}.exe（安装程序）
  3. 7-Zip SFX → dist/TracePipeline-Portable-v{version}.exe（便捷版自解压）

用法:
    python scripts/package.py                     # 完整打包（安装版 + 便捷版）
    python scripts/package.py --skip-portable     # 仅安装版
    python scripts/package.py --skip-installer    # 仅便捷版
    python scripts/package.py --skip-frontend     # 跳过前端构建
"""
from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

# ---------------------------------------------------------------------------
# 常量和路径
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
SPEC_FILE = PROJECT_ROOT / "TracePipeline.spec"
FRONTEND_DIR = PROJECT_ROOT / "frontend"
STATIC_DIR = PROJECT_ROOT / "backend" / "static"
DIST_DIR = PROJECT_ROOT / "dist"
BUILD_DIR = PROJECT_ROOT / "build"
ICON_FILE = PROJECT_ROOT / "reference" / "ECUT.ico"
VENV_PYTHON = PROJECT_ROOT / "venv" / "Scripts" / "python.exe"
ISCC_EXE = Path("D:/Inno Setup 6/ISCC.exe")
ISS_LANG_DIR = Path("D:/Inno Setup 6/Languages")
SEVEN_ZIP = Path("C:/Program Files/7-Zip/7z.exe")
SFX_MODULE = Path("C:/Program Files/7-Zip/7z.sfx")

# 输出目录名
APP_NAME = "TracePipeline"

# ---------------------------------------------------------------------------
# 工具函数
# ---------------------------------------------------------------------------
CSI = "\033["
RED, GREEN, YELLOW, CYAN, RESET = (
    f"{CSI}91m",
    f"{CSI}92m",
    f"{CSI}93m",
    f"{CSI}96m",
    f"{CSI}0m",
)


def _now() -> str:
    return time.strftime("%H:%M:%S")


def info(msg: str) -> None:
    print(f"{GREEN}[{_now()}]{RESET} {msg}")


def warn(msg: str) -> None:
    print(f"{YELLOW}[{_now()}] ⚠ {msg}{RESET}")


def error(msg: str) -> None:
    print(f"{RED}[{_now()}] ✗ {msg}{RESET}")


def run(cmd: list[str], *, desc: str = "", cwd: Path | None = None) -> int:
    """运行命令并实时打印输出。返回退出码。"""
    label = f"  {desc}" if desc else ""
    info(f"执行: {' '.join(cmd)}{label}")
    proc = subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        stdout=sys.stdout,
        stderr=sys.stderr,
        stdin=subprocess.DEVNULL,
    )
    if proc.returncode != 0:
        error(f"命令失败，退出码: {proc.returncode}")
    return proc.returncode


def read_version() -> str:
    """从 trace_pipeline/__init__.py 读取 __version__。"""
    init_file = PROJECT_ROOT / "trace_pipeline" / "__init__.py"
    if not init_file.exists():
        warn(f"找不到版本文件: {init_file}，使用默认版本 0.0.0")
        return "0.0.0"
    content = init_file.read_text(encoding="utf-8")
    m = re.search(r'__version__\s*=\s*["\']([^"\']+)["\']', content)
    version = m.group(1) if m else "0.0.0"
    info(f"读取版本号: {version}")
    return version


def format_size(num_bytes: int) -> str:
    """将字节数格式化为人类可读的字符串。"""
    for unit in ("B", "KB", "MB", "GB"):
        if num_bytes < 1024:
            return f"{num_bytes:.1f} {unit}"
        num_bytes /= 1024
    return f"{num_bytes:.1f} TB"


def dir_size(path: Path) -> int:
    """递归计算目录总大小（字节）。"""
    total = 0
    for f in path.rglob("*"):
        if f.is_file():
            total += f.stat().st_size
    return total


# ---------------------------------------------------------------------------
# 前置检查
# ---------------------------------------------------------------------------
def check_prerequisites(
    skip_frontend: bool = False,
    skip_installer: bool = False,
    skip_portable: bool = False,
) -> bool:
    """检查打包所需的前置条件。返回 True 表示全部通过。"""
    ok = True

    # Python 虚拟环境
    if not VENV_PYTHON.exists():
        warn(f"未找到 venv Python: {VENV_PYTHON}")
        ok = False
    else:
        info(f"venv Python: {VENV_PYTHON}")

    # 前端构建产物
    index_html = STATIC_DIR / "index.html"
    if not index_html.exists():
        if skip_frontend:
            warn("前端尚未构建，但已跳过（--skip-frontend）")
        else:
            warn(f"前端尚未构建: {index_html} 不存在，将自动构建")
    else:
        info(f"前端构建产物: {STATIC_DIR}")

    # PyInstaller（在 venv 中）
    pi = PROJECT_ROOT / "venv" / "Scripts" / "pyinstaller.exe"
    if not pi.exists():
        error(f"PyInstaller 未安装: {pi}")
        ok = False
    else:
        info(f"PyInstaller: {pi}")

    # 图标
    if not ICON_FILE.exists():
        error(f"图标文件不存在: {ICON_FILE}")
        ok = False
    else:
        info(f"图标: {ICON_FILE} ({format_size(ICON_FILE.stat().st_size)})")

    # Inno Setup 6
    if not skip_installer:
        if not ISCC_EXE.exists():
            warn(f"未找到 Inno Setup 6 编译器: {ISCC_EXE}")
        else:
            info(f"Inno Setup 6: {ISCC_EXE}")

    # 7-Zip（便捷版需要）
    if not skip_portable:
        if not SEVEN_ZIP.exists():
            warn(f"未找到 7-Zip: {SEVEN_ZIP}，便捷版将不可用")
        elif not SFX_MODULE.exists():
            warn(f"未找到 7-Zip SFX 模块: {SFX_MODULE}，便捷版将不可用")
        else:
            info(f"7-Zip: {SEVEN_ZIP}")

    return ok


# ---------------------------------------------------------------------------
# 步骤 0: 构建前端
# ---------------------------------------------------------------------------
def build_frontend() -> bool:
    """执行 npm run build 构建 Vue 前端。"""
    package_json = FRONTEND_DIR / "package.json"
    if not package_json.exists():
        error(f"找不到 {package_json}")
        return False

    info("正在构建前端 (npm run build)...")
    rc = run(["npm", "install"], desc="安装前端依赖", cwd=FRONTEND_DIR)
    if rc != 0:
        return False
    rc = run(["npm", "run", "build"], desc="构建前端", cwd=FRONTEND_DIR)
    if rc != 0:
        error("前端构建失败")
        return False

    index_html = STATIC_DIR / "index.html"
    if not index_html.exists():
        error(f"构建产物缺失: {index_html}")
        return False
    info(f"前端构建完成 → {STATIC_DIR}")
    return True


# ---------------------------------------------------------------------------
# 步骤 1: PyInstaller 打包
# ---------------------------------------------------------------------------
def run_pyinstaller() -> bool:
    """使用 PyInstaller 将应用打包为独立文件夹。"""
    if not SPEC_FILE.exists():
        error(f"打包规格文件不存在: {SPEC_FILE}")
        return False

    old_dist = DIST_DIR / APP_NAME
    if old_dist.exists():
        info(f"清理旧输出: {old_dist}")
        try:
            shutil.rmtree(old_dist, ignore_errors=False)
        except (PermissionError, OSError):
            warn("shutil.rmtree 失败，尝试使用系统命令清理...")
            subprocess.run(
                ["cmd", "/c", "rmdir", "/s", "/q", str(old_dist)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

    # 同时清理旧 .7z 临时文件
    for pattern in ["*.7z", "*.sfxcfg"]:
        for f in DIST_DIR.glob(pattern):
            info(f"清理临时文件: {f}")
            f.unlink()

    info("正在运行 PyInstaller（此步骤可能需要数分钟）...")
    rc = run(
        [str(VENV_PYTHON), "-m", "PyInstaller", "--distpath", str(DIST_DIR), str(SPEC_FILE)],
        desc="PyInstaller 打包",
    )
    if rc != 0:
        error("PyInstaller 打包失败")
        return False

    exe = DIST_DIR / APP_NAME / f"{APP_NAME}.exe"
    if not exe.exists():
        error(f"打包产物缺失: {exe}")
        return False

    size = dir_size(DIST_DIR / APP_NAME)
    info(f"PyInstaller 打包完成 → {DIST_DIR / APP_NAME}")
    info(f"程序文件夹大小: {format_size(size)}")
    return True


# ---------------------------------------------------------------------------
# 步骤 2: Inno Setup 安装程序
# ---------------------------------------------------------------------------
def generate_iss(version: str) -> Path:
    """生成 Inno Setup 脚本，返回 .iss 文件路径。"""
    dist_dir_bs = str(DIST_DIR)
    icon_bs = str(ICON_FILE)
    lang_bs = str(ISS_LANG_DIR)

    iss_content = f'''; Inno Setup 6 安装脚本 — TracePipeline
; 由 scripts/package.py 自动生成

[Setup]
AppId={{{{7B3F1C9A-5D2E-40F8-A61B-C8E4D9F01236}}}}
AppName={APP_NAME}
AppVersion={version}
AppPublisher=ECUT
AppPublisherURL=https://github.com/ECUT
AppSupportURL=https://github.com/ECUT
DefaultDirName={{autopf}}\\{APP_NAME}
DefaultGroupName={APP_NAME}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
OutputDir={dist_dir_bs}
OutputBaseFilename={APP_NAME}-Setup-v{version}
SetupIconFile={icon_bs}
UninstallDisplayIcon={{app}}\\reference\\ECUT.ico
UninstallDisplayName=TracePipeline v{version}
VersionInfoVersion={version}

[Languages]
Name: "chinesesimplified"; MessagesFile: "{lang_bs}\\ChineseSimplified.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Files]
Source: "{dist_dir_bs}\\{APP_NAME}\\*"; DestDir: "{{app}}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{{group}}\\{APP_NAME}"; Filename: "{{app}}\\{APP_NAME}.exe"; IconFilename: "{{app}}\\reference\\ECUT.ico"
Name: "{{group}}\\卸载 TracePipeline"; Filename: "{{uninstallexe}}"
Name: "{{commondesktop}}\\{APP_NAME}"; Filename: "{{app}}\\{APP_NAME}.exe"; IconFilename: "{{app}}\\reference\\ECUT.ico"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "创建桌面快捷方式"; GroupDescription: "其他快捷方式"

[Run]
Filename: "{{app}}\\{APP_NAME}.exe"; Description: "启动 TracePipeline"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{{app}}\\logs"
Type: files; Name: "{{app}}\\config.json"
'''
    iss_path = PROJECT_ROOT / f"{APP_NAME}-setup.iss"
    iss_path.write_text(iss_content, encoding="utf-8")
    info(f".iss 脚本已生成: {iss_path}")
    return iss_path


def run_inno_setup(iss_path: Path) -> bool:
    """调用 Inno Setup 6 编译器生成安装程序。"""
    if not ISCC_EXE.exists():
        error(f"Inno Setup 6 编译器不存在: {ISCC_EXE}")
        return False

    info("正在编译安装程序...")
    rc = run(
        [str(ISCC_EXE), str(iss_path)],
        desc="Inno Setup 编译",
    )
    if rc != 0:
        error("Inno Setup 编译失败")
        return False

    setup_exe = DIST_DIR / f"{APP_NAME}-Setup-v{read_version()}.exe"
    if setup_exe.exists():
        size = setup_exe.stat().st_size
        info(f"安装程序已生成: {setup_exe}")
        info(f"安装程序大小: {format_size(size)}")
    return True


# ---------------------------------------------------------------------------
# 步骤 3: 7-Zip 自解压便捷版
# ---------------------------------------------------------------------------
def generate_sfx_config(version: str) -> Path:
    """生成 7-Zip SFX 配置文件。"""
    config = f''';!@Install@!UTF-8!
Title="TracePipeline v{version} 便捷版"
BeginPrompt="即将解压 TracePipeline v{version} 便捷版。是否继续？"
ExtractPathText="选择解压目标文件夹:"
ExtractDialogText="解压后自动运行 TracePipeline"
RunProgram="{APP_NAME}.exe"
GUIFlags="8+32"
;!@InstallEnd@!
'''
    cfg_path = DIST_DIR / f"{APP_NAME}-portable.sfxcfg"
    cfg_path.write_text(config, encoding="utf-8")
    return cfg_path


def build_portable_sfx(version: str) -> bool:
    """使用 7-Zip 创建自解压便捷版。

    步骤:
      1. 7z 将程序文件夹打包为 .7z（最高压缩比）
      2. 拼接 SFX 模块 + 配置文件 + .7z 归档 → 自解压 .exe
    """
    if not SEVEN_ZIP.exists():
        error(f"7-Zip 未找到: {SEVEN_ZIP}")
        return False
    if not SFX_MODULE.exists():
        error(f"7-Zip SFX 模块未找到: {SFX_MODULE}")
        return False

    app_dir = DIST_DIR / APP_NAME
    if not app_dir.exists():
        error(f"程序文件夹不存在: {app_dir}")
        return False

    archive_7z = DIST_DIR / f"{APP_NAME}-portable.7z"

    # Step A: 创建 .7z 归档（mx=9 最高压缩，md=256m 大字典）
    info("正在创建 7z 归档（最高压缩）...")
    rc = run(
        [
            str(SEVEN_ZIP), "a", "-t7z",
            "-mx=9", "-md=256m", "-ms=on",
            str(archive_7z),
            str(app_dir / "*"),
        ],
        desc="7z 压缩",
        cwd=app_dir,
    )
    if rc != 0 or not archive_7z.exists():
        error("7z 归档创建失败")
        return False

    archive_size = archive_7z.stat().st_size
    info(f"7z 归档: {format_size(archive_size)}")

    # Step B: 生成 SFX 配置文件
    cfg_path = generate_sfx_config(version)

    # Step C: 拼接 SFX 模块 + 配置 + 归档 → 便捷版 .exe
    portable_exe = DIST_DIR / f"{APP_NAME}-Portable-v{version}.exe"
    info(f"正在拼接自解压程序: {portable_exe.name}")
    with open(portable_exe, "wb") as out:
        out.write(SFX_MODULE.read_bytes())
        out.write(cfg_path.read_bytes())
        out.write(archive_7z.read_bytes())

    # 清理临时文件
    archive_7z.unlink()
    cfg_path.unlink()

    portable_size = portable_exe.stat().st_size
    info(f"便捷版已生成: {portable_exe}")
    info(f"便捷版大小: {format_size(portable_size)}")
    return True


# ---------------------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------------------
def _setup_console() -> None:
    """确保控制台支持 Unicode 输出。"""
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError):
        pass


def main() -> int:
    _setup_console()
    parser = argparse.ArgumentParser(
        description="TracePipeline 应用打包脚本",
    )
    parser.add_argument(
        "--skip-frontend",
        action="store_true",
        help="跳过前端构建（假设 backend/static/ 已存在）",
    )
    parser.add_argument(
        "--skip-installer",
        action="store_true",
        help="跳过安装程序生成",
    )
    parser.add_argument(
        "--skip-portable",
        action="store_true",
        help="跳过便捷版（自解压）生成",
    )
    args = parser.parse_args()

    print(f"\n{CYAN}{'=' * 60}{RESET}")
    print(f"{CYAN}  TracePipeline 应用打包脚本{RESET}")
    print(f"{CYAN}  项目: {PROJECT_ROOT}{RESET}")
    print(f"{CYAN}{'=' * 60}{RESET}\n")

    # ---- 前置检查 ----
    info(">>> 前置检查")
    if not check_prerequisites(
        skip_frontend=args.skip_frontend,
        skip_installer=args.skip_installer,
        skip_portable=args.skip_portable,
    ):
        return 1

    version = read_version()
    print()

    # ---- 步骤 0: 前端构建 ----
    if not args.skip_frontend:
        info(">>> 步骤 0: 前端构建")
        if not build_frontend():
            return 1
        print()
    else:
        info(">>> 步骤 0: 跳过前端构建（--skip-frontend）\n")

    # ---- 步骤 1: PyInstaller ----
    info(">>> 步骤 1: PyInstaller 打包")
    if not run_pyinstaller():
        return 1
    print()

    # ---- 步骤 2: Inno Setup 安装版 ----
    if not args.skip_installer:
        info(">>> 步骤 2: Inno Setup 安装程序")
        iss_path = generate_iss(version)
        if not run_inno_setup(iss_path):
            warn("安装程序生成失败，但程序文件夹已就绪")
    else:
        info(">>> 步骤 2: 跳过安装程序（--skip-installer）")
    print()

    # ---- 步骤 3: 7-Zip 自解压便捷版 ----
    if not args.skip_portable:
        info(">>> 步骤 3: 7-Zip 自解压便捷版")
        if not build_portable_sfx(version):
            warn("便捷版生成失败，但其他产物已就绪")
    else:
        info(">>> 步骤 3: 跳过便捷版（--skip-portable）")

    # ---- 完成 ----
    print(f"\n{CYAN}{'=' * 60}{RESET}")
    print(f"{GREEN}  打包完成 ✓{RESET}")
    print(f"{CYAN}{'=' * 60}{RESET}\n")
    print(f"  程序文件夹: {DIST_DIR / APP_NAME}")
    print(f"  体积:       {format_size(dir_size(DIST_DIR / APP_NAME))}")

    setup_exe = DIST_DIR / f"{APP_NAME}-Setup-v{version}.exe"
    if setup_exe.exists():
        print(f"  安装版:     {setup_exe.name}  ({format_size(setup_exe.stat().st_size)})")

    portable_exe = DIST_DIR / f"{APP_NAME}-Portable-v{version}.exe"
    if portable_exe.exists():
        print(f"  便捷版:     {portable_exe.name}  ({format_size(portable_exe.stat().st_size)})")
    print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
