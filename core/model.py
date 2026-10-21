"""数据模型：把 .docx 的 XML 事实整理成规则层可以直接判断的结构。

约定：
- 这里只放「已解析出的事实」，不做任何格式判断；
- 所有长度单位统一为毫米（mm），字号统一为磅（pt）。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


def snippet(text: str, limit: int = 20) -> str:
    """段落摘要，用于让用户真的能找到位置。"""
    text = " ".join(text.split())
    return text if len(text) <= limit else text[:limit] + "…"


@dataclass
class Role:
    """Paragraph 的分类。规则按角色决定期望值。"""

    BODY = "body"            # 正文
    HEADING = "heading"      # 各级标题
    CAPTION = "caption"      # 图表题注
    REF_ENTRY = "ref_entry"  # 参考文献条目
    OTHER = "other"          # 封面、摘要标题等不受本工具管的部分


@dataclass
class Paragraph:
    index: int                      # 1 起的正文段落序号，报告里就用这个
    text: str
    style_id: str = ""              # w:pStyle（如 Heading1 / Normal），可能为空
    style_name: str = ""            # styles.xml 里对应的 w:name
    outline_level: Optional[int] = None  # 0/1/2 => 一/二/三级标题
    role: str = Role.OTHER
    heading_level: int = 0          # 仅 HEADING 有效：1/2/3
    # 以下为「生效值」：直接格式优先于样式，已做继承合并
    font_ascii: Optional[str] = None
    font_east_asia: Optional[str] = None
    size_pt: Optional[float] = None
    bold: Optional[bool] = None
    align: Optional[str] = None              # left/center/right/both/distribute
    first_line_chars: Optional[float] = None  # w:firstLineChars / 100
    first_line_twips: Optional[float] = None  # w:firstLine，1 字符=100 (twips)
    line_rule: Optional[str] = None          # auto(倍数) / exact(固定值)
    line_value: Optional[float] = None       # auto: 1/240 倍；exact: twips
    space_before_pt: Optional[float] = None
    space_after_pt: Optional[float] = None
    page_index: int = 0             # 该段落在第几个分节（1 起），仅用于定位提示

    @property
    def location(self) -> str:
        return f"第 {self.index} 段「{snippet(self.text)}」"


@dataclass
class Section:
    index: int
    page_width_mm: float
    page_height_mm: float
    margin_top_mm: float
    margin_bottom_mm: float
    margin_left_mm: float
    margin_right_mm: float
    orientation: str = "portrait"


@dataclass
class RefUse:
    """正文里的 [n] 引用。"""

    numbers: List[int]
    paragraph_index: int


@dataclass
class Doc:
    path: str
    paragraphs: List[Paragraph] = field(default_factory=list)
    sections: List[Section] = field(default_factory=list)
    ref_entries: Dict[int, Paragraph] = field(default_factory=dict)  # 条目序号 -> 段落
    ref_uses: List[RefUse] = field(default_factory=list)

    @property
    def body_paragraphs(self) -> List[Paragraph]:
        return [p for p in self.paragraphs if p.role == Role.BODY]

    @property
    def headings(self) -> List[Paragraph]:
        return [p for p in self.paragraphs if p.role == Role.HEADING]
