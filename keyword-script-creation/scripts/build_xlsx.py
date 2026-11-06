# -*- coding: utf-8 -*-
"""kwdata.json → 交付 Excel（关键词脚本）。

用法：
    python scripts/build_xlsx.py work/《剧名》_S03_kwdata.json
    python scripts/build_xlsx.py work/...json --out "out/《剧名》...xlsx"

设计：
- 单一数据源：所有单元格都由 kwdata.json 派生，不在这里写死任何剧情。
- 一行一组，10 列，顺序与规范一致。
- 附件6 引用由 lib/refs.py 展开成原文，条号无效直接报错。
"""
import os
import re
import sys
import json
import math
import argparse
import unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(SKILL, "lib"))

import refs  # noqa: E402
from openpyxl import Workbook  # noqa: E402
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side  # noqa: E402
from openpyxl.utils import get_column_letter  # noqa: E402

FONT = "微软雅黑"
COLS = ["序列组编号", "时长", "画面参数", "正向提示词", "场景与妆造简述",
        "微观分镜", "风格细节描述补充", "音频与对白设计", "分层音效设计", "反向提示词"]
WIDTHS = [14, 8, 50, 88, 36, 48, 34, 34, 30, 36]

NEG_BASE = ("【基础禁用项】模糊、变形、多余手指、手指扭曲、手指粘连、文字、水印、低质量、"
            "画面闪烁、人物不一致、塑料质感、伪影、摩尔纹、过曝、死黑、字幕、logo、二维码、台标、片头片尾。")
NEG_QUALITY = ("【画面质量禁用项】油画感、塑料质感、3D模型感、AI绘画感、卡通风格、二次元、"
               "模糊、失焦、过曝、死黑、噪点溢出、画面抖动、穿帮镜头。")
NEG_FACE = ("【人物畸变禁用项】面部变形、五官错乱、手指畸形、多手指、少手指、肢体穿帮、"
            "人物变脸、体态畸形、妆容不符、着装不符。")

DEFAULT_CHECKS = {
    "round1": ["所有组时长在区间内（2.0：4–15 秒；2.5：≤30 秒）",
               "使用 2.5 的组已标【2.5模型】；竖屏无 2.5",
               "同一组内模型唯一，无 2.0/2.5 混用",
               "无同组跨场景",
               "无任何背景音乐",
               "除硬切外无转场特效",
               "十大字段齐全、顺序正确",
               "编号连续，无跳号/重号/断号",
               "剧本核心剧情/人物/台词 100% 还原",
               "画幅统一，无混用",
               "（短篇）全片累计 600–900 秒，各幕占比达标"],
    "round2": ["正向提示词结构正确、七字段齐全",
               "时间轴 0.0 起、首尾相接、末段=组时长、0.1 秒",
               "核心人物面部/着装/造型每组复写",
               "单组信息密度适中（一个核心信息）",
               "运镜简单明确，复杂运镜已物理化且给理由",
               "微观分镜 2–6 个、单镜 1–6 秒、无 >8 秒无意义长镜",
               "动作/情绪物理化，含微表情与呼吸",
               "非聚焦主体有非零动态",
               "反向提示词五段齐全、画幅项正确、剧情项逐组不同",
               "引用带原文、条号有效"],
    "round3": ["整体叙事连贯，符合本模式节奏",
               "每 3–5 个分镜有情绪/冲突/反转点",
               "开篇钩子与结尾悬念/收束到位",
               "音频对白时长与组匹配、口型同步",
               "核心人物/道具在视觉重心（竖屏安全区/横屏均衡）",
               "无平台审核红线内容",
               "同场景跨组环境/光影/道具一致",
               "景别梯度符合叙事逻辑",
               "全覆盖：原文每句/动作/环境/心理都有落点"],
}
SHORTFILM_CHECKS = ["三幕占比达标（20–25 / 50–55 / 20–25）", "八个节点齐备",
                    "节奏曲线有起伏", "人物弧光完整"]
WARNINGS = []


def warn(msg):
    WARNINGS.append(msg)
    print("[warn] " + msg)


