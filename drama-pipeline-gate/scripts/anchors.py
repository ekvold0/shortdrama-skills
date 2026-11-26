# -*- coding: utf-8 -*-
"""人物锚点单一源（V2.0 两阶段版）。

规则不变：每个角色的外貌/服装/道具只在这里写一次，所有集的关键词脚本从这里逐字复刻，
不许各写一份、不许手改单集；`gate.py anchors` 会逐组校验是否与这里一致。

V2.0 变化（两阶段）：
  阶段一「先填名字」——只登记角色名与别名，anchor 留空。此时 anchors 校验只查
    「名字有没有登记」「有没有串到别的角色」，不查外貌一致性。
  阶段二「再补信息」——逐角色把 anchor（可观察、可测量的完整锚点句）与 features
    （readback 判红用的特征词）补齐，该角色才算 full。

数据源：`角色锚点.json`（本项目，建议放在剧集目录根部）。查找顺序：
  1) 环境变量 GATE_ANCHORS 指向的文件
  2) 当前目录的 角色锚点.json / anchors.json
  3) 本脚本同目录的 角色锚点.json / anchors.json
  4) 都没有 → 退回下面的内置示例四人，并打印警告（此时本剧角色不会被真校验）

命令：
  python anchors.py init    --script 剧本.docx [--project 《剧名》] [--out 角色锚点.json]
  python anchors.py status  [角色锚点.json]
  python anchors.py check   [角色锚点.json]
  python anchors.py render  [角色锚点.json]      # 输出可粘贴的「角色名：锚点句」整块
"""

from __future__ import annotations

import json
import os
import re
import sys

SCHEMA = "anchors/1"

# ---------------------------------------------------------------- 内置示例（仅演示）
LIN = "（示例）林晓，24岁女性，163cm偏瘦，鹅蛋脸，内双，黑发低马尾，深蓝涤棉工服洗得发白、袖口磨毛，黑色帆布鞋，左膝有护膝"
WANG = "（示例）王桂兰，55岁女性，158cm微胖，圆脸，短卷发染黑，枣红针织开衫，黑裤子，左手腕戴玉镯，右手拎布兜"
ZHOU = "（示例）老周，45 岁男性，平头，鬓角灰；深蓝司机制服，肩线磨白；只通过车内后视镜出现，不入正脸，不回头"
CHEN = "（示例）陈姐，40 岁上下女性，圆脸偏胖，T 区出油；浅蓝底小白花衬衫（与王桂兰的暗红碎花明确区分），袖口挽到小臂中段；短发别在耳后；左前第一排靠过道侧坐"

ALL = {"LIN": LIN, "WANG": WANG, "ZHOU": ZHOU, "CHEN": CHEN}
LIN_BLOCK = "林晓：" + LIN
WANG_BLOCK = "王桂兰：" + WANG
BLOCKS = {"林晓": LIN_BLOCK, "王桂兰": WANG_BLOCK}

SAMPLE = [
    {"key": "LIN", "name": "林晓", "aliases": [], "role": "女主",
     "stage": "full", "anchor": LIN, "features": ["深蓝", "工牌", "耳机"]},
    {"key": "WANG", "name": "王桂兰", "aliases": [], "role": "女主母亲",
     "stage": "full", "anchor": WANG, "features": ["暗红", "碎花"]},
    {"key": "ZHOU", "name": "老周", "aliases": [], "role": "公交司机",
     "stage": "full", "anchor": ZHOU, "features": ["后视镜"]},
    {"key": "CHEN", "name": "陈姐", "aliases": [], "role": "乘客",
     "stage": "full", "anchor": CHEN, "features": ["衬衫", "短发"]},
]

CANDIDATES = ("角色锚点.json", "anchors.json")

# 剧本里不是人名的“说话人”标签
NOT_NAME = {
    "旁白", "画外音", "内心独白", "字幕", "镜头", "场景", "时间", "地点", "音效", "音乐",
    "转场", "黑场", "片头", "片尾", "提示", "注", "说明", "出场人物", "人物", "导演",
    "系统", "手机", "广播", "电话", "微信", "短信", "群消息", "备注", "原文片段",
    "视觉风格", "画面内容", "景别", "运镜", "台词", "情绪", "画外",
}


