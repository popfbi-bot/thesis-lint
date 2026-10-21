"""把解析 + 规则 + 结果串起来。cli 与测试都走这里，保证口径一致。"""

from __future__ import annotations

from typing import Dict, List

from .docx import load
from .report import CheckResult
from .rules import RULES


def check_file(path: str, preset: dict) -> CheckResult:
    doc = load(path)
    issues: List = []
    titles: Dict[str, str] = {}
    for rule in RULES:
        titles[rule.RULE_ID] = rule.TITLE
        issues.extend(rule.check(doc, preset))
    return CheckResult(doc, preset, issues, titles)
