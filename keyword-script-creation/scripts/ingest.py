# -*- coding: utf-8 -*-
"""读剧本文档 + 分镜头脚本文档 → source.json + 对齐报告。

用法：
    python scripts/ingest.py --script 剧本.docx --storyboard 分镜.xlsx --out work/X_S03_source.json
    python scripts/ingest.py --script 剧本.txt --storyboard 分镜.docx --out ...

输出的 source.json 给 verify.py --source 做覆盖检查；控制台打印对齐报告，供第 2 步裁决。
"""
import os
import re
import sys
import json
import argparse

from docx import Document
from openpyxl import load_workbook

SCENE_RE = re.compile(r"^\s*(【\s*场景[^】]*】|场景\s*[0-9一二三四五六七八九十]+|第[一二三四五六七八九十百0-9]+[场集]|[0-9]{1,3}[\.、．]\s*(内景|外景|日|夜)|内景|外景|INT\.|EXT\.)")
SPEAK_RE = re.compile(r"^\s*([\u4e00-\u9fa5A-Za-z0-9·]{1,8})\s*(（[^）]{0,20}）)?\s*[：:]\s*(.+)$")
DUR_RE = re.compile(r"(\d+(?:\.\d+)?)")
ASPECT_RE = re.compile(r"(9\s*[:：]\s*16|4\s*[:：]\s*3|16\s*[:：]\s*9|1080\s*[x×*]\s*1920|1920\s*[x×*]\s*1440)")
HEADER_ALIAS = {
    "镜号": ("镜号", "镜头号", "序号", "编号"),
    "景别": ("景别", "镜头景别"),
    "时长": ("时长", "时长(秒)", "时长（秒）", "秒数"),
    "机位": ("机位", "机位/运镜", "运镜", "角度", "机位角度"),
    "画面": ("画面内容", "画面", "内容", "画面描述"),
    "音频": ("音频", "音频/对白", "对白", "声音", "台词"),
    "备注": ("备注", "说明", "画面备注"),
    "单元": ("单元", "AI单元", "生成单元", "AI 单元"),
    "技法": ("技法", "主技法", "技法落点"),
    "参考": ("参考电影", "画面参数·参考电影", "参考"),
}


def read_txt(path):
    for enc in ("utf-8-sig", "utf-8", "gb18030"):
        try:
            with open(path, "r", encoding=enc) as f:
                return f.read()
        except UnicodeDecodeError:
            continue
    raise SystemExit("无法识别文本编码：%s" % path)


def read_docx(path):
    doc = Document(path)
    paras = [(p.text or "").strip() for p in doc.paragraphs]
    tables = []
    for t in doc.tables:
        rows = [[(c.text or "").strip() for c in r.cells] for r in t.rows]
        if rows:
            tables.append(rows)
    return paras, tables


def parse_script(path):
    if path.lower().endswith(".txt"):
        raw_paras = read_txt(path).splitlines()
        tables = []
    else:
        raw_paras, tables = read_docx(path)
    lines, scenes = [], []
    texts = [re.sub(r"^[△▲]\s*", "", p.strip()) for p in raw_paras]
    texts = [t for t in texts if t]
    # 先统计「冒号前的短前缀」出现次数：只有 2–4 字且出现≥2 次的才认作说话人，
    # 避免把「监控画面：钢梁掉下」「他在手心写：三个月」这类动作行误判成台词。
    freq = {}
    for t in texts:
        m = SPEAK_RE.match(t)
        if m:
            freq[m.group(1)] = freq.get(m.group(1), 0) + 1
    cast = {k for k, v in freq.items() if 2 <= len(k) <= 4 and v >= 2}
    if not cast:
        cast = set(freq)
    for t in texts:
        if SCENE_RE.match(t) and len(t) <= 40:
            scenes.append({"no": len(scenes) + 1, "text": t})
            lines.append({"type": "scene", "text": t})
            continue
        m = SPEAK_RE.match(t)
        if m and len(m.group(3)) >= 2 and m.group(1) in cast:
            lines.append({"type": "dialogue", "speaker": m.group(1),
                          "paren": m.group(2) or "", "text": m.group(3).strip()})
        else:
            lines.append({"type": "action", "text": t})
    if not lines and tables:
        for rows in tables:
            for row in rows:
                txt = " ".join(x for x in row if x)
                if txt:
                    lines.append({"type": "action", "text": txt})
    return lines, scenes


