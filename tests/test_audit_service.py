from __future__ import annotations

import json
import zipfile
from datetime import datetime
from pathlib import Path

from backend.services import audit_service as audit_module
from backend.services.audit_service import AuditService


class TestAuditServiceGet:
    """验证 AuditService.get() 的 limit 参数合规。"""

    def test_clamps_file_scan_limit_above_500(self, tmp_path, monkeypatch) -> None:
        monkeypatch.setattr(audit_module, "_PROJECT_ROOT", tmp_path)
        log_dir = tmp_path / "logs" / datetime.now().strftime("%Y-%m-%d")
        log_dir.mkdir(parents=True)
        log_file = log_dir / "run.jsonl"
        lines = [
            json.dumps({
                "timestamp": "",
                "extra": {"event_type": "audit", "action": f"action_{i}", "params": {}, "result": ""},
            })
            for i in range(600)
        ]
        log_file.write_text("\n".join(lines), encoding="utf-8")

        service = AuditService()

        result = service.get(limit=9999)

        assert len(result) == 500

    def test_clamps_limit_below_1(self) -> None:
        service = AuditService()
        service.log("test")
        result = service.get(limit=0)
        assert len(result) == 1  # 至少返回 1 条

    def test_clamps_limit_negative(self) -> None:
        service = AuditService()
        service.log("test")
        result = service.get(limit=-5)
        assert len(result) == 1

    def test_passes_valid_limit_through(self) -> None:
        service = AuditService()
        for i in range(10):
            service.log(f"action_{i}")
        result = service.get(limit=5)
        assert len(result) == 5

    def test_fallback_on_invalid_type(self) -> None:
        service = AuditService()
        service.log("test")
        result = service.get(limit="abc")  # type: ignore[arg-type]
        assert len(result) == 1


class TestAuditServiceZipMemberSize:
    """验证 _scan_zip_file 跳过超大 zip member。"""

    def test_skips_oversized_jsonl_member(self, tmp_path) -> None:
        """超过 10 MiB 的 jsonl member 应被跳过。"""
        zip_path = tmp_path / "test.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            # 写入一个正常大小的文件
            normal_rec = json.dumps({
                "event_type": "audit",
                "extra": {"action": "normal", "params": {}},
            })
            zf.writestr("normal.jsonl", normal_rec)
            # 写入一个超大 member（超过 10 MiB）
            oversized_content = "x" * (11 * 1024 * 1024)
            zf.writestr("oversized.jsonl", oversized_content)

        records: list[dict] = []
        AuditService._scan_zip_file(zip_path, records, limit=100)

        # 只应包含 normal 记录，超大 member 被跳过
        assert len(records) == 1
        assert records[0]["action"] == "normal"

    def test_handles_empty_zip_gracefully(self, tmp_path) -> None:
        """空 zip 不应抛出异常。"""
        zip_path = tmp_path / "empty.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            pass  # 空 zip

        records: list[dict] = []
        # 不应抛出异常
        AuditService._scan_zip_file(zip_path, records, limit=100)
        assert len(records) == 0

    def test_skips_non_jsonl_members(self, tmp_path) -> None:
        """非 .jsonl 文件应被跳过。"""
        zip_path = tmp_path / "test.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("notes.txt", "some text")
            zf.writestr("data.csv", "a,b,c\n1,2,3")

        records: list[dict] = []
        AuditService._scan_zip_file(zip_path, records, limit=100)
        assert len(records) == 0

    def test_skips_oversized_but_keeps_normal(self, tmp_path) -> None:
        """超大 member 被跳过，但正常 member 仍被读取。"""
        zip_path = tmp_path / "mixed.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            # 正常 member
            for i in range(3):
                rec = json.dumps({
                    "event_type": "audit",
                    "extra": {"action": f"action_{i}", "params": {}},
                })
                zf.writestr(f"log_{i}.jsonl", rec)
            # 超大 member
            zf.writestr("huge.jsonl", "x" * (11 * 1024 * 1024))

        records: list[dict] = []
        AuditService._scan_zip_file(zip_path, records, limit=100)
        assert len(records) == 3
        actions = [r["action"] for r in records]
        assert "action_0" in actions
        assert "action_1" in actions
        assert "action_2" in actions