def aspect_label(meta):
    a = str(meta.get("aspect", "")).strip()
    res = str(meta.get("resolution", "")).strip()
    if a.startswith("9:16") or a == "9x16":
        base = "竖屏9:16"
    elif a.startswith("4:3") or a == "4x3":
        base = "横屏4:3"
    elif meta.get("mode") == "vertical":
        base = "竖屏9:16"
    elif meta.get("mode") in ("horizontal", "shortfilm"):
        base = "横屏4:3"
    else:
        base = "未指定画幅"
    return base + ("（%s）" % res if res else "")


def ref_text(params, where=""):
    r = params.get("ref")
    if isinstance(r, (list, tuple)) and len(r) >= 2:
        genre, n = r[0], int(r[1])
        use = r[2] if len(r) > 2 else "按本组调度取用"
        try:
            return refs.inline_edit(genre, n, use)
        except refs.RefError as e:
            raise SystemExit("%s 附件6 引用无效：%s" % (where, str(e).strip("'\"")))
    if params.get("reference"):
        return str(params["reference"])
    warn("%s 未填参考电影（params.ref）" % where)
    return "（未指定参考电影，需补：附件6 体裁第N条＋原文＋本片用法）"


def clean(s):
    return re.sub(r"[。；;，,、\s]+$", "", str(s or "").strip())


def param_cell(g, meta):
    p = g.get("params") or {}
    parts = [
        ("摄影机参数", p.get("camera", "")),
        ("画面质感参数", p.get("texture", "")),
        ("色彩参数", p.get("color", "")),
        ("机位参数", p.get("position", "")),
        ("运镜参数", p.get("movement", "")),
        ("光影参数", p.get("light", "")),
        ("动作参数", p.get("action", "")),
        ("场面调度参数", p.get("blocking", "")),
        ("参考电影参数", ref_text(p, "组%s " % g.get("no", ""))),
    ]
    return "；".join("【%s】%s" % (k, clean(v)) for k, v in parts)


def breath_phrase(shot):
    b = shot.get("breath")
    emo = shot.get("emo", "")
    if b in (0, "0", None):
        return ""
    if "呼吸" in emo:
        return ""
    try:
        return "，呼吸每分钟%d次" % int(b)
    except (TypeError, ValueError):
        return ""


def shot_windows(g):
    t = 0.0
    out = []
    for s in g.get("shots", []):
        d = float(s.get("dur", 0) or 0)
        out.append((t, round(t + d, 1)))
        t = round(t + d, 1)
    return out, t


def prompt_cell(g, meta, anchors=None):
    shots = g.get("shots", [])
    wins, total = shot_windows(g)
    dur = float(g.get("duration", 0) or 0)
    if abs(total - dur) > 0.051:
        warn("组%s 分镜时长合计 %.1f 秒 ≠ 组时长 %.1f 秒" % (g.get("no", ""), total, dur))
    lines = []
    for s, (a, b) in zip(shots, wins):
        emo = (clean(s.get("emo", "")) + breath_phrase(s)).strip()
        lines.append(
            "%.1f—%.1f秒：画面主体：%s；动作物理化拆解：%s；情绪物理化拆解：%s；"
            "镜头语言：%s；对白/旁白：%s；音效：%s；画面备注：%s。"
            % (a, b, clean(s.get("pic", "")), clean(s.get("act", "")), emo, clean(s.get("cam", "")),
               clean(s.get("dialogue")) or "无", clean(s.get("sfx", "")), clean(s.get("note", ""))))
    chars = (anchors or {}).get("characters") or []
    if chars:
        anchor = "；".join("%s：%s" % (c.get("name", ""), clean(c.get("look", ""))) for c in chars)
        lines.append("【人物锚点·逐组复写】%s。" % anchor)
    res = str(meta.get("resolution", "")).replace("x", "×").replace("*", "×")
    label = aspect_label(meta)
    if res and res not in label:
        label = "%s（%s）" % (label.split("（")[0], res)
    lines.append("【生成限定词】4K超清、写实摄影、无AI畸变、无穿帮、人物面部特征统一、动作自然流畅、%s画幅。"
                 % label)
    return "\n".join(lines)


