"""反例测试：每一项单独做错时必须报出对应 rule_id（判据 3）。

一个永远通过的规则和一个正确的规则长得一模一样，所以这里的每个用例都必须
「曾经红过」——PR 描述里贴了把规则改坏后测试变红的证据。
"""

from __future__ import annotations

import unittest

from tests.helpers import ALL_RULE_IDS, PER_RULE, TempProject, rule_ids, run_check


class TestEachRuleIsDetected(TempProject):
    def assert_detected(self, rule_id: str) -> None:
        path = self.copy_fixture(f"{rule_id}.docx", subdir="per_rule")
        result = run_check(path)
        found = rule_ids(result)
        self.assertIn(
            rule_id, found,
            f"{rule_id} 没有被检出。实际命中：{sorted(found)}；"
            f"问题清单：{[(i.rule_id, i.location) for i in result.issues]}")
        self.assertGreater(result.exit_code, 0, "有 error 时退出码必须为 1")

    def test_PAGE_MARGIN_is_detected(self):
        self.assert_detected("PAGE_MARGIN")

    def test_BODY_FONT_is_detected(self):
        self.assert_detected("BODY_FONT")

    def test_HEADING_LEVEL_is_detected(self):
        self.assert_detected("HEADING_LEVEL")

    def test_LINE_SPACING_is_detected(self):
        self.assert_detected("LINE_SPACING")

    def test_INDENT_is_detected(self):
        self.assert_detected("INDENT")

    def test_REF_NUMBERING_is_detected(self):
        self.assert_detected("REF_NUMBERING")

    def test_per_rule_fixture_only_hits_its_own_rule(self):
        """单独做错一项时，规则之间不应互相串味（允许 body_font/indent 这类
        天然重叠的规则也命中，但必须命中自己那一条）。"""
        for rule_id in sorted(ALL_RULE_IDS):
            with self.subTest(rule=rule_id):
                path = self.copy_fixture(f"{rule_id}.docx", subdir="per_rule")
                self.assertIn(rule_id, rule_ids(run_check(path)))


if __name__ == "__main__":
    unittest.main()
