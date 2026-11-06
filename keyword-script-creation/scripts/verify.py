# -*- coding: utf-8 -*-
"""机器校验 kwdata.json。40+ 条规则，输出 error / warning。

用法：
    python scripts/verify.py work/《剧名》_S03_kwdata.json
    python scripts/verify.py ... --strict           # 有 error 时退出码 1
    python scripts/verify.py ... --source ...json   # 额外做原文覆盖检查
    python scripts/verify.py ... --json report.json

规则编号对应 references/90-自检清单与报告.md 的「机器码」。
"""
import os
import re
import sys
import json
import argparse

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "lib"))
import refs  # noqa: E402

ISSUES = []


def add(level, code, gid, msg):
    ISSUES.append({"level": level, "code": code, "group": gid, "msg": msg})


def err(code, gid, msg):
    add("error", code, gid, msg)


def warn(code, gid, msg):
    add("warning", code, gid, msg)


def norm_text(s):
    return re.sub(r"[\s，。！？、：；,.!?:;\"'“”‘’（）()《》【】…—\-]", "", s or "")


def gid_of(g, i):
    return g.get("no") or ("#%d" % (i + 1))


def durations(g):
    t = 0.0
    out = []
    for s in g.get("shots", []):
        d = float(s.get("dur", 0) or 0)
        out.append((round(t, 1), round(t + d, 1), d))
        t = round(t + d, 1)
    return out, t


def check_meta(d):
    meta = d.get("meta") or {}
    if d.get("schema") != "kwdata/1":
        err("schema", "-", "schema 应为 kwdata/1，实际 %r" % d.get("schema"))
    for k in ("title", "mode", "aspect"):
        if not meta.get(k):
            err("meta.missing", "-", "meta.%s 缺失" % k)
    if meta.get("mode") not in ("vertical", "horizontal", "shortfilm"):
        err("mode.invalid", "-", "meta.mode 必须是 vertical/horizontal/shortfilm")
    an = d.get("anchors") or {}
    if not an.get("characters"):
        err("anchor.missing", "-", "anchors.characters 为空")
    else:
        for c in an["characters"]:
            if not c.get("name") or not c.get("look"):
                err("anchor.incomplete", "-", "人物锚点缺 name 或 look：%r" % c)
    if not an.get("space"):
        warn("anchor.space", "-", "anchor.space 为空（空间坐标未建，易串座）")
    if not (d.get("story") or {}).get("summary"):
        warn("story.summary", "-", "story.summary 为空")


