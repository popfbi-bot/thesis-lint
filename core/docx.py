"""zip + XML 解析层 —— 全项目唯一碰 .docx 的地方。

.docx 本质是一个 zip 包，正文在 word/document.xml，样式继承表在 word/styles.xml。
这里只做三件事：

1. 把 XML 拆成「节（sectPr）/ 段落（w:p）/ 文本（w:t）」；
2. 把样式（w:pStyle -> styles.xml 里的 pPr/rPr、带 basedOn 继承）合并成「生效值」；
3. 按段落内容与样式名给出角色（正文/标题/题注/参考文献条目）。

不做任何格式是否合规的判断——那是 rules/ 的事。

单位换算（OOXML 规定）：
- twips: 1 inch = 1440 twips = 25.4mm  ->  1 twip = 25.4/1440 mm
- half-point: w:sz 是半磅
- w:firstLineChars: 百分之一字符（200 = 2 字符）
- w:spacing w:line: lineRule=auto 时 240 = 1 倍行距；exact 时单位为 twips
"""

from __future__ import annotations

import re
import zipfile
from typing import Dict, Iterable, List, Optional, Tuple
from xml.etree import ElementTree as ET

from .model import Doc, Paragraph, RefUse, Role, Section

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"

TWIP_MM = 25.4 / 1440.0
EMU_MM = 25.4 / 914400.0

# 段落里的可切换标记
_TAB = W + "tab"
_BR = W + "br"
_CR = W + "cr"

_CAPTION_RE = re.compile(r"^\s*(图|表|Fig\.?|Table|Figure)\s*[0-9０-９]+([.\-－—][0-9０-９]+)*")
_REF_ENTRY_RE = re.compile(r"^\s*[\[［]\s*([0-9０-９]+)\s*[\]］]")
_REF_HEADING_RE = re.compile(r"^\s*(参考文献|References?)\s*$", re.IGNORECASE)
_CITATION_RE = re.compile(r"[\[［]\s*([0-9０-９]+(?:\s*[-–—~,，、]\s*[0-9０-９]+)*)\s*[\]］]")


class DocxError(Exception):
    """输入不是可解析的 .docx。"""


# --------------------------------------------------------------------------
# 底层 XML 取值
# --------------------------------------------------------------------------

def _attr(elem: Optional[ET.Element], name: str, ns: str = W) -> Optional[str]:
    if elem is None:
        return None
    return elem.get(ns + name)


def _val(elem: Optional[ET.Element]) -> Optional[str]:
    """读 w:xxx 元素的 w:val。"""
    return _attr(elem, "val")


def _onoff(elem: Optional[ET.Element]) -> Optional[bool]:
    """读开关型属性（w:b、w:keepNext 等）。缺省 val 视为 True。"""
    if elem is None:
        return None
    val = _attr(elem, "val")
    if val is None:
        return True
    return val.lower() not in ("0", "false", "off")


def _num(value: Optional[str]) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _twips_to_mm(value: Optional[str]) -> float:
    n = _num(value)
    return 0.0 if n is None else n * TWIP_MM


def _read_xml(zf: zipfile.ZipFile, name: str) -> Optional[ET.Element]:
    try:
        data = zf.read(name)
    except KeyError:
        return None
    return ET.fromstring(data)


# --------------------------------------------------------------------------
# styles.xml：样式继承
# --------------------------------------------------------------------------

class Style:
    __slots__ = ("style_id", "name", "based_on", "ppr", "rpr", "outline_level")

    def __init__(self, style_id: str, name: str, based_on: Optional[str],
                 ppr: ET.Element | None, rpr: ET.Element | None):
        self.style_id = style_id
        self.name = name
        self.based_on = based_on
        self.ppr = ppr
        self.rpr = rpr
        self.outline_level: Optional[int] = None


def _load_styles(root: Optional[ET.Element]) -> Dict[str, Style]:
    styles: Dict[str, Style] = {}
    if root is None:
        return styles
    for st in root.findall(W + "style"):
        if _attr(st, "type") != "paragraph":
            continue
        sid = _attr(st, "styleId") or ""
        name_el = st.find(W + "name")
        name = _val(name_el) or sid
        based_on = _val(st.find(W + "basedOn"))
        ppr = st.find(W + "pPr")
        rpr = st.find(W + "rPr")
        style = Style(sid, name, based_on, ppr, rpr)
        if ppr is not None:
            style.outline_level = _int(_val(ppr.find(W + "outlineLvl")))
        styles[sid] = style
    # 解析基于名称的 outline（如 Heading1 样式没有 outlineLvl 时按名字兜底）
    for style in styles.values():
        if style.outline_level is None:
            m = re.match(r"(?:heading|标题)\s*([1-9])", style.name, re.IGNORECASE)
            if m:
                style.outline_level = int(m.group(1)) - 1
    return styles


