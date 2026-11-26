#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""FL-06 生成环节脚本化 —— 只做 dry-run（投喂清单 + 预算 + 缺件核对）。

真发单（--live）还没实现：那一步要吃即梦账号额度，等使用方明确授权再开。

用法：
    python run_generate.py <关键词kwdata.json> [--assets <素材根>] [--out <输出目录>]
                           [--limit N] [--tier 2.0] [--live]

它做四件事（都不联网、不花钱）：
    1. 逐组核对 refs：编号能否追到文件、文件在不在、正文 [图片N] 与 refs 是否对齐、
       图/视频/音频是否超过档位上限、音频有没有单独用、时长是否超档位。
    2. 算预算：这次一共要跑几组、占多少图/视频/音频、哪些组必须拆。
    3. 排产物路径：每组一个 mp4 目标名，按 FL-05 命名（剧名_S集号_组号_v版本）。
    4. 出清单：plan.json（给脚本看）+ 投喂清单.md（给人照着点）。

退出码：0 全绿 / 1 有阻塞项（缺文件、超上限、编号对不上）/ 2 用了 --live 但尚未实现。
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys

# 子进程/管道里 stdout 默认走本地编码（GBK），自检按 UTF-8 解码会读到乱码，统一显式设成 UTF-8
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

try:
    import ct_rules as CT          # 复用同一套档位口径，避免两处数字打架
    PIC_REF = CT.PIC_REF
    image_limit = CT._image_limit
    tier_of = CT._tier_of
    _is_board_ref = CT._is_board_ref
except Exception:                  # 允许在别处单独用（口径回落到本文件常量）
    PIC_REF = re.compile(r"\[图片\s*(\d+)\]")
    image_limit = None
    tier_of = None

    def _is_board_ref(r):      # ct_rules 不可用时的最小实现（V2.4）
        if not isinstance(r, dict):
            return False
        tag = _s(r.get('kind')) + ' ' + _s(r.get('type')) + ' ' + _s(r.get('role'))
        return any(t in tag for t in ('board', '分镜图', '关键帧', 'first_frame', 'shot_ref'))

# 平台素材上限（需求文档 FL-04，使用方 2026-11-26 确认的数字）
# group_sec = 本组生成时长上限；ref_min/ref_max = 单条参考视频/音频的时长区间；
# ref_group_sec = 视频组、音频组各自的总时长上限（与生成时长分开算）
TIERS = {
    # 2.0：单条参考视频/音频 4–15 秒；本组生成时长也卡 4–15 秒（4 秒下限与分镜单元 4–15 秒一致）
    "2.0":        {"img": 9,  "vid": 3,  "aud": 3,  "group_sec": 15, "shot_sec": 15,
                   "audio_alone": False, "ref_min": 4, "ref_max": 15, "ref_group_sec": 15,
                   "min_sec": 4},
    # 2.5 flash 单条参考视频/音频是 4–30 秒（使用方 2026-11-26 更正，此前误记为 2–30）
    "2.5-flash":  {"img": 10, "vid": 5,  "aud": 5,  "group_sec": 30, "shot_sec": 30,
                   "audio_alone": True,  "ref_min": 4, "ref_max": 30, "ref_group_sec": 30,
                   "min_sec": 4},
    "2.5":        {"img": 30, "vid": 10, "aud": 10, "group_sec": 30, "shot_sec": 30,
                   "audio_alone": True,  "ref_min": 4, "ref_max": 30, "ref_group_sec": 30,
                   "min_sec": 4},
}

KIND_ALIAS = {
    "image": "img", "img": "img", "图片": "img", "图": "img", "face": "img",
    "cloth": "img", "back": "img", "board": "img", "scene": "img", "staging": "img",
    "video": "vid", "vid": "vid", "视频": "vid", "motion": "vid",
    "audio": "aud", "aud": "aud", "音频": "aud", "voice": "aud", "sound": "aud",
}


def norm_tier(t):
    """把 2.0 / 2.5 / 2.5 flash / 2.5 标准版 归到三档之一。"""
    s = str(t or "").strip().lower()
    if not s:
        return ""
    if "flash" in s:
        return "2.5-flash"
    if "2.5" in s:
        return "2.5"
    if "2.0" in s or "seedance" in s or s in ("2", "2.0"):
        return "2.0"
    return ""


