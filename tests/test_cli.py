"""CLI 行为与报告渲染。"""

from __future__ import annotations

import os
import re
import subprocess
import sys
import unittest

from tests.helpers import ROOT, TempProject, run_check
from core.presets import list_presets, load_preset
from core.report import render_html, render_markdown, render_terminal


def cli(*args: str):
    return subprocess.run([sys.executable, os.path.join(ROOT, "cli.py"), *args],
                          capture_output=True, text=True, cwd=ROOT)


class TestCli(TempProject):
    def test_presets_lists_at_least_three(self):
        proc = cli("presets")
        self.assertEqual(0, proc.returncode, proc.stderr)
        for name in ("undergrad", "master", "gb-7714"):
            self.assertIn(name, proc.stdout)
            self.assertIn(name, list_presets())

    def test_every_preset_has_required_meta(self):
        for name in list_presets():
            with self.subTest(preset=name):
                data = load_preset(name)
                for key in ("name", "description", "source"):
                    self.assertTrue(str(data[key]).strip(), f"{name} 缺 {key}")

    def test_check_writes_reports(self):
        path = self.copy_fixture("bad.docx")
        md = os.path.join(self.tmp, "report.md")
        html = os.path.join(self.tmp, "report.html")
        proc = cli("check", path, "--out", md, "--html", html, "--no-color")
        self.assertEqual(1, proc.returncode)
        self.assertTrue(os.path.getsize(md) > 0)
        self.assertTrue(os.path.getsize(html) > 0)

    def test_unknown_preset_is_usage_error(self):
        proc = cli("check", self.copy_fixture("good.docx"), "--preset", "nope")
        self.assertEqual(2, proc.returncode)
        self.assertIn("找不到 preset", proc.stderr)

    def test_non_docx_is_usage_error(self):
        bogus = os.path.join(self.tmp, "not-a-docx.docx")
        with open(bogus, "w", encoding="utf-8") as fh:
            fh.write("hi")
        proc = cli("check", bogus)
        self.assertEqual(2, proc.returncode)
        self.assertIn("不是有效的 .docx", proc.stderr)


class TestReports(TempProject):
    def setUp(self) -> None:
        super().setUp()
        self.bad = run_check(self.copy_fixture("bad.docx"))
        self.good = run_check(self.copy_fixture("good.docx"))

    def test_terminal_summary_last_line(self):
        text = render_terminal(self.bad, color=False)
        last = [ln for ln in text.splitlines() if ln.strip()][-1]
        self.assertEqual("11 errors, 1 warnings", last)

    def test_markdown_lists_every_issue(self):
        text = render_markdown(self.bad)
        for issue in self.bad.issues:
            self.assertIn(issue.rule_id, text)
            self.assertIn(issue.fix_hint, text)
        self.assertIn("允许列出但未引用的条目", text)

    def test_html_is_single_file_and_offline(self):
        html = render_html(self.bad)
        self.assertTrue(html.lstrip().startswith("<!DOCTYPE html>"))
        self.assertIn("<style>", html)
        # 不能有任何外链：离线打开、截图都不该依赖网络
        self.assertIsNone(re.search(r"<link[^>]+href=", html))
        self.assertIsNone(re.search(r"<script", html))
        self.assertIsNone(re.search(r"src=[\"']https?:", html))
        self.assertNotIn("http://", html.replace("http://schemas", ""))

    def test_html_escapes_content(self):
        """论文正文里出现尖括号也不能破坏报告结构。"""
        from core.report import CheckResult
        from core.rules.base import Issue

        evil = Issue("INDENT", "error", '第 1 段「<script>alert(1)</script>」',
                     "<b>实际</b>", "&应&为&", "<i>改</i>", "依据")
        result = CheckResult(self.good.doc, self.good.preset, [evil], {"INDENT": "首行缩进"})
        html = render_html(result)
        self.assertNotIn("<script>alert(1)</script>", html)
        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", html)
        self.assertIn("&amp;应&amp;为&amp;", html)

    def test_good_html_shows_pass(self):
        html = render_html(self.good)
        self.assertIn("PASS", html)
        self.assertIn("全部通过", html)


if __name__ == "__main__":
    unittest.main()
