#!/usr/bin/env python3
"""生成 tests/fixtures 里的 .docx 样例。

样例必须能被 Word 正常打开、也能被本项目的小解析器读懂，所以这里用标准库
手工拼出最小可用的 OOXML 包（zip + document.xml + styles.xml + rels）。

fixtures/
  good.docx                       全部合规（undergrad preset）-> 0 errors
  bad.docx                        6 个维度各错一处 -> >=6 个 error，覆盖全部 rule_id
  per_rule/<rule>.docx            只在某一项做错，其余完全合规
  master_good.docx                按 master preset 合规（固定值行距）
只读生成一次即可，产物进版本库，测试不依赖它。
"""

from __future__ import annotations

import os
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(HERE), "fixtures")

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"

CONTENT_TYPES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
  <Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>
</Types>"""

ROOT_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>"""

DOC_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
</Relationships>"""

# 样式：正文 Normal 全部属性写清楚，避免依赖「Word 默认值」这种解析器看不到的东西。
STYLES = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="{W_NS}">
  <w:docDefaults>
    <w:rPrDefault><w:rPr>
      <w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman" w:eastAsia="宋体"/>
      <w:sz w:val="24"/><w:szCs w:val="24"/>
    </w:rPr></w:rPrDefault>
    <w:pPrDefault><w:pPr><w:spacing w:line="276" w:lineRule="auto"/></w:pPr></w:pPrDefault>
  </w:docDefaults>
  <w:style w:type="paragraph" w:styleId="Normal"><w:name w:val="Normal"/>
    <w:pPr>
      <w:spacing w:before="0" w:after="0" w:line="360" w:lineRule="auto"/>
      <w:ind w:firstLineChars="200" w:firstLine="480"/>
      <w:jc w:val="both"/>
    </w:pPr>
    <w:rPr>
      <w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman" w:eastAsia="宋体"/>
      <w:sz w:val="24"/><w:b w:val="0"/>
    </w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="Heading1"><w:name w:val="heading 1"/>
    <w:basedOn w:val="Normal"/>
    <w:pPr>
      <w:outlineLvl w:val="0"/>
      <w:spacing w:before="0" w:after="0" w:line="360" w:lineRule="auto"/>
      <w:ind w:firstLineChars="0" w:firstLine="0"/>
      <w:jc w:val="center"/>
    </w:pPr>
    <w:rPr>
      <w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman" w:eastAsia="黑体"/>
      <w:sz w:val="32"/><w:b w:val="0"/>
    </w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="Heading2"><w:name w:val="heading 2"/>
    <w:basedOn w:val="Normal"/>
    <w:pPr>
      <w:outlineLvl w:val="1"/>
      <w:spacing w:before="0" w:after="0" w:line="360" w:lineRule="auto"/>
      <w:ind w:firstLineChars="0" w:firstLine="0"/>
      <w:jc w:val="left"/>
    </w:pPr>
    <w:rPr>
      <w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman" w:eastAsia="黑体"/>
      <w:sz w:val="28"/><w:b w:val="0"/>
    </w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="Heading3"><w:name w:val="heading 3"/>
    <w:basedOn w:val="Normal"/>
    <w:pPr>
      <w:outlineLvl w:val="2"/>
      <w:spacing w:before="0" w:after="0" w:line="360" w:lineRule="auto"/>
      <w:ind w:firstLineChars="0" w:firstLine="0"/>
      <w:jc w:val="left"/>
    </w:pPr>
    <w:rPr>
      <w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman" w:eastAsia="黑体"/>
      <w:sz w:val="24"/><w:b w:val="0"/>
    </w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="Caption"><w:name w:val="caption"/>
    <w:basedOn w:val="Normal"/>
    <w:pPr>
      <w:spacing w:before="0" w:after="0" w:line="240" w:lineRule="auto"/>
      <w:ind w:firstLineChars="0" w:firstLine="0"/>
      <w:jc w:val="center"/>
    </w:pPr>
    <w:rPr>
      <w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman" w:eastAsia="宋体"/>
      <w:sz w:val="21"/>
    </w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="RefEntry"><w:name w:val="参考文献条目"/>
    <w:basedOn w:val="Normal"/>
    <w:pPr>
      <w:spacing w:before="0" w:after="0" w:line="360" w:lineRule="auto"/>
      <w:ind w:firstLineChars="0" w:firstLine="0"/>
      <w:jc w:val="left"/>
    </w:pPr>
    <w:rPr>
      <w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman" w:eastAsia="宋体"/>
      <w:sz w:val="24"/>
    </w:rPr>
  </w:style>
</w:styles>"""

