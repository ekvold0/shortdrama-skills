#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""grokfilm 技法层规则 CT01–CT06（两个技能共用同一份实现）

被 storyboard-creation/scripts/verify.py 与 keyword-script-creation/scripts/verify.py 导入。
两份文件内容必须完全一致（改规则请两边同步，见各自 README「技法层规则」）。

统一返回 [{level, code, ref, msg}]，level 取 "error" / "warning"：
    error   命中即必须改，不得交付
    warning 提示性，交付前需人工确认

规则码：
    CT01 空泛词                —— 写了等于没写，模型随机发挥
    CT02 九子参数齐全/顺序      —— 关键词层 params 九键缺项或乱序
    CT03 一镜一主运镜           —— 同一镜出现多个运动轴
    CT04 单镜时长上限           —— 由各 verify.py 自身检查，此处不重复
    CT05 典故不入正文           —— 影史典故必须移入「参考电影」
    CT06 参考电影格式与数量      —— 《片名》年份，限 1 部
"""

import re

# ---------------------------------------------------------------- 词表

#: CT01 空泛词。命中即 error：这类词在模型侧等于「没有任何约束」，
#: 写了不仅无效，还会稀释已写好的参数。替换表见 keyword-script-creation/references/45 §3。
VAGUE_WORDS = [
    "电影感", "电影质感", "电影级", "氛围感", "大片感", "高级感", "高级调色",
    "油画感", "绘画感", "笔触", "3D感", "CG感", "渲染感",
    "二次元", "动漫风", "日系", "唯美", "震撼",
    "张力拉满", "情绪张力", "时空交错", "蒙太奇感", "呼吸感",
    "专业级", "工业级", "沉浸感",
]

#: CT03 运动轴家族：同一家族内只算一个轴，跨家族 ≥2 即一镜多主运镜。
MOVE_FAMILY = {
    "推": ["推近", "推进", "前推"],
    "拉": ["拉远", "后拉", "后拉远"],
    "摇": ["横摇", "上摇", "下摇", "竖摇", "摇镜"],
    "移": ["横移", "平移"],
    "跟": ["跟拍", "跟随"],
    "升降": ["升降", "上升", "下降", "摇臂"],
    "环绕": ["环绕", "旋转"],
    "甩": ["甩镜"],
    "变焦": ["变焦"],
    "俯仰": ["俯仰"],
}

#: 关键词层 params 九子键（定序不可乱）
PARAM_KEYS = ["camera", "texture", "color", "position", "movement",
              "light", "action", "blocking", "reference"]
PARAM_LABEL = {
    "camera": "摄影机", "texture": "画面质感", "color": "色彩",
    "position": "机位", "movement": "运镜", "light": "光影",
    "action": "动作", "blocking": "场面调度", "reference": "参考电影",
}

REF_PAT = re.compile(r"《([^》]+)》\s*(\d{4})?")


# ---------------------------------------------------------------- 工具

def _s(v):
    if v is None:
        return ""
    if isinstance(v, str):
        return v
    if isinstance(v, (int, float)):
        return str(v)
    if isinstance(v, (list, tuple)):
        return " ".join(_s(x) for x in v)
    if isinstance(v, dict):
        return " ".join(_s(x) for x in v.values())
    return str(v)


def _vague(text):
    return [w for w in VAGUE_WORDS if w in (text or "")]


def _move_families(text):
    text = text or ""
    hit = set()
    for fam, words in MOVE_FAMILY.items():
        if any(w in text for w in words):
            hit.add(fam)
    return hit


def _check_ref(value, code, ref, out, where):
    text = _s(value).strip()
    if not text:
        return
    found = REF_PAT.findall(text)
    if not found:
        out.append({"level": "error", "code": code, "ref": ref,
                    "msg": "{}的参考电影应写成《片名》年份，实际为：{}".format(where, text[:40])})
        return
    if len(found) > 1:
        out.append({"level": "error", "code": code, "ref": ref,
                    "msg": "{}挂了 {} 部参考电影（限 1 部，多了模型会把风格平均成四不像）".format(
                        where, len(found))})
    for name, year in found:
        if not year:
            out.append({"level": "warning", "code": code, "ref": ref,
                        "msg": "{}的参考电影《{}》缺年份（片名＋年份才可复现）".format(where, name)})


#: CT07 英文技法名。词表由 cine_tech.json 的 en 字段现生成，加新技法不用改脚本。
_EN_CACHE = None


def _en_patterns(minlen=5):
    global _EN_CACHE
    if _EN_CACHE is not None:
        return _EN_CACHE
    out = []
    try:
        import cine_tech
        for t in TECHS_OR_EMPTY():
            en = _s(t.get("en")).split("(")[0].strip()
            if len(en) < minlen:
                continue
            words = [w for w in re.split(r"[^A-Za-z\-]+", en) if len(w) >= 4]
            if not words:
                continue
            pat = re.compile(r"\b" + r"[\s\-]*".join(re.escape(w) for w in words) + r"\b", re.I)
            out.append((pat, t))
    except Exception:  # noqa: BLE001
        pass
    _EN_CACHE = out
    return out


def TECHS_OR_EMPTY():
    try:
        import cine_tech
        return cine_tech.TECHS
    except Exception:  # noqa: BLE001
        return []


def _en_hits(text):
    """返回命中的英文技法条目列表。"""
    text = text or ""
    if not re.search(r"[A-Za-z]{4,}", text):
        return []
    return [t for pat, t in _en_patterns() if pat.search(text)]


def _ct07(text, ref, out, where):
    for t in _en_hits(text):
        out.append({"level": "error", "code": "CT07", "ref": ref,
                    "msg": "{}里出现英文技法名『{}』——降维成中文可执行写法（{} / 落点 {}）".format(
                        where, _s(t.get("en")), _s(t.get("cn")), _s(t.get("slot")))})


#: CT08 T4 禁投：中文名出现在正面写法里即拦。前置否定（无/禁/不/非/免/去）不算命中。
NEG_PREFIX = ("无", "禁", "不", "非", "免", "去", "除", "避免", "杜绝")


def _t4_names():
    return [(t.get("cn"), t) for t in TECHS_OR_EMPTY()
            if t.get("tier") == "T4" and len(_s(t.get("cn"))) >= 2]


def _ct08(text, ref, out, where):
    text = text or ""
    if not text:
        return
    for cn, t in _t4_names():
        start = 0
        while True:
            i = text.find(cn, start)
            if i < 0:
                break
            start = i + 1
            pre = text[max(0, i - 3):i]
            if any(p in pre for p in NEG_PREFIX):
                continue  # 「无配乐」「禁叠化」这类否定写法是正确的
            out.append({"level": "error", "code": "CT08", "ref": ref,
                        "msg": "{}里出现 T4 禁投技法『{}』——改用：{}".format(
                            where, cn, _s(t.get("note")).split("替代")[-1].lstrip("＝= ") or "55 §7 等价替代")})
            break


# ---------------------------------------------------------------- 分镜层

def check_storyboard(data):
    """分镜层校验：CT01/CT03/CT05/CT06。返回列表。"""
    out = []
    for u in (data.get("units") or []):
        uid = _s(u.get("id")) or "?"
        _check_ref(u.get("reference"), "CT06", uid, out, "单元 {}".format(uid))
        for sh in (u.get("shots") or []):
            sid = _s(sh.get("id")) or "?"
            cam = _s(sh.get("camera"))
            con = _s(sh.get("content"))
            for w in _vague(cam + " " + con):
                out.append({"level": "error", "code": "CT01", "ref": sid,
                            "msg": "出现空泛词『{}』——改成可观察/可测量的结果（55 §1）".format(w)})
            fams = _move_families(cam)
            if len(fams) > 1:
                out.append({"level": "warning", "code": "CT03", "ref": sid,
                            "msg": "机位与运镜含 {} 个运动轴（{}），一镜只留 1 个主运镜".format(
                                len(fams), "/".join(sorted(fams)))})
            if re.search(r"《[^》]+》", con):
                out.append({"level": "error", "code": "CT05", "ref": sid,
                            "msg": "画面内容里出现典故片名——必须移入『画面参数·参考电影』列"})
            _check_ref(sh.get("reference"), "CT06", sid, out, "镜 {}".format(sid))
            _ct07(cam, sid, out, "机位与运镜")
            _ct07(con, sid, out, "画面内容")
            _ct08(cam + " " + con, sid, out, "机位与画面")
    return out


# ---------------------------------------------------------------- 关键词层

def check_keyword(data):
    """关键词层校验：CT01/CT02/CT03/CT05/CT06。返回列表。"""
    out = []
    for i, g in enumerate(data.get("groups") or []):
        gid = _s(g.get("no")) or "#{}".format(i + 1)
        p = g.get("params") or {}

        # CT02 九子参数齐全 + 定序
        for k in PARAM_KEYS:
            if k == "reference":
                v = _s(p.get("reference")) or _s(p.get("ref"))
            else:
                v = _s(p.get(k))
            if not v.strip():
                out.append({"level": "error", "code": "CT02", "ref": gid,
                            "msg": "params 缺『{}』（{}）——九子参数齐全才可投".format(
                                PARAM_LABEL[k], k)})
        idx = [PARAM_KEYS.index(k) for k in p.keys() if k in PARAM_KEYS]
        if idx and idx != sorted(idx):
            out.append({"level": "warning", "code": "CT02", "ref": gid,
                        "msg": "params 键序乱：应为 {}（45 §1）".format(" → ".join(PARAM_KEYS))})

        # CT01 空泛词（params + 分镜文本）
        blob = _s(p) + " " + _s(g.get("makeup"))
        for w in _vague(blob):
            out.append({"level": "error", "code": "CT01", "ref": gid,
                        "msg": "参数里出现空泛词『{}』——换成可测量写法（45 §3）".format(w)})

        for j, s in enumerate(g.get("shots") or [], 1):
            sid = "%s-镜%s" % (gid, _s(s.get("id")) or j)
            cam = _s(s.get("cam"))
            pic = _s(s.get("pic"))
            for w in _vague(cam + " " + pic + " " + _s(s.get("style"))):
                out.append({"level": "error", "code": "CT01", "ref": sid,
                            "msg": "分镜文本出现空泛词『{}』（45 §3）".format(w)})
            fams = _move_families(cam)
            if len(fams) > 1:
                out.append({"level": "warning", "code": "CT03", "ref": sid,
                            "msg": "cam 含 {} 个运动轴（{}），一镜只留 1 个主运镜（45 §5.1）".format(
                                len(fams), "/".join(sorted(fams)))})
            if re.search(r"《[^》]+》", pic):
                out.append({"level": "error", "code": "CT05", "ref": sid,
                            "msg": "pic 里出现典故片名——典故只进 params.reference"})
            _ct07(cam + " " + pic + " " + _s(s.get("style")), sid, out, "分镜文本")
            _ct08(cam + " " + pic + " " + _s(s.get("style")), sid, out, "分镜文本")

        _check_ref(p.get("reference"), "CT06", gid, out, "组 {}".format(gid))
    return out


# ------------------------------------------------------------ 数据自检

EXPECT_COUNT = 300


def data_warnings():
    """校验 cine_tech.json 条数/版本，返回 warning 列表（升级清单 A1 验收项）。

    数据没部署时不阻断校验——技法层降级为纯文本规则，但必须让人看见。
    """
    out = []
    try:
        import cine_tech
    except Exception as exc:  # noqa: BLE001
        out.append({"level": "warning", "code": "CT00", "ref": "-",
                    "msg": "cine_tech 未部署或不可导入（{}）——技法层降级为纯文本规则".format(exc)})
        return out
    count = getattr(cine_tech, "COUNT", None)
    if count != EXPECT_COUNT:
        out.append({"level": "warning", "code": "CT00", "ref": "-",
                    "msg": "cine_tech.json 条数 {} ≠ {}，技法库未同步（复跑 A1 部署）".format(
                        count, EXPECT_COUNT)})
    return out
