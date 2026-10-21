#!/usr/bin/env python3
"""thesis-lint —— 一条命令给学位论文做格式体检。

用法：
    python cli.py check thesis.docx
    python cli.py check thesis.docx --preset master --out report.md
    python cli.py check thesis.docx --html report.html
    python cli.py presets

退出码：有 error -> 1；只有 warn 或无问题 -> 0。
本工具只读：不修改输入文件，不创建工作目录残留。
"""

from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core import __version__                    # noqa: E402
from core.checker import check_file            # noqa: E402
from core.docx import DocxError                # noqa: E402
from core.presets import PresetError, list_presets, load_preset  # noqa: E402
from core.report import render_terminal, write_outputs           # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="thesis-lint",
        description="给 .docx 学位论文做格式体检，输出可整改的问题清单。纯本地、零第三方依赖。",
    )
    parser.add_argument("-V", "--version", action="version", version=f"thesis-lint {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    p_check = sub.add_parser("check", help="检查一份 .docx 论文")
    p_check.add_argument("docx", help="待检查的 .docx 文件")
    p_check.add_argument("--preset", default="undergrad",
                         help="规范 preset 名称（默认 undergrad），用 presets 子命令查看全部")
    p_check.add_argument("--out", metavar="REPORT.md", help="同时输出 Markdown 报告")
    p_check.add_argument("--html", metavar="REPORT.html",
                         help="同时输出单文件 HTML 报告（内联 CSS，可离线打开、可直接截图）")
    p_check.add_argument("--no-color", action="store_true", help="终端不着色（也认 NO_COLOR 环境变量）")
    p_check.add_argument("--color", action="store_true",
                         help="强制着色（默认跟终端是否 tty 自动判断）")

    sub.add_parser("presets", help="列出可用 preset")
    return parser


def cmd_presets() -> int:
    names = list_presets()
    if not names:
        print("presets 目录里没有可用的规范文件。", file=sys.stderr)
        return 1
    print(f"可用 preset（{len(names)}）：")
    for name in names:
        try:
            data = load_preset(name)
        except PresetError as exc:
            print(f"  {name:12s}  ⚠ {exc}")
            continue
        print(f"  {name:12s}  {data['name']} —— {data['description']}")
        print(f"  {'':12s}  依据：{data['source']}")
    return 0


def cmd_check(args) -> int:
    try:
        preset = load_preset(args.preset)
    except PresetError as exc:
        print(f"错误：{exc}", file=sys.stderr)
        return 2
    try:
        result = check_file(args.docx, preset)
    except DocxError as exc:
        print(f"错误：{exc}", file=sys.stderr)
        return 2

    # 默认 color=None：交给 _supports_color() 按 isatty / NO_COLOR 判断，
    # 不能写成 not args.no_color，那会强制着色、绕过 tty 判断。
    color = True if args.color else (False if args.no_color else None)
    sys.stdout.write(render_terminal(result, sys.stdout, color=color) + "\n")

    written = write_outputs(result, args.out, args.html)
    for path in written:
        print(f"报告已写入：{path}")
    return result.exit_code


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "presets":
        return cmd_presets()
    if args.command == "check":
        return cmd_check(args)
    parser.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
