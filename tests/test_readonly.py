"""只读测试（验收 6）：跑前后对输入文件取 sha256，必须一致；也不留下临时目录残留。"""

from __future__ import annotations

import glob
import hashlib
import os
import tempfile
import unittest

from tests.helpers import ROOT, TempProject, run_check


def sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


class TestReadOnly(TempProject):
    def test_check_does_not_modify_input(self):
        for name in ("good.docx", "bad.docx"):
            with self.subTest(fixture=name):
                path = self.copy_fixture(name)
                before = sha256(path)
                run_check(path)
                self.assertEqual(before, sha256(path), f"{name} 被修改了")

    def test_check_does_not_create_files_beside_input(self):
        path = self.copy_fixture("bad.docx")
        workdir = os.path.dirname(path)
        before = set(os.listdir(workdir))
        run_check(path)
        self.assertEqual(before, set(os.listdir(workdir)), "检查过程产生了新的文件")

    def test_check_does_not_touch_repo_fixtures(self):
        """直接检查版本库里的 fixture（不拷贝）也不能改动它。"""
        path = os.path.join(ROOT, "fixtures", "good.docx")
        before = sha256(path)
        run_check(path)
        self.assertEqual(before, sha256(path))

    def test_report_writing_only_creates_requested_files(self):
        from core.report import write_outputs

        path = self.copy_fixture("bad.docx")
        outdir = tempfile.mkdtemp(dir=self.tmp)
        md = os.path.join(outdir, "report.md")
        html = os.path.join(outdir, "report.html")
        write_outputs(run_check(path), md, html)
        self.assertEqual({"report.md", "report.html"}, set(os.listdir(outdir)))
        self.assertFalse(glob.glob(os.path.join(outdir, "*~")))


if __name__ == "__main__":
    unittest.main()
