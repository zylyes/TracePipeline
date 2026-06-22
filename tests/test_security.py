from __future__ import annotations

import base64
import concurrent.futures
import sys
import threading
from io import BytesIO
from types import SimpleNamespace

from PIL import Image

sys.modules.setdefault(
    "webview",
    SimpleNamespace(FileDialog=SimpleNamespace(SAVE="save", FOLDER="folder")),
)

from backend.gui_api import GuiApi  # noqa: E402
from backend.utils.security import PathSecurityChecker  # noqa: E402


def test_safe_path_allows_trusted_external_base_only_when_requested(tmp_path) -> None:
    project_root = tmp_path / "project"
    external_root = tmp_path / "external"
    project_root.mkdir()
    external_root.mkdir()
    target = external_root / "image.png"

    checker = PathSecurityChecker(project_root)

    assert checker.safe_path(str(target), external_root) is None
    assert (
        checker.safe_path(str(target), external_root, allow_external_base=True) == target.resolve()
    )


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
    api._user_selected_paths_lock = threading.Lock()
    target = tmp_path / "external" / "reports.zip"

    assert api._safe_user_selected_path(str(target)) is None


def test_gui_api_allows_registered_external_selected_path(tmp_path) -> None:
    api = object.__new__(GuiApi)
    api._path_checker = PathSecurityChecker(tmp_path / "project")
    api._user_selected_paths_lock = threading.Lock()
    target = tmp_path / "external" / "reports.zip"
    api._user_selected_paths = {target.resolve().absolute()}

    assert api._safe_user_selected_path(str(target)) == target.resolve().absolute()


def test_gui_api_allows_registered_external_selected_folder(tmp_path) -> None:
    api = object.__new__(GuiApi)
    api._path_checker = PathSecurityChecker(tmp_path / "project")
    api._user_selected_paths_lock = threading.Lock()
    target = tmp_path / "external"
    api._user_selected_paths = {target.resolve().absolute()}

    assert api._safe_user_selected_path(str(target), expect_dir=True) == target.resolve().absolute()


def test_gui_api_selected_paths_concurrent_read_write(tmp_path) -> None:
    api = object.__new__(GuiApi)
    api._path_checker = PathSecurityChecker(tmp_path / "project")
    api._user_selected_paths = set()
    api._user_selected_paths_lock = threading.Lock()
    target = tmp_path / "external" / "reports.zip"
    api._remember_user_selected_path(str(target))

    errors: list[Exception] = []

    def remember_worker() -> None:
        try:
            for _ in range(100):
                api._remember_user_selected_path(str(target))
        except Exception as exc:  # pragma: no cover - reported by assertion below
            errors.append(exc)

    def check_worker() -> None:
        try:
            for _ in range(100):
                assert api._safe_user_selected_path(str(target)) == target.resolve().absolute()
        except Exception as exc:  # pragma: no cover - reported by assertion below
            errors.append(exc)

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        futures = [pool.submit(remember_worker) for _ in range(4)]
        futures.extend(pool.submit(check_worker) for _ in range(4))
        concurrent.futures.wait(futures)

    assert not errors


def _write_png(path, size=(320, 180), color=(40, 80, 120)) -> None:
    image = Image.new("RGB", size, color)
    image.save(path, format="PNG")


def test_gui_api_thumbnail_returns_bounded_png_data_url(tmp_path) -> None:
    target = tmp_path / "plot.png"
    _write_png(target, size=(900, 300))
    api = object.__new__(GuiApi)
    api._safe_known_path = lambda _path: target

    data_url = api.get_image_thumbnail(str(target), 128)

    assert data_url.startswith("data:image/png;base64,")
    payload = data_url.split(",", 1)[1]
    thumbnail = Image.open(BytesIO(base64.b64decode(payload)))
    assert max(thumbnail.size) <= 128


def test_gui_api_thumbnail_rejects_unsafe_path(tmp_path) -> None:
    api = object.__new__(GuiApi)
    api._safe_known_path = lambda _path: None

    assert api.get_image_thumbnail(str(tmp_path / "plot.png")) == ""


def test_gui_api_thumbnail_rejects_unsafe_extension(tmp_path) -> None:
    target = tmp_path / "plot.svg"
    target.write_text("<svg></svg>", encoding="utf-8")
    api = object.__new__(GuiApi)
    api._safe_known_path = lambda _path: target

    assert api.get_image_thumbnail(str(target)) == ""


def test_gui_api_thumbnail_rejects_oversized_file(tmp_path) -> None:
    target = tmp_path / "plot.png"
    target.write_bytes(b"\x89PNG\r\n\x1a\n" + b"0" * GuiApi._MAX_IMAGE_SIZE)
    api = object.__new__(GuiApi)
    api._safe_known_path = lambda _path: target

    assert api.get_image_thumbnail(str(target)) == ""


def test_gui_api_image_meta_changes_with_file_signature(tmp_path) -> None:
    target = tmp_path / "plot.png"
    _write_png(target, size=(80, 80))
    api = object.__new__(GuiApi)
    api._safe_known_path = lambda _path: target
    before = api.get_image_meta(str(target))

    _write_png(target, size=(160, 80), color=(90, 20, 20))
    after = api.get_image_meta(str(target))

    assert (before["mtime_ns"], before["size"]) != (after["mtime_ns"], after["size"])
