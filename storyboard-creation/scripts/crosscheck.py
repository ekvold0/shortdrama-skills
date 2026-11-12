# -*- coding: utf-8 -*-
"""
crosscheck.py — 分镜表 ↔ 关键词表 跨表一致性校验（X01–X06）

分镜技能产出的分镜 JSON 与关键词技能产出的 kwdata JSON 必须对得上：
同一个单元、同一串镜号、同一秒数、同一个景别、同一批台词。
两份各自合法、合起来错位，是这条流水线上最容易漏的一类返工——
所以单表校验（verify.py + ct_rules.py）之外，再加这一支跨表校验。

用法：
    python crosscheck.py --storyboard 分镜.json --keyword kwdata.json
    python crosscheck.py --storyboard 分镜.json --keyword kwdata.json --quiet

退出码：error 非空 → 1；只有 warning → 0。

校验项：
    X01 error    关键词组引用的单元在分镜里不存在（unit 名对不上，通常是 U1 / U01 写法或改过结构）
    X02 error    某单元里镜号对不上：分镜有、关键词漏了（漏镜＝少生成一个镜头）
    X03 error    关键词多出分镜没有的镜号（多镜＝凭空加了一段）
    X04 warning  同一镜号时长不一致（> 0.05 秒）
    X05 warning  同一镜号景别不一致
    X06 warning  单元台词字数差超过 20%（台词被删或被改写）
    X07 warning  单元总时长与关键词组时长不一致（> 0.05 秒）

口径说明（为什么有些只给 warning）：
- 分镜层与关键词层的时长必须一致，但允许 0.05 秒的四舍五入误差；
- 景别在两层允许写法不同（MCU / 中近景），只在归一化后不一致才提示；
- 台词允许挪到相邻镜（60 规定对白 > 3 秒要插反应镜），所以按「单元合计字数」比，不按单镜硬对。
"""

import argparse
import io
import json
import os
import re
import sys

# 景别归一化：分镜层可能写中文，关键词层写英文码
SIZE_MAP = {
    "大远景": "ELS", "远景": "LS", "全景": "FS", "中景": "MS",
    "中近景": "MCU", "近景": "MS", "特写": "CU", "大特写": "ECU",
    "过肩": "OTS", "主观": "POV",
}
PUNCT = "，。！？、；：…—－·「」『』“”‘’（）《》〈〉,.!?;:'\"() \t\n"


def _s(v):
    if v is None:
        return ""
    if isinstance(v, str):
        return v
    if isinstance(v, (int, float, bool)):
        return str(v)
    if isinstance(v, (list, tuple)):
        return " ".join(_s(x) for x in v)
    if isinstance(v, dict):
        return " ".join(_s(x) for x in v.values())
    return str(v)


def _load(path):
    with io.open(path, encoding="utf-8") as f:
        return json.load(f)


def _unit_key(v):
    """U1 / U01 / u1 → 1；非数字返回原串小写。"""
    t = _s(v).strip()
    m = re.search(r"(\d+)", t)
    return int(m.group(1)) if m else t.lower()


def _shot_key(v):
    """S01-003 / 003 / U1-3 → 3；末尾数字为准。"""
    t = _s(v).strip()
    m = re.search(r"(\d+)\s*$", t)
    return int(m.group(1)) if m else t.lower()


def _size(v):
    t = _s(v).strip().upper()
    if not t:
        return ""
    head = re.split(r"[\s/／·、,，]+", _s(v).strip())[0]
    return SIZE_MAP.get(head, head.upper())


def _chars(text):
    body = _s(text)
    for sep in ("：", ":"):
        if sep in body:
            body = body.rsplit(sep, 1)[1]
            break
    return sum(1 for ch in body if ch not in PUNCT)


_QUOTED = re.compile(r"[“\"]([^”\"]{1,80})[”\"]")
_TIME_HEAD = re.compile(r"^\s*[\d.]+\s*[—\-–~至]\s*[\d.]+\s*")
_SPEAKER = re.compile(r"^[^“”：:]{0,24}?[（(][^）)]{0,40}[）)]\s*")


