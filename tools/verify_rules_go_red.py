#!/usr/bin/env python3
"""证明每条规则「会失败」。

把规则里的 `return issues` 改成 `return []`（等于让规则永远通过），跑对应的
反例测试——必须变红；随后恢复文件，全量测试必须变绿。

用途：防止「永远绿的死规则」混进来。验收时直接跑：
    python3 tools/verify_rules_go_red.py
"""

import subprocess, sys, os, shutil, re

RULES = {
    "PAGE_MARGIN": ("core/rules/page_margin.py", "        return issues\n\n\nRULE_ID"),
    "BODY_FONT": ("core/rules/body_font.py", "        return issues\n\n\ndef describe_line_config"),
    "HEADING_LEVEL": ("core/rules/heading_level.py", "        return issues\n\n\nRULE_ID"),
    "LINE_SPACING": ("core/rules/line_spacing.py", "        return issues\n\n\ndef _key"),
    "INDENT": ("core/rules/indent.py", "        return issues\n\n\ndef _describe"),
    "REF_NUMBERING": ("core/rules/ref_numbering.py", "        return issues\n\n\ndef _all_entries"),
}

for rule, (path, anchor) in RULES.items():
    src = open(path, encoding="utf-8").read()
    backup = src
    assert anchor in src, f"{rule}: anchor not found"
    # 把「返回 issues」换成「永远返回空」
    src = src.replace(anchor, anchor.replace("        return issues", "        return []", 1), 1)
    open(path, "w", encoding="utf-8").write(src)
    try:
        test = f"tests.test_rules_detection.TestEachRuleIsDetected.test_{rule}_is_detected"
        proc = subprocess.run([sys.executable, "-m", "unittest", test],
                              capture_output=True, text=True)
        verdict = "RED (as expected)" if proc.returncode != 0 else "STILL GREEN ✗"
        print(f"{rule:15s} -> {verdict}")
    finally:
        open(path, "w", encoding="utf-8").write(backup)

# 再确认恢复后全绿
proc = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-t", "."],
                      capture_output=True, text=True)
print("\nrestored:", proc.stderr.strip().splitlines()[-1])