# ---------------------------------------------------------------- 读取
def _find_path(path=None):
    if path:
        return path if os.path.exists(path) else ""
    env = os.environ.get("GATE_ANCHORS", "").strip()
    if env and os.path.exists(env):
        return env
    for base in (os.getcwd(), os.path.dirname(os.path.abspath(__file__))):
        for fn in CANDIDATES:
            p = os.path.join(base, fn)
            if os.path.exists(p):
                return p
    return ""


def load(path=None, quiet=False):
    """返回 {schema, project, source, characters:[{key,name,aliases,role,stage,anchor,features,...}]}。"""
    p = _find_path(path)
    if not p:
        if not quiet:
            print("[提示] 没找到 角色锚点.json，正在使用内置的示例四人（林晓/王桂兰/老周/陈姐）。")
            print("       当前剧本的角色不会被真正校验。先跑："
                  "python anchors.py init --script <剧本.docx>")
        return {"schema": SCHEMA, "project": "（示例）", "source": "builtin",
                "characters": [dict(c) for c in SAMPLE]}
    data = json.load(open(p, encoding="utf-8"))
    chars = data.get("characters") or []
    for c in chars:
        c.setdefault("aliases", [])
        c.setdefault("features", [])
        c.setdefault("anchor", "")
        c.setdefault("role", "")
        c.setdefault("key", "")
        # stage 缺省按内容推断，避免手写 json 的人漏字段
        if not c.get("stage"):
            c["stage"] = "full" if c.get("anchor") and c.get("features") else (
                "look" if c.get("anchor") else "names")
    data["characters"] = chars
    data["source"] = p
    return data


def names(data=None):
    """名字 → 角色 dict（含别名）。"""
    data = data or load(quiet=True)
    out = {}
    for c in data.get("characters", []):
        for n in [c.get("name", "")] + list(c.get("aliases") or []):
            n = (n or "").strip()
            if n:
                out[n] = c
    return out


def features(data=None):
    """readback 判红用：{名字: [特征词]}（只收已补 features 的角色）。"""
    data = data or load(quiet=True)
    out = {}
    for c in data.get("characters", []):
        f = [x for x in (c.get("features") or []) if x]
        if f:
            out[c.get("name", "")] = f
    return out


def blocks(data=None):
    """可粘贴整块：{"林晓": "林晓：<锚点句>"}（只收已写 anchor 的）。"""
    data = data or load(quiet=True)
    out = {}
    for c in data.get("characters", []):
        a = (c.get("anchor") or "").strip()
        if a:
            out[c.get("name", "")] = "%s：%s" % (c.get("name", ""), a)
    return out


# ---------------------------------------------------------------- 剧本抽名字
def _iter_script_lines(path):
    ext = os.path.splitext(path)[1].lower()
    if ext == ".docx":
        try:
            import docx  # python-docx
        except ImportError:
            raise SystemExit("读 .docx 需要 python-docx：pip install python-docx")
        d = docx.Document(path)
        for p in d.paragraphs:
            if p.text.strip():
                yield p.text.strip()
        for t in d.tables:
            for row in t.rows:
                for cell in row.cells:
                    for line in cell.text.splitlines():
                        if line.strip():
                            yield line.strip()
    elif ext in (".xlsx", ".xlsm"):
        try:
            import openpyxl
        except ImportError:
            raise SystemExit("读 .xlsx 需要 openpyxl：pip install openpyxl")
        wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
        for ws in wb.worksheets:
            for row in ws.iter_rows(values_only=True):
                for cell in row:
                    if isinstance(cell, str):
                        for line in cell.splitlines():
                            if line.strip():
                                yield line.strip()
    else:
        for line in open(path, encoding="utf-8", errors="replace"):
            if line.strip():
                yield line.strip()