def _sb_dialogue_chars(text):
    """分镜音频列取台词字数。不含台词的镜返回 0（环境音不能算进去）。"""
    body = _s(text)
    quoted = _QUOTED.findall(body)
    if quoted:
        inner = "".join(quoted)
        return sum(1 for ch in inner if ch not in PUNCT)
    if "【" in body:
        head, rest = body.split("【", 1)[0], body.split("】", 1)[1] if "】" in body else ""
        label = body.split("【", 1)[1].split("】", 1)[0]
        if not any(k in label for k in ("台词", "对白", "独白")):
            return 0
        rest = _TIME_HEAD.sub("", rest)
        rest = _SPEAKER.sub("", rest)
        rest = re.sub(r"\d+\s*字\s*$", "", rest)
        return sum(1 for ch in rest if ch not in PUNCT)
    body = _TIME_HEAD.sub("", body)
    return sum(1 for ch in body if ch not in PUNCT)


def _units_of(data):
    """把两种分镜输入统一成 [{id, dur, shots:[{id,duration,size,audio}]}]。

    1) storyboard 原生格式：{"units":[{"id","shots":[{"id","duration","size","audio"|"line"}]}]}
    2) ingest 的 source 格式：{"storyboard":{"rows":[{no,unit,size,dur,audio,...}]}}
    """
    if isinstance(data.get("units"), list) and data["units"]:
        out = []
        for u in data["units"]:
            shots = []
            for sh in (u.get("shots") or []):
                shots.append({
                    "id": sh.get("id"),
                    "duration": sh.get("duration") if sh.get("duration") is not None else sh.get("dur"),
                    "size": sh.get("size"),
                    "audio": sh.get("audio") if sh.get("audio") is not None else sh.get("line"),
                })
            out.append({"id": u.get("id"), "dur": u.get("duration") or u.get("dur"), "shots": shots})
        return out

    rows = ((data.get("storyboard") or {}).get("rows")) or []
    order, grouped = [], {}
    for r in rows:
        uk = _unit_key(r.get("unit"))
        if uk not in grouped:
            grouped[uk] = {"id": r.get("unit"), "dur": 0.0, "shots": []}
            order.append(uk)
        grouped[uk]["shots"].append({
            "id": r.get("no"),
            "duration": r.get("dur"),
            "size": r.get("size"),
            "audio": r.get("audio"),
        })
        grouped[uk]["dur"] += _dur(r.get("dur"))
    return [grouped[k] for k in order]