def check_groups(d):
    meta = d.get("meta") or {}
    mode = meta.get("mode")
    groups = d.get("groups") or []
    if not groups:
        err("groups.empty", "-", "没有序列组")
        return
    cps = float(meta.get("chars_per_sec", 2.25) or 2.25)
    seen = {}
    last_seq = None
    last_prefix = None
    for i, g in enumerate(groups):
        gid = gid_of(g, i)
        # 编号
        no = str(g.get("no", ""))
        m = re.search(r"(\d+)\s*$", no.split("【")[0])
        if not m:
            err("id.format", gid, "编号无法解析序号：%r" % no)
        else:
            seq = int(m.group(1))
            prefix = no.split("【")[0][:m.start(1)].strip()
            if no in seen:
                err("id.duplicate", gid, "编号重复（与 %s）" % seen[no])
            seen[no] = gid
            if prefix == last_prefix and last_seq is not None and seq != last_seq + 1:
                err("id.sequence", gid, "编号不连续：上一组 %d，本组 %d" % (last_seq, seq))
            last_seq, last_prefix = seq, prefix
        # 时长与模型
        dur = float(g.get("duration", 0) or 0)
        model = str(g.get("model", "2.0"))
        if model not in ("2.0", "2.5"):
            err("model.invalid", gid, "model 必须是 2.0 或 2.5，实际 %r" % model)
        if mode == "vertical" and model == "2.5":
            err("model.tag", gid, "竖屏禁用 2.5 模型")
        if model == "2.5":
            if dur > 30.05:
                err("dur.range", gid, "2.5 模型组 %.1f 秒 > 30 秒" % dur)
            if "【2.5模型】" not in no:
                warn("model.tag", gid, "2.5 组编号未标【2.5模型】")
        elif dur < 3.95 or dur > 15.05:
            err("dur.range", gid, "组时长 %.1f 秒不在 4–15 秒" % dur)
        # 分镜
        shots = g.get("shots") or []
        if not (2 <= len(shots) <= (8 if model == "2.5" else 6)):
            err("shot.count", gid, "分镜 %d 个，应为 2–%d" % (len(shots), 8 if model == "2.5" else 6))
        wins, total = durations(g)
        if abs(total - dur) > 0.051:
            err("dur.sum", gid, "分镜合计 %.1f 秒 ≠ 组时长 %.1f 秒" % (total, dur))
        for j, s in enumerate(shots, 1):
            sid = s.get("id") or "%03d" % j
            sd = float(s.get("dur", 0) or 0)
            if sd < 0.95 or sd > 6.05:
                err("shot.dur", gid, "镜%s 时长 %.1f 秒不在 1–6 秒" % (sid, sd))
            if sd > 8:
                warn("shot.long", gid, "镜%s %.1f 秒，超过 8 秒需有连贯调度支撑" % (sid, sd))
            for k in ("size", "cam", "pic", "act", "emo", "sfx", "note"):
                if not str(s.get(k, "")).strip():
                    err("shot.field", gid, "镜%s 缺 %s" % (sid, k))
            if not str(s.get("style", "")).strip():
                err("style.missing", gid, "镜%s 缺风格细节 style" % sid)
            if s.get("breath") not in (None, "", 0, "0") and "呼吸" not in str(s.get("emo", "")):
                try:
                    if int(s["breath"]) not in (12, 15, 16, 19, 20):
                        warn("breath.value", gid, "镜%s 呼吸 %s 不在 12/15/16/19/20" % (sid, s["breath"]))
                except (TypeError, ValueError):
                    err("breath.value", gid, "镜%s breath 不是整数" % sid)
        # 时间轴
        for j, (a, b, _) in enumerate(wins):
            if j == 0 and a != 0.0:
                err("prompt.timeline", gid, "时间轴未从 0.0 开始")
            if j > 0 and abs(a - wins[j - 1][1]) > 0.001:
                err("prompt.timeline", gid, "镜%s 起点 %.1f 与上一镜终点 %.1f 不接" % (j + 1, a, wins[j - 1][1]))
        if wins and abs(wins[-1][1] - dur) > 0.051:
            err("prompt.timeline", gid, "末段结束 %.1f ≠ 组时长 %.1f" % (wins[-1][1], dur))
        # 台词
        chars = 0
        for s in shots:
            t = s.get("dialogue") or ""
            if t:
                if "：" not in t:
                    err("dialogue.format", gid, "台词缺「角色：内容」格式：%s" % t[:20])
                chars += len(re.findall(r"[\u4e00-\u9fffA-Za-z0-9]", t.rsplit("：", 1)[-1]))
        sec = round(chars / cps, 1)
        ws = float((g.get("audio") or {}).get("whitespace", 0.5) or 0)
        if chars and sec + ws > dur + 0.05:
            err("audio.fit", gid, "台词 %.1f 秒 + 留白 %.1f 秒 > 组时长 %.1f 秒" % (sec, ws, dur))
        if chars and sec < 5:
            warn("audio.fit", gid, "台词量 %.1f 秒 < 5 秒，需注明单句组" % sec)
        if chars and sec > 12:
            warn("audio.fit", gid, "台词量 %.1f 秒 > 12 秒" % sec)
        if not str((g.get("audio") or {}).get("note", "")).strip() and chars and sec < 5:
            warn("audio.note", gid, "单句组需在 audio.note 注明")
        # 分层音效
        L = g.get("sfx_layers") or {}
        for k, label in (("voice", "人声层"), ("core", "核心音效层"),
                         ("ambient", "环境细节层"), ("reverb", "空间混响层")):
            if not str(L.get(k, "")).strip():
                err("sfx.layer", gid, "缺%s" % label)
        # 场景妆造
        if not str(g.get("makeup", "")).strip():
            err("makeup.missing", gid, "场景与妆造为空")
        # 反向
        neg = g.get("neg") or {}
        if not str(neg.get("plot", "")).strip():
            err("neg.plot", gid, "缺剧情不符禁用项")
        # 引用
        p = g.get("params") or {}
        if p.get("ref"):
            r = p["ref"]
            try:
                if len(r) < 2:
                    raise refs.RefError("ref 至少 [体裁, 条号]")
                refs.get_entry("edit", int(r[1]), r[0])
            except (refs.RefError, ValueError) as e:
                err("ref.inline", gid, "附件6 引用无效：%s" % str(e).strip("'\""))
        elif not p.get("reference"):
            err("ref.inline", gid, "缺参考电影（params.ref）")
        # 站位裸方位
        blob = " ".join(str(g.get(k, "")) for k in ("makeup",)) + " " + " ".join(
            str((g.get("params") or {}).get(k, "")) for k in ("blocking", "position"))
        if re.search(r"(居左|居右)(?![前后中])", blob):
            warn("space.bare", gid, "出现裸「居左/居右」，应写物理方位＋相对关系")