CAST_RE = re.compile(r"^\s*(?:人物|出场人物|角色|主要人物|人物表)\s*[：:]\s*(.+)$")
LABEL_RE = re.compile(r"^\s*([\u4e00-\u9fa5]{2,4})\s*(?:OS|os|O\.S\.|VO|vo|画外|内心)?\s*[：:]\s*(.+)$")
SPEAK_RE = re.compile(r"([\u4e00-\u9fa5]{2,4})\s*(?:说|问|答|喊|叫|嘟囔|冷笑|吼道|低声|接口)")
BRACKET_RE = re.compile(r"[【\[]\s*([\u4e00-\u9fa5]{2,4})\s*[】\]]\s*[：:]")

# 像标签但不是角色名的（集号/场次/转场/提示）
BAD_LABEL = re.compile(
    r"(上|下|本|全|这|那|每|第)[一集集场幕部]|集$|场$|幕$|闪回|回忆|倒计时|片头|片尾|"
    r"黑场|过场|特写|全景|中景|近景|远景|空镜|字幕|画面|声音|铃声|手机|电话|微信|广播")


def extract_names(path):
    """从剧本里抽候选角色名。

    优先级：① 剧本自带的「人物：A、B、C」人物表（最权威）② 行首「角色名：台词」
    与「【角色名】：」显式标签（自动剥 OS/VO/画外 后缀）③ `X说/X问` 只给已有名字加权，
    不单独造名字（否则「我就说」会把「我就」当成角色）。
    """
    label = {}
    speak = {}
    cast = []
    lines = list(_iter_script_lines(path))
    for line in lines:
        mc = CAST_RE.match(line)
        if mc:
            for raw in re.split(r"[、，,／/\s]+", mc.group(1)):
                n = re.sub(r"(等|若干|们|众人|其他)$", "", raw.strip())
                if 2 <= len(n) <= 4 and n not in NOT_NAME and not BAD_LABEL.search(n) and n not in cast:
                    cast.append(n)
        m = LABEL_RE.match(line) or BRACKET_RE.match(line)
        if m:
            n = m.group(1)
            if n not in NOT_NAME and not BAD_LABEL.search(n):
                label[n] = label.get(n, 0) + 1
        for m in SPEAK_RE.finditer(line):
            n = m.group(1)
            speak[n] = speak.get(n, 0) + 1
    out = []
    for n in cast:
        out.append((n, 999 + label.get(n, 0) * 3, label.get(n, 0), speak.get(n, 0)))
    for n, c in label.items():
        if n in cast:
            continue
        out.append((n, c * 3 + speak.get(n, 0), c, speak.get(n, 0)))
    out.sort(key=lambda t: (-t[1], t[0]))
    return out


def init(script, out, project=""):
    if not os.path.exists(script):
        raise SystemExit("剧本不存在：%s" % script)
    found = extract_names(script)
    chars = []
    for i, (n, score, lc, sc) in enumerate(found, 1):
        chars.append({
            "key": "C%02d" % i,
            "name": n,
            "aliases": [],
            "role": "",
            "stage": "names",
            "anchor": "",
            "features": [],
            "_证据": "台词标签×%d／提及×%d" % (lc, sc),
        })
    data = {"schema": SCHEMA, "project": project or os.path.splitext(os.path.basename(script))[0],
            "updated": "", "script": script, "characters": chars}
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
    print("已写 %s：登记 %d 个角色（stage=names）" % (out, len(chars)))
    for n, score, lc, sc in found:
        print("  %-6s 台词标签×%d 提及×%d" % (n, lc, sc))
    print("\n下一步：打开该 json，删掉不是角色的名字，给每个角色补 anchor 与 features，")
    print("        再把 stage 改成 look（只有外貌）或 full（外貌+特征词），然后跑 anchors.py check")
    return 0


# ---------------------------------------------------------------- 检查
def status(path=None):
    data = load(path)
    chars = data.get("characters", [])
    print("锚点表：%s（%s）｜%d 个角色" % (data.get("source"), data.get("project", ""), len(chars)))
    order = {"names": 0, "look": 1, "full": 2}
    for c in chars:
        st = c.get("stage", "names")
        miss = []
        if not (c.get("anchor") or "").strip():
            miss.append("anchor")
        if not (c.get("features") or []):
            miss.append("features")
        mark = {"names": "① 只有名字", "look": "② 有外貌", "full": "③ 完整"}[st]
        print("  %-6s %-10s %s%s" % (
            c.get("name", "?"), mark,
            "缺：" + "/".join(miss) if miss else "齐",
            "" if not c.get("role") else "（%s）" % c["role"]))
    names_left = [c.get("name") for c in chars if order.get(c.get("stage", "names"), 0) < 2]
    if names_left:
        print("\n还没补完：%s" % "、".join(names_left))
    return 0


