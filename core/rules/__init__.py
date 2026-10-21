"""规则注册表。

每条规则是一个模块，暴露 RULE_ID / TITLE / check(doc, preset) -> list[Issue]。
v0.1 只有这 6 条，不要在这里加第 7 条。
"""

from __future__ import annotations

from typing import List

from . import body_font, heading_level, indent, line_spacing, page_margin, ref_numbering

RULES = [
    page_margin,
    body_font,
    heading_level,
    line_spacing,
    indent,
    ref_numbering,
]

RULE_IDS: List[str] = [r.RULE_ID for r in RULES]

__all__ = ["RULES", "RULE_IDS"]
