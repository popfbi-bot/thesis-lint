# 参与开发

## 环境

Python 3.10+，不需要装任何第三方包。

```bash
python3 -m unittest discover -s tests -t . -v
```

## 改规则时的三条硬约束

1. **不许写死判据数值。** 字体、字号、页边距、行距全部来自 `presets/*.json`。代码里出现 `12.0`、`"宋体"` 这类字面量视为 bug。
2. **每条规则必须能失败。** 新增或修改规则后跑一遍：

   ```bash
   python3 tools/verify_rules_go_red.py
   ```

   它会把规则改成永远返回空，确认对应反例测试真的变红。永远绿的规则等于没写。
3. **出处写进 `source`。** 规则模块头注释和 Issue 的 `source` 都要能指到具体条款（国标号 + 条款号，或某校规范文件名 + 章节）。

## 加一条新规则

1. 在 `core/rules/` 下新建文件，暴露 `RULE_ID` / `TITLE` / `check(doc, preset)`。
2. 在 `core/rules/__init__.py` 的 `RULES` 里登记。
3. 判据加到三个 preset 里（并补 `tests/test_cli.py::test_every_preset_has_required_meta` 需要的元字段）。
4. `tools/build_fixtures.py` 加一份「只错这一项」的 `per_rule/<RULE_ID>.docx`，重跑生成。
5. 测试补齐：`test_<rule>_is_detected` + `test_<rule>_no_false_positive`。

## fixtures 是生成物

`fixtures/` 里的 `.docx` 由 `tools/build_fixtures.py` 手工拼 OOXML 生成，不用 Word 做。改样例请改脚本后重跑，不要直接改二进制文件。

## 不要动的东西

- `tests/` 里已有的断言值——那是口径基准。要改口径先讨论。
- `VERSION` / `CHANGELOG.md`（发布时由维护者更新）。
- 不要直接推 `main`，走 PR。
