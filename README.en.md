# thesis-lint

**One command to format-check your thesis: `python cli.py check thesis.docx`.**

![report.html screenshot](docs/report.png)

Runs entirely on your machine with zero third-party dependencies. Feed it a `.docx`, get back a list of problems you can actually act on: which rule, which paragraph, what you have, what you need, and how to fix it.

No LLM. Your manuscript is never uploaded. Same input, same output, every time.

## Why you can trust it

- **Local, offline, read-only.** It reads the XML inside `.docx` using nothing but Python's `zipfile` and `xml.etree`. A test asserts the input file's sha256 is unchanged after a run.
- **Every rule cites its source.** Each issue carries a `source` field pointing at the standard clause (GB/T 7713.1—2006, GB/T 7714—2015), not "because I said so".
- **The rules are proven to fail.** The repo ships a deliberately broken `bad.docx` and `tools/verify_rules_go_red.py` — break any rule and its test goes red immediately.

## Quick start

Python 3.10+. Nothing to `pip install`.

```bash
python cli.py check thesis.docx
python cli.py check thesis.docx --preset master --out report.md
python cli.py check thesis.docx --html report.html
python cli.py presets
```

Terminal output is grouped by severity and ends with a single summary line:

```
11 errors, 1 warnings
```

`--html` writes a single self-contained file (inline CSS) you can open offline or screenshot and post:

![all clear](docs/report-pass.png)

## Exit codes

| Situation | Exit code |
|---|---|
| Any error | `1` |
| Warnings only | `0` |
| Clean | `0` |

## Six checks in v0.1

| # | Check | `rule_id` |
|---|---|---|
| 1 | Paper size & margins | `PAGE_MARGIN` |
| 2 | Body paragraph style | `BODY_FONT` |
| 3 | Heading hierarchy | `HEADING_LEVEL` |
| 4 | Line spacing | `LINE_SPACING` |
| 5 | First-line indent | `INDENT` |
| 6 | Reference numbering | `REF_NUMBERING` |

**Not checked yet** (planned for v0.2): TOC fields, caption formatting, page numbers, full GB/T 7714 bibliographic fields, equation numbering, headers/footers.

### Reference numbering is one-directional

Only "in-text citation → bibliography entry" is checked. An entry that is listed but never cited is **not** an error — many universities allow it. The report says so explicitly, so you never delete a useful reference just to silence a warning.

## Presets

Criteria live in `presets/*.json`, not in code, because every school has its own rules. Three ship with the tool: `undergrad`, `master`, `gb-7714`. Each preset must declare `name`, `description` and `source` — the `source` becomes the «依据» line in every report, and loading fails without it.

Point `--preset` at your own file to match your school's spec. See [README.md](README.md) for the full JSON shape.

## Development

```bash
python3 -m unittest discover -s tests -t . -v
python3 tools/build_fixtures.py
python3 tools/verify_rules_go_red.py
```
