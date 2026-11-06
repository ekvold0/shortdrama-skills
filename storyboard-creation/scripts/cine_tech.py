# -*- coding: utf-8 -*-
"""grokfilm 300 条技法注册表（自动生成，勿手改）。

用法: from cine_tech import TECHS, BY_SLUG, by_slot, by_tier, allowed, fill

by_slot 兼容两种写法：
    by_slot('C3d 画面参数·运镜')  -> 按落点代码取（30 条）
    by_slot('3')                  -> 按十字段列号取（C3 全部子项）

真源：工作区 技法库整合/cine_tech.json；技能内为只读副本。
"""
import json
import os

_HERE = os.path.dirname(os.path.abspath(__file__))
_CANDIDATES = [
    os.path.join(_HERE, "cine_tech.json"),           # 与 py 同目录（技能内副本）
    os.path.join(_HERE, "..", "cine_tech.json"),     # 上一级（真源布局）
]
_P = next((p for p in _CANDIDATES if os.path.exists(p)), _CANDIDATES[0])

DATA = json.load(open(_P, encoding="utf-8"))
VERSION = DATA.get("version", "")
COUNT = DATA.get("count", 0)
TECHS = DATA["items"]
BY_SLUG = {t["slug"]: t for t in TECHS}


def by_tier(t):
    return [x for x in TECHS if x["tier"] == t]


def by_slot(code):
    """落点代码（含空格，如 'C3d 画面参数·运镜'）或十字段列号（如 '3'）。"""
    s = str(code).strip()
    if s.startswith("C") and " " in s:
        return [x for x in TECHS if x["slot"] == s]
    return [x for x in TECHS if x["kw_col"] == s]


def by_cat(c):
    return [x for x in TECHS if x["category"] == c]


#: fill() 的常用别名：文档里写 deg/direction/angle 也能填对槽（模板槽名是 n/dir）。
_SLOT_ALIAS = {"deg": "n", "degree": "n", "angle": "n", "direction": "dir", "speed": "v"}


def fill(slug, **kw):
    """按模板填槽。未提供的槽保留 {xxx} 原样，便于看出还缺什么。"""
    t = BY_SLUG[slug]["template"]
    for k, v in kw.items():
        k = _SLOT_ALIAS.get(k, k)
        t = t.replace("{" + k + "}", str(v))
    return t


def allowed(tiers=("T1", "T2")):
    return [x for x in TECHS if x["tier"] in tiers]


def english_names(minlen=5):
    """英文技法名小写集合（去掉括号注释），供校验器生成词表。"""
    out = set()
    for t in TECHS:
        base = t["en"].split("(")[0].strip().lower()
        if len(base) >= minlen:
            out.add(base)
    return sorted(out)