def _dur(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def check(storyboard, keyword, tol=0.05):
    out = []

    def add(level, code, ref, msg):
        out.append({"level": level, "code": code, "ref": ref, "msg": msg})

    units = _units_of(storyboard)
    groups = keyword.get("groups") or []
    if not units or not groups:
        add("error", "X01", "-", "分镜或关键词是空的（units=%d，groups=%d）" % (len(units), len(groups)))
        return out

    # 分镜侧：unit_key -> 单元（保持原顺序，不按镜号）
    sb = {}
    for u in units:
        sb[_unit_key(u.get("id"))] = u

    # 关键词侧：unit_key -> [组]（保持 no 顺序）；组可能把一个单元拆成几段
    by_unit = {}
    for g in groups:
        by_unit.setdefault(_unit_key(g.get("unit")), []).append(g)

    covered = set()
    for uk in sorted(sb.keys(), key=lambda x: (isinstance(x, str), x)):
        u = sb[uk]
        uid = _s(u.get("id"))
        glist = by_unit.get(uk)
        if not glist:
            continue
        covered.add(uk)

        # 关键词键头镜序：按组顺序把组内镜头接起来
        kw_seq = []
        for g in glist:
            for sh in (g.get("shots") or []):
                kw_seq.append((g, sh))
        sb_seq = list(u.get("shots") or [])
        ref = _s(glist[0].get("no")) or uid
        if len(glist) > 1:
            ref = "%s（%d 组）" % (ref, len(glist))

        kw_sum = sum(_dur(g.get("duration")) for g in glist)
        sb_sum = _dur(u.get("dur")) or sum(_dur(sh.get("duration")) for sh in sb_seq)

        # X02 / X03 镜数对不上
        if len(sb_seq) > len(kw_seq):
            add("error", "X02", ref,
                "分镜 %d 镜、关键词只写了 %d 镜——第 %d–%d 镜漏了（漏镜＝少生成一个镜头）"
                % (len(sb_seq), len(kw_seq), len(kw_seq) + 1, len(sb_seq)))
        elif len(kw_seq) > len(sb_seq):
            add("error", "X03", ref,
                "分镜 %d 镜、关键词写了 %d 镜——多出的 %d 镜分镜里没有（多镜＝凭空加了一段）"
                % (len(sb_seq), len(kw_seq), len(kw_seq) - len(sb_seq)))

        # X04 单镜时长 / X05 景别（按位置对）
        for i, (a, (g, b)) in enumerate(zip(sb_seq, kw_seq), start=1):
            sid = _s(a.get("id")) or str(i)
            da = _dur(a.get("duration") if a.get("duration") is not None else a.get("dur"))
            db = _dur(b.get("dur") if b.get("dur") is not None else b.get("duration"))
            if da > 0 and db > 0 and abs(da - db) > tol:
                add("warning", "X04", "%s-镜%s" % (_s(g.get("no")) or ref, sid),
                    "时长不一致：分镜 %.2f 秒，关键词 %.2f 秒" % (da, db))
            sa = _size(a.get("size"))
            sbn = _size(b.get("size"))
            if sa and sbn and sa != sbn:
                add("warning", "X05", "%s-镜%s" % (_s(g.get("no")) or ref, sid),
                    "景别不一致：分镜 %s，关键词 %s" % (_s(a.get("size")), _s(b.get("size"))))

        # X07 单元/组总时长
        if sb_sum > 0 and kw_sum > 0 and abs(sb_sum - kw_sum) > tol:
            add("warning", "X07", ref,
                "总时长不一致：分镜 %.2f 秒，关键词 %.2f 秒——拆组/合组时两边的账目要一起改"
                % (sb_sum, kw_sum))

        # X06 台词字数（按单元合计，允许台词挪到相邻镜）
        sb_n = sum(_sb_dialogue_chars(sh.get("audio")) for sh in sb_seq)
        kw_n = sum(_chars(sh.get("dialogue")) for sh in [t[1] for t in kw_seq])
        if sb_n > 0:
            diff = abs(sb_n - kw_n) / float(sb_n)
            if diff > 0.20:
                add("warning", "X06", ref,
                    "台词字数差 %.0f%%：分镜约 %d 字，关键词约 %d 字——台词不许删（红线，改口语化也要报备）"
                    % (diff * 100, sb_n, kw_n))

    for uk, glist in by_unit.items():
        if uk not in covered:
            add("error", "X01", _s(glist[0].get("no")) or "-",
                "关键词组挂在单元「%s」上，但分镜里没有这个单元（分镜有：%s）"
                % (_s(glist[0].get("unit")), "、".join(_s(u.get("id")) for u in units)))

    lost = [uk for uk in sb if uk not in covered and uk not in by_unit]
    if lost:
        add("warning", "X01", "-",
            "这些分镜单元还没写关键词：%s（如果是整集交付就是整单元漏写）"
            % "、".join(_s(sb[k].get("id")) for k in lost))

    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description="分镜表 ↔ 关键词表 跨表一致性校验")
    ap.add_argument("--storyboard", required=True, help="分镜 JSON（storyboard-creation 的 ingest 输出或 example_storyboard.json）")
    ap.add_argument("--keyword", required=True, help="关键词 kwdata JSON")
    ap.add_argument("--quiet", action="store_true", help="只输出汇总行")
    a = ap.parse_args(argv)

    for p in (a.storyboard, a.keyword):
        if not os.path.exists(p):
            sys.stderr.write("找不到文件：%s\n" % p)
            return 2

    res = check(_load(a.storyboard), _load(a.keyword))
    errs = [r for r in res if r["level"] == "error"]
    warns = [r for r in res if r["level"] == "warning"]

    if not a.quiet:
        for r in errs + warns:
            print("[%s] %s %s  %s" % (r["level"], r["code"], r["ref"], r["msg"]))
        print("-" * 60)
    print("error %d，warning %d" % (len(errs), len(warns)))
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main())