def _int(value: Optional[str]) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(float(value))
    except ValueError:
        return None


def _style_chain(style_id: Optional[str], styles: Dict[str, Style]) -> List[Style]:
    """返回从根到自身的样式链，用于合并（后面的覆盖前面的）。"""
    chain: List[Style] = []
    seen = set()
    cur = styles.get(style_id or "")
    while cur is not None and cur.style_id not in seen:
        seen.add(cur.style_id)
        chain.append(cur)
        cur = styles.get(cur.based_on or "")
    chain.reverse()
    return chain


def _doc_defaults(root: Optional[ET.Element]) -> Tuple[Optional[ET.Element], Optional[ET.Element]]:
    """docDefaults 里的 rPr / pPr。"""
    if root is None:
        return None, None
    dd = root.find(W + "docDefaults")
    if dd is None:
        return None, None
    rpr = dd.find(f"{W}rPrDefault/{W}rPr")
    ppr = dd.find(f"{W}pPrDefault/{W}pPr")
    return rpr, ppr


# --------------------------------------------------------------------------
# 段落属性解析
# --------------------------------------------------------------------------

class ParaFacts:
    """一个段落 pPr/rPr 里出现的原始属性（可能为 None 表示该层没写）。"""

    def __init__(self) -> None:
        self.style_id: Optional[str] = None
        self.outline_level: Optional[int] = None
        self.align: Optional[str] = None
        self.first_line_chars: Optional[float] = None
        self.first_line_twips: Optional[float] = None
        self.hanging_chars: Optional[float] = None
        self.line_rule: Optional[str] = None
        self.line_value: Optional[float] = None
        self.space_before_pt: Optional[float] = None
        self.space_after_pt: Optional[float] = None
        self.font_ascii: Optional[str] = None
        self.font_east_asia: Optional[str] = None
        self.size_pt: Optional[float] = None
        self.bold: Optional[bool] = None


def _apply_ppr(facts: ParaFacts, ppr: Optional[ET.Element]) -> None:
    if ppr is None:
        return
    lvl = _int(_val(ppr.find(W + "outlineLvl")))
    if lvl is not None:
        facts.outline_level = lvl
    align = _val(ppr.find(W + "jc"))
    if align:
        facts.align = align
    ind = ppr.find(W + "ind")
    if ind is not None:
        # firstLineChars 优先于 firstLine；两者互斥地表示首行缩进
        flc = _num(_attr(ind, "firstLineChars"))
        fl = _num(_attr(ind, "firstLine"))
        hang = _num(_attr(ind, "hangingChars"))
        if flc is not None:
            facts.first_line_chars = flc / 100.0
            facts.first_line_twips = None
        elif fl is not None:
            facts.first_line_twips = fl
            facts.first_line_chars = None
        if hang is not None:
            facts.hanging_chars = hang / 100.0
    spacing = ppr.find(W + "spacing")
    if spacing is not None:
        rule = _attr(spacing, "lineRule") or "auto"
        line = _num(_attr(spacing, "line"))
        if line is not None:
            facts.line_rule = rule
            facts.line_value = line
        before = _num(_attr(spacing, "before"))
        after = _num(_attr(spacing, "after"))
        if before is not None:
            facts.space_before_pt = before / 20.0
        if after is not None:
            facts.space_after_pt = after / 20.0


def _apply_rpr(facts: ParaFacts, rpr: Optional[ET.Element]) -> None:
    if rpr is None:
        return
    fonts = rpr.find(W + "rFonts")
    if fonts is not None:
        ascii_font = _attr(fonts, "ascii") or _attr(fonts, "hAnsi")
        ea_font = _attr(fonts, "eastAsia")
        if ascii_font:
            facts.font_ascii = ascii_font
        if ea_font:
            facts.font_east_asia = ea_font
    sz = _num(_val(rpr.find(W + "sz")))
    if sz is not None:
        facts.size_pt = sz / 2.0
    bold = _onoff(rpr.find(W + "b"))
    if bold is not None:
        facts.bold = bold


def _merge(*layers: ParaFacts) -> ParaFacts:
    """后面的层覆盖前面的层（None 不覆盖）。"""
    out = ParaFacts()
    for layer in layers:
        for slot, value in vars(layer).items():
            if value is not None:
                setattr(out, slot, value)
    return out


# --------------------------------------------------------------------------
# 段落文本
# --------------------------------------------------------------------------