def _norm(s):
    """比对用归一化：去空格与所有标点，只比字面内容（顿号/逗号/括号写法差异不算错）。"""
    return re.sub(r"[\s，,。；;、：:（）()【】\[\]《》<>“”\"'·…—\-]+", "", s or "")


def check(path=None):
    data = load(path)
    chars = data.get("characters", [])
    bad = []

    seen = {}
    for c in chars:
        n = (c.get("name") or "").strip()
        if not n:
            bad.append("有角色缺 name")
            continue
        for x in [n] + list(c.get("aliases") or []):
            if x in seen and seen[x] != n:
                bad.append("名字/别名重复：%s 同时属于 %s 与 %s" % (x, seen[x], n))
            seen[x] = n

    for c in chars:
        n = c.get("name", "")
        st = c.get("stage", "names")
        a = (c.get("anchor") or "").strip()
        if st in ("look", "full"):
            if not a:
                bad.append("%s：stage=%s 但 anchor 是空的" % (n, st))
            elif len(_norm(a)) < 20:
                bad.append("%s：anchor 太短（%d 字），至少年龄/身高/脸/发型/服装/配饰几个可观察项"
                           % (n, len(_norm(a))))
        if st == "full" and not [x for x in (c.get("features") or []) if x]:
            bad.append("%s：stage=full 但 features 是空的（readback 无法判红）" % n)
        if st == "names" and (a or c.get("features")):
            bad.append("%s：stage 还是 names，但已经填了内容——把 stage 改成 look/full" % n)

    # 两个角色锚点一模一样 = 同一个人写了两个名字，该合并或设别名
    by_anchor = {}
    for c in chars:
        a = _norm(c.get("anchor"))
        if len(a) >= 20:
            by_anchor.setdefault(a, []).append(c.get("name", ""))
    for a, ns in by_anchor.items():
        if len(ns) > 1:
            bad.append("%s 的锚点完全相同——是同一个人的两个名字？合并，或把其中一个加进 aliases"
                       % "/".join(ns))

    print("=" * 60)
    print("角色锚点表自检：%d 个角色｜%s" % (len(chars), data.get("source")))
    if bad:
        for b in bad:
            print("  [红] " + b)
        print("结论：不通过（%d 条）" % len(bad))
        return 1
    print("结论：通过")
    return 0