def shots_cell(g):
    wins, _ = shot_windows(g)
    lines = []
    for s, (a, b) in zip(g.get("shots", []), wins):
        seg = "%s｜%s｜%.1f秒（%.1f—%.1f）｜%s｜%s" % (
            s.get("id", ""), s.get("size", ""), float(s.get("dur", 0)), a, b,
            s.get("cam", ""), s.get("pic", ""))
        if s.get("act") and s.get("act") not in seg:
            seg += "｜" + s["act"]
        lines.append(seg)
    link = g.get("link") or (g.get("shots") or [{}])[-1].get("note", "")
    if link:
        lines.append("衔接备注：%s" % link)
    return "\n".join(lines)


def style_cell(g):
    lines = []
    for s in g.get("shots", []):
        if s.get("style"):
            lines.append("%s｜%s" % (s.get("id", ""), s["style"]))
    if not lines:
        warn("组%s 缺风格细节（shots[].style）" % g.get("no", ""))
    return "\n".join(lines)


def audio_cell(g):
    wins, _ = shot_windows(g)
    dur = float(g.get("duration", 0) or 0)
    lines = []
    for s, (a, b) in zip(g.get("shots", []), wins):
        if s.get("dialogue"):
            lines.append("（%.1f—%.1f）%s" % (a, b, s["dialogue"]))
    if not lines:
        lines.append("本组无对白。")
    aud = g.get("audio") or {}
    ws = float(aud.get("whitespace", 0.5) or 0)
    if ws > 0:
        lines.append("【留白】%.1f—%.1f 共%.1f秒" % (dur - ws, dur, ws))
    sil = float(aud.get("silence", 0) or 0)
    if sil > 0:
        lines.append("【静音】%.1f—%.1f 共%.1f秒" % (dur - sil, dur, sil))
    if aud.get("note"):
        lines.append(aud["note"])
    return "\n".join(lines)


def layers_cell(g):
    L = g.get("sfx_layers") or {}
    names = [("人声层", "voice"), ("核心音效层", "core"), ("环境细节层", "ambient"), ("空间混响层", "reverb")]
    out = []
    for label, key in names:
        v = L.get(key)
        if not v:
            warn("组%s 分层音效缺「%s」" % (g.get("no", ""), label))
            v = "（待补）"
        out.append("%s：%s" % (label, v))
    return "\n".join(out)


def neg_cell(g, meta):
    mode = meta.get("mode", "vertical")
    if mode == "vertical" or str(meta.get("aspect", "")).startswith("9:16"):
        scene = "【场景穿帮禁用项】场景错乱、道具不符、时空穿帮、光影混乱、画幅错误、非竖屏9:16、横屏画幅、转场特效。"
    else:
        scene = "【场景穿帮禁用项】场景错乱、道具不符、时空穿帮、光影混乱、画幅错误、非横屏4:3、竖屏画幅、16:9、转场特效。"
    plot = ((g.get("neg") or {}).get("plot") or "").strip()
    extra = ((g.get("neg") or {}).get("extra") or "").strip()
    if not plot:
        warn("组%s 缺剧情不符禁用项（neg.plot）" % g.get("no", ""))
    tail = plot + ("，" + extra if extra else "")
    return "\n".join([NEG_BASE, NEG_QUALITY, NEG_FACE, scene, "【剧情不符禁用项】%s。" % tail])


def dur_cell(g):
    d = float(g.get("duration", 0) or 0)
    tag = "【2.5模型】" if str(g.get("model")) == "2.5" and "【2.5模型】" not in str(g.get("no", "")) else ""
    return "%.1f秒%s" % (d, tag)


def row_values(g, meta, anchors=None):
    return [g.get("no", ""), dur_cell(g), param_cell(g, meta), prompt_cell(g, meta, anchors),
            g.get("makeup", ""), shots_cell(g), style_cell(g), audio_cell(g),
            layers_cell(g), neg_cell(g, meta)]


# ---------- 样式 ----------
HEADER_FILL = PatternFill("solid", fgColor="1F3864")
SECTION_FILL = PatternFill("solid", fgColor="D9E2F3")
THIN = Side(style="thin", color="BFBFBF")
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)


def style_header(ws, row, ncol):
    for c in range(1, ncol + 1):
        cell = ws.cell(row=row, column=c)
        cell.font = Font(name=FONT, size=9, bold=True, color="FFFFFF")
        cell.fill = HEADER_FILL
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = BORDER
    ws.row_dimensions[row].height = 30


