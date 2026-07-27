#!/usr/bin/env python3
"""Tests for the offline LINUX DO draft auditor."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "audit_draft", SCRIPT_DIR / "audit_draft.py"
)
assert SPEC and SPEC.loader
AUDIT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(AUDIT)


class AuditDraftTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        references = SCRIPT_DIR.parent / "references"
        cls.categories = AUDIT.load_json(references / "category-rules.json")
        cls.checklists = AUDIT.load_json(
            references / "post-type-checklists.json"
        )

    def audit(self, payload):
        return AUDIT.audit_payload(payload, self.categories, self.checklists)

    def test_ai_assisted_text_is_blocked(self):
        report = self.audit(
            {
                "title": "测试",
                "body": "这是用户提供的完整测试正文，用于验证离线检查器能够识别明确声明的 AI 辅助信息。",
                "category": "开发调优",
                "post_type": "general",
                "tags": [],
                "metadata": {"ai_assisted": True},
            }
        )
        self.assertEqual(report["verdict"], "DO_NOT_POST")
        self.assertTrue(
            any(item["code"] == "CORE-001" for item in report["findings"])
        )

    def test_cloud_drive_requires_category_and_provider_tags(self):
        report = self.audit(
            {
                "title": "资源分享",
                "body": "这是一个包含多个网盘链接的资源说明，正文包含资源范围、来源和使用环境，供测试规则使用。",
                "category": "资源荟萃",
                "post_type": "cloud_drive",
                "tags": ["夸克网盘"],
                "metadata": {
                    "resource_name": "示例资源",
                    "description": "测试数据",
                    "source": "自有文件",
                    "drive_providers": ["夸克网盘", "百度网盘"],
                    "browser_accessible": True,
                    "ai_assisted": False
                },
            }
        )
        codes = {item["code"] for item in report["findings"]}
        self.assertIn("CATEGORY-004", codes)
        self.assertIn("DRIVE-002", codes)
        self.assertEqual(report["verdict"], "NEEDS_CHANGES")

    def test_complete_help_post_reaches_manual_review_only(self):
        report = self.audit(
            {
                "title": "程序启动失败排查",
                "body": "我在本地测试环境中遇到启动失败。这里是我自己写的背景、复现步骤和观察结果，正文长度足够用于审核。",
                "category": "开发调优",
                "post_type": "help",
                "tags": ["求助"],
                "metadata": {
                    "environment": "Linux, Python 3.13",
                    "attempted": "检查依赖和日志",
                    "error_or_symptom": "进程退出",
                    "expected": "正常启动",
                    "ai_assisted": False
                },
            }
        )
        self.assertNotEqual(report["verdict"], "DO_NOT_POST")
        self.assertNotEqual(report["verdict"], "NEEDS_CHANGES")

    def test_short_link_is_blocked(self):
        report = self.audit(
            {
                "title": "链接测试",
                "body": "这是用户自行撰写的测试正文，包含一个用于验证短链识别逻辑的外部地址，请勿实际访问。",
                "category": "搞七捻三",
                "post_type": "general",
                "tags": [],
                "links": ["https://bit.ly/example"],
                "metadata": {"ai_assisted": False},
            }
        )
        self.assertEqual(report["verdict"], "DO_NOT_POST")
        self.assertTrue(
            any(item["code"] == "LINK-001" for item in report["findings"])
        )


if __name__ == "__main__":
    unittest.main()
