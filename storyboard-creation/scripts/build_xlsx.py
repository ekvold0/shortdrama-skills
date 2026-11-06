#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把分镜 JSON 生成为 Excel 交付件（五个工作表）

用法：
    python build_xlsx.py storyboard.json -o 交付.xlsx

依赖：openpyxl（DSH 运行时自带）

工作表：
  1. 分镜表     七字段表（镜号/景别/时长/机位/画面/台词音效/情绪）
  2. AI 单元    每个单元一段结构化文本（字段/内容两列）
  3. 锚点表     角色、道具、视觉、声音、空间常量
  4. 自检       项目信息 + 三轮自检记录
  5. 台词留痕   原句 → 改写句 → 理由
  6. 技法映射   按需生成：镜头带 tech 字段才出（镜号/技法/落点/档位/参数片段）
"""

import argparse
import json

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

HEADER_FILL = PatternFill("solid", fgColor="1F3864")
HEADER_FONT = Font(color="FFFFFF", bold=True, size=11)
SUB_FILL = PatternFill("solid", fgColor="D9E2F3")
THIN = Side(style="thin", color="BFBFBF")
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
WRAP = Alignment(wrap_text=True, vertical="top")


def style_header(ws, row=1, cols=None):
    cols = cols or ws.max_column
    for c in range(1, cols + 1):
        cell = ws.cell(row=row, column=c)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = Alignment(wrap_text=True, vertical="center", horizontal="center")
        cell.border = BORDER
    ws.row_dimensions[row].height = 26


def apply_body(ws, start_row=2):
    for row in ws.iter_rows(min_row=start_row, max_row=ws.max_row, max_col=ws.max_column):
        for cell in row:
            cell.alignment = WRAP
            cell.border = BORDER


def set_widths(ws, widths):
    for i, w in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = w


def shot_table(wb, units):
    ws = wb.create_sheet("分镜表")
    headers = ["镜号", "单元", "场次", "景别", "时长(秒)", "机位与运镜",
               "画面内容与景深设计", "台词 / 音效", "情绪目标", "画面参数·参考电影"]
    ws.append(headers)
    style_header(ws)

    def sound_text(sound):
        if not isinstance(sound, dict):
            return ""
        return "\n".join(
            "{}：{}".format(name, sound.get(key, "") or "无")
            for name, key in (("人声", "voice"), ("核心音效", "fx"),
                              ("环境细节", "ambience"), ("空间混响", "reverb"))
        )

    def line_text(line):
        if isinstance(line, list):
            return "\n".join(
                "第{}-{}秒 {}：{}".format(i.get("start", ""), i.get("end", ""),
                                        i.get("role", ""), i.get("text", ""))
                for i in line
            )
        return line or ""

    for u in units:
        uid = u.get("id", "")
        first = True
        unit_line = line_text(u.get("line", ""))
        unit_sound = sound_text(u.get("sound"))
        for sh in u.get("shots", []) or []:
            line = line_text(sh.get("line", "")) or (unit_line if first else "")
            sound_txt = sound_text(sh.get("sound")) or (unit_sound if first else "")
            first = False
            ws.append([
                sh.get("id", ""),
                uid,
                u.get("scene", ""),
                sh.get("size", ""),
                sh.get("duration", ""),
                sh.get("camera", ""),
                sh.get("content", ""),
                (("对白：{}\n".format(line)) if line else "") + (sound_txt or "—"),
                sh.get("emotion", "") or u.get("emotion", ""),
                sh.get("reference", "") or u.get("reference", ""),
            ])

    set_widths(ws, [12, 8, 8, 10, 9, 26, 52, 34, 30, 18])
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = "A1:J{}".format(ws.max_row)
    apply_body(ws)


AI_FIELDS = [
    ("幕场坐标", "coord"),
    ("分镜号", "shot_id"),
    ("原文片段", "source"),
    ("画幅", "aspect"),
    ("视觉风格", "style"),
    ("出场角色", "cast"),
    ("时间坐标", "time"),
    ("年代坐标", "era"),
    ("日期坐标", "date"),
    ("气候天象", "weather"),
    ("时间线与子镜头", "timeline"),
    ("动作物理化拆解", "action"),
    ("情绪物理化拆解", "emotion"),
    ("本分镜对白", "line"),
    ("本分镜音效", "sound"),
    ("画面参数·参考电影", "reference"),
    ("衔接备注", "link"),
]


def ai_units(wb, units):
    ws = wb.create_sheet("AI单元")
    ws.append(["单元", "字段", "内容"])
    style_header(ws)

    for u in units:
        uid = u.get("id", "")
        first = True
        for label, key in AI_FIELDS:
            value = u.get(key, "")
            if value in (None, "", [], {}):
                value = "无"
            if key == "sound" and isinstance(value, dict):
                value = "\n".join("{}：{}".format(k, v) for k, v in value.items())
            if not isinstance(value, str):
                value = json.dumps(value, ensure_ascii=False, indent=2)
            ws.append([uid if first else "", label, value])
            if first:
                ws.cell(row=ws.max_row, column=1).font = Font(bold=True)
                first = False

    set_widths(ws, [10, 18, 110])
    ws.freeze_panes = "A2"
    apply_body(ws)


def anchors(wb, meta):
    ws = wb.create_sheet("锚点表")
    ws.append(["类别", "名称", "内容"])
    style_header(ws)
    items = (meta.get("anchors") or [])
    if not items:
        for cat in ("角色", "声线", "贯穿道具", "视觉常量", "声音母题", "空间座位图"):
            ws.append([cat, "", "（待填）"])
    else:
        for it in items:
            ws.append([it.get("type", ""), it.get("name", ""), it.get("content", "")])
    set_widths(ws, [14, 20, 100])
    ws.freeze_panes = "A2"
    apply_body(ws)


CHECKS = [
    ("第一轮", "1.1", "每句台词都有镜号承接"),
    ("第一轮", "1.2", "每个动作/心理/环境变化都有落点"),
    ("第一轮", "1.3", "过渡段单独给镜"),
    ("第一轮", "1.4", "删减内容有理由"),
    ("第一轮", "1.5", "非线性的视觉标识齐全"),
    ("第一轮", "1.6", "有台词的角色均出镜"),
    ("第一轮", "1.7", "无只闻其声（除标注例外）"),
    ("第一轮", "1.8", "群像未堆同框"),
    ("第二轮", "2.1", "各镜合计＝单元合计＝总时长"),
    ("第二轮", "2.2", "无单元 <4 秒 / >15 秒"),
    ("第二轮", "2.3", "单元内不跨场景"),
    ("第二轮", "2.4", "单元间时间连续或递进"),
    ("第二轮", "2.5", "台词逐句可讲完（2.5–3.0 字/秒）"),
    ("第二轮", "2.6", "每镜覆盖对白＋0.5–1 秒留白"),
    ("第二轮", "2.7", ">3 秒对白有反应镜"),
    ("第二轮", "2.8", "总时长不超上限"),
    ("第二轮", "2.9", "集末纯黑 ≤1 秒"),
    ("第三轮", "3.1", "画幅与参数一致、全片统一"),
    ("第三轮", "3.2", "字段齐全、顺序正确"),
    ("第三轮", "3.3", "无『同上/同前/见前文』"),
    ("第三轮", "3.4", "无牛顿/毫米/频率/肌群名"),
    ("第三轮", "3.5", "每镜节奏锚 ≤1"),
    ("第三轮", "3.6", "情绪分级正确；B 级 1–3 次"),
    ("第三轮", "3.7", "景别列只填枚举"),
    ("第三轮", "3.8", "角度用『度』，无半角 °"),
    ("第三轮", "3.9", "声音四层齐全、无 BGM"),
    ("第三轮", "3.10", "文字标注后期叠加"),
    ("第三轮", "3.11", "全部硬切，无转场特效"),
    ("第三轮", "3.12", "无裸『居左/居右』"),
    ("第三轮", "3.13", "手别/越肩/视线/位置/机位自洽"),
    ("第三轮", "3.14", "驾驶场景无违规回头"),
    ("第三轮", "3.15", "每场有空间座位图且一致"),
    ("第三轮", "3.16", "景别递进/递退"),
    ("第三轮", "3.17", "运镜目的清楚、量级不矛盾"),
    ("第三轮", "3.18", "封闭场景有 1–2 个呼吸口"),
    ("第三轮", "3.19", "台词改动有留痕"),
    ("第三轮", "3.20", "外部引用写全出处"),
    ("第三轮", "3.21", "与前后集衔接无漏洞"),
    ("第三轮", "3.22", "合规风险已标注"),
]


def checks(wb, meta):
    ws = wb.create_sheet("自检")

    ws.append(["项目信息", "", ""])
    ws.merge_cells("A1:C1")
    ws["A1"].fill = HEADER_FILL
    ws["A1"].font = HEADER_FONT
    ws["A1"].alignment = Alignment(horizontal="center", vertical="center")

    info = [
        ("剧名", meta.get("project", "")),
        ("集数", meta.get("episode", "")),
        ("模式", meta.get("mode", "")),
        ("画幅 / 分辨率", "{} / {}".format(meta.get("aspect", ""), meta.get("resolution", ""))),
        ("时长上限(秒)", meta.get("target_seconds", "")),
        ("自检日期", meta.get("check_date", "")),
    ]
    for k, v in info:
        ws.append([k, v, ""])
        ws.merge_cells(start_row=ws.max_row, start_column=2, end_row=ws.max_row, end_column=3)

    ws.append([])
    ws.append([])
    header_row = ws.max_row
    ws.append(["轮次", "编号", "检查项", "结果", "问题描述"])
    for c in range(1, 6):
        cell = ws.cell(row=header_row, column=c)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = Alignment(wrap_text=True, vertical="center", horizontal="center")

    for rnd, no, item in CHECKS:
        ws.append([rnd, no, item, "", ""])

    set_widths(ws, [10, 8, 42, 10, 40])
    apply_body(ws, start_row=header_row + 1)


def line_changes(wb, meta):
    ws = wb.create_sheet("台词留痕")
    ws.append(["镜号", "原句", "改写句", "理由"])
    style_header(ws)
    items = meta.get("line_changes") or []
    if not items:
        ws.append(["", "（无改动）", "", ""])
    else:
        for it in items:
            ws.append([it.get("shot", ""), it.get("original", ""),
                       it.get("rewritten", ""), it.get("reason", "")])
    set_widths(ws, [12, 46, 46, 34])
    ws.freeze_panes = "A2"
    apply_body(ws)


def tech_map(wb, units):
    """按需生成「技法映射」表：镜头带 tech 字段才出。

    tech 支持两种写法：
        "荷兰角｜C3c 画面参数·机位｜T2"
        {"name": "荷兰角", "slot": "C3c 画面参数·机位", "tier": "T2", "params": "..."}
    """
    rows = []
    for u in units:
        for sh in u.get("shots", []) or []:
            tech = sh.get("tech")
            if not tech:
                continue
            items = tech if isinstance(tech, list) else [tech]
            for it in items:
                if isinstance(it, dict):
                    rows.append([sh.get("id", ""), u.get("id", ""),
                                 it.get("name", ""), it.get("slot", ""),
                                 it.get("tier", ""), it.get("params", "")])
                else:
                    parts = [p.strip() for p in str(it).split("｜")]
                    parts += [""] * (4 - len(parts))
                    rows.append([sh.get("id", ""), u.get("id", "")] + parts[:4])
    if not rows:
        return False
    ws = wb.create_sheet("技法映射")
    ws.append(["镜号", "单元", "技法", "落点", "档位", "参数片段"])
    style_header(ws)
    for r in rows:
        ws.append(r)
    set_widths(ws, [12, 8, 24, 26, 8, 60])
    ws.freeze_panes = "A2"
    apply_body(ws)
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("path")
    ap.add_argument("-o", "--out", required=True)
    args = ap.parse_args()

    with open(args.path, "r", encoding="utf-8") as f:
        data = json.load(f)

    meta = data.get("meta", {}) or {}
    units = data.get("units", []) or []

    wb = Workbook()
    wb.remove(wb.active)

    shot_table(wb, units)
    ai_units(wb, units)
    anchors(wb, meta)
    checks(wb, meta)
    line_changes(wb, meta)
    tech_map(wb, units)

    wb.save(args.out)
    print("已生成：{}（{} 个单元，{} 个镜头）".format(
        args.out, len(units), sum(len(u.get("shots", []) or []) for u in units)))


if __name__ == "__main__":
    main()
