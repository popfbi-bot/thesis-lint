"""规则 6：参考文献序号连续性与引用对应关系。

依据：GB/T 7714—2015《信息与文献 参考文献著录规则》10.1「按正文中引用顺序连续编号」
      与 10.2「参考文献表用方括号数字标注，顺序编码制」。
检查两件事：
1. 列表内序号从 1 连续递增、无重复；
2. 正文 [n] 引用必须都能在列表里找到条目。
   反向（列了但没引用）不算错——允许「未引用但列出」，报告里会说明。
"""

from __future__ import annotations

import re
from typing import Dict, List, Optional

from ..model import Doc, Paragraph, Role
from .base import LEVEL_ERROR, LEVEL_WARN, Rule

NO_REVERSE_NOTE = "允许列出但未引用的条目，因此不检查反向对应"


class RefNumbering(Rule):
    RULE_ID = "REF_NUMBERING"
    TITLE = "参考文献序号连续性"
    SOURCE = "GB/T 7714—2015 10.1（顺序编码制连续编号）、10.2（方括号数字标注）"

    @classmethod
    def check(cls, doc: Doc, preset: dict) -> List[Issue]:
        issues: List[Issue] = []
        entries: Dict[int, Paragraph] = doc.ref_entries
        if not entries and not doc.ref_uses:
            return issues

        # 1) 列表内序号：从 1 连续、无重复
        numbers = sorted(entries)
        if numbers:
            if numbers[0] != 1:
                first = entries[numbers[0]]
                issues.append(cls.issue(
                    LEVEL_ERROR, first.location, f"起始序号为 [{numbers[0]}]", "从 [1] 开始",
                    "第一条参考文献改为 [1] 并顺延后续编号",
                    source=f"GB/T 7714—2015 10.1；{NO_REVERSE_NOTE}"))

            expected = 1
            for num in numbers:
                if num != expected:
                    p = entries[num]
                    missing = expected if num == expected + 1 else f"{expected}–{num - 1}"
                    issues.append(cls.issue(
                        LEVEL_ERROR, p.location,
                        f"序号跳号：出现 [{num}]，缺 [{missing}]",
                        "序号从 1 连续递增",
                        f"把 [{num}] 及其后的编号连续重排，或补上缺失条目",
                        source=f"GB/T 7714—2015 10.1；{NO_REVERSE_NOTE}"))
                    break  # 一处断裂就够定位，避免刷屏
                expected = num + 1

        # 重复序号：ref_entries 用 setdefault 去重，条数对不上就说明有重复
        if len(numbers) != len(_all_entries(doc)):
            seen: Dict[int, int] = {}
            for p in _all_entries(doc):
                n = _entry_number(p.text)
                if n is not None:
                    seen[n] = seen.get(n, 0) + 1
            for n, cnt in sorted(seen.items()):
                if cnt > 1:
                    issues.append(cls.issue(
                        LEVEL_ERROR, f"参考文献列表 [{n}]", f"出现 {cnt} 次", "每个序号唯一",
                        f"删除或重排重复的 [{n}] 条目",
                        source=f"GB/T 7714—2015 10.1；{NO_REVERSE_NOTE}"))

        # 2) 正文引用 -> 列表条目
        missing_refs: Dict[int, List[int]] = {}
        for use in doc.ref_uses:
            for n in use.numbers:
                if n not in entries:
                    missing_refs.setdefault(n, []).append(use.paragraph_index)
        if not entries and doc.ref_uses:
            uses = doc.ref_uses[0]
            issues.append(cls.issue(
                LEVEL_ERROR, f"第 {uses.paragraph_index} 段正文引用 [{uses.numbers[0]}]",
                "正文引用了文献，但全文没有参考文献条目", "存在对应的 [n] 条目",
                "补一节「参考文献」并按顺序编码",
                source=f"GB/T 7714—2015 10.2；{NO_REVERSE_NOTE}"))
        for n, where in sorted(missing_refs.items()):
            locs = "、".join(str(i) for i in where[:5])
            issues.append(cls.issue(
                LEVEL_ERROR, f"第 {locs} 段正文引用 [{n}]",
                f"正文引用了 [{n}]，参考文献列表里没有这一条",
                f"列表中存在 [{n}] 条目",
                f"补上 [{n}] 条目，或修正正文引用编号",
                source=f"GB/T 7714—2015 10.2；{NO_REVERSE_NOTE}"))

        # 3) 有列表、正文却一次没引用：提示级别（很多学校允许，不判错）
        if entries and not doc.ref_uses:
            issues.append(cls.issue(
                LEVEL_WARN, "参考文献列表",
                f"列了 {len(entries)} 条，正文中未出现任何 [n] 引用",
                "正文使用 [n] 标注引用",
                "确认是否漏标引用",
                source=f"GB/T 7714—2015 10.2；{NO_REVERSE_NOTE}"))
        return issues


def _all_entries(doc: Doc) -> List[Paragraph]:
    return [p for p in doc.paragraphs if p.role == Role.REF_ENTRY]


def _entry_number(text: str) -> Optional[int]:
    m = re.match(r"^\s*[\[［]\s*([0-9]+)\s*[\]］]", text)
    return int(m.group(1)) if m else None


RULE_ID = RefNumbering.RULE_ID
TITLE = RefNumbering.TITLE
SOURCE = RefNumbering.SOURCE


def check(doc: Doc, preset: dict) -> List[Issue]:
    return RefNumbering.check(doc, preset)
