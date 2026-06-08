from __future__ import annotations

import sys
from types import SimpleNamespace

sys.modules.setdefault(
    "webview",
    SimpleNamespace(FileDialog=SimpleNamespace(SAVE="save", FOLDER="folder")),
)

from backend.gui_api import GuiApi
from backend.utils.security import PathSecurityChecker


def test_safe_path_allows_trusted_external_base_only_when_requested(tmp_path) -> None:
    project_root = tmp_path / "project"
    external_root = tmp_path / "external"
    project_root.mkdir()
    external_root.mkdir()
    target = external_root / "image.png"

    checker = PathSecurityChecker(project_root)

    assert checker.safe_path(str(target), external_root) is None
    assert checker.safe_path(
        str(target), external_root, allow_external_base=True
    ) == target.resolve()


def test_safe_path_rejects_windows_device_name_variants(tmp_path) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()
    checker = PathSecurityChecker(project_root)

    assert checker.safe_path("CON.txt") is None
    assert checker.safe_path("nested/NUL.log") is None


def test_gui_api_rejects_unregistered_external_selected_path(tmp_path) -> None:
    api = object.__new__(GuiApi)
    api._path_checker = PathSecurityChecker(tmp_path / "project")
    api._user_selected_paths = set()
    target = tmp_path / "external" / "reports.zip"

    assert api._safe_user_selected_path(str(target)) is None


def test_gui_api_allows_registered_external_selected_path(tmp_path) -> None:
    api = object.__new__(GuiApi)
    api._path_checker = PathSecurityChecker(tmp_path / "project")
    target = tmp_path / "external" / "reports.zip"
    api._user_selected_paths = {target.resolve().absolute()}

    assert api._safe_user_selected_path(str(target)) == target.resolve().absolute()


def test_gui_api_allows_registered_external_selected_folder(tmp_path) -> None:
    api = object.__new__(GuiApi)
    api._path_checker = PathSecurityChecker(tmp_path / "project")
    target = tmp_path / "external"
    api._user_selected_paths = {target.resolve().absolute()}

    assert api._safe_user_selected_path(str(target), expect_dir=True) == target.resolve().absolute()
