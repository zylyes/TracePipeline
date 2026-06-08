from __future__ import annotations

from backend.services.stats_service import StatsService


def test_stats_cache_key_changes_with_stat_config(tmp_path) -> None:
    input_dir = tmp_path / "input"
    input_dir.mkdir()
    (input_dir / "O76_process.xlsx").write_bytes(b"placeholder")
    service = StatsService()

    base = {"input_dir": str(input_dir), "min_intersections": 5}
    changed = {"input_dir": str(input_dir), "min_intersections": 9}

    assert service._make_key("O76", base) != service._make_key("O76", changed)


def test_stats_cache_key_changes_with_input_file_fingerprint(tmp_path) -> None:
    input_dir = tmp_path / "input"
    input_dir.mkdir()
    workbook = input_dir / "O76_process.xlsx"
    workbook.write_bytes(b"old")
    service = StatsService()
    config = {"input_dir": str(input_dir)}

    first_key = service._make_key("O76", config)
    workbook.write_bytes(b"new-content")

    assert first_key != service._make_key("O76", config)


def test_stats_cache_key_changes_with_input_dir(tmp_path) -> None:
    first_dir = tmp_path / "first"
    second_dir = tmp_path / "second"
    first_dir.mkdir()
    second_dir.mkdir()
    (first_dir / "O76_process.xlsx").write_bytes(b"same")
    (second_dir / "O76_process.xlsx").write_bytes(b"same")
    service = StatsService()

    assert service._make_key("O76", {"input_dir": str(first_dir)}) != service._make_key(
        "O76", {"input_dir": str(second_dir)}
    )


def test_stats_cache_is_bounded() -> None:
    service = StatsService()

    assert service._cache._maxsize == 128
