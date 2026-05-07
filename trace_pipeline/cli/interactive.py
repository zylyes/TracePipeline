"""交互式目标选择。"""
from __future__ import annotations

import re
from collections.abc import Sequence
from typing import List

from ..io.discovery import TraceFile

__all__ = ["select_targets_interactive"]


def _parse_selection(raw: str, max_n: int) -> List[int]:
    """解析用户输入的索引字符串，返回 0-based 索引列表。"""
    cleaned = raw.strip().lower()
    if cleaned in ("", "all", "a"):
        return list(range(max_n))

    selected: List[int] = []
    for token in re.split(r"\s*,\s*", cleaned):
        token = token.strip()
        if not token:
            continue
        if "-" in token:
            parts = token.split("-", 1)
            try:
                lo, hi = int(parts[0]), int(parts[1])
            except ValueError:
                raise ValueError(f"无效区间: {token}")
            if lo < 1 or hi > max_n or lo > hi:
                raise ValueError(f"区间 {lo}-{hi} 超出范围 1-{max_n}")
            selected.extend(range(lo - 1, hi))
        else:
            try:
                idx = int(token)
            except ValueError:
                raise ValueError(f"无效索引: {token}")
            if idx < 1 or idx > max_n:
                raise ValueError(f"索引 {idx} 超出范围 1-{max_n}")
            selected.append(idx - 1)

    if not selected:
        raise ValueError("未选择任何目标")
    return sorted(set(selected))


def select_targets_interactive(discovered: Sequence[TraceFile]) -> List[TraceFile]:
    """交互式选择处理目标。"""
    if not discovered:
        print("没有可用的迹线表文件。")
        return []

    print(f"\n发现 {len(discovered)} 个迹线表文件:\n")
    for i, tf in enumerate(discovered, start=1):
        print(f"  [{i:>3}]  {tf.stem}  (露头: {tf.outcrop})")

    print("\n输入要处理的编号（支持: all / 1,3,5 / 1-5 / 1,3-5,7）")
    while True:
        try:
            raw = input(">>> ").strip()
            indices = _parse_selection(raw, len(discovered))
            chosen = [discovered[i] for i in indices]
            print(f"已选择 {len(chosen)} 个目标: {', '.join(tf.stem for tf in chosen)}")
            return chosen
        except ValueError as exc:
            print(f"输入无效: {exc}，请重新输入")
        except (EOFError, KeyboardInterrupt):
            print("\n已取消")
            return []
