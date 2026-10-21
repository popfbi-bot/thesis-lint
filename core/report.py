"""报告渲染：终端 / Markdown / 单文件 HTML。

三条输出共享同一个 CheckResult，只是排版不同。
HTML 要求单文件、内联 CSS、可离线打开、可直接截图，所以不留任何外链。
"""

from __future__ import annotations

import html
import os
import sys
from datetime import datetime
from typing import Dict, List

from .model import Doc
from .rules.base import LEVEL_ERROR, LEVEL_WARN, Issue

LEVEL_ORDER = (LEVEL_ERROR, LEVEL_WARN)
LEVEL_LABEL = {LEVEL_ERROR: "错误", LEVEL_WARN: "警告"}


class CheckResult:
    def __init__(self, doc: Doc, preset: dict, issues: List[Issue], rule_titles: Dict[str, str]):
        self.doc = doc
        self.preset = preset
        self.issues = issues
        self.rule_titles = rule_titles

    @property
    def errors(self) -> List[Issue]:
        return [i for i in self.issues if i.level == LEVEL_ERROR]

    @property
    def warnings(self) -> List[Issue]:
        return [i for i in self.issues if i.level == LEVEL_WARN]

    @property
    def exit_code(self) -> int:
        """有 error -> 1；只有 warn 或全无问题 -> 0。"""
        return 1 if self.errors else 0

    @property
    def summary(self) -> str:
        return f"{len(self.errors)} errors, {len(self.warnings)} warnings"

    def grouped(self) -> List[tuple]:
        out = []
        for level in LEVEL_ORDER:
            items = [i for i in self.issues if i.level == level]
            if items:
                out.append((level, items))
        return out


# --------------------------------------------------------------------------
# 终端
# --------------------------------------------------------------------------

_COLOR = {
    LEVEL_ERROR: "\033[1;31m",   # 亮红
    LEVEL_WARN: "\033[1;33m",    # 黄
    "reset": "\033[0m",
    "dim": "\033[2m",
    "bold": "\033[1m",
    "green": "\033[1;32m",
    "cyan": "\033[36m",
}


def _supports_color(stream) -> bool:
    if os.environ.get("NO_COLOR"):
        return False
    return bool(getattr(stream, "isatty", lambda: False)())


def render_terminal(result: CheckResult, stream=None, color: bool | None = None) -> str:
    stream = stream or sys.stdout
    use_color = _supports_color(stream) if color is None else color

    def c(text: str, *keys: str) -> str:
        if not use_color:
            return text
        return "".join(_COLOR[k] for k in keys) + text + _COLOR["reset"]

    preset = result.preset
    lines: List[str] = []
    lines.append(c("thesis-lint", "bold") + "  " + c(f"v{_version()}", "dim"))
    lines.append(f"文件：{os.path.basename(result.doc.path)}")
    lines.append(f"规范：{preset['name']}（{os.path.basename(preset.get('_path', ''))}）")
    lines.append(f"依据：{preset['source']}")
    lines.append(f"规模：{len(result.doc.paragraphs)} 段 / {len(result.doc.sections)} 节")
    lines.append("")

    if not result.issues:
        lines.append(c("✓ 格式体检全部通过，可以放心交稿。", "green"))
        lines.append("")
        lines.append(c("0 errors, 0 warnings", "green"))
        return "\n".join(lines)

    for level, items in result.grouped():
        head = f"{LEVEL_LABEL[level]}（{len(items)}）"
        key = "bold"
        lines.append(c(head, key, "red" if level == LEVEL_ERROR else "yellow"))
        by_rule: Dict[str, List[Issue]] = {}
        for it in items:
            by_rule.setdefault(it.rule_id, []).append(it)
        for rule_id, group in by_rule.items():
            title = result.rule_titles.get(rule_id, rule_id)
            lines.append(f"  {c(rule_id, 'cyan')}  {title}")
            for it in group:
                lines.append(f"    {c('✗' if level == LEVEL_ERROR else '!', key)} {it.location}")
                lines.append(f"      实际：{it.actual}")
                lines.append(f"      应为：{it.expected}")
                lines.append(f"      怎么改：{it.fix_hint}")
        lines.append("")

    total = result.summary
    lines.append(c(total, "red" if result.errors else "yellow"))
    return "\n".join(lines)


def _version() -> str:
    try:
        from .. import __version__
        return __version__
    except Exception:  # pragma: no cover - 版本号只是装饰
        return "0.1.0"


# --------------------------------------------------------------------------
# Markdown
# --------------------------------------------------------------------------

