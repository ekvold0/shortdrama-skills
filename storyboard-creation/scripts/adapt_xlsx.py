"""分镜表 xlsx → data.json 适配器（存量项目迁移用）。

为什么需要它：verify.py 吃的是 data.json（18 个单元字段 + 5 个镜头字段），
而存量项目全是 Excel 分镜表，列只有 9 个。没有适配器，300 多个 xlsx 都用不上新校验。

用法：
  python adapt_xlsx.py <分镜表.xlsx> --out <data.json> [--episode S03] [--aspect 9:16]

原则：
  1. **不编内容**。Excel 里没有的字段就不写，交给适配报告列出来，由人补。
  2. 只做机械映射（列 → 字段、段落 → 字段），不做改写。
  3. 输出 adapt_report.txt：哪些字段表里没有、每个单元缺什么。
  4. V2.3：表头模糊匹配（去分隔符后按包含关系认列），缺必需列时打印实际表头后退出。
"""
import argparse
import json
import os
import re

from openpyxl import load_workbook

# 分镜表列名（现行模板）
COL_SHOT = "镜号"
COL_SIZE = "景别"
COL_DUR = "时长"
COL_CAM = "机位与运镜"
COL_CONTENT = "画面内容与景深设计"
COL_ACTION = "动作"  # V2.1 新增列；存量表没有，则回退到从「画面内容与景深设计」摘录
COL_LANDING = "短镜落地"  # V2.3 新增列：并进/后期/砍掉，短于 4 秒的镜头必填（CT26）
COL_LINE = "台词/音效"
COL_EMO = "情绪目标"
COL_CUT = "剪辑法/转场"
COL_UNIT = "单元"

UNIT_FIELDS = ["id", "scene", "coord", "shot_id", "source", "aspect", "style",
               "cast", "time", "era", "date", "weather", "timeline",
               "action", "emotion", "line", "sound", "link"]

DUR_RE = re.compile(r"([0-9]+(?:\.[0-9]+)?)\s*秒")
TIMELINE_RE = re.compile(r"第\s*([0-9.]+)\s*[—-]\s*([0-9.]+)\s*秒\s*[｜|]\s*(.+)")
# 台词行样例：0.6—3.2 王桂兰（中高音，语速约每秒2.7字）“我说，让个座。”7字
LINE_SEG_RE = re.compile(r"([0-9]+(?:\.[0-9]+)?)\s*[—\-]\s*([0-9]+(?:\.[0-9]+)?)\s*([^“”]*)[“”]([^“”]+)[“”]")
QUOTE_RE = re.compile(r"[“”]([^“”]+)[“”]")


def s(v):
    if v is None:
        return ""
    if isinstance(v, str):
        return v.strip()
    return str(v).strip()


def find_sheet(wb, *names):
    for name in names:
        for ws in wb.worksheets:
            if s(ws.title) == name:
                return ws
    for name in names:
        for ws in wb.worksheets:
            if name in s(ws.title):
                return ws
    return None


def read_kv(ws):
    """两列 key-value 表 → dict（保持顺序）。"""
    out = {}
    if ws is None:
        return out
    for row in ws.iter_rows(min_row=1, values_only=True):
        if not row:
            continue
        k = s(row[0]) if len(row) > 0 else ""
        v = s(row[1]) if len(row) > 1 else ""
        if k:
            out[k] = v
    return out


def parse_dur(text):
    m = DUR_RE.search(s(text))
    return float(m.group(1)) if m else None


def parse_dialogue(text):
    """台词/音效 列 → line（带起止时间的句子列表）+ 表演提示。

    只认【人物台词】标签段里的「起—止 说话人（提示）“台词”」，
    字数核算交给 verify（它只数引号内的字，按真实跨度算语速）。
    """
    t = s(text)
    lines, notes = [], []
    for m in LINE_SEG_RE.finditer(t):
        start, end, who, words = m.group(1), m.group(2), s(m.group(3)), s(m.group(4))
        speaker = re.split(r"[（(]", who)[0].strip()
        note = ""
        nm = re.search(r"[（(]([^）)]*)[）)]", who)
        if nm:
            note = s(nm.group(1))
            notes.append("{}（{}）".format(speaker, note))
        lines.append({"speaker": speaker, "start": float(start), "end": float(end),
                      "text": words, "note": note})
    return lines, notes


def parse_shot_no(raw, episode):
    """001 → S03-001；已带前缀的原样保留。"""
    t = s(raw)
    if not t:
        return ""
    if re.match(r"^[A-Z]+\d*-", t):
        return t
    m = re.search(r"(\d+)$", t)
    if not m:
        return t
    return "{}-{}".format(episode, m.group(1).zfill(3))