def _paragraph_text(p: ET.Element) -> str:
    parts: List[str] = []
    for node in p.iter():
        if node.tag == W + "t":
            parts.append(node.text or "")
        elif node.tag == _TAB:
            parts.append("\t")
        elif node.tag in (_BR, _CR):
            parts.append("\n")
    return "".join(parts)


# --------------------------------------------------------------------------
# 分节与页面
# --------------------------------------------------------------------------

def _parse_section(sect: ET.Element, index: int) -> Section:
    pg_sz = sect.find(W + "pgSz")
    pg_mar = sect.find(W + "pgMar")
    width = height = 0.0
    orientation = "portrait"
    if pg_sz is not None:
        w = _num(_attr(pg_sz, "w"))
        h = _num(_attr(pg_sz, "h"))
        width = (w or 0) * TWIP_MM
        height = (h or 0) * TWIP_MM
        if _attr(pg_sz, "orient") == "landscape":
            orientation = "landscape"
    top = bottom = left = right = 0.0
    if pg_mar is not None:
        top = _twips_to_mm(_attr(pg_mar, "top"))
        bottom = _twips_to_mm(_attr(pg_mar, "bottom"))
        left = _twips_to_mm(_attr(pg_mar, "left"))
        right = _twips_to_mm(_attr(pg_mar, "right"))
    return Section(index, round(width, 2), round(height, 2),
                   round(top, 2), round(bottom, 2), round(left, 2), round(right, 2),
                   orientation)


# --------------------------------------------------------------------------
# 角色判定
# --------------------------------------------------------------------------

def _style_name_heading_level(name: str) -> Optional[int]:
    m = re.match(r"(?:heading|标题)\s*([1-3])$", name.strip(), re.IGNORECASE)
    if m:
        return int(m.group(1))
    return None


def classify(index: int, text: str, style_name: str, outline_level: Optional[int],
             in_ref_section: bool) -> Tuple[str, int]:
    """返回 (role, heading_level)。

    判定顺序有意如此：标题 -> 参考文献条目 -> 题注 -> 正文。
    参考文献章节里的段落不再按题注/正文处理，否则「[1] 作者. 题名」会被误判。
    """
    stripped = text.strip()
    lvl = _style_name_heading_level(style_name)
    if lvl is None and outline_level is not None and 0 <= outline_level <= 2:
        lvl = outline_level + 1
    if lvl:
        return Role.HEADING, lvl
    if in_ref_section:
        # 参考文献章节里只认 [n] 开头的条目；其余（含正文误入）按正文处理
        if _REF_ENTRY_RE.match(stripped):
            return Role.REF_ENTRY, 0
        return Role.BODY, 0
    if not stripped:
        return Role.OTHER, 0
    if _CAPTION_RE.match(stripped):
        return Role.CAPTION, 0
    return Role.BODY, 0


def _is_ref_heading(text: str) -> bool:
    return bool(_REF_HEADING_RE.match(text.strip()))


# --------------------------------------------------------------------------
# 参考文献
# --------------------------------------------------------------------------

def _expand_numbers(spec: str) -> List[int]:
    """把 "1,3-5" 展开成 [1,3,4,5]。容忍 ，、～ 等中文标点。"""
    out: List[int] = []
    for chunk in re.split(r"[,，、]", spec):
        chunk = chunk.strip()
        if not chunk:
            continue
        m = re.match(r"^([0-9]+)\s*[-–—~]\s*([0-9]+)$", chunk)
        if m:
            lo, hi = int(m.group(1)), int(m.group(2))
            if lo <= hi and hi - lo < 200:
                out.extend(range(lo, hi + 1))
            continue
        if chunk.isdigit():
            out.append(int(chunk))
    return out


def _collect_refs(paragraphs: List[Paragraph]) -> Tuple[Dict[int, Paragraph], List[RefUse]]:
    entries: Dict[int, Paragraph] = {}
    uses: List[RefUse] = []
    for p in paragraphs:
        if p.role == Role.REF_ENTRY:
            m = _REF_ENTRY_RE.match(p.text)
            if m:
                num = int(m.group(1))
                entries.setdefault(num, p)  # 重复序号交给规则报
                # 条目内部的编号不算正文引用
                continue
        if p.role in (Role.BODY, Role.HEADING, Role.CAPTION):
            numbers: List[int] = []
            for m in _CITATION_RE.finditer(p.text):
                numbers.extend(_expand_numbers(m.group(1)))
            if numbers:
                uses.append(RefUse(numbers, p.index))
    return entries, uses


# --------------------------------------------------------------------------
# 入口
# --------------------------------------------------------------------------