def render_markdown(result: CheckResult) -> str:
    doc, preset = result.doc, result.preset
    out: List[str] = []
    out.append("# 论文格式体检报告")
    out.append("")
    out.append(f"- 文件：`{os.path.basename(doc.path)}`")
    out.append(f"- 规范：**{preset['name']}**（`{os.path.basename(preset.get('_path', ''))}`）")
    out.append(f"- 依据：{preset['source']}")
    out.append(f"- 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}")
    out.append(f"- 规模：{len(doc.paragraphs)} 段 / {len(doc.sections)} 节")
    out.append("")
    out.append(f"## {result.summary}")
    out.append("")

    if not result.issues:
        out.append("✓ 六项检查全部通过。")
        out.append("")
        out.append("> 允许「列出但未引用」的参考文献条目，因此不检查反向对应关系。")
        return "\n".join(out)

    for level, items in result.grouped():
        icon = "🔴" if level == LEVEL_ERROR else "🟡"
        out.append(f"### {icon} {LEVEL_LABEL[level]}（{len(items)}）")
        out.append("")
        by_rule: Dict[str, List[Issue]] = {}
        for it in items:
            by_rule.setdefault(it.rule_id, []).append(it)
        for rule_id, group in by_rule.items():
            title = result.rule_titles.get(rule_id, rule_id)
            out.append(f"#### `{rule_id}` {title}")
            out.append("")
            for idx, it in enumerate(group, 1):
                out.append(f"{idx}. **{it.location}**")
                out.append(f"   - 实际：{it.actual}")
                out.append(f"   - 应为：{it.expected}")
                out.append(f"   - 怎么改：{it.fix_hint}")
                out.append(f"   - 依据：{it.source}")
            out.append("")
    out.append("> 参考文献只检查「正文引用 → 列表条目」方向；允许列出但未引用的条目。")
    return "\n".join(out)


# --------------------------------------------------------------------------
# HTML（单文件 + 内联 CSS）
# --------------------------------------------------------------------------

_CSS = """
:root {
  --bg: #0f1115; --card: #171a21; --fg: #e8eaed; --dim: #9aa3af;
  --error: #ff5c68; --error-bg: #2a1417; --warn: #f0b429; --warn-bg: #2a2312;
  --ok: #37d67a; --line: #262b36; --accent: #6ea8fe;
}
* { box-sizing: border-box; }
body {
  margin: 0; padding: 40px 20px 64px; background: var(--bg); color: var(--fg);
  font: 15px/1.7 -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC",
        "Hiragino Sans GB", "Microsoft YaHei", sans-serif;
}
.wrap { max-width: 900px; margin: 0 auto; }
.title { font-size: 26px; font-weight: 700; letter-spacing: .5px; margin: 0 0 6px; }
.sub { color: var(--dim); font-size: 13px; margin-bottom: 28px; }
.cards { display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px; margin-bottom: 28px; }
.card { background: var(--card); border: 1px solid var(--line); border-radius: 14px; padding: 18px 20px; }
.card .n { font-size: 34px; font-weight: 800; line-height: 1.1; }
.card .k { color: var(--dim); font-size: 12px; letter-spacing: 1px; text-transform: uppercase; }
.card.err .n { color: var(--error); }
.card.wrn .n { color: var(--warn); }
.card.ok .n { color: var(--ok); }
.meta { background: var(--card); border: 1px solid var(--line); border-radius: 14px; padding: 16px 20px; margin-bottom: 28px; font-size: 13px; }
.meta div { display: flex; gap: 10px; padding: 3px 0; }
.meta b { color: var(--dim); font-weight: 500; min-width: 64px; }
h2 { font-size: 16px; margin: 30px 0 12px; letter-spacing: .5px; }
h2 .badge { font-size: 12px; padding: 2px 9px; border-radius: 999px; margin-left: 8px; vertical-align: 2px; }
h2.err .badge { background: var(--error-bg); color: var(--error); }
h2.wrn .badge { background: var(--warn-bg); color: var(--warn); }
.rule { background: var(--card); border: 1px solid var(--line); border-left: 3px solid var(--line); border-radius: 12px; padding: 16px 20px; margin-bottom: 14px; }
.rule.err { border-left-color: var(--error); }
.rule.wrn { border-left-color: var(--warn); }
.rule .hd { display: flex; align-items: baseline; gap: 10px; margin-bottom: 10px; flex-wrap: wrap; }
.rule .rid { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 12px; color: var(--accent); background: #1d2330; padding: 2px 8px; border-radius: 6px; }
.rule .rt { font-weight: 600; }
.issue { padding: 10px 0; border-top: 1px dashed var(--line); }
.issue:first-of-type { border-top: none; }
.issue .loc { font-weight: 600; margin-bottom: 6px; }
.issue .row { display: grid; grid-template-columns: 62px 1fr; gap: 8px; font-size: 14px; padding: 2px 0; }
.issue .row .lab { color: var(--dim); font-size: 12px; padding-top: 3px; }
.issue .row.act .val { color: var(--error); }
.issue .row.exp .val { color: var(--ok); }
.issue .src { color: var(--dim); font-size: 12px; margin-top: 6px; }
.pass { background: var(--card); border: 1px solid var(--line); border-left: 3px solid var(--ok); border-radius: 12px; padding: 22px 24px; font-size: 16px; }
.pass .big { font-size: 20px; font-weight: 700; color: var(--ok); margin-bottom: 6px; }
.foot { color: var(--dim); font-size: 12px; margin-top: 30px; border-top: 1px solid var(--line); padding-top: 14px; }
"""


