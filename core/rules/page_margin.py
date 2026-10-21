"""规则 1：纸张与页边距。

依据：GB/T 7713.1—2006《学位论文编写规则》5.1「论文应采用 A4 纸（210mm×297mm）」
      与各高校通用要求「上/下/左/右页边距不小于规定值」。
判据由 preset 的 page 段给出，容差 ±tolerance_mm（默认 1mm）。
"""

from __future__ import annotations

from typing import List

from ..model import Doc
from .base import LEVEL_ERROR, Rule, fmt_mm

A4_WIDTH_MM = 210.0
A4_HEIGHT_MM = 297.0


class PageMargin(Rule):
    RULE_ID = "PAGE_MARGIN"
    TITLE = "纸张与页边距"
    SOURCE = "GB/T 7713.1—2006 5.1；高校通用规范（A4 + 上/下/左/右页边距）"

    @classmethod
    def check(cls, doc: Doc, preset: dict) -> List[Issue]:
        page = preset["page"]
        tol = float(page.get("tolerance_mm", 1.0))
        issues: List[Issue] = []

        for sec in doc.sections:
            where = f"第 {sec.index} 节（页面设置）"

            # 纸张：只认 A4，横竖都算 A4（表格页横排很常见）
            is_a4 = (
                abs(sec.page_width_mm - A4_WIDTH_MM) <= tol
                and abs(sec.page_height_mm - A4_HEIGHT_MM) <= tol
            ) or (
                abs(sec.page_width_mm - A4_HEIGHT_MM) <= tol
                and abs(sec.page_height_mm - A4_WIDTH_MM) <= tol
            )
            if not is_a4:
                if sec.page_width_mm == 0 and sec.page_height_mm == 0:
                    actual = "未设置纸张大小"
                else:
                    actual = f"{sec.page_width_mm:g}mm × {sec.page_height_mm:g}mm"
                issues.append(cls.issue(
                    LEVEL_ERROR, where, actual, "A4（210mm × 297mm）",
                    "布局 → 页面设置 → 纸张大小改为 A4"))

            for key, label, value in (
                ("margin_top_mm", "上边距", sec.margin_top_mm),
                ("margin_bottom_mm", "下边距", sec.margin_bottom_mm),
                ("margin_left_mm", "左边距", sec.margin_left_mm),
                ("margin_right_mm", "右边距", sec.margin_right_mm),
            ):
                expected = float(page[key])
                if abs(value - expected) > tol:
                    issues.append(cls.issue(
                        LEVEL_ERROR, f"{where} {label}",
                        fmt_mm(value), fmt_mm(expected),
                        f"布局 → 页边距 → {label} 改为 {expected:g}mm（容差 ±{tol:g}mm）"))
        return issues


RULE_ID = PageMargin.RULE_ID
TITLE = PageMargin.TITLE
SOURCE = PageMargin.SOURCE


def check(doc: Doc, preset: dict) -> List[Issue]:
    return PageMargin.check(doc, preset)
