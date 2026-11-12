# -*- coding: utf-8 -*-
"""由样例数据生成 source_example.json，供 verify.py --source 做覆盖检查回归。"""
import os
import sys
import json

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

d = json.load(open(os.path.join(SKILL, "examples", "example_kwdata.json"), encoding="utf-8"))
lines = []
for g in d["groups"]:
    for s in g["shots"]:
        dl = (s.get("dialogue") or "").strip()
        if "：" in dl:
            sp, _, txt = dl.partition("：")
            lines.append({"type": "dialogue", "speaker": sp.split("（")[0], "paren": "", "text": txt})
data = {
    "schema": "source/1",
    "script": {"lines": lines},
    "storyboard": {"units": [{"unit": g["no"], "shots": [s["id"] for s in g["shots"]]} for g in d["groups"]]},
}
out = os.path.join(HERE, "source_example.json")
json.dump(data, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("已生成 %s：%d 句台词" % (out, len(lines)))