def _e(text: object) -> str:
    return html.escape(str(text), quote=True)


def render_html(result: CheckResult) -> str:
    doc, preset = result.doc, result.preset
    name = os.path.basename(doc.path)
    n_err, n_wrn = len(result.errors), len(result.warnings)
    ok = not result.issues

    parts: List[str] = []
    parts.append("<!DOCTYPE html>")
    parts.append('<html lang="zh-CN"><head><meta charset="utf-8">')
    parts.append('<meta name="viewport" content="width=device-width, initial-scale=1">')
    parts.append(f"<title>论文格式体检报告 - {_e(name)}</title>")
    parts.append(f"<style>{_CSS}</style></head><body><div class=\"wrap\">")
    parts.append('<div class="title">论文格式体检报告</div>')
    parts.append(
        f'<div class="sub">{_e(name)} · 规范 {_e(preset["name"])} · '
        f'{datetime.now().strftime("%Y-%m-%d %H:%M")}</div>')

    ok_card = "ok" if ok else "wrn"
    parts.append('<div class="cards">')
    parts.append(f'<div class="card err"><div class="n">{n_err}</div><div class="k">Errors</div></div>')
    parts.append(f'<div class="card wrn"><div class="n">{n_wrn}</div><div class="k">Warnings</div></div>')
    verdict = "PASS" if ok else "FAIL"
    parts.append(f'<div class="card {ok_card}"><div class="n">{verdict}</div><div class="k">Verdict</div></div>')
    parts.append('</div>')

    parts.append('<div class="meta">')
    parts.append(f'<div><b>规范</b><span>{_e(preset["name"])}（{_e(os.path.basename(preset.get("_path", "")))}）</span></div>')
    parts.append(f'<div><b>依据</b><span>{_e(preset["source"])}</span></div>')
    parts.append(f'<div><b>规模</b><span>{len(doc.paragraphs)} 段 / {len(doc.sections)} 节</span></div>')
    parts.append('</div>')

    if ok:
        parts.append('<div class="pass"><div class="big">✓ 六项检查全部通过</div>')
        parts.append('可以直接交稿了。</div>')
    else:
        for level, items in result.grouped():
            cls = "err" if level == LEVEL_ERROR else "wrn"
            parts.append(f'<h2 class="{cls}">{LEVEL_LABEL[level]}<span class="badge">{len(items)}</span></h2>')
            by_rule: Dict[str, List[Issue]] = {}
            for it in items:
                by_rule.setdefault(it.rule_id, []).append(it)
            for rule_id, group in by_rule.items():
                title = result.rule_titles.get(rule_id, rule_id)
                parts.append(f'<div class="rule {cls}">')
                parts.append(f'<div class="hd"><span class="rid">{_e(rule_id)}</span>'
                             f'<span class="rt">{_e(title)}</span></div>')
                for it in group:
                    parts.append('<div class="issue">')
                    parts.append(f'<div class="loc">{_e(it.location)}</div>')
                    parts.append(f'<div class="row act"><span class="lab">实际</span><span class="val">{_e(it.actual)}</span></div>')
                    parts.append(f'<div class="row exp"><span class="lab">应为</span><span class="val">{_e(it.expected)}</span></div>')
                    parts.append(f'<div class="row"><span class="lab">怎么改</span><span class="val">{_e(it.fix_hint)}</span></div>')
                    parts.append(f'<div class="src">依据：{_e(it.source)}</div>')
                    parts.append('</div>')
                parts.append('</div>')
        parts.append(f'<div class="meta"><div><b>合计</b><span>{n_err} errors, {n_wrn} warnings</span></div></div>')

    parts.append('<div class="foot">只读检查，未修改原文件。参考文献只检查「正文引用 → 列表条目」方向，'
                 '允许列出但未引用的条目。</div>')
    parts.append("</div></body></html>")
    return "\n".join(parts)


# --------------------------------------------------------------------------
# 落盘
# --------------------------------------------------------------------------

def write_outputs(result: CheckResult, out_md: str | None, out_html: str | None) -> List[str]:
    written: List[str] = []
    if out_md:
        with open(out_md, "w", encoding="utf-8") as fh:
            fh.write(render_markdown(result) + "\n")
        written.append(out_md)
    if out_html:
        with open(out_html, "w", encoding="utf-8") as fh:
            fh.write(render_html(result) + "\n")
        written.append(out_html)
    return written
