"""真实入口（默认 CLI，不加 --no-color）的着色路径。

历史 bug：_COLOR 缺 "red"/"yellow"，只要检出 error 就 KeyError，
而 57 个测试全绿——因为没人跑过默认入口。这个模块专治这种「测试绿 ≠ 能用」。
"""

from __future__ import annotations

import ast
import os
import subprocess
import sys
import unittest

from tests.helpers import ALL_RULE_IDS, ROOT, TempProject


def cli(*args: str):
    """跑真实入口。不传 --no-color：这里要覆盖的就是默认路径。"""
    env = dict(os.environ)
    env.pop("NO_COLOR", None)  # NO_COLOR 会把默认路径降级成无色，绕开着色分支
    return subprocess.run([sys.executable, os.path.join(ROOT, "cli.py"), *args],
                          capture_output=True, text=True, cwd=ROOT, env=env)


class TestDefaultCliPath(TempProject):
    def test_cli_default_color_on_error_doc_does_not_crash(self):
        proc = cli("check", self.copy_fixture("bad.docx"))
        self.assertEqual(1, proc.returncode, proc.stdout + proc.stderr)
        self.assertNotIn("Traceback", proc.stderr)
        for rule_id in ALL_RULE_IDS:
            with self.subTest(rule_id=rule_id):
                self.assertIn(rule_id, proc.stdout)

    def test_cli_default_color_on_clean_doc(self):
        proc = cli("check", self.copy_fixture("good.docx"))
        self.assertEqual(0, proc.returncode, proc.stdout + proc.stderr)
        self.assertIn("0 errors", proc.stdout)

    def test_cli_html_output_created(self):
        path = self.copy_fixture("bad.docx")
        report = os.path.join(self.tmp, "report.html")
        proc = cli("check", path, "--html", report)
        self.assertEqual(1, proc.returncode, proc.stdout + proc.stderr)
        self.assertTrue(os.path.getsize(report) > 0)
        with open(report, encoding="utf-8") as fh:
            html = fh.read()
        for forbidden in ("http://", "https://", "<script src=", '<link rel="stylesheet"'):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, html)

    def test_every_color_key_exists(self):
        """静态扫描 report.py：c(...) 里用到的颜色键必须都在 _COLOR 里登记过。"""
        from core.report import _COLOR

        with open(os.path.join(ROOT, "core", "report.py"), encoding="utf-8") as fh:
            tree = ast.parse(fh.read())

        registered = set(_COLOR)
        used: set[str] = set()
        for node in ast.walk(tree):
            if not (isinstance(node, ast.Call) and getattr(node.func, "id", None) == "c"):
                continue
            for arg in node.args[1:]:
                # 常量、以及 "a" if cond else "b" 这类条件式都要拆开看
                used |= {n.value for n in ast.walk(arg) if isinstance(n, ast.Constant)}
        keys = {k for k in used if isinstance(k, str)}
        self.assertEqual(set(), keys - registered,
                         f"report.py 用了未登记的颜色键：{sorted(keys - registered)}")

        # 反向验证：c() 真的会查表，用渲染一遍的方式把每个已登记键都走一次
        from core.model import Doc
        from core.presets import load_preset
        from core.report import CheckResult, render_terminal
        from core.rules.base import Issue

        issues = [Issue("INDENT", "error", "L", "a", "b", "c", "d"),
                  Issue("REF_NUMBERING", "warn", "L", "a", "b", "c", "d")]
        result = CheckResult(Doc("x.docx"), load_preset("undergrad"), issues, {})
        rendered = render_terminal(result, color=True)
        self.assertIn("\033[", rendered)


if __name__ == "__main__":
    unittest.main()