A4_TWIPS_W = 11906
A4_TWIPS_H = 16838


def mm_to_twips(mm: float) -> int:
    return round(mm * 1440 / 25.4)


def esc(text: str) -> str:
    return (text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


class Para:
    """一段的最小描述：样式 + 直接格式覆盖 + 文本。"""

    def __init__(self, text: str, style: str = "Normal", *, ppr: str = "", rpr: str = ""):
        self.text = text
        self.style = style
        self.ppr = ppr
        self.rpr = rpr


def _para_xml(p: Para) -> str:
    ppr_inner = f'<w:pStyle w:val="{p.style}"/>' + p.ppr
    rpr = f"<w:rPr>{p.rpr}</w:rPr>" if p.rpr else ""
    return (f"<w:p><w:pPr>{ppr_inner}</w:pPr>"
            f"<w:r>{rpr}<w:t xml:space=\"preserve\">{esc(p.text)}</w:t></w:r></w:p>")


def document_xml(paras, *, margins=(25.0, 25.0, 30.0, 25.0), page=(210.0, 297.0),
                 sect_ppr: str = "") -> str:
    top, bottom, left, right = margins
    body = "".join(_para_xml(p) for p in paras)
    sect = (
        f'<w:sectPr>{sect_ppr}'
        f'<w:pgSz w:w="{mm_to_twips(page[0])}" w:h="{mm_to_twips(page[1])}"/>'
        f'<w:pgMar w:top="{mm_to_twips(top)}" w:right="{mm_to_twips(right)}" '
        f'w:bottom="{mm_to_twips(bottom)}" w:left="{mm_to_twips(left)}" '
        f'w:header="851" w:footer="992" w:gutter="0"/>'
        f'</w:sectPr>'
    )
    return (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            f'<w:document xmlns:w="{W_NS}"><w:body>{body}{sect}</w:body></w:document>')


def write_docx(path: str, document: str, styles: str = STYLES) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", CONTENT_TYPES)
        zf.writestr("_rels/.rels", ROOT_RELS)
        zf.writestr("word/_rels/document.xml.rels", DOC_RELS)
        zf.writestr("word/document.xml", document)
        zf.writestr("word/styles.xml", styles)


# --------------------------------------------------------------------------
# 语义化的小构造器
# --------------------------------------------------------------------------

def body(text: str, *, ppr: str = "", rpr: str = "") -> Para:
    return Para(text, "Normal", ppr=ppr, rpr=rpr)


def h1(text: str, *, ppr: str = "", rpr: str = "") -> Para:
    return Para(text, "Heading1", ppr=ppr, rpr=rpr)


def h2(text: str, *, ppr: str = "", rpr: str = "") -> Para:
    return Para(text, "Heading2", ppr=ppr, rpr=rpr)


def h3(text: str, *, ppr: str = "", rpr: str = "") -> Para:
    return Para(text, "Heading3", ppr=ppr, rpr=rpr)


def caption(text: str) -> Para:
    return Para(text, "Caption")


def ref_entry(text: str) -> Para:
    return Para(text, "RefEntry")


def ref_heading(text: str = "参考文献") -> Para:
    # 参考文献标题：黑体三号、居中、不缩进——但因为它不以 [n] 开头，
    # 解析层会把它当章节标题，角色为 other，不参与正文/题注检查。
    return Para(text, "Heading1")


# 让某些段落呈现「Word 默认没写行距」的样子需要直接格式，这里给常用片段
LINE_15 = '<w:spacing w:before="0" w:after="0" w:line="360" w:lineRule="auto"/>'
LINE_20PT = '<w:spacing w:before="0" w:after="0" w:line="400" w:lineRule="exact"/>'
INDENT_2 = '<w:ind w:firstLineChars="200" w:firstLine="480"/>'
NO_INDENT = '<w:ind w:firstLineChars="0" w:firstLine="0"/>'


# --------------------------------------------------------------------------
# 合规样例
# --------------------------------------------------------------------------

def good_paragraphs() -> list:
    return [
        Para("摘要", "Heading1"),
        body("本文研究了格式检查工具的设计与实现，重点解决人工核对遗漏率高的问题。"),
        body("实验表明规则引擎可以覆盖学位论文的主要格式项，并且结果可复现。"),
        h1("第一章 绪论"),
        body("学位论文格式规范条目繁多，人工逐条核对通常需要数小时[1]。"),
        h2("1.1 研究背景"),
        body("已有研究多依赖人工审阅，缺少自动化手段[2]。"),
        h3("1.1.1 国内现状"),
        body("国内高校普遍发布了论文格式规范文件，但缺少配套检查工具[1,2]。"),
        caption("图1-1 论文格式检查流程"),
        h2("1.2 研究目标"),
        body("本文目标是输出一份可直接整改的问题清单。"),
        ref_heading(),
        ref_entry("[1] 张三. 学位论文格式规范研究[J]. 中国高教研究, 2023, 39(4): 12-18."),
        ref_entry("[2] 李四. 文档自动化检查方法[M]. 北京: 科学出版社, 2022: 45-60."),
    ]


def master_paragraphs() -> list:
    """master preset 要求固定值 20pt 行距。"""
    paras = good_paragraphs()
    exact = '<w:spacing w:before="0" w:after="0" w:line="400" w:lineRule="exact"/>'
    bold = '<w:b w:val="1"/>'
    out = []
    for p in paras:
        if p.style in ("Normal", "RefEntry"):
            p.ppr = exact
        if p.style in ("Heading1", "Heading2"):
            p.rpr = bold
        out.append(p)
    return out


# --------------------------------------------------------------------------
# 坏样例：6 个维度各错一处
# --------------------------------------------------------------------------

def bad_paragraphs() -> list:
    return [
        Para("摘要", "Heading1"),
        body("本文研究了格式检查工具的设计与实现，重点解决人工核对遗漏率高的问题。"),
        # 2) 正文段落格式错：中文字体变成仿宋（应为宋体）
        Para("这一段的中文字体被改成了仿宋，属于正文段落格式错误。", "Normal",
             ppr=LINE_15, rpr='<w:rFonts w:eastAsia="仿宋"/>'),
        h1("第一章 绪论"),
        # 3) 标题层级格式错：一级标题字号被改成 14pt（应为 16pt）
        Para("第一章 绪论（字号不符）", "Heading1", rpr='<w:sz w:val="28"/>'),
        h2("1.1 研究背景"),
        # 4) 行距错：这一段只有单倍行距，与全文 1.5 倍不一致
        Para("这一段的行距被改成了单倍，是全篇唯一一处不统一。", "Normal",
             ppr='<w:spacing w:before="0" w:after="0" w:line="240" w:lineRule="auto"/>'),
        # 5) 首行缩进错：正文段落没有首行缩进
        Para("这一段没有首行缩进，正文每段起行应空两字。", "Normal",
             ppr=LINE_15 + NO_INDENT),
        h3("1.1.1 国内现状"),
        body("国内高校普遍发布了论文格式规范文件，但缺少配套检查工具[1,2]。"),
        caption("图1-1 论文格式检查流程"),
        ref_heading(),
        ref_entry("[1] 张三. 学位论文格式规范研究[J]. 中国高教研究, 2023, 39(4): 12-18."),
        ref_entry("[3] 李四. 文档自动化检查方法[M]. 北京: 科学出版社, 2022: 45-60."),
        # 6) 参考文献序号错：[3] 造成跳号（缺 [2]）；正文还引用了不存在的 [9]
        body("另有一处引用指向了不存在的条目[9]。"),
    ]


# 上边距 20mm，应为 25mm
BAD_MARGINS = (20.0, 25.0, 30.0, 25.0)
# master preset 要求上边距 30mm
MASTER_MARGINS = (30.0, 25.0, 30.0, 25.0)
BAD_PAGE = (216.0, 279.0)               # Letter 纸


def per_rule() -> dict:
    """每项单独做错的段落表；其余部分保持合规。"""
    base = good_paragraphs

    def replace(paras, index, new):
        out = list(paras)
        out[index] = new
        return out

    cases = {}

    def with_citation(paras):
        """per_rule 样例统一在题注前插入一段引用 [9] 的正文，让 REF_NUMBERING 样例真的坏。"""
        out = list(paras)
        seq = [p.text for p in out]
        try:
            at = seq.index("图1-1 论文格式检查流程")
        except ValueError:
            return out
        out.insert(at, body("另有一处引用指向了不存在的条目[9]。"))
        return out

    # 1 页边距：只改页面设置，段落不动
    cases["PAGE_MARGIN"] = (base(), dict(margins=BAD_MARGINS))

    # 2 正文字体：只有正文第 1 段字体错
    ps = replace(base(), 1, Para("本文研究了格式检查工具的设计与实现，重点解决人工核对遗漏率高的问题。",
                                 "Normal", rpr='<w:rFonts w:eastAsia="楷体"/>'))
    cases["BODY_FONT"] = (ps, {})

    # 3 标题层级：只有二级标题字号错
    ps = replace(base(), 5, Para("1.1 研究背景", "Heading2", rpr='<w:sz w:val="24"/>'))
    cases["HEADING_LEVEL"] = (ps, {})

    # 4 行距：只有一段变成单倍
    ps = replace(base(), 2, Para("实验表明规则引擎可以覆盖学位论文的主要格式项，并且结果可复现。",
                                 "Normal",
                                 ppr='<w:spacing w:before="0" w:after="0" w:line="240" w:lineRule="auto"/>'))
    cases["LINE_SPACING"] = (ps, {})

    # 5 首行缩进：只有一段没有缩进
    ps = replace(base(), 4, Para("学位论文格式规范条目繁多，人工逐条核对通常需要数小时[1]。",
                                 "Normal", ppr=LINE_15 + NO_INDENT))
    cases["INDENT"] = (ps, {})

    # 6 参考文献：只有序号跳号（[1] [3]）
    ps = replace(base(), 14, ref_entry("[3] 李四. 文档自动化检查方法[M]. 北京: 科学出版社, 2022: 45-60."))
    cases["REF_NUMBERING"] = (ps, {})

    # 引用 [9] 段只放进 REF_NUMBERING 样例，其他样例保持干净，避免互相干扰
    cases["REF_NUMBERING"] = (with_citation(cases["REF_NUMBERING"][0]),
                              cases["REF_NUMBERING"][1])
    return cases


def main() -> None:
    write_docx(os.path.join(OUT, "good.docx"), document_xml(good_paragraphs()))
    write_docx(os.path.join(OUT, "master_good.docx"),
               document_xml(master_paragraphs(), margins=MASTER_MARGINS))
    write_docx(os.path.join(OUT, "bad.docx"),
               document_xml(bad_paragraphs(), margins=BAD_MARGINS, page=BAD_PAGE))
    for rule_id, (paras, kwargs) in per_rule().items():
        write_docx(os.path.join(OUT, "per_rule", f"{rule_id}.docx"),
                   document_xml(paras, **kwargs))
    print("fixtures written to", OUT)


if __name__ == "__main__":
    main()
