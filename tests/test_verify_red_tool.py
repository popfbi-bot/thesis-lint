"""守卫「证明规则会失败」的那个工具本身。

`tools/verify_rules_go_red.py` 是验收判据 7 的证据来源。如果它只会看退出码，
那么一个「因为 import 失败而变红」的测试也会被它认成「规则确实检出了」——
证据就成了假的。这里验证它在两种假红面前都会拒绝。
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOOL = "tools/verify_rules_go_red.py"
TEST_FILE = "tests/test_rules_detection.py"

#: 本文件每跑一次要复制工程并起 7 个子进程（约 2 分钟），因此默认不参与
#: `unittest discover`。改工具时显式开关跑它：THESIS_LINT_SLOW_TESTS=1
SLOW = os.environ.get("THESIS_LINT_SLOW_TESTS") == "1"


@unittest.skipUnless(SLOW, "慢测试：设 THESIS_LINT_SLOW_TESTS=1 才运行")
class TestVerifyRedTool(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="thesis-lint-verify-"))
        self.project = self.tmp / "project"
        shutil.copytree(
            ROOT,
            self.project,
            ignore=shutil.ignore_patterns(*self._COPY_EXCLUDES),
        )

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    #: 工具恢复后会跑一遍测试；本文件也会复制工程再跑一次工具，于是层层递归。
    #: 复制工程时把本文件排除掉，并给内层一个标记，让它只跑规则相关用例。
    _COPY_EXCLUDES = (".git", "__pycache__", ".pytest_cache", "tests/test_verify_red_tool.py")

    def _run(self) -> subprocess.CompletedProcess:
        try:
            env = {**os.environ, "THESIS_LINT_VERIFY_SUBSET": "1"}
            return subprocess.run(
                [sys.executable, TOOL],
                capture_output=True,
                text=True,
                cwd=str(self.project),
                timeout=180,
                env=env,
            )
        except subprocess.TimeoutExpired:  # pragma: no cover - 递归没断掉时给出明确信号
            self.fail("verify 工具超时：内层测试递归调用了它自己")

    def _patch(self, relative: str, old: str, new: str) -> None:
        path = self.project / relative
        text = path.read_text(encoding="utf-8")
        self.assertIn(old, text, f"{relative} 里没找到要替换的片段")
        path.write_text(text.replace(old, new, 1), encoding="utf-8")

    def test_tool_passes_on_clean_tree(self):
        result = self._run()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("RED (as expected)", result.stdout)

    def test_tool_rejects_test_that_is_already_red(self):
        """规则完好、测试自己坏了：不能算「规则会失败」的证据。"""
        self._patch(
            TEST_FILE,
            "def test_PAGE_MARGIN_is_detected(self):",
            "def test_PAGE_MARGIN_is_detected(self):\n        import nonexistent_module_xyz",
        )
        result = self._run()
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertIn("INVALID", result.stdout)

    def test_tool_rejects_red_without_expected_assertion(self):
        """变红但没有命中预期断言文案：同上，证据不成立。"""
        self._patch(TEST_FILE, f'f"{{rule_id}} 没有被检出。实际命中', 'f"{rule_id} 缺失。实际命中')
        result = self._run()
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertIn("RED FOR WRONG REASON", result.stdout)


if __name__ == "__main__":
    unittest.main()
