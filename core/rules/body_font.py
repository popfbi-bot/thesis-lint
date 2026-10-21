"""规则 2：正文段落格式（中文字体、字号、行距、首行缩进、段前段后间距）。

依据：GB/T 7713.1—2006 6.3.1「正文一般用宋体小四号（12pt）」；
      行距与段距按 preset 配置（高校惯例：1.5 倍行距、段前段后 0）。
本规则只检查正文段落（role=body）；标题归 heading_level，参考文献条目归 ref_numbering / indent。
"""

from __future__ import annotations

from typing import List, Optional

from ..model import Doc, Paragraph
from .base import LEVEL_ERROR, LEVEL_WARN, Rule, fmt_pt


def describe_line(p: Paragraph) -> str:
    if p.line_rule is None or p.line_value is None:
        return "未设置（默认单倍）"
    if p.line_rule == "auto":
        return f"{p.line_value / 240:g} 倍行距"
    # exact 之外的规则（atLeast 等）极少见，按固定值的单位读即可
    return f"固定值 {p.line_value / 20:g}pt"


def describe_indent(p: Paragraph) -> str:
    if p.first_line_chars is not None:
        return f"{p.first_line_chars:g} 字符"
    if p.first_line_twips is not None:
        return f"{p.first_line_twips} twips"
    return "无首行缩进"


class BodyFont(Rule):
    RULE_ID = "BODY_FONT"
    TITLE = "正文段落格式"
    SOURCE = "GB/T 7713.1—2006 6.3.1；preset.body 配置"

    @classmethod
    def check(cls, doc: Doc, preset: dict) -> List[Issue]:
        cfg = preset["body"]
        issues: List[Issue] = []
        body = doc.body_paragraphs
        if not body:
            return issues

        expected_font = cfg["font_east_asia"]
        expected_size = float(cfg["size_pt"])
        expected_line = preset["line_spacing"]
        expected_indent = float(cfg["first_line_indent_chars"])
        max_before = float(cfg["space_before_pt_max"])
        max_after = float(cfg["space_after_pt_max"])

        for p in body:
            loc = p.location

            if p.font_east_asia and p.font_east_asia != expected_font:
                issues.append(cls.issue(
                    LEVEL_ERROR, loc, f"中文字体 {p.font_east_asia}", expected_font,
                    f"选中该段 → 字体 → 中文字体改为「{expected_font}」"))

            if p.size_pt is not None and abs(p.size_pt - expected_size) > 0.01:
                issues.append(cls.issue(
                    LEVEL_ERROR, loc, f"字号 {fmt_pt(p.size_pt)}", fmt_pt(expected_size),
                    f"选中该段 → 字号改为 {fmt_pt(expected_size)}"))

            # 行距：与 preset 声明的主行距不一致即报（不统一的情形由 LINE_SPACING 汇总）
            if not _line_matches(p, expected_line):
                issues.append(cls.issue(
                    LEVEL_ERROR, loc, f"行距 {describe_line(p)}",
                    describe_line_config(expected_line),
                    "段落 → 行距 改回规范值"))

            if not _indent_matches(p, expected_indent):
                issues.append(cls.issue(
                    LEVEL_ERROR, loc, f"首行缩进 {describe_indent(p)}",
                    f"{expected_indent:g} 字符",
                    "段落 → 特殊格式 → 首行缩进 2 字符"))

            if p.space_before_pt is not None and p.space_before_pt > max_before + 0.01:
                issues.append(cls.issue(
                    LEVEL_WARN, loc, f"段前间距 {fmt_pt(p.space_before_pt)}",
                    f"≤ {fmt_pt(max_before)}",
                    "段落 → 间距 → 段前 改为 0"))

            if p.space_after_pt is not None and p.space_after_pt > max_after + 0.01:
                issues.append(cls.issue(
                    LEVEL_WARN, loc, f"段后间距 {fmt_pt(p.space_after_pt)}",
                    f"≤ {fmt_pt(max_after)}",
                    "段落 → 间距 → 段后 改为 0"))
        return issues


def describe_line_config(cfg: dict) -> str:
    if cfg["rule"] == "auto":
        return f"{cfg['value']:g} 倍行距"
    return f"固定值 {cfg['value']:g}pt"


def _line_matches(p: Paragraph, cfg: dict) -> bool:
    # 段落没写行距 = Word 默认单倍行距；只有规范要求单倍时才算通过
    if p.line_rule is None or p.line_value is None:
        return cfg["rule"] == "auto" and abs(cfg["value"] - 1.0) < 0.01
    if p.line_rule != cfg["rule"]:
        return False
    if cfg["rule"] == "auto":
        return abs(p.line_value / 240.0 - float(cfg["value"])) <= 0.01
    # exact: preset 用磅，段落里是 twips
    return abs(p.line_value / 20.0 - float(cfg["value"])) <= 0.1


def _indent_matches(p: Paragraph, expected_chars: float) -> bool:
    if p.first_line_chars is not None:
        return abs(p.first_line_chars - expected_chars) <= 0.05
    # 等价写法：2 字符 ≈ 2 × 字号 = 200 twips（小四 12pt → 24pt = 480 twips）
    if p.first_line_twips is not None:
        return abs(p.first_line_twips - expected_chars * 100) <= 1
    return False


RULE_ID = BodyFont.RULE_ID
TITLE = BodyFont.TITLE
SOURCE = BodyFont.SOURCE


def check(doc: Doc, preset: dict) -> List[Issue]:
    return BodyFont.check(doc, preset)
