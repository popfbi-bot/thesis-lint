"""核心判据（验收 2）：bad.docx 在 6 个维度各错一处，必须报出 >=6 个 error，
且 rule_id 互不相同、覆盖全部 6 条规则。

如果 bad.docx 只报出 3 个错，就说明有 3 条规则是「永远绿」的死规则。
"""

from __future__ import annotations

import unittest

from tests.helpers import ALL_RULE_IDS, TempProject, rule_ids, run_check


class TestBadDocx(TempProject):
    def setUp(self) -> None:
        super().setUp()
        self.path = self.copy_fixture("bad.docx")
        self.result = run_check(self.path)

    def test_at_least_six_errors(self):
        self.assertGreaterEqual(
            len(self.result.errors), 6,
            f"bad.docx 只报出 {len(self.result.errors)} 个 error："
            f"{[(i.rule_id, i.location) for i in self.result.errors]}")

    def test_covers_all_six_rules(self):
        covered = rule_ids(self.result)
        self.assertEqual(
            ALL_RULE_IDS, covered,
            f"未覆盖的规则：{sorted(ALL_RULE_IDS - covered)}")

    def test_error_rule_ids_are_distinct_per_dimension(self):
        """每个 error 的 rule_id 都应来自 6 条规则之一，且 6 条都至少有一个 error。"""
        error_rules = {i.rule_id for i in self.result.errors}
        self.assertEqual(ALL_RULE_IDS, error_rules)

    def test_every_issue_has_actionable_fields(self):
        for issue in self.result.issues:
            with self.subTest(rule=issue.rule_id, loc=issue.location):
                self.assertTrue(issue.location, "location 不能为空")
                # 段落级问题要指到「第 N 段」，页面级问题要指到「第 N 节」
                self.assertRegex(issue.location, r"第 \d+ (段|节)|参考文献列表")
                self.assertTrue(issue.actual)
                self.assertTrue(issue.expected)
                self.assertTrue(issue.fix_hint)
                self.assertTrue(issue.source, "每条问题都要可追溯到依据")
                self.assertIn(issue.level, ("error", "warn"))

    def test_location_contains_paragraph_index_and_snippet(self):
        """location 要能让用户真的找到位置：段落序号 + 前 20 字摘要。"""
        loc = [i for i in self.result.issues if i.location.startswith("第 3 段")][0]
        self.assertIn("「", loc.location)
        self.assertIn("这一段的中文字体", loc.location)

    def test_exit_code_is_one(self):
        self.assertEqual(1, self.result.exit_code)


if __name__ == "__main__":
    unittest.main()