def _s(v):
    if v is None:
        return ""
    if isinstance(v, (dict, list)):
        return json.dumps(v, ensure_ascii=False)
    return str(v)


def body_text(g):
    """正文（提示词 + 参数 + 分镜 + 妆造）——用来数 [图片N]。"""
    p = g.get("params") or {}
    parts = [_s(v) for v in p.values()]
    parts += [_s(g.get("prompt")), _s(g.get("makeup")), _s(g.get("scene")), _s(g.get("shots"))]
    return " ".join(parts)


def _scan_max_version(out_dir, title):
    # 目录里已有的最高版本号（V2.10：版本自动递增，不靠手写）。
    mx = 0
    if not out_dir or not os.path.isdir(out_dir):
        return 0
    for fn in os.listdir(out_dir):
        if not fn.startswith(title + "_"):
            continue
        m = re.search(r"_v(\d+)\.mp4$", fn)
        if m:
            mx = max(mx, int(m.group(1)))
    return mx


def plan_group(g, idx, assets_root, out_dir, default_tier, title, ep, ver):
    """单组的投喂计划 + 阻塞项。"""
    gid = _s(g.get("no")) or "U%02d" % (idx + 1)
    tier_raw = tier_of(g) if tier_of else (g.get("model") or g.get("tier") or "")
    tier_raw = _s(tier_raw).strip() or default_tier
    tier = norm_tier(tier_raw)
    limits = TIERS.get(tier)
    dur = float(g.get("duration") or 0)

    used = sorted(set(int(n) for n in PIC_REF.findall(body_text(g))))
    refs = g.get("refs")
    issues, warns = [], []

    if not tier:
        warns.append("没写档位（model/tier）——按 %.1f 秒排，上限按 2.0 算" % dur)
        tier, limits = "2.0", TIERS["2.0"]
    if dur <= 0:
        issues.append("duration 缺失或为 0")
    elif dur > limits["group_sec"]:
        issues.append("组时长 %.1f 秒超过 %s 上限 %d 秒——拆组" % (dur, tier, limits["group_sec"]))
    elif limits.get("min_sec") and dur < limits["min_sec"]:
        issues.append("组时长 %.1f 秒低于 %s 下限 %d 秒——太短，合并到相邻组"
                      % (dur, tier, limits["min_sec"]))

    by_kind = {"img": [], "vid": [], "aud": [], "board": []}
    missing = []
    sec_sum = {"vid": 0.0, "aud": 0.0}
    for i, r in enumerate(refs or [], 1):
        if not isinstance(r, dict):
            continue
        no = r.get("no", i)
        try:
            no = int(no)
        except (TypeError, ValueError):
            no = i
        kind = KIND_ALIAS.get(_s(r.get("kind") or r.get("type")).strip().lower(), "")
        is_board = _is_board_ref(r)
        if is_board:
            kind = "board"      # 分镜图占一张图片名额、不参与身份链（V2.12 平台实测）
        f = _s(r.get("file")).strip()
        if not kind:
            warns.append("refs 第 %s 项 kind 认不出（%s）" % (no, _s(r.get("kind"))))
            kind = "img"
        if not f:
            issues.append("refs 第 %s 项缺 file——编号必须落到文件名" % no)
            continue
        by_kind[kind].append(no)
        if is_board:
            by_kind["img"].append(no)   # 名额按图片算：分镜图也吃一张
        sec = r.get("sec", r.get("duration"))
        try:
            sec = float(sec) if sec not in (None, "") else 0.0
        except (TypeError, ValueError):
            sec = 0.0
        if sec and kind in ("vid", "aud"):
            lo, hi = limits["ref_min"], limits["ref_max"]
            if sec > hi or (lo and sec < lo):
                issues.append("refs 第 %s 项 %.1f 秒超出 %s 单条参考时长 %s"
                              % (no, sec, tier, ("%g–%g 秒" % (lo, hi)) if lo else ("≤%g 秒" % hi)))
            sec_sum[kind] += sec
        if assets_root:
            cand = f if os.path.isabs(f) else os.path.join(assets_root, f)
            if not os.path.exists(cand):
                missing.append(os.path.basename(f))

    if refs is None and used:
        issues.append("正文写了 %d 个 [图片N]，但 refs 整段缺失" % len(used))
    have = set(by_kind["img"]) | set(by_kind["vid"]) | set(by_kind["aud"])
    orphan = [n for n in used if n not in have]
    unused = sorted(n for n in have if n not in used)
    if orphan:
        issues.append("正文引用了 refs 里没有的编号：%s" % ", ".join("[图片%d]" % n for n in orphan))
    if unused:
        warns.append("refs 里 %d 项没被正文引用（白占名额）：%s"
                     % (len(unused), ", ".join("图%d" % n for n in unused)))
    if len(by_kind["img"]) > limits["img"]:
        issues.append("图 %d 张 > %s 上限 %d 张" % (len(by_kind["img"]), tier, limits["img"]))
    if len(by_kind["vid"]) > limits["vid"]:
        issues.append("视频 %d 段 > %s 上限 %d 段" % (len(by_kind["vid"]), tier, limits["vid"]))
    if len(by_kind["aud"]) > limits["aud"]:
        issues.append("音频 %d 段 > %s 上限 %d 段" % (len(by_kind["aud"]), tier, limits["aud"]))
    if by_kind["aud"] and not limits["audio_alone"] and not by_kind["img"] and not by_kind["vid"]:
        issues.append("只挂了音频参考——%s 的音频不能单独用，至少配 1 图或 1 视频" % tier)
    for kind, label in (("vid", "视频组"), ("aud", "音频组")):
        if sec_sum[kind] > limits["ref_group_sec"] + 1e-6:
            issues.append("%s总时长 %.1f 秒超过 %s 上限 %d 秒"
                          % (label, sec_sum[kind], tier, limits["ref_group_sec"]))
    if missing:
        issues.append("文件不存在：%s" % "、".join(missing[:4]) + ("…" if len(missing) > 4 else ""))

    # V2.9 落库命名：组号必须在文件名里，且与画布节点标题同源
    # 文件：<剧名>_<组号>_v<版本>.mp4 ｜ 画布节点标题：<组号>（补帧写 <组号>_补帧）
    gid_tag = gid if re.match(r"^S\d+-XZ-\d+", gid) else "S%s-%s" % (ep, gid)
    out_name = "%s_%s_v%s.mp4" % (title, gid_tag, ver)
    node_title = gid_tag
    return {
        "no": gid,
        "tier_raw": _s(tier_raw),
        "tier": tier,
        "duration": dur,
        "refs": {"img": by_kind["img"], "vid": by_kind["vid"], "aud": by_kind["aud"]},
        "used_refs": used,
        "issues": issues,
        "warns": warns,
        "status": "blocked" if issues else "ready",
        "out": os.path.join(out_dir, out_name) if out_dir else out_name,
        "node_title": node_title,
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description="FL-06 生成环节 dry-run（投喂清单 + 预算）")
    ap.add_argument("kw", help="关键词 kwdata JSON")
    ap.add_argument("--assets-root", "--assets", dest="assets", default="",
                    help="资产根目录（项目的 资产/ 目录，与 verify 的 --assets-root 同一个值）")
    ap.add_argument("--out", default="", help="产物与清单输出目录（默认与 kwdata 同目录）")
    ap.add_argument("--tier", default="2.0", help="没写档位的组按这个排（默认 2.0）")
    ap.add_argument("--limit", type=int, default=0, help="只排前 N 组（分批生成用）")
    ap.add_argument("--live", action="store_true", help="真发单（尚未实现）")
    a = ap.parse_args(argv)

    if a.live:
        print("--live 尚未实现。真发单要吃即梦账号额度，需要先确认：")
        print("  1) dreamina-cli 的 multimodal2video 登录态；2) 单组失败要不要自动重试；")
        print("  3) 下载回来的文件按什么名归档（当前规划见下方产物列）。")
        return 2

    with open(a.kw, encoding="utf-8") as f:
        data = json.load(f)
    meta = data.get("meta") or {}
    title = _s(meta.get("title")) or os.path.splitext(os.path.basename(a.kw))[0]
    ep = _s(meta.get("episode") or meta.get("ep") or "01")
    ver = _s(meta.get("version") or "1")
    out_dir = a.out or os.path.dirname(os.path.abspath(a.kw))
    os.makedirs(out_dir, exist_ok=True)
    max_v = _scan_max_version(out_dir, title)
    try:
        vn = int(ver)
    except (TypeError, ValueError):
        vn = 1
    ver_note = ""
    if max_v and vn <= max_v:
        vn = max_v + 1
        ver_note = "自动递增到 v{}（目录里已有 v{}，避免覆盖旧版；旧版请移到 archive/）".format(vn, max_v)
        print("[提示] " + ver_note)
    ver = str(vn)

    groups = data.get("groups") or []
    if a.limit:
        groups = groups[: a.limit]
    plans = [plan_group(g, i, a.assets, out_dir, a.tier, title, ep, ver)
             for i, g in enumerate(groups)]

    blocked = [p for p in plans if p["status"] == "blocked"]
    total_dur = sum(p["duration"] for p in plans)
    tot = {k: sum(len(p["refs"][k]) for p in plans) for k in ("img", "vid", "aud")}

    # ---- 控制台 ----
    print("《%s》S%s ｜ %d 组 ｜ 计划 %0.1f 秒（%0.1f 分钟）" % (title, ep, len(plans), total_dur, total_dur / 60))
    print("素材占用：图 %d 张 / 视频 %d 段 / 音频 %d 段" % (tot["img"], tot["vid"], tot["aud"]))
    for p in plans:
        flag = "OK " if p["status"] == "ready" else "!! "
        print("%s%s %5.1f秒 %-9s 图%d/视%d/音%d  %s"
              % (flag, p["no"], p["duration"], p["tier"],
                 len(p["refs"]["img"]), len(p["refs"]["vid"]), len(p["refs"]["aud"]),
                 os.path.basename(p["out"])))
        for m in p["issues"]:
            print("     [阻塞] " + m)
        for m in p["warns"]:
            print("     [提醒] " + m)
    if blocked:
        print("\n阻塞 %d 组 / 可跑 %d 组。" % (len(blocked), len(plans) - len(blocked)))
    else:
        print("\n全部 %d 组可投喂。" % len(plans))

    # ---- 落盘 ----
    plan = {"title": title, "episode": ep, "version": ver, "version_note": ver_note, "total_duration": round(total_dur, 1),
            "totals": tot, "groups": plans}
    pj = os.path.join(out_dir, "投喂清单_%s_S%s.json" % (title, ep))
    with open(pj, "w", encoding="utf-8") as f:
        json.dump(plan, f, ensure_ascii=False, indent=2)

    lines = ["# 投喂清单 ·《%s》S%s" % (title, ep), "",
             "- 组数 %d，计划 %.1f 秒（%.1f 分钟）" % (len(plans), total_dur, total_dur / 60),
             "- 素材占用：图 %d / 视频 %d / 音频 %d" % (tot["img"], tot["vid"], tot["aud"]),
             "- 可跑 %d 组，阻塞 %d 组" % (len(plans) - len(blocked), len(blocked)), "",
             "| 状态 | 组号 | 时长 | 档位 | 图 | 视频 | 音频 | 产物 | 阻塞项 |",
             "|---|---|---|---|---|---|---|---|---|"]
    for p in plans:
        lines.append("| %s | %s | %.1f | %s | %d | %d | %d | %s | %s |"
                     % ("✅" if p["status"] == "ready" else "❌", p["no"], p["duration"], p["tier"],
                        len(p["refs"]["img"]), len(p["refs"]["vid"]), len(p["refs"]["aud"]),
                        os.path.basename(p["out"]), "；".join(p["issues"]) or "-"))
    lines += ["", "## 提醒（不阻塞，但要人看一眼）", ""]
    any_warn = False
    for p in plans:
        for m in p["warns"]:
            any_warn = True
            lines.append("- %s：%s" % (p["no"], m))
    if not any_warn:
        lines.append("- 无")
    md = os.path.join(out_dir, "投喂清单_%s_S%s.md" % (title, ep))
    with open(md, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    print("清单已写：%s" % md)
    print("机器可读：%s" % pj)
    return 1 if blocked else 0


if __name__ == "__main__":
    sys.exit(main())
