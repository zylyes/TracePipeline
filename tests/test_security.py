from __future__ import annotations

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
