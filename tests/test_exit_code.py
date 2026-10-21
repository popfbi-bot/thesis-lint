"""退出码（验收 5）：有 error -> 1；只有 warn -> 0；无问题 -> 0。"""

from __future__ import annotations

import os
import subprocess
import sys
import unittest

from tests.helpers import ROOT, TempProject, run_check
from core.checker import check_file
from core.model import Doc, Section
from core.presets import load_preset
from core.report import CheckResult
from core.rules.base import Issue


class TestExitCode(TempProject):
    def test_exit_code_error(self):
        path = self.copy_fixture("bad.docx", )
        result = run_check(path)
        self.assertTrue(result.errors)
        self.assertEqual(1, result.exit_code)

    def test_exit_code_clean(self):
        path = self.copy_fixture("good.docx")
        result = run_check(path)
        self.assertEqual([], result.issues)
        self.assertEqual(0, result.exit_code)

    def test_exit_code_warnings_only(self):
        """只有警告时不能返回 1。用空 Doc 之外的自造结果，避免依赖某份 fixture 的细节。"""
        result = CheckResult(Doc("x.docx"), load_preset("undergrad"),
                             [Issue("REF_NUMBERING", "warn", "参考文献列表", "a", "b", "c", "d")],
                             {"REF_NUMBERING": "参考文献序号连续性"})
        self.assertEqual(0, result.exit_code)
        self.assertEqual("0 errors, 1 warnings", result.summary)

    def test_cli_exit_code_error(self):
        proc = subprocess.run(
            [sys.executable, os.path.join(ROOT, "cli.py"), "check", self.copy_fixture("bad.docx"),
             "--no-color"],
            capture_output=True, text=True)
        self.assertEqual(1, proc.returncode, proc.stdout + proc.stderr)
        self.assertIn("errors", proc.stdout)

    def test_cli_exit_code_clean(self):
        proc = subprocess.run(
            [sys.executable, os.path.join(ROOT, "cli.py"), "check", self.copy_fixture("good.docx"),
             "--no-color"],
            capture_output=True, text=True)
        self.assertEqual(0, proc.returncode, proc.stdout + proc.stderr)
        self.assertIn("0 errors, 0 warnings", proc.stdout)


if __name__ == "__main__":
    unittest.main()