def split_sound(text):
    """台词/音效 列 → 四层（voice/fx/ambience/reverb）。只按标签切，不猜内容。"""
    t = s(text)
    layers = {"voice": "", "fx": "", "ambience": "", "reverb": ""}
    if not t:
        return layers
    label_map = [("人物台词", "voice"), ("台词", "voice"), ("对白", "voice"),
                 ("环境音", "ambience"), ("拟音", "fx"), ("音效", "fx")]
    parts = re.split(r"【([^】]+)】", t)
    cur = None
    for i, p in enumerate(parts):
        if i % 2 == 1:
            cur = None
            for key, bucket in label_map:
                if key in p:
                    cur = bucket
                    break
        else:
            if not s(p):
                continue
            if cur:
                layers[cur] = (layers[cur] + "；" + s(p)).strip("；")
            else:
                layers["fx"] = (layers["fx"] + "；" + s(p)).strip("；")
    if not any(layers.values()):
        layers["voice"] = t
    return layers


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("xlsx")
    ap.add_argument("--out", required=True)
    ap.add_argument("--episode", default="S01")
    ap.add_argument("--aspect", default="9:16")
    ap.add_argument("--era", default="", help="时代（全片恒定，可省；给了才写入 meta）")
    ap.add_argument("--weather", default="", help="天气（全片恒定，可省；给了才写入 meta）")
    args = ap.parse_args()

    wb = load_workbook(args.xlsx, data_only=True)
    ws_sb = find_sheet(wb, "分镜表")
    if ws_sb is None:
        raise SystemExit("找不到『分镜表』sheet")

    header = [s(c) for c in next(ws_sb.iter_rows(min_row=1, max_row=1, values_only=True))]
    col = {}
    for i, h in enumerate(header):
        col[h] = i

    # V2.3：表头不再死认——先精确匹配，再按去分隔符后的包含关系兜一层。
    # 存量表里「时长」常写成「时长(秒)」「时长（秒）」，新版还会多出「短镜落地」这类列。
    def _nrm(x):
        return re.sub(r"[\s\-—_/／·()（）:：]", "", s(x)).lower()

    wanted = (COL_SHOT, COL_UNIT, COL_SIZE, COL_DUR, COL_CAM, COL_ACTION,
              COL_LANDING, COL_CONTENT, COL_LINE, COL_EMO, COL_CUT)
    for want in wanted:
        if want in col:
            continue
        wn = _nrm(want)
        for i, h in enumerate(header):
            hn = _nrm(h)
            if hn and (wn == hn or wn in hn):
                col[want] = i
                break
    miss_required = [k for k in (COL_SHOT, COL_DUR) if k not in col]
    if miss_required:
        raise SystemExit("分镜表缺必需列 {}；表头实际是：{}".format(miss_required, header))
    miss_optional = [k for k in (COL_ACTION, COL_LANDING, COL_CUT, COL_UNIT) if k not in col]
    if miss_optional:
        print("[提示] 分镜表没有这些列，按旧表处理：{}".format(miss_optional))

    def cell(row, name):
        idx = col.get(name)
        if idx is None or idx >= len(row):
            return ""
        return s(row[idx])

    # 逐行分单元
    order, groups = [], {}
    for row in ws_sb.iter_rows(min_row=2, values_only=True):
        if not row or not cell(row, COL_SHOT):
            continue
        uid = cell(row, COL_UNIT) or "U1"
        if uid not in groups:
            groups[uid] = []
            order.append(uid)
        groups[uid].append(row)

    # 辅助表
    kv_unit = read_kv(find_sheet(wb, "生成单元"))
    kv_const = read_kv(find_sheet(wb, "常量与自检"))
    kv_story = read_kv(find_sheet(wb, "梗概与结构"))

    cast = [k for k in kv_const if k and not re.match(r"^[一二三四五六七八九十]+、", k)]

    units = []
    report = {"file": args.xlsx, "missing_by_field": {}, "units": []}
    for uid in order:
        rows = groups[uid]
        shots, lines, emotes = [], [], []
        t_cur = 0.0
        for row in rows:
            dur = parse_dur(cell(row, COL_DUR)) or 0.0
            sid = parse_shot_no(cell(row, COL_SHOT), args.episode)
            shots.append({
                "id": sid,
                "size": cell(row, COL_SIZE),
                "duration": dur,
                "camera": cell(row, COL_CAM),
                "content": cell(row, COL_CONTENT),
                "action": cell(row, COL_ACTION),
                "landing": cell(row, COL_LANDING),
            })
            ln = cell(row, COL_LINE)
            if ln:
                lines.append(ln)
            em = cell(row, COL_EMO)
            if em:
                emotes.append("{}：{}".format(sid, em))
            t_cur += dur

        # 生成单元段落（同 sheet 的段落式分镜）
        para = ""
        for k, v in kv_unit.items():
            if uid in k:
                para = v
                break
        def para_line(label):
            m = re.search(r"【" + label + r"】([^\n]*)", para)
            return s(m.group(1)) if m else ""

        timeline = []
        for sh in shots:
            timeline.append("{}｜{}，{}".format(sh["id"], sh["size"], sh["camera"]))
        line_items, per_notes = parse_dialogue(" ".join(lines))
        # action：V2.1 有「动作」列就直接用；存量表没有，则逐字摘录「画面内容与景深设计」，
        # 打 derived 标记交人剥离景深/机位措辞（不编内容）。
        own_action = "；".join(s(sh["action"]) for sh in shots if s(sh["action"]))
        action_text = own_action or "；".join(s(sh["content"]) for sh in shots if s(sh["content"]))
        unit = {
            "id": uid,
            "scene": args.episode,
            "coord": "{} / {}".format(args.episode, uid),
            "shot_id": shots[0]["id"] if shots else "",
            "source": para_line("原文片段"),
            "aspect": "{}｜1080×1920".format(args.aspect),
            "style": para_line("视觉风格"),
            "cast": "、".join(cast),
            "timeline": "\n".join(timeline),
            "action": action_text,
            "action_derived": "" if own_action else (
                "content（自动摘录，待人工剥离景深/机位措辞）" if action_text else ""),
            "emotion": "；".join(emotes),
            "line": line_items if line_items else "",
            "sound": split_sound(" ".join(lines)),
            "shots": shots,
        }
        if per_notes:
            unit["sound"]["note"] = "；".join(per_notes)
        # time 从「生成单元」表的段落头取（U1　0:00.0—0:12.5（12.5秒））
        m = re.search(r"([0-9]{1,2}:[0-9]{2}\.[0-9])\s*[—-]\s*([0-9]{1,2}:[0-9]{2}\.[0-9])", para)
        if m:
            unit["time"] = "{}—{}".format(m.group(1), m.group(2))
        if "时空" in " ".join(kv_story.keys()):
            for k, v in kv_story.items():
                if "时空" in k:
                    unit["date"] = v
                    break
        units.append(unit)
        miss = [f for f in UNIT_FIELDS if f not in unit or unit.get(f) in ("", None)]
        report["units"].append({"id": uid, "missing": miss})
        for f in miss:
            report["missing_by_field"].setdefault(f, 0)
            report["missing_by_field"][f] += 1

    total = round(sum(sh["duration"] for u in units for sh in u["shots"]), 1)
    data = {
        "meta": {
            "project": os.path.basename(os.path.dirname(os.path.abspath(args.xlsx))),
            "episode": args.episode,
            "mode": "vertical",
            "aspect": args.aspect,
            "resolution": "1080x1920",
            "total_seconds": total,
            "check_date": "",
            "anchors": [{"type": "角色", "name": k, "content": s(kv_const[k])[:120]}
                        for k in cast],
        },
        "units": units,
    }
    # era / weather 是全片恒定量：命令行给了才写进 meta（供单元继承），不编默认值
    for key in ("era", "weather"):
        val = getattr(args, key, None)
        if val:
            data["meta"][key] = val
    os.makedirs(os.path.dirname(os.path.abspath(args.out)) or ".", exist_ok=True)
    json.dump(data, open(args.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    rep_path = os.path.splitext(args.out)[0] + "_adapt_report.txt"
    lines_out = ["适配报告：{}".format(args.xlsx),
                 "单元 {}｜镜头 {}｜合计 {:.1f} 秒".format(len(units), sum(len(u["shots"]) for u in units), total),
                 "",
                 "【表里根本没有的字段】（按缺口单元数排序）"]
    for f, n in sorted(report["missing_by_field"].items(), key=lambda x: -x[1]):
        lines_out.append("  {:<10} 缺 {}/{} 个单元{}".format(f, n, len(units),
                          "  ← 分镜表无对应列，需人工补" if n == len(units) else ""))
    lines_out.append("")
    lines_out.append("【逐单元】")
    for u in report["units"]:
        lines_out.append("  {}: 缺 {}".format(u["id"], "、".join(u["missing"]) or "无"))
    open(rep_path, "w", encoding="utf-8").write("\n".join(lines_out))
    print("units:", len(units), "shots:", sum(len(u["shots"]) for u in units), "total:", total, "s")
    print("->", args.out)
    print("->", rep_path)


if __name__ == "__main__":
    main()
