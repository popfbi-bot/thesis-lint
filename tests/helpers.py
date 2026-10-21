"""测试公共工具：跑 check、收集 issue、构造最小 docx。"""

from __future__ import annotations

import os
import shutil
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

FIXTURES = os.path.join(ROOT, "fixtures")
PER_RULE = os.path.join(FIXTURES, "per_rule")

# 验收判据要求的 6 条规则
ALL_RULE_IDS = {
    "PAGE_MARGIN",
    "BODY_FONT",
    "HEADING_LEVEL",
    "LINE_SPACING",
    "INDENT",
    "REF_NUMBERING",
}


def run_check(path: str, preset: str = "undergrad"):
    from core.checker import check_file
    from core.presets import load_preset
    return check_file(path, load_preset(preset))


def rule_ids(result) -> set:
    return {i.rule_id for i in result.issues}


def fixture(*parts: str) -> str:
    return os.path.join(FIXTURES, *parts)


class TempProject(unittest.TestCase):
    """把 fixture 拷到临时目录再检查，保证测试不会碰到版本库里的文件。"""

    def setUp(self) -> None:
        self.tmp = tempfile.mkdtemp(prefix="thesis-lint-test-")

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def copy_fixture(self, name: str, *, subdir: str = "") -> str:
        src = fixture(subdir, name) if subdir else fixture(name)
        dst = os.path.join(self.tmp, name)
        shutil.copyfile(src, dst)
        return dst
