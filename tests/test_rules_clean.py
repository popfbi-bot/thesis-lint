"""正例测试：合规数据不得误报（判据 4）。

和反例测试成对出现：只有反例会红、正例不红的规则，才是真的在判断格式。
"""

from __future__ import annotations

import unittest

from tests.helpers import ALL_RULE_IDS, TempProject, rule_ids, run_check


class TestNoFalsePositive(TempProject):
    def issues_of(self, rule_id: str, path=None, preset: str = "undergrad"):
        path = path or self.copy_fixture("good.docx")
        result = run_check(path, preset)
        return [i for i in result.issues if i.rule_id == rule_id], result

    def test_PAGE_MARGIN_no_false_positive(self):
        issues, _ = self.issues_of("PAGE_MARGIN")
        self.assertEqual([], issues, f"合规文档被误报：{[(i.location, i.actual) for i in issues]}")

    def test_BODY_FONT_no_false_positive(self):
        issues, _ = self.issues_of("BODY_FONT")
        self.assertEqual([], issues, f"合规文档被误报：{[(i.location, i.actual) for i in issues]}")

    def test_HEADING_LEVEL_no_false_positive(self):
        issues, _ = self.issues_of("HEADING_LEVEL")
        self.assertEqual([], issues, f"合规文档被误报：{[(i.location, i.actual) for i in issues]}")

    def test_LINE_SPACING_no_false_positive(self):
        issues, _ = self.issues_of("LINE_SPACING")
        self.assertEqual([], issues, f"合规文档被误报：{[(i.location, i.actual) for i in issues]}")

    def test_INDENT_no_false_positive(self):
        issues, _ = self.issues_of("INDENT")
        self.assertEqual([], issues, f"合规文档被误报：{[(i.location, i.actual) for i in issues]}")

    def test_REF_NUMBERING_no_false_positive(self):
        issues, _ = self.issues_of("REF_NUMBERING")
        self.assertEqual([], issues, f"合规文档被误报：{[(i.location, i.actual) for i in issues]}")

    def test_good_docx_has_zero_issues(self):
        result = run_check(self.copy_fixture("good.docx"))
        self.assertEqual([], [(i.rule_id, i.location, i.actual) for i in result.issues])
        self.assertEqual(0, result.exit_code)
        self.assertEqual("0 errors, 0 warnings", result.summary)

    def test_master_preset_good_docx_has_zero_issues(self):
        """固定值行距的 preset 同样不能误报——证明判据不是写死 1.5 倍。"""
        result = run_check(self.copy_fixture("master_good.docx"), preset="master")
        self.assertEqual([], [(i.rule_id, i.location, i.actual) for i in result.issues])
        self.assertEqual(0, result.exit_code)

    def test_undergrad_preset_on_master_doc_reports_line_spacing(self):
        """反向确认 preset 真的在起作用：同一份固定值行距文档，按 1.5 倍规范检查必须报错。"""
        result = run_check(self.copy_fixture("master_good.docx"), preset="undergrad")
        self.assertIn("LINE_SPACING", rule_ids(result))
        self.assertGreater(result.exit_code, 0)


if __name__ == "__main__":
    unittest.main()
