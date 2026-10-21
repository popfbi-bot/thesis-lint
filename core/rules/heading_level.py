"""规则 3：标题层级格式。

依据：GB/T 7713.1—2006 6.2「章、节、条三级标题，编号 1 / 1.1 / 1.1.1，层次不得颠倒」；
      各高校通用要求：一级标题黑体三号、二级标题黑体四号、三级标题黑体小四，标题不缩进。
判据由 preset.headings 给出：每级一套 {font_east_asia, size_pt, bold}。
另外检查「层级不得跳级」：出现三级标题之前必须先出现二级标题。
"""

from __future__ import annotations

from typing import Dict, List, Optional

from ..model import Doc, Paragraph
from .base import LEVEL_ERROR, LEVEL_WARN, Rule, fmt_pt


class HeadingLevel(Rule):
    RULE_ID = "HEADING_LEVEL"
    TITLE = "标题层级格式"
    SOURCE = "GB/T 7713.1—2006 6.2；preset.headings 配置"

    @classmethod
    def check(cls, doc: Doc, preset: dict) -> List[Issue]:
        levels: Dict[str, dict] = preset["headings"]
        issues: List[Issue] = []
        seen_max_level = 0

        for p in doc.headings:
            cfg = levels.get(str(p.heading_level))
            if cfg is None:
                continue
            name = f"{p.heading_level} 级标题"
            loc = p.location
            expected_font = cfg["font_east_asia"]
            expected_size = float(cfg["size_pt"])
            expected_bold = bool(cfg["bold"])

            if p.font_east_asia and p.font_east_asia != expected_font:
                issues.append(cls.issue(
                    LEVEL_ERROR, loc, f"{name}字体 {p.font_east_asia}", expected_font,
                    f"标题样式的中文字体改为「{expected_font}」"))

            if p.size_pt is not None and abs(p.size_pt - expected_size) > 0.01:
                issues.append(cls.issue(
                    LEVEL_ERROR, loc, f"{name}字号 {fmt_pt(p.size_pt)}", fmt_pt(expected_size),
                    f"标题字号改为 {fmt_pt(expected_size)}"))

            if p.bold is not None and bool(p.bold) != expected_bold:
                actual = "加粗" if p.bold else "未加粗"
                expected = "加粗" if expected_bold else "不加粗"
                issues.append(cls.issue(
                    LEVEL_ERROR, loc, f"{name}{actual}", expected,
                    f"标题{'加粗' if expected_bold else '取消加粗'}"))

            # 层级跳级：从一级直接到三级
            if p.heading_level > seen_max_level + 1:
                issues.append(cls.issue(
                    LEVEL_ERROR, loc,
                    f"从 {seen_max_level or '正文'} 直接跳到 {p.heading_level} 级标题",
                    "标题层级逐级出现（1 → 2 → 3）",
                    "补齐缺失的上一级标题，或把该标题降/升一级",
                    source="GB/T 7713.1—2006 6.2 层次不得颠倒"))
            seen_max_level = max(seen_max_level, p.heading_level)
        return issues


RULE_ID = HeadingLevel.RULE_ID
TITLE = HeadingLevel.TITLE
SOURCE = HeadingLevel.SOURCE


def check(doc: Doc, preset: dict) -> List[Issue]:
    return HeadingLevel.check(doc, preset)