def style_body(ws, row, ncol, center_cols=()):
    for c in range(1, ncol + 1):
        cell = ws.cell(row=row, column=c)
        cell.font = Font(name=FONT, size=8)
        cell.alignment = Alignment(horizontal="center" if c in center_cols else "left",
                                   vertical="top", wrap_text=True)
        cell.border = BORDER


def _units(s):
    """按 Excel 半角字符宽度计：东亚全角计 2，其余计 1。"""
    return sum(2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1 for ch in s)


def est_height(values, widths):
    """估算自动换行后的行高（pt）。8pt 字体、每行约 12.5pt。"""
    lines = 1
    for v, w in zip(values, widths):
        s = "" if v is None else str(v)
        per = max(6, int(w * 1.18 + 0.8))
        n = sum(max(1, math.ceil(_units(seg) / per)) for seg in s.split("\n"))
        lines = max(lines, n)
    return min(409, max(30, int(lines * 12.5 + 10)))


def audit(g, meta):
    chars_per_sec = float(meta.get("chars_per_sec", 2.25) or 2.25)
    total_chars = 0
    for s in g.get("shots", []):
        t = s.get("dialogue") or ""
        if "：" in t:
            t = t.rsplit("：", 1)[1]
        total_chars += len(re.findall(r"[\u4e00-\u9fffA-Za-z0-9]", t))
    sec = round(total_chars / chars_per_sec, 1) if total_chars else 0.0
    dur = float(g.get("duration", 0) or 0)
    ws = float((g.get("audio") or {}).get("whitespace", 0.5) or 0)
    used = round(sec + ws, 1)
    if not total_chars:
        verdict = "无对白"
    elif used > dur + 0.05:
        verdict = "超时"
    elif sec < 5:
        verdict = "偏短（单句组可接受）"
    elif sec > 12:
        verdict = "偏长"
    else:
        verdict = "OK"
    return [g.get("no", ""), dur, total_chars, sec, ws, used, round(dur - used, 1), verdict]


def sheet_main(wb, d, meta):
    ws = wb.active
    ws.title = "关键词脚本"
    ws.append(COLS)
    style_header(ws, 1, len(COLS))
    for g in d["groups"]:
        vals = row_values(g, meta, d.get("anchors"))
        ws.append(vals)
        r = ws.max_row
        style_body(ws, r, len(COLS), center_cols=(1, 2))
        h = est_height(vals, WIDTHS)
        if h >= 409:
            warn("组%s 内容超过 Excel 单行上限 409pt，D 列提示词过长，建议拆成两组或精简画面备注" % g.get("no", ""))
        ws.row_dimensions[r].height = h
    for i, w in enumerate(WIDTHS, 1):
        ws.column_dimensions[get_column_letter(i)].width = w
    ws.freeze_panes = "B2"
    ws.auto_filter.ref = "A1:%s%d" % (get_column_letter(len(COLS)), ws.max_row)
    ws.page_setup.orientation = "landscape"
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    return ws


def sheet_overview(wb, d, meta):
    ws = wb.create_sheet("全片序列组总览")
    head = ["序号", "幕", "场", "序列组编号", "场景名称", "时长(秒)", "模型", "核心事件/对白", "累计(秒)", "关键节点"]
    ws.append(head)
    style_header(ws, 1, len(head))
    acc = 0.0
    for i, g in enumerate(d["groups"], 1):
        dur = float(g.get("duration", 0) or 0)
        acc = round(acc + dur, 1)
        event = g.get("event") or (g.get("shots") or [{}])[0].get("pic", "")
        vals = [i, g.get("act", ""), g.get("scene_no", ""), g.get("no", ""), g.get("scene_name", ""),
                dur, g.get("model", ""), event[:80], acc, g.get("node", "")]
        ws.append(vals)
        style_body(ws, ws.max_row, len(head), center_cols=(1, 2, 3, 6, 7, 9))
        ws.row_dimensions[ws.max_row].height = est_height(vals, [6, 8, 8, 18, 26, 9, 8, 50, 10, 14])
    for i, w in enumerate([6, 8, 8, 18, 26, 9, 8, 50, 10, 14], 1):
        ws.column_dimensions[get_column_letter(i)].width = w
    ws.append(["合计", "", "", "%d组" % len(d["groups"]), "", acc, "", "", acc, ""])
    r = ws.max_row
    style_body(ws, r, len(head), center_cols=(1, 4, 6, 9))
    for c in range(1, len(head) + 1):
        ws.cell(row=r, column=c).font = Font(name=FONT, size=9, bold=True)
    ws.freeze_panes = "A2"


