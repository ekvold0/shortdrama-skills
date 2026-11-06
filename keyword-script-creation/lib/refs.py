# -*- coding: utf-8 -*-
"""附件3/4/5/6 条目检索与引用展开。

设计原则：
1. 只按条取用，不整库倾倒——280 条全文约 12 万字，全展开会烧掉上下文。
2. 条号/标题不存在时直接报错，绝不降级、不猜——引用错了比不引用更糟。
3. 附件6 的引用必须连同原文一起写进单元格（标准版第 9 条），expand 负责拼装。

CLI:
    python refs.py list face
    python refs.py get face 1
    python refs.py get edit 11 --genre 电视剧
    python refs.py search sound 心跳
    python refs.py expand edit 电视剧 11 "本组用它把对峙拍成施压"
    python refs.py check "……附件6 电视剧第11条【手持晃动权力压迫】……"
    python refs.py index edit

Python:
    from refs import get_entry, inline_edit, check_text
"""
import os
import sys
import json
import argparse

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import att3_face     # noqa: E402
import att4_dialogue  # noqa: E402
import att5_sound     # noqa: E402
import att6_edit      # noqa: E402

LIBS = {
    "face": ("附件3 表情与微表情", att3_face.ATT3),
    "dialogue": ("附件4 对话与台词", att4_dialogue.ATT4),
    "sound": ("附件5 声音设计", att5_sound.ATT5),
    "edit": ("附件6 分镜与切镜", att6_edit.ATT6),
}
ALIAS = {
    "3": "face", "att3": "face", "face": "face", "表情": "face", "微表情": "face",
    "4": "dialogue", "att4": "dialogue", "dialogue": "dialogue", "台词": "dialogue", "对白": "dialogue",
    "5": "sound", "att5": "sound", "sound": "sound", "音效": "sound", "声音": "sound",
    "6": "edit", "att6": "edit", "edit": "edit", "分镜": "edit", "切镜": "edit",
}
FUNC_KEYS = ("情绪功能", "叙事功能")


class RefError(KeyError):
    pass


def norm_kind(kind):
    k = str(kind).strip().lower()
    if k not in ALIAS:
        raise RefError("未知库：%s（可用：face/dialogue/sound/edit）" % kind)
    return ALIAS[k]


def _sections(kind):
    return LIBS[norm_kind(kind)][1]["sections"]


def title_of(e):
    return e.get("title", "")


def count(kind):
    """某库的总条数（各节相加）。"""
    return sum(len(s.get("entries") or []) for s in _sections(kind))


def genre_of(e):
    return e.get("genre", "")


def get_entry(kind, n, genre=None):
    """取单条。edit 库必须给 genre；条号不存在时报错并列出该库可用条号。"""
    kind = norm_kind(kind)
    secs = _sections(kind)
    if kind == "edit" and not genre:
        hits = [s for s in secs if any(e["n"] == int(n) for e in s["entries"])]
        if len(hits) > 1:
            raise RefError("附件6 第%d条在多个体裁中都有，必须指定 genre：%s"
                           % (int(n), "、".join(s.get("genre", "") for s in hits)))
        genre = hits[0].get("genre") if hits else None
    for s in secs:
        if genre and s.get("genre") != genre:
            continue
        for e in s["entries"]:
            if e["n"] == int(n):
                return e
    where = "（体裁：%s）" % genre if genre else ""
    raise RefError("%s 没有第%s条%s" % (LIBS[kind][0], n, where))


def find_by_title(kind, title):
    for s in _sections(kind):
        for e in s["entries"]:
            if title_of(e) == title:
                return e
    return None


def search(kind, word):
    kind = norm_kind(kind)
    out = []
    for s in _sections(kind):
        for e in s["entries"]:
            blob = " ".join(str(v) for k, v in e.items() if k != "section")
            if word in blob:
                out.append(e)
    return out


def entry_text(e, with_section=False):
    lines = []
    head = "第%s条【%s】" % (e["n"], title_of(e))
    if e.get("genre"):
        head = "%s %s" % (e["genre"], head)
    lines.append(head)
    for k in ("定义", "AI执行", "情绪功能", "叙事功能", "适用场景", "代表作品", "内容", "备注"):
        if e.get(k):
            lines.append("%s：%s" % (k, e[k]))
    if with_section:
        lines.append("（所属：%s）" % e.get("section", ""))
    return "\n".join(lines)


