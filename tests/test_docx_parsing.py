"""解析层测试：.docx = zip + XML，这一层的错误会让所有规则一起失效。

覆盖：样式继承（basedOn）、docDefaults、直接格式优先、首行缩进两种写法、
倍数/固定值行距换算、多分节、参考文献章节判定、引用区间展开。
"""

from __future__ import annotations

import unittest

from tests.helpers import TempProject
from core.docx import _expand_numbers, _load_styles, load
from core.model import Role
from tools.build_fixtures import (
    Para, body, caption, document_xml, h1, ref_entry, ref_heading, write_docx,
)


class TestTwipsAndUnits(unittest.TestCase):
    def test_a4_mm_roundtrip(self):
        """210mm 存成 twips 再读回来，误差要小于 0.1mm。"""
        from core.docx import TWIP_MM
        self.assertAlmostEqual(11906 * TWIP_MM, 210.0, delta=0.1)
        self.assertAlmostEqual(16838 * TWIP_MM, 297.0, delta=0.1)


class TestCitationExpansion(unittest.TestCase):
    def test_ranges_and_lists(self):
        self.assertEqual([1, 3, 4, 5], _expand_numbers("1,3-5"))
        self.assertEqual([1, 2, 3], _expand_numbers("1，2、3"))
        self.assertEqual([2, 3, 4], _expand_numbers("2–4"))

    def test_absurd_range_is_ignored(self):
        self.assertEqual([], _expand_numbers("1-99999"))


class TestParsing(TempProject):
    _n = 0

    def build(self, paras, **kw) -> str:
        type(self)._n += 1
        path = f"{self.tmp}/t{type(self)._n}.docx"
        write_docx(path, document_xml(paras, **kw))
        return path

    def test_style_inheritance_from_based_on(self):
        """Heading2 basedOn Normal：未覆盖的属性要从 Normal 继承过来。"""
        path = self.build([h1("第一章 绪论"), body("正文段落文字内容。")])
        doc = load(path)
        h = doc.paragraphs[0]
        self.assertEqual(1, h.heading_level)
        self.assertEqual("黑体", h.font_east_asia)
        self.assertAlmostEqual(16.0, h.size_pt)

    def test_direct_format_overrides_style(self):
        path = self.build([Para("标题被改小了", "Heading1", rpr='<w:sz w:val="28"/>')])
        doc = load(path)
        self.assertAlmostEqual(14.0, doc.paragraphs[0].size_pt)

    def test_first_line_chars_and_twips_are_both_understood(self):
        chars = self.build([body("甲", ppr='<w:ind w:firstLineChars="200"/>')])
        twips = self.build([body("乙", ppr='<w:ind w:firstLine="480"/>')])
        self.assertAlmostEqual(2.0, load(chars).paragraphs[0].first_line_chars)
        self.assertAlmostEqual(480, load(twips).paragraphs[0].first_line_twips)

    def test_line_spacing_auto_vs_exact(self):
        auto = self.build([body("甲", ppr='<w:spacing w:line="360" w:lineRule="auto"/>')])
        exact = self.build([body("乙", ppr='<w:spacing w:line="400" w:lineRule="exact"/>')])
        p_auto = load(auto).paragraphs[0]
        p_exact = load(exact).paragraphs[0]
        self.assertEqual(("auto", 360.0), (p_auto.line_rule, p_auto.line_value))
        self.assertEqual(("exact", 400.0), (p_exact.line_rule, p_exact.line_value))

    def test_roles(self):
        path = self.build([
            h1("第一章 绪论"),
            body("正文段落，引用文献[1]。"),
            caption("图1-1 系统结构"),
            ref_heading(),
            ref_entry("[1] 张三. 题名[J]. 期刊, 2023."),
        ])
        doc = load(path)
        roles = [p.role for p in doc.paragraphs]
        self.assertEqual([Role.HEADING, Role.BODY, Role.CAPTION, Role.OTHER,
                          Role.REF_ENTRY], roles)
        self.assertIn(1, doc.ref_entries)
        self.assertEqual([1], doc.ref_uses[0].numbers)

    def test_bracket_number_after_ref_section_is_entry(self):
        """参考文献章节里以 [n] 开头的段落必须算条目，不能被当成正文引用。"""
        path = self.build([ref_heading(), ref_entry("[2] 李四. 题名[M]. 2022.")])
        doc = load(path)
        self.assertEqual(Role.REF_ENTRY, doc.paragraphs[1].role)
        self.assertEqual([], doc.ref_uses)

    def test_multiple_sections_are_counted(self):
        paras = [
            f'<w:p><w:pPr><w:sectPr><w:pgSz w:w="11906" w:h="16838"/>'
            f'<w:pgMar w:top="1417" w:right="1417" w:bottom="1417" w:left="1701"/></w:sectPr></w:pPr>'
            f'<w:r><w:t>第一节</w:t></w:r></w:p>',
            '<w:p><w:r><w:t>第二节正文</w:t></w:r></w:p>',
        ]
        body_xml = ("".join(paras) +
                    '<w:sectPr><w:pgSz w:w="16838" w:h="11906" w:orient="landscape"/>'
                    '<w:pgMar w:top="1417" w:right="1417" w:bottom="1417" w:left="1701"/></w:sectPr>')
        from tools.build_fixtures import W_NS
        xml = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
               f'<w:document xmlns:w="{W_NS}"><w:body>{body_xml}</w:body></w:document>')
        path = self.tmp + "/multi.docx"
        write_docx(path, xml)
        doc = load(path)
        self.assertEqual(2, len(doc.sections))
        self.assertEqual("landscape", doc.sections[1].orientation)

    def test_missing_styles_xml_still_parses(self):
        """styles.xml 缺失时不能崩，只是拿不到样式继承。"""
        import zipfile
        path = self.tmp + "/nostyles.docx"
        with zipfile.ZipFile(path, "w") as zf:
            zf.writestr("word/document.xml", document_xml([body("没有样式表")]))
        doc = load(path)
        self.assertEqual(1, len(doc.paragraphs))


if __name__ == "__main__":
    unittest.main()