def sheet_checks(wb, d, meta):
    ws = wb.create_sheet("三次循环自检")
    width = 5
    for i, w in enumerate([7, 46, 10, 34, 34], 1):
        ws.column_dimensions[get_column_letter(i)].width = w
    sc = d.get("selfcheck") or {}

    def title(text):
        ws.append([text])
        r = ws.max_row
        ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=width)
        c = ws.cell(row=r, column=1)
        c.font = Font(name=FONT, size=10, bold=True)
        c.fill = SECTION_FILL
        c.alignment = Alignment(horizontal="left", vertical="center")
        ws.row_dimensions[r].height = 22

    def head_row():
        ws.append(["序号", "检查项", "结果", "发现问题", "修改措施"])
        style_header(ws, ws.max_row, width)

    def body_row(vals):
        ws.append(vals)
        style_body(ws, ws.max_row, width, center_cols=(1, 3))
        ws.row_dimensions[ws.max_row].height = est_height(vals, [7, 46, 10, 34, 34])

    titles = [("表1 · 核心红线与必填字段", "round1"),
              ("表2 · AI 生成适配", "round2"),
              ("表3 · 叙事逻辑与平台合规", "round3")]
    for text, key in titles:
        title(text)
        head_row()
        provided = [it if isinstance(it, dict) else {"item": it} for it in (sc.get(key) or [])]
        pool = {}
        for it in provided:
            pool.setdefault(clean(it.get("item", "")), it)
        used = set()
        canon = list(DEFAULT_CHECKS[key])
        if key == "round3" and meta.get("mode") == "shortfilm":
            canon += SHORTFILM_CHECKS
        idx = 0
        for item in canon:
            idx += 1
            it = pool.get(clean(item))
            if it is not None:
                used.add(clean(item))
                body_row([idx, item, it.get("result", "未填"), it.get("issue", ""), it.get("fix", "")])
            else:
                body_row([idx, item, "未填", "", "（待补）"])
        for it in provided:
            k = clean(it.get("item", ""))
            if k and k not in used:
                idx += 1
                body_row([idx, it.get("item", ""), it.get("result", ""), it.get("issue", ""), it.get("fix", "")])
        ws.append([])

    title("表4 · 自检过程报告")
    sm = sc.get("summary") or {}
    rows = [
        ("项目名称 / 集数或片长", "%s / %s" % (
            meta.get("title", ""), "第%s集" % meta["episode"] if meta.get("episode") else "全片")),
        ("画幅", aspect_label(meta)),
        ("使用模型", meta.get("default_model", "2.0")),
        ("序列组总数 / 全片总时长", "%d 组 / %.1f 秒" % (
            len(d["groups"]), sum(float(g.get("duration", 0) or 0) for g in d["groups"]))),
        ("第一次循环", "问题数 %s，已改 %s，结论 %s" % (
            sm.get("problems", ""), sm.get("fixed", ""), sm.get("conclusion", ""))),
        ("第二次循环", ""),
        ("第三次循环", ""),
        ("修改前后对比摘要", sm.get("notes", "")),
        ("最终结论", sm.get("conclusion", "")),
        ("自检人 / 审核人", ""),
    ]
    for k, v in rows:
        ws.append([k, v])
        r = ws.max_row
        ws.merge_cells(start_row=r, start_column=2, end_row=r, end_column=width)
        c1 = ws.cell(row=r, column=1)
        c1.font = Font(name=FONT, size=9, bold=True)
        c1.fill = SECTION_FILL
        c1.alignment = Alignment(vertical="center", wrap_text=True)
        c2 = ws.cell(row=r, column=2)
        c2.font = Font(name=FONT, size=9)
        c2.alignment = Alignment(vertical="top", wrap_text=True)
        for cc in range(1, width + 1):
            ws.cell(row=r, column=cc).border = BORDER
        ws.row_dimensions[r].height = 24