def col_map(header):
    m = {}
    for idx, h in enumerate(header):
        hh = (h or "").replace("\n", "").strip()
        for key, aliases in HEADER_ALIAS.items():
            if key in m:
                continue
            if any(a == hh or (a in hh and len(hh) <= 12) for a in aliases):
                m[key] = idx
                break
    return m


def rows_to_shots(rows):
    """找到表头行，读镜号非空的行。"""
    head_i = -1
    cmap = {}
    for i, row in enumerate(rows[:20]):
        c = col_map(row)
        if "镜号" in c and ("画面" in c or "景别" in c):
            head_i, cmap = i, c
            break
    if head_i < 0:
        return [], {}, head_i
    shots = []
    for row in rows[head_i + 1:]:
        def get(k):
            idx = cmap.get(k)
            return (row[idx] if idx is not None and idx < len(row) else "") or ""
        no = get("镜号").strip()
        if not no:
            if shots:
                break
            continue
        dm = DUR_RE.search(get("时长"))
        shots.append({
            "no": no,
            "size": get("景别"),
            "dur": float(dm.group(1)) if dm else 0.0,
            "cam": get("机位"),
            "pic": get("画面"),
            "audio": get("音频"),
            "note": get("备注"),
            "unit": get("单元"),
            "tech": get("技法"),
            "ref": get("参考"),
        })
    return shots, cmap, head_i


def load_storyboard(path):
    if path.lower().endswith(".docx"):
        _, tables = read_docx(path)
        best = ([], {}, -1)
        for rows in tables:
            shots, cmap, hi = rows_to_shots(rows)
            if len(shots) > len(best[0]):
                best = (shots, cmap, hi)
        return best[0], best[1], best[2]
    wb = load_workbook(path, data_only=True, read_only=True)
    best = ([], {}, -1, "")
    for ws in wb.worksheets:
        rows = [[("" if v is None else str(v)).strip() for v in r] for r in ws.iter_rows(values_only=True)]
        shots, cmap, hi = rows_to_shots(rows)
        if len(shots) > len(best[0]):
            best = (shots, cmap, hi, ws.title)
    return best[0], best[1], best[2]


def guess_aspect(texts):
    for t in texts:
        m = ASPECT_RE.search(t or "")
        if m:
            s = m.group(1).replace(" ", "").replace("：", ":")
            if "9:16" in s or "1080" in s:
                return "9:16", "1080x1920"
            if "4:3" in s or "1920" in s:
                return "4:3", "1920x1440"
    return "", ""


def build_units(shots):
    """有单元列按单元聚合；没有则按 累计≤15 秒 自动切，标待确认。"""
    has_unit = any(s.get("unit") for s in shots)
    units = []
    if has_unit:
        cur = None
        for s in shots:
            u = s["unit"] or (cur["unit"] if cur else "U1")
            if cur is None or u != cur["unit"]:
                cur = {"unit": u, "shots": [], "dur": 0.0, "confirmed": True,
                       "tech": [], "ref": []}
                units.append(cur)
            cur["shots"].append(s["no"])
            cur["dur"] = round(cur["dur"] + s["dur"], 1)
            _collect(cur, s)
    else:
        cur = {"unit": "auto-1", "shots": [], "dur": 0.0, "confirmed": False,
               "tech": [], "ref": []}
        for s in shots:
            if cur["shots"] and cur["dur"] + s["dur"] > 15.0:
                units.append(cur)
                cur = {"unit": "auto-%d" % (len(units) + 1), "shots": [], "dur": 0.0,
                       "confirmed": False, "tech": [], "ref": []}
            cur["shots"].append(s["no"])
            cur["dur"] = round(cur["dur"] + s["dur"], 1)
            _collect(cur, s)
        if cur["shots"]:
            units.append(cur)
    return units, has_unit


