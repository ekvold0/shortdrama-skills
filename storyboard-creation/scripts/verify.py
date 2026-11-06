#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""分镜脚本校验器（无第三方依赖）

用法：
    python verify.py storyboard.json
    python verify.py storyboard.json --json report.json

数据模型（一个单元 = 一个 AI 生成块 = 若干镜头）：
{
  "meta": {"project","episode","mode","aspect","resolution","target_seconds","total_seconds"},
  "units": [{
      "id": "U01", "scene": "S01", "shot_id": "S01-001",
      "coord","source","aspect","style","cast","time","era","date","weather",
      "timeline","action","emotion","emotion_level","line","sound","link",
      "shots": [{"id":"S01-001","size":"MCU","duration":3.0,"camera":"...","content":"..."}]
  }]
}

校验：字段/枚举/时长账目/镜号连续/违禁表述/语速配平/声音四层/情绪分级
退出码：0 通过；1 有失败项
"""

import argparse
import json
import re
import sys

SIZES = ["ELS", "LS", "FS", "MS", "中近景", "MCU", "CU", "ECU", "OTS"]
MAX_SHOT = {"vertical": 8.0, "horizontal": 10.0, "shortfilm": 15.0}
UNIT_MIN, UNIT_MAX = 4.0, 15.0
TOLERANCE = 0.05

UNIT_FIELDS = ["id", "scene", "coord", "shot_id", "source", "aspect", "style",
               "cast", "time", "era", "date", "weather", "timeline",
               "action", "emotion", "line", "sound", "link"]
SHOT_FIELDS = ["id", "size", "duration", "camera", "content"]
SOUND_LAYERS = ["voice", "fx", "ambience", "reverb"]

FORBIDDEN = [
    (r"同上|同前|见前文", "出现『同上/同前/见前文』，单元必须自包含"),
    (r"牛顿|\d+\s*N\b", "出现力学单位（伪精确）"),
    (r"毫米|mm\b", "出现毫米级参数（伪精确）"),
    (r"每秒\s*\d|频率\s*\d|赫兹|Hz\b", "出现频率类参数（伪精确）"),
    (r"颧大肌|眼轮匝肌|皱眉肌|咬肌|AU\s*\d", "出现 FACS 肌群名（A 级只写中文部位与方向）"),
    (r"BGM|配乐|背景音乐", "出现 BGM/配乐（声音只用四层）"),
    (r"叠化|淡入淡出|划像|转场特效", "出现转场特效（镜头间只用硬切）"),
    (r"画面左|画面右|居左|居右", "出现裸左右方位（改用物理方位）"),
    (r"°", "出现半角度符号（改用汉字『度』）"),
]
PUNCT = re.compile(r"[\s，。！？、；：“”‘’（）《》…—\-·,.!?;:\"'()\[\]]")


def fnum(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def text_of(value):
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, list):
        return " ".join(text_of(v) for v in value)
    if isinstance(value, dict):
        return " ".join(text_of(v) for v in value.values())
    return str(value)


def strip_punct(s):
    s = re.sub(r"【[^】]*】", "", s or "")
    return PUNCT.sub("", s)


def shot_number(shot_id):
    s = str(shot_id or "").strip()
    m = re.match(r"^(M\d+-S\d+)-(\d+)(?:-(\d+))?$", s)
    if m:
        return m.group(1), int(m.group(2)), m.group(3)
    m = re.match(r"^(S\d+)-(\d+)(?:-(\d+))?$", s)
    if m:
        return m.group(1), int(m.group(2)), m.group(3)
    return None, None, None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("path")
    ap.add_argument("--json", dest="json_out", default=None)
    args = ap.parse_args()

    with open(args.path, "r", encoding="utf-8") as f:
        data = json.load(f)

    meta = data.get("meta", {}) or {}
    units = data.get("units", []) or []
    mode = str(meta.get("mode", "vertical")).lower()
    max_shot = MAX_SHOT.get(mode, 8.0)

    fails, warns = [], []

    if not units:
        fails.append("没有任何单元（units 为空）")

    total_shots = 0
    unit_sums = {}
    gallery = []
    all_text = []

    for u in units:
        uid = str(u.get("id", "?"))
        for key in UNIT_FIELDS:
            if key not in u or u.get(key) in (None, "", [], {}):
                if key == "line":
                    continue
                if key in ("source", "link"):
                    warns.append("单元 {} 的『{}』为空（没有内容也要显式写『无』）".format(uid, key))
                else:
                    fails.append("单元 {} 缺少字段『{}』".format(uid, key))

        shots = u.get("shots", []) or []
        if not shots:
            fails.append("单元 {} 没有镜头".format(uid))
            continue

        usum = 0.0
        for sh in shots:
            total_shots += 1
            sid = str(sh.get("id", "?"))
            for key in SHOT_FIELDS:
                if key not in sh or sh.get(key) in (None, "", []):
                    fails.append("{} 缺少字段『{}』".format(sid, key))
            size = str(sh.get("size", "")).strip()
            if size and size not in SIZES:
                fails.append("{} 景别『{}』不在枚举内（{}）".format(sid, size, "/".join(SIZES)))
            dur = fnum(sh.get("duration"))
            if dur is None or dur <= 0:
                fails.append("{} 时长非法：{}".format(sid, sh.get("duration")))
            else:
                usum += dur
                if dur > max_shot + 1e-9:
                    fails.append("{} 时长 {:.1f} 秒，超过 {} 模式单镜上限 {:.0f} 秒".format(
                        sid, dur, mode, max_shot))
            for key in ("camera", "content"):
                all_text.append(text_of(sh.get(key)))

        unit_sums[uid] = round(usum, 1)
        if usum < UNIT_MIN - 1e-9:
            fails.append("单元 {} 时长 {:.1f} 秒，低于 4 秒下限".format(uid, usum))
        if usum > UNIT_MAX + 1e-9:
            fails.append("单元 {} 时长 {:.1f} 秒，超过 15 秒上限".format(uid, usum))

        sound = u.get("sound")
        if isinstance(sound, dict):
            for layer in SOUND_LAYERS:
                if layer not in sound:
                    warns.append("单元 {} 声音缺『{}』层（没有也要写『无』）".format(uid, layer))
        else:
            fails.append("单元 {} 的 sound 应为对象（voice/fx/ambience/reverb 四层）".format(uid))

        # 台词配平：优先用每句的起止时间核算；没有起止时间则退回单元总时长
        line = u.get("line")
        chars, span = 0, 0.0
        if isinstance(line, list) and line:
            for item in line:
                if isinstance(item, dict):
                    chars += len(strip_punct(text_of(item.get("text", ""))))
                    s0, e0 = fnum(item.get("start")), fnum(item.get("end"))
                    if s0 is not None and e0 is not None and e0 > s0:
                        span += e0 - s0
                else:
                    chars += len(strip_punct(text_of(item)))
            if span <= 0:
                span = usum
        else:
            chars = len(strip_punct(text_of(line)))
            span = usum
        if chars > 0 and span > 0:
            speed = chars / span
            if speed > 3.5 + 1e-9:
                fails.append("单元 {} 台词 {} 字 / {:.1f} 秒 = {:.2f} 字/秒，超过上限 3.5".format(
                    uid, chars, span, speed))
            elif speed < 1.5:
                warns.append("单元 {} 台词仅 {:.2f} 字/秒，确认是否留白过多".format(uid, speed))

        for key in ("timeline", "action", "emotion", "line"):
            all_text.append(text_of(u.get(key)))
        all_text.append(text_of(sound))

        levels = u.get("emotion_level")
        if levels is not None and str(levels).strip().upper() not in ("A", "B", "C"):
            warns.append("单元 {} 情绪级别『{}』不在 A/B/C 内".format(uid, levels))

    shot_total = round(sum(unit_sums.values()), 1)
    declared = fnum(meta.get("total_seconds"))
    if declared is None:
        warns.append("未提供 meta.total_seconds，跳过总时长核对（当前合计 {:.1f} 秒）".format(shot_total))
    elif abs(shot_total - declared) > TOLERANCE:
        fails.append("账目不平：单元合计 {:.1f} 秒 ≠ 声明总时长 {:.1f} 秒（差 {:+.1f}）".format(
            shot_total, declared, shot_total - declared))

    target = fnum(meta.get("target_seconds"))
    if target is not None and shot_total > target + TOLERANCE:
        fails.append("总时长 {:.1f} 秒超过上限 {:.1f} 秒".format(shot_total, target))

    # 镜号
    by_scene = {}
    seen = set()
    for u in units:
        for sh in u.get("shots", []) or []:
            sid = str(sh.get("id", ""))
            if sid in seen:
                fails.append("镜号重复：{}".format(sid))
            seen.add(sid)
            prefix, num, _ = shot_number(sid)
            if prefix is None:
                warns.append("镜号格式不规范：{}（应为 S03-005 或 M3-S09-05）".format(sid))
            else:
                by_scene.setdefault(prefix, []).append(num)
    for prefix, nums in by_scene.items():
        if sorted(nums) != list(range(min(nums), min(nums) + len(nums))):
            fails.append("{} 镜号不连续（现有 {}）".format(prefix, sorted(nums)))

    # 违禁表述
    blob = "\n".join(all_text)
    for pattern, message in FORBIDDEN:
        found = re.findall(pattern, blob)
        if found:
            fails.append("{}（命中 {} 处，如：{}）".format(
                message, len(found), "、".join(str(s) for s in found[:3])))

    # 技法层规则 CT01–CT06（实现见 ct_rules.py）
    try:
        from ct_rules import check_storyboard, data_warnings
        for item in check_storyboard(data) + data_warnings():
            line = "{} {}：{}".format(item["code"], item["ref"], item["msg"])
            (fails if item["level"] == "error" else warns).append(line)
    except ImportError:
        warns.append("ct_rules.py 未找到，跳过 CT01–CT06 技法层校验")

    # 情绪分级统计
    levels = {"A": 0, "B": 0, "C": 0}
    for u in units:
        lv = str(u.get("emotion_level", "")).strip().upper()
        if lv in levels:
            levels[lv] += 1
    if levels["B"] == 0 and total_shots > 0:
        warns.append("未标注任何 B 级情绪峰值（高潮至少 1 次）")
    if levels["B"] > 3:
        warns.append("B 级情绪峰值 {} 次，建议 1–3 次".format(levels["B"]))

    # 画幅
    if not meta.get("aspect"):
        fails.append("meta.aspect 缺失：画幅必须由用户提供，不得假设")
    if not meta.get("resolution"):
        warns.append("meta.resolution 缺失，建议补齐分辨率")

    report = {
        "file": args.path, "mode": mode, "shots": total_shots, "units": len(units),
        "total_seconds": shot_total, "declared_seconds": declared,
        "emotion_levels": levels, "fails": fails, "warns": warns,
        "passed": len(fails) == 0,
    }

    print("=" * 60)
    print("分镜校验报告")
    print("=" * 60)
    print("文件：{}".format(args.path))
    print("模式：{}｜单元 {}｜镜头 {}｜总时长 {:.1f} 秒".format(
        mode, len(units), total_shots, shot_total))
    print("情绪分级：A {} / B {} / C {}".format(levels["A"], levels["B"], levels["C"]))
    print("-" * 60)
    if fails:
        print("【失败 {} 项】".format(len(fails)))
        for i, m in enumerate(fails, 1):
            print("  {}. {}".format(i, m))
    else:
        print("【失败 0 项】")
    if warns:
        print("【警告 {} 项】".format(len(warns)))
        for i, m in enumerate(warns, 1):
            print("  {}. {}".format(i, m))
    print("-" * 60)
    print("结论：{}".format("通过" if not fails else "需修改后重检"))

    if args.json_out:
        with open(args.json_out, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        print("机器可读报告：{}".format(args.json_out))

    return 0 if not fails else 1


if __name__ == "__main__":
    sys.exit(main())