def sheet_anchor(wb, d, meta):
    ws = wb.create_sheet("梗概与锚点")
    ws.column_dimensions["A"].width = 16
    ws.column_dimensions["B"].width = 100
    story = d.get("story") or {}
    an = d.get("anchors") or {}
    vis = an.get("visual") or {}
    groups = d["groups"]

    def sec(title):
        ws.append([title, ""])
        r = ws.max_row
        ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=2)
        c = ws.cell(row=r, column=1)
        c.font = Font(name=FONT, size=10, bold=True)
        c.fill = SECTION_FILL
        c.alignment = Alignment(vertical="center")
        ws.row_dimensions[r].height = 22

    def kv(k, v):
        ws.append([k, v])
        r = ws.max_row
        ws.cell(row=r, column=1).font = Font(name=FONT, size=9, bold=True)
        ws.cell(row=r, column=1).alignment = Alignment(vertical="top", wrap_text=True)
        ws.cell(row=r, column=2).font = Font(name=FONT, size=9)
        ws.cell(row=r, column=2).alignment = Alignment(vertical="top", wrap_text=True)
        for c in (1, 2):
            ws.cell(row=r, column=c).border = BORDER
        ws.row_dimensions[r].height = est_height([v], [100])

    sec("一、故事")
    for k, label in [("summary", "故事梗概"), ("hook", "反转/钩子"), ("timeline", "时间线地点"),
                     ("curve", "情绪曲线"), ("props", "贯穿道具"), ("link", "上下集衔接")]:
        if story.get(k):
            kv(label, story[k])

    sec("二、人物锚点")
    for c in an.get("characters") or []:
        kv(c.get("name", ""), "%s\n声音：%s" % (c.get("look", ""), c.get("voice", "")))
    sec("三、道具锚点")
    for p in an.get("props") or []:
        kv(p.get("name", ""), p.get("note", ""))
    sec("四、视觉与空间")
    for k, label in [("palette", "色彩"), ("texture", "质感"), ("motif", "核心意象"),
                     ("subtitle", "字幕"), ("transition", "转场")]:
        if vis.get(k):
            kv(label, vis[k])
    if an.get("space"):
        kv("空间坐标", an["space"])

    sec("五、时长账目")
    total = sum(float(g.get("duration", 0) or 0) for g in groups)
    kv("序列组数", str(len(groups)))
    kv("全片总时长", "%.1f 秒" % total)
    kv("单组区间", "%.1f — %.1f 秒" % (
        min(float(g.get("duration", 0) or 0) for g in groups),
        max(float(g.get("duration", 0) or 0) for g in groups)))
    kv("模式窗口", {"vertical": "单集 ≤180 秒", "horizontal": "单集 ≤180 秒",
                    "shortfilm": "600–900 秒"}.get(meta.get("mode"), "未定"))

    sec("六、引用索引（附件6 原文已内联）")
    for g in groups:
        p = g.get("params") or {}
        if p.get("ref"):
            r = p["ref"]
            kv(g.get("no", ""), "附件6 %s第%s条｜%s" % (r[0], r[1], r[2] if len(r) > 2 else ""))
        elif p.get("reference"):
            kv(g.get("no", ""), str(p["reference"])[:120])

    sec("七、版本")
    kv("版本", meta.get("version", "V1.0"))
    kv("日期", meta.get("date", ""))
    kv("依据", meta.get("based_on", ""))
    kv("来源剧本", meta.get("source_script", ""))
    kv("来源分镜", meta.get("source_storyboard", ""))
    kv("语速", "%.2f 字/秒" % float(meta.get("chars_per_sec", 2.25) or 2.25))