def load(path: str) -> Doc:
    """解析 .docx 为 Doc。只读，不落地任何临时文件。"""
    try:
        zf = zipfile.ZipFile(path)
    except FileNotFoundError:
        raise DocxError(f"找不到文件：{path}")
    except zipfile.BadZipFile:
        raise DocxError(f"不是有效的 .docx（zip 解析失败）：{path}")

    with zf:
        doc_root = _read_xml(zf, "word/document.xml")
        if doc_root is None:
            raise DocxError(f"缺少 word/document.xml，不是 Word 文档：{path}")
        styles_root = _read_xml(zf, "word/styles.xml")

    styles = _load_styles(styles_root)
    default_rpr, default_ppr = _doc_defaults(styles_root)

    body = doc_root.find(W + "body")
    if body is None:
        raise DocxError("document.xml 里没有 w:body")

    doc = Doc(path=path)

    # 逐段解析：w:p 与结尾的 w:sectPr 按出现顺序排列，sectPr 决定「从哪一段起换节」
    raw_paragraphs: List[Optional[ET.Element]] = []
    pending_section_per_para: List[Optional[ET.Element]] = []
    for elem in body:
        if elem.tag == W + "p":
            ppr = elem.find(W + "pPr")
            raw_paragraphs.append(elem)
            pending_section_per_para.append(ppr.find(W + "sectPr") if ppr is not None else None)
        elif elem.tag == W + "sectPr":
            raw_paragraphs.append(None)
            pending_section_per_para.append(elem)

    sections: List[Section] = []
    facts_list: List[ParaFacts] = []
    section_of_para: List[int] = []
    section_index = 0
    current_section = 0
    for elem, sect in zip(raw_paragraphs, pending_section_per_para):
        if sect is not None:
            section_index += 1
            sections.append(_parse_section(sect, section_index))
        if elem is None:
            continue
        current_section = max(section_index, 1)
        section_of_para.append(current_section)
        facts_list.append(_extract_facts(elem, styles, default_ppr, default_rpr))

    if not sections:
        # 完全没有 sectPr：给一个占位分节，交给 page_margin 报错
        sections.append(Section(1, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0))

    # 2) 组装 Paragraph（先算角色，再算生效值）
    in_ref_section = False
    for i, (elem, facts) in enumerate(zip(raw_paragraphs, facts_list), start=1):
        p = Paragraph(index=i, text=_paragraph_text(elem))
        style = styles.get(facts.style_id or "")
        p.style_id = facts.style_id or ""
        p.style_name = style.name if style else ""
        p.outline_level = facts.outline_level
        if _is_ref_heading(p.text):
            in_ref_section = True
            p.role = Role.OTHER
            p.heading_level = 0
        else:
            p.role, p.heading_level = classify(i, p.text, p.style_name,
                                               facts.outline_level, in_ref_section)
        p.font_ascii = facts.font_ascii
        p.font_east_asia = facts.font_east_asia
        p.size_pt = facts.size_pt
        p.bold = facts.bold
        p.align = facts.align
        p.first_line_chars = facts.first_line_chars
        p.first_line_twips = facts.first_line_twips
        p.line_rule = facts.line_rule
        p.line_value = facts.line_value
        p.space_before_pt = facts.space_before_pt
        p.space_after_pt = facts.space_after_pt
        p.page_index = section_of_para[i - 1] if i - 1 < len(section_of_para) else 1
        doc.paragraphs.append(p)

    doc.sections = sections
    doc.ref_entries, doc.ref_uses = _collect_refs(doc.paragraphs)
    return doc


def _extract_facts(p: ET.Element, styles: Dict[str, Style],
                   default_ppr: Optional[ET.Element],
                   default_rpr: Optional[ET.Element]) -> ParaFacts:
    """把 docDefaults -> 样式链 -> 直接格式 合并成生效值。"""
    ppr = p.find(W + "pPr")
    style_id = _val(ppr.find(W + "pStyle")) if ppr is not None else None

    layers: List[ParaFacts] = []

    base = ParaFacts()
    _apply_ppr(base, default_ppr)
    _apply_rpr(base, default_rpr)
    layers.append(base)

    for style in _style_chain(style_id, styles):
        sf = ParaFacts()
        _apply_ppr(sf, style.ppr)
        _apply_rpr(sf, style.rpr)
        sf.style_id = style.style_id
        layers.append(sf)

    direct = ParaFacts()
    _apply_ppr(direct, ppr)
    # 段落标记的 rPr（w:pPr/w:rPr）也影响整段
    if ppr is not None:
        _apply_rpr(direct, ppr.find(W + "rPr"))
    # 段内第一个 run 的直接格式：学术论文正文通常整段一致
    for run in p.findall(W + "r"):
        rpr = run.find(W + "rPr")
        if rpr is not None:
            _apply_rpr(direct, rpr)
            break
    direct.style_id = style_id
    layers.append(direct)

    return _merge(*layers)
