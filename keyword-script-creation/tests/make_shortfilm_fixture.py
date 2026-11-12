# -*- coding: utf-8 -*-
"""回归夹具：由 example_kwdata.json 克隆出 60 组、720 秒的短篇数据。

仅为验证 shortfilm 分支（总览 sheet / 三幕占比 / M#-C##-XZ-### 编号 / 600–900 秒账目），
不含真实剧情，不要当交付样本。
"""
import os
import sys
import json
import copy

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
EX = os.path.join(os.path.dirname(HERE), "examples")
src = json.load(open(os.path.join(EX, "example_kwdata.json"), encoding="utf-8"))

meta = src["meta"]
meta.update({"title": "示例·短篇（回归）", "mode": "shortfilm", "aspect": "4:3",
             "resolution": "1920x1440", "default_model": "2.0", "episode": None,
             "target_total_sec": 720, "version": "V1.0"})

base = copy.deepcopy(src["groups"][0])
base["duration"] = 12.0
base["params"]["camera"] = base["params"]["camera"].replace("竖屏9:16（1080×1920）", "横屏4:3（1920×1440）")
base["params"]["blocking"] = base["params"]["blocking"].replace("竖屏中心安全区", "横屏画面左右均衡")
for k, s in enumerate(base["shots"]):
    s["dur"] = 3.0
    s["dialogue"] = "王桂兰（中高音，语速约每秒2.5字）：我说，小伙子，让个座，我站不住了。" if k == 0 else ""
base["audio"] = {"note": "单句组，落在 5—12 秒区间。", "whitespace": 0.5, "silence": 0}
base["neg"]["plot"] = "王桂兰坐下、林晓抬头对视、吊环静止、车厢空荡"

SCENES = ["城市公交晚高峰车厢", "医院走廊", "出租屋客厅", "小区门口"]
ACTS = [("M1", 13), ("M2", 33), ("M3", 14)]  # 13*12=156s(21.7%) 33*12=396s(55%) 14*12=168s(23.3%)
groups = []
i = 0
for act, n in ACTS:
    for _ in range(n):
        i += 1
        g = copy.deepcopy(base)
        scene_no = (i - 1) // 5 + 1
        idx = (i - 1) % 5 + 1
        g["no"] = "%s-C%02d-XZ-%03d" % (act, scene_no, idx)
        g["act"] = act
        g["scene_no"] = "C%02d" % scene_no
        g["scene_name"] = SCENES[(scene_no - 1) % len(SCENES)]
        g["event"] = "第%d组：王桂兰施压，林晓沉默。" % i
        g["node"] = "钩子" if i == 1 else ("转折" if i == 31 else ("收束" if i == 60 else ""))
        g["makeup"] = g["makeup"].replace("城市公交晚高峰车厢", g["scene_name"])
        groups.append(g)

data = {
    "schema": "kwdata/1",
    "meta": meta,
    "story": src["story"],
    "anchors": src["anchors"],
    "acts": [
        {"act": "M1", "name": "建置", "target": "20–25%", "node": "开场钩子/人物处境"},
        {"act": "M2", "name": "对抗", "target": "50–55%", "node": "升级/反转/代价"},
        {"act": "M3", "name": "收束", "target": "20–25%", "node": "选择/回响"},
    ],
    "groups": groups,
    "selfcheck": src["selfcheck"],
}
out = os.path.join(EX, "example_shortfilm.json")
json.dump(data, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("已生成 %s：%d 组，%.1f 秒" % (out, len(groups), sum(g["duration"] for g in groups)))
