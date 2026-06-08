from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_package_script_compiles() -> None:
    script = ROOT / "scripts" / "package.py"

    compile(script.read_text(encoding="utf-8"), str(script), "exec")


def test_release_metadata_versions_match() -> None:
    init_text = (ROOT / "trace_pipeline" / "__init__.py").read_text(encoding="utf-8")
    version = re.search(r'__version__\s*=\s*"([^"]+)"', init_text).group(1)  # type: ignore[union-attr]
    package = json.loads((ROOT / "frontend" / "package.json").read_text(encoding="utf-8"))
    package_lock = json.loads((ROOT / "frontend" / "package-lock.json").read_text(encoding="utf-8"))
    setup = (ROOT / "TracePipeline-setup.iss").read_text(encoding="utf-8-sig")

    assert package["version"] == version
    assert package_lock["version"] == version
    assert package_lock["packages"][""]["version"] == version
    assert f"AppVersion={version}" in setup
    assert f"OutputBaseFilename=TracePipeline-Setup-v{version}" in setup
    assert f"UninstallDisplayName=TracePipeline v{version}" in setup
    assert f"VersionInfoVersion={version}" in setup


def test_installer_uses_tracked_icon() -> None:
    setup = (ROOT / "TracePipeline-setup.iss").read_text(encoding="utf-8-sig")
    package_script = (ROOT / "scripts" / "package.py").read_text(encoding="utf-8")

    assert "reference\\favicon.ico" in setup
    assert "ECUT.ico" not in setup
    assert '"favicon.ico"' in package_script
    assert '"ECUT.ico"' not in package_script
