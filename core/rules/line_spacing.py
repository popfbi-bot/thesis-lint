"""规则 4：行距。

两件事：
1. 与 preset 声明的行距比对（1.5 倍 / 固定值 20pt 等）；
2. 报「同一篇里行距不统一」——以全文出现最多的行距为基准，把偏离的段落单独标出来。

依据：GB/T 7713.1—2006 6.3.1 未硬性规定行距，但要求全文体例一致；
      具体数值取自 preset.line_spacing（高校通用：1.5 倍行距）。
"""

from __future__ import annotations

from collections import Counter
from typing import List

from ..model import Doc, Role
from .base import LEVEL_ERROR, LEVEL_WARN, Rule
from .body_font import describe_line



class LineSpacing(Rule):
    RULE_ID = "LINE_SPACING"
    TITLE = "行距"
    SOURCE = "preset.line_spacing；GB/T 7713.1—2006 6.3.1（体例一致）"

    @classmethod
    def check(cls, doc: Doc, preset: dict) -> List[Issue]:
        cfg = preset["line_spacing"]
        issues: List[Issue] = []

        # 参与比对的段落：正文 + 参考文献条目（题注、标题单独规定，不参与）
        targets = [p for p in doc.paragraphs if p.role in (Role.BODY, Role.REF_ENTRY)]
        if not targets:
            return issues

        keys = [_key(p) for p in targets]

        # 1) 不一致：以最常见行距为基准
        counts = Counter(keys)
        dominant = counts.most_common(1)[0][0]
        for p, k in zip(targets, keys):
            if k != dominant:
                issues.append(cls.issue(
                    LEVEL_WARN, p.location, describe_line(p),
                    f"与全文主行距一致：{_describe_key(dominant)}",
                    "全选正文 → 段落 → 行距 统一设置",
                    source="GB/T 7713.1—2006 6.3.1 体例一致"))

        # 2) 与规范不符（同一类问题只报一次，逐段列出位置）
        bad = [p for p in targets if not _matches(p, cfg)]
        if bad:
            sample = bad[0]
            more = "" if len(bad) == 1 else f"（另 {len(bad) - 1} 段同样问题）"
            issues.append(cls.issue(
                LEVEL_ERROR, sample.location + more,
                describe_line(sample),
                _describe_cfg(cfg),
                "全选正文 → 段落 → 行距 改为规范值"))
        return issues


def _key(p) -> tuple:
    if p.line_rule is None or p.line_value is None:
        return ("auto", 240.0)  # Word 默认：单倍行距
    return (p.line_rule, round(float(p.line_value), 1))


def _describe_key(key: tuple) -> str:
    rule, value = key
    if rule == "auto":
        return f"{value / 240:g} 倍行距"
    return f"固定值 {value / 20:g}pt"


def _matches(p, cfg: dict) -> bool:
    rule, value = _key(p)
    if rule != cfg["rule"]:
        return False
    if rule == "auto":
        return abs(value / 240.0 - float(cfg["value"])) <= 0.01
    return abs(value / 20.0 - float(cfg["value"])) <= 0.1


def _describe_cfg(cfg: dict) -> str:
    if cfg["rule"] == "auto":
        return f"{cfg['value']:g} 倍行距"
    return f"固定值 {cfg['value']:g}pt"


RULE_ID = LineSpacing.RULE_ID
TITLE = LineSpacing.TITLE
SOURCE = LineSpacing.SOURCE


def check(doc: Doc, preset: dict) -> List[Issue]:
    return LineSpacing.check(doc, preset)
