"""preset 加载与校验：元字段缺失、配置段缺字段都要给出人能看懂的错误。"""

from __future__ import annotations

import json
import os
import unittest

from tests.helpers import TempProject
from core.presets import PresetError, list_presets, load_preset


class TestPreset(TempProject):
    def write(self, data) -> str:
        path = os.path.join(self.tmp, "p.json")
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False)
        return path

    def base(self) -> dict:
        return json.loads(json.dumps(load_preset("undergrad")))

    def test_builtin_presets_load(self):
        for name in list_presets():
            with self.subTest(preset=name):
                self.assertIn("source", load_preset(name))

    def test_missing_meta_field_raises(self):
        for key in ("name", "description", "source"):
            with self.subTest(missing=key):
                data = self.base()
                data.pop(key)
                with self.assertRaises(PresetError) as ctx:
                    load_preset(self.write(data))
                self.assertIn(key, str(ctx.exception))

    def test_missing_page_field_raises_friendly_error(self):
        data = self.base()
        data["page"].pop("margin_top_mm")
        with self.assertRaises(PresetError) as ctx:
            load_preset(self.write(data))
        self.assertIn("margin_top_mm", str(ctx.exception))
        self.assertNotIn("KeyError", str(ctx.exception))

    def test_bad_line_spacing_rule_raises(self):
        data = self.base()
        data["line_spacing"]["rule"] = "multiple"
        with self.assertRaises(PresetError):
            load_preset(self.write(data))

    def test_missing_heading_level_raises(self):
        data = self.base()
        data["headings"].pop("3")
        with self.assertRaises(PresetError):
            load_preset(self.write(data))


if __name__ == "__main__":
    unittest.main()
