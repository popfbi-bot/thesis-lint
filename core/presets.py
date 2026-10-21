"""preset 加载。

preset 是 JSON，必须含 name / description / source 三个元字段：
- name：给人看的名字
- description：一句话说明适用范围
- source：依据出处（国标条款号或高校规范文件名），可追溯到具体文本

校验放在这里，缺字段直接报错——避免「不知道依据的规则」混进检查结果。
"""

from __future__ import annotations

import json
import os
from typing import Dict, List

HERE = os.path.dirname(os.path.abspath(__file__))
PRESET_DIR = os.path.join(os.path.dirname(HERE), "presets")

META_KEYS = ("name", "description", "source")
REQUIRED_SECTIONS = ("page", "body", "headings", "line_spacing", "references")

# 每个配置段里必须有、且类型会被规则直接使用的字段
PAGE_KEYS = ("margin_top_mm", "margin_bottom_mm", "margin_left_mm", "margin_right_mm")
BODY_KEYS = ("font_east_asia", "size_pt", "first_line_indent_chars",
             "space_before_pt_max", "space_after_pt_max")
HEADING_KEYS = ("font_east_asia", "size_pt", "bold")


class PresetError(Exception):
    pass


def preset_dir() -> str:
    return PRESET_DIR


def list_presets() -> List[str]:
    if not os.path.isdir(PRESET_DIR):
        return []
    return sorted(
        os.path.splitext(f)[0]
        for f in os.listdir(PRESET_DIR)
        if f.endswith(".json")
    )


def load_preset(name_or_path: str) -> Dict:
    path = name_or_path
    if not os.path.isfile(path):
        path = os.path.join(PRESET_DIR, name_or_path)
        if not path.endswith(".json"):
            path += ".json"
    if not os.path.isfile(path):
        raise PresetError(
            f"找不到 preset：{name_or_path}（可选：{', '.join(list_presets())}）")
    with open(path, "r", encoding="utf-8") as fh:
        try:
            data = json.load(fh)
        except json.JSONDecodeError as exc:
            raise PresetError(f"preset 不是合法 JSON：{path}（{exc}）")
    validate(data, path)
    data["_path"] = path
    return data


def validate(data: Dict, path: str = "<preset>") -> None:
    if not isinstance(data, dict):
        raise PresetError(f"{path}：preset 必须是 JSON 对象")
    missing = [k for k in META_KEYS if not str(data.get(k, "")).strip()]
    if missing:
        raise PresetError(f"{path}：缺少元字段 {', '.join(missing)}")
    missing = [k for k in REQUIRED_SECTIONS if k not in data]
    if missing:
        raise PresetError(f"{path}：缺少配置段 {', '.join(missing)}")
    _require(data["page"], PAGE_KEYS, f"{path}：page 缺少字段")
    _require(data["body"], BODY_KEYS, f"{path}：body 缺少字段")
    for level in ("1", "2", "3"):
        if level not in data["headings"]:
            raise PresetError(f"{path}：headings 缺少 {level} 级标题配置")
        _require(data["headings"][level], HEADING_KEYS,
                 f"{path}：headings.{level} 缺少字段")
    spacing = data["line_spacing"]
    if spacing.get("rule") not in ("auto", "exact"):
        raise PresetError(f'{path}：line_spacing.rule 只能是 "auto" 或 "exact"')
    if not isinstance(spacing.get("value"), (int, float)):
        raise PresetError(f"{path}：line_spacing.value 必须是数字")


def _require(section: dict, keys, prefix: str) -> None:
    if not isinstance(section, dict):
        raise PresetError(f"{prefix.split('：')[0]}：配置段必须是对象")
    missing = [k for k in keys if k not in section]
    if missing:
        raise PresetError(f"{prefix} {', '.join(missing)}")
