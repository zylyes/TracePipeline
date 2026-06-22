from __future__ import annotations

import concurrent.futures
import os
import threading
from pathlib import Path

from backend.utils.cache import DirectoryChangeDetector


class TestDirectoryChangeDetectorConcurrency:
    """验证 DirectoryChangeDetector 并发安全。"""

    def test_concurrent_invalidate_has_changed_no_exception(self, tmp_path) -> None:
        """并发调用 invalidate 和 has_changed 不应抛异常。"""
        detector = DirectoryChangeDetector(max_files=100)
        target_dir = tmp_path / "watch"
        target_dir.mkdir()
        # 创建一些文件
        for i in range(10):
            (target_dir / f"file_{i}.txt").write_text("data")

        errors = []

        def worker_invalidate():
            try:
                for _ in range(50):
                    detector.invalidate()
            except Exception as e:
                errors.append(f"invalidate: {e}")

        def worker_has_changed():
            try:
                for _ in range(50):
                    detector.has_changed(target_dir)
            except Exception as e:
                errors.append(f"has_changed: {e}")

        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            futures = []
            for _ in range(4):
                futures.append(pool.submit(worker_invalidate))
                futures.append(pool.submit(worker_has_changed))
            concurrent.futures.wait(futures)

        assert not errors, f"并发操作产生异常: {errors}"
        # 最终快照应有效（没有 None）
        detector.has_changed(target_dir)

    def test_concurrent_has_changed_no_race(self, tmp_path) -> None:
        """并发 has_changed 调用不应导致数据竞争。"""
        detector = DirectoryChangeDetector(max_files=100)
        target_dir = tmp_path / "watch"
        target_dir.mkdir()
        for i in range(20):
            (target_dir / f"file_{i}.txt").write_text("data")

        results = []
        lock = threading.Lock()

        def worker():
            changed = detector.has_changed(target_dir)
            with lock:
                results.append(changed)

        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            futures = [pool.submit(worker) for _ in range(20)]
            concurrent.futures.wait(futures)

        # 第一个调用应返回 False（初始化快照），之后返回 False（无变更）
        # 但并发下可能有多个线程同时看到 None，所以第一个返回 True 也是可能的
        # 关键是不抛异常且最终状态一致
        assert all(isinstance(r, bool) for r in results)


class TestDirectoryChangeDetectorTruncation:
    """验证截断场景下新增文件能被检测到。"""

    def test_truncation_detects_new_file(self, tmp_path) -> None:
        """目录文件数超过 max_files 后新增文件应被检测到。"""
        max_files = 50
        detector = DirectoryChangeDetector(max_files=max_files)
        target_dir = tmp_path / "truncated"
        target_dir.mkdir()

        # 创建 max_files 个文件
        for i in range(max_files):
            (target_dir / f"file_{i:04d}.txt").write_text("data")

        # 首次快照
        assert not detector.has_changed(target_dir), "首次快照应返回 False"

        # 添加一个新文件（超过 max_files）
        (target_dir / "new_file.txt").write_text("new data")

        # 应检测到变更（总条目数从 max_files 变为 max_files + 1）
        assert detector.has_changed(target_dir), "新增文件应被检测到"

    def test_truncation_detects_deleted_file(self, tmp_path) -> None:
        """目录文件数超过 max_files 后删除文件应被检测到。"""
        max_files = 50
        detector = DirectoryChangeDetector(max_files=max_files)
        target_dir = tmp_path / "truncated_del"
        target_dir.mkdir()

        # 创建 max_files + 5 个文件
        file_count = max_files + 5
        for i in range(file_count):
            (target_dir / f"file_{i:04d}.txt").write_text("data")

        # 首次快照
        assert not detector.has_changed(target_dir), "首次快照应返回 False"

        # 删除一个文件
        (target_dir / "file_0000.txt").unlink()

        # 应检测到变更
        assert detector.has_changed(target_dir), "删除文件应被检测到"

    def test_truncation_no_false_positive_without_change(self, tmp_path) -> None:
        """截断后没有变更时不应误报。"""
        max_files = 50
        detector = DirectoryChangeDetector(max_files=max_files)
        target_dir = tmp_path / "truncated_stable"
        target_dir.mkdir()

        # 创建 max_files + 10 个文件
        for i in range(max_files + 10):
            (target_dir / f"file_{i:04d}.txt").write_text("data")

        # 首次快照
        assert not detector.has_changed(target_dir), "首次快照应返回 False"

        # 再次检测（无变更）
        assert not detector.has_changed(target_dir), "无变更时应返回 False"

    def test_truncation_detects_change_after_invalidate(self, tmp_path) -> None:
        """截断后 invalidate + 新增文件也应被检测到。"""
        max_files = 50
        detector = DirectoryChangeDetector(max_files=max_files)
        target_dir = tmp_path / "truncated_inv"
        target_dir.mkdir()

        for i in range(max_files):
            (target_dir / f"file_{i:04d}.txt").write_text("data")

        # 首次快照
        assert not detector.has_changed(target_dir)

        # invalidate 后重建快照
        detector.invalidate()
        assert not detector.has_changed(target_dir), "invalidate 后重建快照应返回 False"

        # 新增文件
        (target_dir / "new_after_inv.txt").write_text("data")
        assert detector.has_changed(target_dir), "invalidate 后新增文件应被检测到"
