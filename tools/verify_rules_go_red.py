#!/usr/bin/env python3
"""证明每条规则「会失败」。

做法：把规则里的 `return issues` 改成 `return []`（等于让规则永远通过），跑对应的
反例测试——必须变红；随后恢复文件，全量测试必须变绿。

「变红」要有证据，不能只看退出码：测试可能因为 import 失败、fixture 丢失、断言写错
而变红，那和「规则真的检出问题」是两回事。所以这里额外校验两条：

1. 变红前，该测试必须先是绿的（先跑一遍未改动的版本）；
2. 变红时，失败信息里必须出现该测试自己的断言文案，而不是 ImportError / AttributeError。

用法：
    python3 tools/verify_rules_go_red.py
"""

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

#: rule_id -> (规则文件, 要替换的锚点)
RULES = {
    "PAGE_MARGIN": ("core/rules/page_margin.py", "        return issues\n\n\nRULE_ID"),
    "BODY_FONT": ("core/rules/body_font.py", "        return issues\n\n\ndef describe_line_config"),
    "HEADING_LEVEL": ("core/rules/heading_level.py", "        return issues\n\n\nRULE_ID"),
    "LINE_SPACING": ("core/rules/line_spacing.py", "        return issues\n\n\ndef _key"),
    "INDENT": ("core/rules/indent.py", "        return issues\n\n\ndef _describe"),
    "REF_NUMBERING": ("core/rules/ref_numbering.py", "        return issues\n\n\ndef _all_entries"),
}

TEST = "tests.test_rules_detection.TestEachRuleIsDetected.test_{rule}_is_detected"

#: 断言文案里必然出现的片段，用来确认「红」是这条断言造成的。
EVIDENCE = "没有被检出"

#: 这些异常说明测试本身坏了，而不是规则漏检，不能算作有效证据。
BROKEN_TEST_MARKERS = ("ImportError", "ModuleNotFoundError", "AttributeError", "SyntaxError")


def run_test(rule: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "unittest", TEST.format(rule=rule)],
        capture_output=True,
        text=True,
        cwd=str(ROOT),
    )


def _reason(proc: subprocess.CompletedProcess) -> str:
    return (proc.stderr or "") + (proc.stdout or "")


def main() -> int:
    failures: list[str] = []

    for rule, (rel_path, anchor) in RULES.items():
        path = ROOT / rel_path
        original = path.read_text(encoding="utf-8")
        if anchor not in original:
            failures.append(f"{rule}: 锚点没找到（{rel_path} 结构变了？）")
            print(f"{rule:15s} -> SKIP（锚点没找到）")
            continue

        # 1) 先确认这个测试原本是绿的，否则「变红」毫无意义。
        baseline = run_test(rule)
        if baseline.returncode != 0:
            failures.append(f"{rule}: 测试在规则完好时就是红的，无法作为证据")
            print(f"{rule:15s} -> INVALID（规则完好时测试已经红了）")
            continue

        # 2) 让规则永远通过，测试必须变红，且失败原因必须是指定断言。
        path.write_text(original.replace(anchor, anchor.replace("        return issues", "        return []", 1), 1), encoding="utf-8")
        try:
            proc = run_test(rule)
            output = _reason(proc)
        finally:
            path.write_text(original, encoding="utf-8")

        if proc.returncode == 0:
            failures.append(f"{rule}: 规则被改成永远通过后，测试仍然绿")
            print(f"{rule:15s} -> STILL GREEN ✗")
            continue

        if any(marker in output for marker in BROKEN_TEST_MARKERS):
            failures.append(f"{rule}: 变红是因为测试自身异常，不是检出失败")
            print(f"{rule:15s} -> RED FOR WRONG REASON ✗")
            continue

        if EVIDENCE not in output:
            failures.append(f"{rule}: 变红但没命中预期断言（缺少「{EVIDENCE}」）")
            print(f"{rule:15s} -> RED FOR WRONG REASON ✗")
            continue

        print(f"{rule:15s} -> RED (as expected)")

    # 3) 全部恢复后，测试必须绿。
    # 默认跑全量；被 tests/test_verify_red_tool.py 包在子进程里调用时，它会把
    # THESIS_LINT_VERIFY_SUBSET=1 传进来，此时只跑规则相关用例——否则那份全量
    # 测试里又包含本文件的用例，会一层层复制工程、一直递归下去。
    subset = os.environ.get("THESIS_LINT_VERIFY_SUBSET") == "1"
    command = (
        [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-t", ".", "-p", "test_rules*.py"]
        if subset
        else [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-t", "."]
    )
    restored = subprocess.run(command, capture_output=True, text=True, cwd=str(ROOT))
    # unittest 把结果写在 stderr，但最后一行不一定是结论（可能是空的尾巴），
    # 所以取 "OK"/"FAILED" 那一行来打印，并以退出码判定成败。
    lines = [line for line in (restored.stderr or "").splitlines() if line.strip()]
    verdict = next((line for line in reversed(lines) if line.startswith(("OK", "FAILED"))), "NO RESULT")
    print(f"\nrestored: {verdict}")
    if restored.returncode != 0:
        failures.append(f"恢复后测试没有变绿（{verdict}）")
        for line in lines[-15:]:
            print("   ", line)

    if failures:
        print("\nFAILED:")
        for failure in failures:
            print("  -", failure)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