def inline_edit(genre, n, use):
    """附件6 引用展开：必须带原文。格式与产线 ref_inline 一致。"""
    e = get_entry("edit", n, genre)
    func = e.get("叙事功能", e.get("情绪功能", ""))
    s = ("附件6 %s第%d条【%s】｜定义：%s｜AI执行：%s｜叙事功能：%s｜适用场景：%s｜代表作品：%s。本组取用：%s"
         % (genre, int(n), title_of(e), e.get("定义", ""), e.get("AI执行", ""), func,
            e.get("适用场景", ""), str(e.get("代表作品", "")).rstrip("。"), use.strip()))
    return s


def inline_attachment(kind, n, use="", genre=None):
    """附件3/4/5 的内联：条名+用到的参数，不展开全文（避免单元格过长）。"""
    e = get_entry(kind, n, genre)
    kind = norm_kind(kind)
    parts = ["附件%d %s第%d条【%s】" % ({"face": 3, "dialogue": 4, "sound": 5}[kind], _label(kind), int(n), title_of(e))]
    if e.get("AI执行"):
        parts.append("AI执行：%s" % e["AI执行"])
    if e.get("内容"):
        parts.append(e["内容"])
    if use:
        parts.append("本组取用：%s" % use.strip())
    return "｜".join(parts)


def _label(kind):
    return {"face": "表情", "dialogue": "台词", "sound": "音效"}[kind]


REF_PAT = __import__("re").compile(r"附件6\s*(网剧|电视剧|动漫|通用)\s*第\s*(\d+)\s*条(?:【([^】]*)】)?")


def check_text(text):
    """扫一段文本里的附件6引用：条号是否存在、标题是否与条号一致、是否只写条号没带原文。"""
    import re
    issues = []
    for m in REF_PAT.finditer(text or ""):
        genre, n, title = m.group(1), int(m.group(2)), m.group(3)
        try:
            e = get_entry("edit", n, genre)
        except RefError as ex:
            issues.append({"pos": m.start(), "level": "error", "msg": str(ex), "raw": m.group(0)})
            continue
        if title and title != title_of(e):
            issues.append({"pos": m.start(), "level": "error",
                           "msg": "标题与条号不符：第%d条是【%s】，写成了【%s】" % (n, title_of(e), title),
                           "raw": m.group(0)})
        # 只写条号没有原文：条号后 200 字内必须出现“定义：”
        tail = text[m.end():m.end() + 240]
        if "定义：" not in tail and "定义:" not in tail:
            issues.append({"pos": m.start(), "level": "error",
                           "msg": "只写条号未内联原文（缺“定义：…”），按标准版第9条不合格",
                           "raw": m.group(0)})
    return issues


def _print(s):
    sys.stdout.write(s + "\n")


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    ap = argparse.ArgumentParser(description="附件3/4/5/6 条目检索")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("list")
    p.add_argument("kind")

    p = sub.add_parser("get")
    p.add_argument("kind")
    p.add_argument("n", type=int)
    p.add_argument("--genre")
    p.add_argument("--section", action="store_true")

    p = sub.add_parser("search")
    p.add_argument("kind")
    p.add_argument("word")

    p = sub.add_parser("expand")
    p.add_argument("genre")
    p.add_argument("n", type=int)
    p.add_argument("use")

    p = sub.add_parser("check")
    p.add_argument("text")

    p = sub.add_parser("index")
    p.add_argument("kind", nargs="?", default="edit")

    a = ap.parse_args()
    if a.cmd == "list":
        kind = norm_kind(a.kind)
        for s in _sections(kind):
            g = ("［%s］" % s.get("genre")) if s.get("genre") else ""
            _print("%s%s（%d条）" % (g, s["name"], len(s["entries"])))
            for e in s["entries"]:
                _print("  %2d  %s" % (e["n"], title_of(e)))
    elif a.cmd == "get":
        _print(entry_text(get_entry(a.kind, a.n, a.genre), a.section))
    elif a.cmd == "search":
        hits = search(a.kind, a.word)
        if not hits:
            _print("没有匹配：%s" % a.word)
        for e in hits:
            _print(entry_text(e))
            _print("-" * 40)
    elif a.cmd == "expand":
        _print(inline_edit(a.genre, a.n, a.use))
    elif a.cmd == "check":
        issues = check_text(a.text)
        if not issues:
            _print("OK：引用全部有效且已内联")
        for i in issues:
            _print("[%s] %s ← %s" % (i["level"], i["msg"], i["raw"]))
    elif a.cmd == "index":
        kind = norm_kind(a.kind)
        for s in _sections(kind):
            for e in s["entries"]:
                _print("%s|%s|%s" % (e.get("genre", ""), e["n"], title_of(e)))


if __name__ == "__main__":
    main()