def check_text(d):
    meta = d.get("meta") or {}
    mode = meta.get("mode")
    groups = d.get("groups") or []
    banned_prompt = ["BGM", "配乐", "背景音乐", "主题曲", "插曲"]
    banned_trans = ["淡入", "淡出", "叠化", "闪白", "滑屏", "溶解", "擦除", "转场特效"]
    vague = ["电影感", "氛围感", "高级感", "有层次", "大片感"]
    refs_ban = ["同上", "同前", "同左", "见前文", "见锚点", "见上"]
    for i, g in enumerate(groups):
        gid = gid_of(g, i)
        blob = json.dumps(g, ensure_ascii=False)
        for w in banned_prompt:
            if w in blob:
                err("audio.bgm", gid, "出现背景音乐相关词：%s" % w)
        for w in banned_trans:
            if w in blob:
                err("cut.hard", gid, "出现转场特效词：%s" % w)
        for w in vague:
            if w in blob:
                warn("param.vague", gid, "出现空泛词：%s" % w)
        for w in refs_ban:
            if w in blob:
                err("field.order", gid, "出现省略引用：%s" % w)
        if "°" in blob:
            err("aspect.uniform", gid, "出现半角度符号°（角度用汉字「度」）")
        neg = g.get("neg") or {}
        if not neg:
            continue
        # 反向五段：build 会补全，这里查必需项与画幅
        plot = str(neg.get("plot", ""))
        if mode == "vertical":
            if "竖屏" not in blob and "9:16" not in blob:
                warn("neg.aspect", gid, "正向/反向未提竖屏画幅")
        else:
            if "4:3" not in blob:
                warn("neg.aspect", gid, "正向/反向未提横屏 4:3")
        if len(plot) < 2:
            err("neg.plot", gid, "剧情不符禁用项过短")


