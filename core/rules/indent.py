"""规则 5：首行缩进。

依据：GB/T 7713.1—2006 6.3.1「正文每段起行空两字」；
      GB/T 7713.1—2006 6.4「图表题注、参考文献条目另行编排，不再缩进」。
正文必须缩进 2 字符；标题、图表题注、参考文献条目不得缩进。
"""

from __future__ import annotations

from typing import List

from ..model import Doc, Paragraph, Role
from .base import LEVEL_ERROR, Rule


class Indent(Rule):
    RULE_ID = "INDENT"
    TITLE = "首行缩进"
    SOURCE = "GB/T 7713.1—2006 6.3.1（正文缩进 2 字）、6.4（题注/参考文献不缩进）"

    @classmethod
    def check(cls, doc: Doc, preset: dict) -> List[Issue]:
        expected_chars = float(preset["body"]["first_line_indent_chars"])
        issues: List[Issue] = []

        for p in doc.paragraphs:
            if p.role == Role.BODY:
                if not _matches(p, expected_chars):
                    issues.append(cls.issue(
                        LEVEL_ERROR, p.location, _describe(p),
                        f"首行缩进 {expected_chars:g} 字符",
                        "段落 → 特殊格式 → 首行缩进 2 字符"))
            elif p.role in (Role.HEADING, Role.CAPTION, Role.REF_ENTRY):
                if _has_indent(p):
                    issues.append(cls.issue(
                        LEVEL_ERROR, p.location, _describe(p), "无首行缩进",
                        _what(p.role)))
        return issues


def _describe(p: Paragraph) -> str:
    if p.first_line_chars is not None:
        return f"首行缩进 {p.first_line_chars:g} 字符"
    if p.first_line_twips is not None:
        return f"首行缩进 {p.first_line_twips} twips"
    return "无首行缩进"


def _has_indent(p: Paragraph) -> bool:
    if p.first_line_chars is not None:
        return abs(p.first_line_chars) > 0.05
    if p.first_line_twips is not None:
        return abs(p.first_line_twips) > 1
    return False


def _matches(p: Paragraph, expected_chars: float) -> bool:
    if p.first_line_chars is not None:
        return abs(p.first_line_chars - expected_chars) <= 0.05
    if p.first_line_twips is not None:
        return abs(p.first_line_twips - expected_chars * 100) <= 1
    return False


def _what(role: str) -> str:
    return {
        Role.HEADING: "把标题的首行缩进改为「无」",
        Role.CAPTION: "题注通常居中、不缩进：特殊格式改为「无」",
        Role.REF_ENTRY: "参考文献条目顶格排版：特殊格式改为「无」",
    }.get(role, "特殊格式改为「无」")


RULE_ID = Indent.RULE_ID
TITLE = Indent.TITLE
SOURCE = Indent.SOURCE


def check(doc: Doc, preset: dict) -> List[Issue]:
    return Indent.check(doc, preset)