def _collect(unit, shot):
    """把镜头级的技法/参考电影汇到单元块（分镜表没有这两列时静默跳过）。"""
    for key in ("tech", "ref"):
        v = (shot.get(key) or "").strip()
        if v and v not in unit[key]:
            unit[key].append(v)


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    ap = argparse.ArgumentParser(description="剧本+分镜 → source.json")
    ap.add_argument("--script", required=True)
    ap.add_argument("--storyboard", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    for p in (a.script, a.storyboard):
        if not os.path.isfile(p):
            raise SystemExit("找不到文件：%s" % p)

    lines, scenes = parse_script(a.script)
    shots, cmap, head_i = load_storyboard(a.storyboard)
    units, has_unit = build_units(shots)

    dialogues = [l for l in lines if l["type"] == "dialogue"]
    srt = " ".join((s.get("audio") or "") + " " + (s.get("pic") or "") for s in shots)
    missing = [d for d in dialogues if d["text"][:8] and d["text"][:8] not in srt]
    over = [u for u in units if u["dur"] > 15.05]
    long_shots = [s for s in shots if s["dur"] > 15.05]
    aspect, res = guess_aspect([a.storyboard] + [s.get("cam", "") + s.get("pic", "") for s in shots[:3]])

    report = {
        "script_lines": len(lines),
        "dialogue_lines": len(dialogues),
        "action_lines": sum(1 for l in lines if l["type"] == "action"),
        "script_scenes": len(scenes),
        "storyboard_rows": len(shots),
        "storyboard_header_row": head_i + 1 if head_i >= 0 else None,
        "storyboard_columns": sorted(cmap.keys()),
        "has_unit_column": has_unit,
        "has_tech_column": "技法" in cmap,
        "has_ref_column": "参考" in cmap,
        "units": len(units),
        "units_over_15s": [u["unit"] for u in over],
        "shots_over_15s": [s["no"] for s in long_shots],
        "dialogue_not_in_storyboard": [d["text"][:40] for d in missing][:30],
        "dialogue_not_in_storyboard_count": len(missing),
        "aspect_guess": aspect,
        "resolution_guess": res,
        "notes": [],
    }
    if not shots:
        report["notes"].append("分镜里没读到镜头行：检查表头是否含「镜号」「画面/景别」。")
    if not has_unit:
        report["notes"].append("分镜无「单元」列：已按累计≤15秒自动切组，需人工确认（confirmed=false）。")
    if missing:
        report["notes"].append("有 %d 句剧本台词在分镜音频/画面里找不到：可能是分镜漏写，或以剧本为准补镜。" % len(missing))
    if over:
        report["notes"].append("有 %d 个单元超过 15 秒：横屏可用 2.5 模型，竖屏必须拆组。" % len(over))

    out = {
        "schema": "source/1",
        "meta": {"script": os.path.abspath(a.script), "storyboard": os.path.abspath(a.storyboard)},
        "script": {"lines": lines, "scenes": scenes,
                   "dialogue_count": len(dialogues),
                   "full_text": "\n".join(l["text"] for l in lines)},
        "storyboard": {"rows": shots, "units": units,
                       "columns": sorted(cmap.keys()),
                       "has_unit_column": has_unit,
                       "header_row": head_i + 1 if head_i >= 0 else None},
        "report": report,
    }
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)

    print("剧本：%d 行（对白 %d，动作 %d，场景 %d）" % (
        len(lines), len(dialogues), report["action_lines"], len(scenes)))
    print("分镜：%d 镜，%d 单元，列 %s，单元列 %s" % (
        len(shots), len(units), "/".join(report["storyboard_columns"]), "有" if has_unit else "无"))
    if aspect:
        print("画幅推断：%s（%s）——需用户确认" % (aspect, res))
    if over:
        print("超 15 秒单元：%s" % "、".join(report["units_over_15s"]))
    if missing:
        print("分镜未覆盖台词 %d 句（前 5）：" % len(missing))
        for d in missing[:5]:
            print("  - %s：%s" % (d["speaker"], d["text"][:40]))
    for n in report["notes"]:
        print("[note] " + n)
    print("已写入：%s" % a.out)


if __name__ == "__main__":
    main()