def check_mode(d):
    meta = d.get("meta") or {}
    mode = meta.get("mode")
    groups = d.get("groups") or []
    total = sum(float(g.get("duration", 0) or 0) for g in groups)
    if mode == "shortfilm":
        if not (600 <= total <= 900):
            err("total.window", "-", "短篇总时长 %.1f 秒不在 600–900 秒" % total)
        if not (40 <= len(groups) <= 120):
            warn("total.groups", "-", "组数 %d，常规 55–110" % len(groups))
        acts = d.get("acts") or []
        if not acts:
            err("act.missing", "-", "短篇缺 acts（三幕/场次规划）")
        else:
            per = {}
            for g in groups:
                per[g.get("act", "")] = per.get(g.get("act", ""), 0.0) + float(g.get("duration", 0) or 0)
            for a in acts:
                name = a.get("act")
                pct = per.get(name, 0.0) / total * 100 if total else 0
                lo, hi = {"M1": (20, 25), "M2": (50, 55), "M3": (20, 25)}.get(name, (0, 100))
                if pct < lo - 10 or pct > hi + 10:
                    err("act.ratio", "-", "%s 占比 %.1f%%，应约 %d–%d%%" % (name, pct, lo, hi))
                elif pct < lo - 0.05 or pct > hi + 0.05:
                    warn("act.ratio", "-", "%s 占比 %.1f%%，偏离 %d–%d%%" % (name, pct, lo, hi))
    else:
        cap = float(meta.get("target_total_sec", 180) or 180)
        if total > cap + 0.1:
            warn("total.window", "-", "单集总时长 %.1f 秒 > 目标 %.0f 秒" % (total, cap))


def check_coverage(d, source_path):
    try:
        with open(source_path, "r", encoding="utf-8") as f:
            src = json.load(f)
    except Exception as e:
        err("coverage", "-", "读取 source.json 失败：%s" % e)
        return
    lines = (src.get("script") or {}).get("lines") or []
    if not lines:
        warn("coverage", "-", "source.json 里没有 script.lines，跳过覆盖检查")
        return
    dlg = []
    for g in d.get("groups") or []:
        for s in g.get("shots") or []:
            t = s.get("dialogue") or ""
            if t:
                dlg.append(norm_text(t.rsplit("：", 1)[-1]))
    all_d = "".join(dlg)
    missing = []
    for ln in lines:
        t = norm_text(ln.get("text") or "")
        if t and t not in all_d:
            missing.append(ln)
    for ln in missing[:20]:
        warn("coverage", "-", "台词未覆盖：%s" % (ln.get("text", "")[:40]))
    if len(missing) > 20:
        warn("coverage", "-", "另有 %d 句未覆盖" % (len(missing) - 20))


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    ap = argparse.ArgumentParser(description="校验 kwdata.json")
    ap.add_argument("json_path")
    ap.add_argument("--source")
    ap.add_argument("--strict", action="store_true")
    ap.add_argument("--json")
    a = ap.parse_args()
    with open(a.json_path, "r", encoding="utf-8") as f:
        d = json.load(f)

    check_meta(d)
    check_groups(d)
    check_text(d)
    check_mode(d)
    # 技法层规则 CT01–CT06（实现见 ct_rules.py）
    try:
        import ct_rules
        for item in ct_rules.check_keyword(d) + ct_rules.data_warnings():
            if item["level"] == "error":
                err(item["code"], item["ref"], item["msg"])
            else:
                warn(item["code"], item["ref"], item["msg"])
    except ImportError:
        err("CT00", "-", "ct_rules.py 未找到，CT01–CT06 未执行")
    if a.source:
        check_coverage(d, a.source)

    errors = [x for x in ISSUES if x["level"] == "error"]
    warns = [x for x in ISSUES if x["level"] == "warning"]
    for x in ISSUES:
        print("[%s] %-14s %-12s %s" % (x["level"], x["code"], x["group"], x["msg"]))
    print("-" * 60)
    print("error %d，warning %d，组数 %d" % (len(errors), len(warns), len(d.get("groups") or [])))
    if a.json:
        with open(a.json, "w", encoding="utf-8") as f:
            json.dump(ISSUES, f, ensure_ascii=False, indent=1)
        print("报告已写入：%s" % a.json)
    if errors and a.strict:
        sys.exit(1)


if __name__ == "__main__":
    main()