def harvest(path=None, kw=""):
    """从已有关键词脚本回捞 anchor（存量剧集迁移用）。

    做法：在「场景与妆造简述」里找 `角色名（…）` 的定义块，把括号里的内容当作 anchor。
    只填 anchor、stage 设 look；features 仍需人工补（它决定 readback 判不判红）。
    """
    if not kw or not os.path.exists(kw):
        print("需要关键词脚本：python anchors.py harvest --kw <关键词xlsx> [角色锚点.json]")
        return 2
    try:
        import openpyxl
    except ImportError:
        raise SystemExit("需要 openpyxl：pip install openpyxl")
    data = load(path)
    names_ = [c.get("name", "") for c in data.get("characters", []) if c.get("name")]
    if "source" in data and data["source"] == "builtin":
        print("[停] 现在用的是内置示例表，先 init 出本剧的表。")
        return 1
    wb = openpyxl.load_workbook(kw, data_only=True)
    got = {}
    for ws in wb.worksheets:
        hdr = [c.value for c in ws[1]] or []
        if "场景与妆造简述" not in hdr:
            continue
        col = hdr.index("场景与妆造简述")
        for row in ws.iter_rows(min_row=2, values_only=True):
            v = row[col] if col < len(row) else None
            if not isinstance(v, str):
                continue
            for n in names_:
                if n in got:
                    continue
                i = v.find(n + "（")
                if i < 0:
                    continue
                j = i + len(n) + 1
                depth = 1
                while j < len(v) and depth:
                    if v[j] == "（":
                        depth += 1
                    elif v[j] == "）":
                        depth -= 1
                    j += 1
                body = v[i + len(n) + 1: j - 1].strip()
                if len(body) >= 20:
                    got[n] = body
    hit = 0
    for c in data.get("characters", []):
        n = c.get("name", "")
        if n in got and not (c.get("anchor") or "").strip():
            c["anchor"] = got[n]
            c["stage"] = "look"
            hit += 1
            print("  ✓ %s 回捞到 %d 字" % (n, len(got[n])))
    miss = [c.get("name") for c in data.get("characters", []) if not (c.get("anchor") or "").strip()]
    if miss:
        print("  ⚠ 没捞到：%s（这些要么本集没出现，要么写法不是「名字（…）」）" % "、".join(miss))
    out = data.get("source")
    json.dump({k: v for k, v in data.items() if k != "source"},
              open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print("已回写 %s（补了 %d 个 anchor）。下一步：给每个角色填 features（readback 判红要用的外形词），stage 改 full。" % (out, hit))
    return 0


def diff(path=None, script=""):
    """剧本人物表 ↔ 角色锚点表 逐名对照（确定性，不猜）。"""
    data = load(path)
    have = {c.get("name", ""): c for c in data.get("characters", []) if c.get("name")}
    if not script:
        script = data.get("script", "")
    if not script or not os.path.exists(script):
        print("需要剧本：python anchors.py diff --script <剧本.docx> [角色锚点.json]")
        return 2
    found = [n for n, *_ in extract_names(script)]
    print("=" * 60)
    print("剧本：%s" % script)
    print("锚点表：%s｜%d 个角色" % (data.get("source"), len(have)))
    only_script = [n for n in found if n not in have]
    only_table = [n for n in have if n not in found]
    if only_script:
        print("  [红] 剧本里有、表里没有（先登记名字）：%s" % "、".join(only_script))
    if only_table:
        print("  [黄] 表里有、本集剧本没出现（可能只是本集没有，或名字写错）：%s" % "、".join(only_table))
    if not only_script and not only_table:
        print("  两边名字一致")
    return 0 if not only_script else 1


def render(path=None):
    bl = blocks(load(path))
    for k, v in bl.items():
        print(v)
    missing = [c.get("name") for c in load(path, quiet=True).get("characters", [])
               if not (c.get("anchor") or "").strip()]
    if missing:
        print("\n# 还没 anchor 的角色：%s" % "、".join(missing))
    return 0


def main(argv):
    cmd = argv[1] if len(argv) > 1 else "status"
    rest = argv[2:]
    if cmd == "init":
        kw = {}
        i = 0
        while i < len(rest):
            if rest[i] == "--script":
                kw["script"] = rest[i + 1]; i += 2
            elif rest[i] == "--out":
                kw["out"] = rest[i + 1]; i += 2
            elif rest[i] == "--project":
                kw["project"] = rest[i + 1]; i += 2
            else:
                i += 1
        return init(kw.get("script", ""), kw.get("out", "角色锚点.json"), kw.get("project", ""))
    if cmd == "harvest":
        kw = {}
        i = 0
        while i < len(rest):
            if rest[i] == "--kw":
                kw["kw"] = rest[i + 1]; i += 2
            elif rest[i].endswith(".json"):
                kw["path"] = rest[i]; i += 1
            else:
                i += 1
        return harvest(kw.get("path"), kw.get("kw", ""))
    if cmd == "diff":
        kw = {}
        i = 0
        while i < len(rest):
            if rest[i] == "--script":
                kw["script"] = rest[i + 1]; i += 2
            elif rest[i].endswith(".json"):
                kw["path"] = rest[i]; i += 1
            else:
                i += 1
        return diff(kw.get("path"), kw.get("script", ""))
    if cmd == "status":
        return status(rest[0] if rest else None)
    if cmd == "check":
        return check(rest[0] if rest else None)
    if cmd == "render":
        return render(rest[0] if rest else None)
    print(__doc__)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