def sheet_audit(wb, d, meta):
    ws = wb.create_sheet("台词时长账目")
    head = ["序列组编号", "时长(秒)", "台词字数", "语音秒", "留白(秒)", "占用合计(秒)", "差值(秒)", "判定"]
    ws.append(head)
    style_header(ws, 1, len(head))
    t_dur = t_chars = t_sec = t_ws = t_used = 0.0
    for g in d["groups"]:
        vals = audit(g, meta)
        ws.append(vals)
        style_body(ws, ws.max_row, len(head), center_cols=tuple(range(1, 9)))
        t_dur += float(vals[1] or 0)
        t_chars += float(vals[2] or 0)
        t_sec += float(vals[3] or 0)
        t_ws += float(vals[4] or 0)
        t_used += float(vals[5] or 0)
    ws.append(["合计", round(t_dur, 1), int(t_chars), round(t_sec, 1), round(t_ws, 1),
               round(t_used, 1), round(t_dur - t_used, 1), ""])
    r = ws.max_row
    style_body(ws, r, len(head), center_cols=tuple(range(1, 9)))
    for c in range(1, len(head) + 1):
        ws.cell(row=r, column=c).font = Font(name=FONT, size=9, bold=True)
    for i, w in enumerate([18, 10, 10, 10, 10, 12, 10, 22], 1):
        ws.column_dimensions[get_column_letter(i)].width = w
    ws.freeze_panes = "A2"
    ws.append([])
    ws.append(["说明：语音秒 = 台词字数 ÷ %.2f；占用合计 = 语音秒 + 留白；差值 = 时长 − 占用。"
               % float(meta.get("chars_per_sec", 2.25) or 2.25)])
    ws.cell(row=ws.max_row, column=1).font = Font(name=FONT, size=8, italic=True)


def sheet_tech(wb, d, meta):
    """按需生成「技法映射」表：shot.tech 有值才出。"""
    rows = []
    for g in d.get("groups") or []:
        for s in g.get("shots") or []:
            tech = s.get("tech")
            if not tech:
                continue
            items = tech if isinstance(tech, list) else [tech]
            for it in items:
                if isinstance(it, dict):
                    rows.append([g.get("no", ""), s.get("id", ""), it.get("name", ""),
                                 it.get("slot", ""), it.get("tier", ""), it.get("params", "")])
                else:
                    parts = [p.strip() for p in str(it).split("｜")]
                    parts += [""] * (4 - len(parts))
                    rows.append([g.get("no", ""), s.get("id", "")] + parts[:4])
    if not rows:
        return False
    ws = wb.create_sheet("技法映射")
    head = ["序列组编号", "镜号", "技法", "落点", "档位", "参数片段"]
    ws.append(head)
    style_header(ws, 1, len(head))
    for r in rows:
        ws.append(r)
        style_body(ws, ws.max_row, len(head))
    for i, w in enumerate([18, 8, 22, 26, 8, 56], 1):
        ws.column_dimensions[get_column_letter(i)].width = w
    ws.freeze_panes = "A2"
    return True


def default_out(path, meta):
    title = meta.get("title") or "未命名"
    ep = meta.get("episode", "")
    ver = str(meta.get("version", "V1.0"))
    if meta.get("mode") == "shortfilm":
        name = "%s_全片_关键词_%s.xlsx" % (title, ver)
    elif ep and str(ep).isdigit():
        name = "%s_S%02d_关键词_%s.xlsx" % (title, int(ep), ver)
    else:
        name = "%s_关键词_%s.xlsx" % (title, ver)
    return os.path.join(os.path.dirname(os.path.abspath(path)), name)


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    ap = argparse.ArgumentParser(description="kwdata.json → 关键词脚本 Excel")
    ap.add_argument("json_path")
    ap.add_argument("--out")
    a = ap.parse_args()

    with open(a.json_path, "r", encoding="utf-8") as f:
        d = json.load(f)
    if d.get("schema") != "kwdata/1":
        warn("schema 不是 kwdata/1（实际 %r），继续尝试" % d.get("schema"))
    meta = d.get("meta") or {}
    if not d.get("groups"):
        raise SystemExit("没有任何 groups")

    wb = Workbook()
    sheet_main(wb, d, meta)
    if meta.get("mode") == "shortfilm":
        sheet_overview(wb, d, meta)
    sheet_checks(wb, d, meta)
    sheet_anchor(wb, d, meta)
    sheet_audit(wb, d, meta)
    sheet_tech(wb, d, meta)

    out = a.out or default_out(a.json_path, meta)
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    wb.save(out)
    total = sum(float(g.get("duration", 0) or 0) for g in d["groups"])
    print("已生成：%s" % out)
    print("组数 %d，总时长 %.1f 秒，sheet：%s" % (len(d["groups"]), total, "、".join(wb.sheetnames)))
    if WARNINGS:
        print("警告 %d 条（不影响生成，交付前需处理）：" % len(WARNINGS))
        for w in WARNINGS:
            print("  - " + w)


if __name__ == "__main__":
    main()
