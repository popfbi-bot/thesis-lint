"""规则公共骨架：Issue 结构与规则元信息。"""

from __future__ import annotations

from dataclasses import asdict, dataclass

LEVEL_ERROR = "error"
LEVEL_WARN = "warn"


@dataclass
class Issue:
    rule_id: str
    level: str          # error | warn
    location: str       # 「第 12 段「……摘要……」」这样用户能直接找过去的位置
    actual: str
    expected: str
    fix_hint: str
    source: str         # 依据出处，必须可追溯

    def to_dict(self) -> dict:
        return asdict(self)


class Rule:
    RULE_ID = ""
    TITLE = ""
    SOURCE = ""         # 默认依据，写进每条 Issue 的 source

    @classmethod
    def issue(cls, level, location, actual, expected, fix_hint, source=None) -> Issue:
        return Issue(
            rule_id=cls.RULE_ID,
            level=level,
            location=location,
            actual=actual,
            expected=expected,
            fix_hint=fix_hint,
            source=source or cls.SOURCE,
        )


def fmt_mm(value: float) -> str:
    return f"{value:.1f}mm"


def fmt_pt(value: float) -> str:
    return f"{value:g}pt"
