#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""grokfilm 技法层规则 CT01–CT15（两个技能共用同一份实现）

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
    CT07 英文技法名             —— 必须降维成中文可执行写法
    CT08 T4 禁投技法            —— 中文名出现在正面写法里即拦（否定写法放行）
    CT09 运镜量化               —— 缺主运镜（error）；有轴无米/度/秒（warning）
    CT10 光影四件套             —— 缺色温 K 或光比 1:n（error）；缺光位/光质（warning）
    CT11 钩子落位               —— 钩子写法混进运镜字段（error）；首组首镜 2 秒内无钩子特征、手法定式写进机位列（warning）
    CT12 英制单位               —— ft/inch/mph 等混进中文参数（error）
    CT13 台词余量               —— 台词说完到切点不足 0.6 秒（warning，49 §三）
    CT14 运动轴种类             —— 全集运镜少于 4 种运动轴（warning，49 §五）
    CT15 时长雷同               —— 相邻 3 个组/单元时长完全一样（warning，49 §二）

    分层说明：CT09/CT10 只作用于关键词层（keywords 的 params/movement/light/shots），
    分镜层按 45 §4「分镜层禁量化」不查运镜量化与光影数值。
    CT11 两层都查但口径不同：关键词层看 groups[0] 的 0–2 秒，分镜层看 units[0] 的 0–2 秒
    （镜头时长字段 keyword 层叫 dur、storyboard 层叫 duration，_head_text 两者都认）。
    CT13 只在关键词层（台词挂在镜头 dialogue 上）；CT14 只在关键词层（movement 是参数槽）；
    CT15 两层都查（关键词看 groups[].duration，分镜看 units[].duration）。
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

#: CT03 运动轴家族：同一家族内只算一轴，跨家族 ≥2 即一镜多主运镜。
#: 中文的省略写法（推镜头／拉镜头／移镜头／跟镜头）要算轴——实测历史交付里
#: 这四种写法最多，只认「推近／推进／前推」会把它们误判成「缺主运镜」。
MOVE_FAMILY = {
    "推": ["推近", "推进", "前推", "推镜"],
    "拉": ["拉远", "后拉", "后拉远", "拉镜"],
    "摇": ["横摇", "上摇", "下摇", "竖摇", "摇镜"],
    "移": ["横移", "平移", "移镜"],
    "跟": ["跟拍", "跟随", "跟镜"],
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

#: CT09 运镜量化：有运动轴时，必须给出米/厘米/度/秒这类可执行量。
MOVE_QUANT = re.compile(r"\d+(\.\d+)?\s*(米|厘米|毫米|度|cm|mm|m|秒)")

#: CT10 光影四件套（写法库见 references/42-打光库.md）。
#: 光位/光质缺失记 warning；色温 K 与光比 1:n 缺失记 error——模型侧这两项没有就是完全随机。
LIGHT_POS = ("顶光", "侧光", "逆光", "背光", "正面光", "侧逆", "左上", "右上",
             "左前", "右前", "左后", "右后", "左侧", "右侧", "上方", "下方",
             "窗光", "环境光", "脚光", "底光", "主光")
LIGHT_QUAL = ("硬光", "柔光", "散射", "漫射", "平行光", "点光", "面光",
              "柔光箱", "反光板", "灯管", "频闪")
LIGHT_K = re.compile(r"\d{3,5}\s*K", re.I)
LIGHT_RATIO = re.compile(r"光比\s*1\s*[:：]\s*\d|1\s*[:：]\s*\d(\.\d+)?")

#: CT11 钩子（写法库见 references/48-开场钩子.md）。
#: 这些词属于首镜的画面/音效，塞进「运镜」字段就是错位；只放明确无歧义的几个。
HOOK_IN_MOVE = ("黑场", "倒放", "静默", "炸光", "先声后影", "结果前置")
#: 全片至少要有这些特征中的一个，否则大概率是忘了写钩子（warning，不阻断）。
#: 「冲击事件词」是从 82 份历史交付里量出来的：只认 12 条模板名，误报 86.6%；
#: 补上撞/摔/砸/耳光这类高精度事件词后降到 9.8%，剩下的基本是提取不到正文的旧文件。
#: 注意：这词表里不许放「闪白」——它被 00 总纲和 verify 的 banned_trans 一起禁掉了，
#: 一个本身违规的词不能算钩子命中（试跑第 3 集时发现过这处打架）。
HOOK_FEATURE = HOOK_IN_MOVE + ("微距", "移焦", "睁眼", "色温突变", "高速入画",
                               "反转机位", "尺度错位", "几何硬对比", "异物入镜", "反常动作",
                               "撞击", "巨响", "摔", "砸", "耳光", "掐", "血", "碎",
                               "断裂", "尖叫", "嘶吼", "惨叫", "泼", "溅", "打翻", "撕",
                               "黑屏", "推门", "踹", "争抢", "抢夺", "倒地",
                               "昏迷", "警报", "炸", "裂开", "绷断", "脱手")

#: CT12 英制单位。口播写「10 英尺」可以，参数里写 10ft 就该换成米。
IMPERIAL = re.compile(r"\d+(\.\d+)?\s*(ft|feet|foot|inch|mph|yd)\b", re.I)


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


#: CT09 运镜量化：缺主运镜=error（模型会自己晃），有轴无量化=warning（晃多少不知道）
def _ct09_move(value, ref, out, where):
    text = _s(value).strip()
    if not text:
        return
    fams = _move_families(text)
    if not fams and "固定" not in text:
        out.append({"level": "error", "code": "CT09", "ref": ref,
                    "msg": "{}缺主运镜——既无运动轴（推/拉/摇/移/跟/升降/环绕/甩/变焦/俯仰）也没写「固定」".format(where)})
    elif fams and not MOVE_QUANT.search(text):
        out.append({"level": "warning", "code": "CT09", "ref": ref,
                    "msg": "{}有运动轴（{}）但没量化——补米/度/秒，例如「推近 0.3 米，用时 2 秒」".format(
                        where, "/".join(sorted(fams)))})


#: CT10 光影四件套：色温 K 与光比 1:n 缺失=error，光位/光质缺失=warning
def _ct10_light(value, ref, out, where):
    text = _s(value).strip()
    if not text:
        return
    hard, soft = [], []
    if not LIGHT_K.search(text):
        hard.append("色温(K)")
    if not LIGHT_RATIO.search(text):
        hard.append("光比(1:n)")
    if not any(w in text for w in LIGHT_POS):
        soft.append("光位")
    if not any(w in text for w in LIGHT_QUAL):
        soft.append("光质")
    if hard:
        out.append({"level": "error", "code": "CT10", "ref": ref,
                    "msg": "{}缺 {}——光比与色温不给数，模型就是随机打光｜现文：{}".format(
                        where, "/".join(hard), text[:36])})
    if soft:
        out.append({"level": "warning", "code": "CT10", "ref": ref,
                    "msg": "{}缺 {}——建议按 42-打光库 的四件套补齐（光位＋光质＋色温＋光比）｜现文：{}".format(
                        where, "/".join(soft), text[:36])})


#: CT11 首段取样：一组里 0—2 秒覆盖到的镜头文本（含跨过 2 秒的那一镜）。
#: 钩子只在这一段里判——全片扫等于「只要片里出现一个『撞』字就过」，测过了，太松。
def _head_text(group, seconds=2.0):
    """取一组/一个单元开头 N 秒的文本。分镜层镜头用 duration，关键词层用 dur。"""
    buf, t = [], 0.0
    for sh in (group.get("shots") or []):
        if t >= seconds:
            break
        buf.append(_s(sh))
        try:
            t += float(sh.get("dur") or sh.get("duration") or 0)
        except (TypeError, ValueError):
            break
    return " ".join(buf)


#: CT11 钩子：钩子是首镜的画面/音效，不是运镜
def _ct11_hook(value, ref, out, where):
    text = _s(value).strip()
    if not text:
        return
    for w in HOOK_IN_MOVE:
        if w in text:
            out.append({"level": "error", "code": "CT11", "ref": ref,
                        "msg": "{}里出现钩子写法『{}』——钩子要落在首镜的画面主体/动作/音效上，不写进运镜字段（48 §6）".format(
                            where, w)})
            break


#: CT12 英制单位：参数里给米，别给英尺
def _ct12_units(value, ref, out, where):
    text = _s(value).strip()
    if not text:
        return
    m = IMPERIAL.search(text)
    if m:
        out.append({"level": "error", "code": "CT12", "ref": ref,
                    "msg": "{}里出现英制单位『{}』——换成米/厘米（1ft≈0.3 米）".format(where, m.group(0).strip())})


#: CT13 台词之后留的余量：台词说完到切点，至少 0.6 秒（49 §三）
TAIL_MIN = 0.6
SPEECH_CPS = 2.25

_PUNCT = "，。！？、；：…—－·「」『』“”‘’（）《》〈〉,.!?;:'\"()"


def _speech_chars(text):
    """数台词字数：去掉「角色（语气，语速）：」前缀、标点与空白，剩下的才是占时间的字。"""
    body = _s(text)
    for sep in ("：", ":"):
        if sep in body:
            body = body.rsplit(sep, 1)[1]
            break
    return len([c for c in body if c not in _PUNCT and not c.isspace()])


#: CT13/CT14/CT15：节奏与可读性（49），只给 warning——节奏是判断，不是硬门
def _ct13_tail(gid, group, out):
    """台词说完到这一组结束，至少留 0.6 秒余量（49 §三）。

    按组算，不按镜算：一组就是一次生成、一个切点；台词经常跨镜说完，
    拿单镜时长去卡台词会全员误报。
    """
    speech = 0
    for s in (group.get("shots") or []):
        speech += _speech_chars(s.get("dialogue"))
    if not speech:
        return
    try:
        dur = float(group.get("duration") or group.get("dur") or 0)
    except (TypeError, ValueError):
        return
    if dur <= 0:
        return
    need = speech / SPEECH_CPS
    gap = dur - need
    if gap < TAIL_MIN:
        out.append({"level": "warning", "code": "CT13", "ref": gid,
                    "msg": "台词共 {} 字约 {:.1f} 秒，这一组只有 {:.1f} 秒——台词后至少留 {:.1f} 秒余量（49 §三）".format(
                        speech, need, dur, TAIL_MIN)})


def _ct14_axes(groups, out):
    """一集里的运动轴种类：少于 4 种就是「一个镜头运动走到底」（49 §五）。"""
    if len(groups or []) < 5:
        return
    fams = set()
    for g in groups:
        for s in (g.get("shots") or []):
            fams |= _move_families(_s(s.get("cam")))
    if len(fams) < 4:
        out.append({"level": "warning", "code": "CT14", "ref": "-",
                    "msg": "全集运镜只有 {} 种运动轴（{}）——49 §五 要求 ≥4 种，另给一个招牌镜".format(
                        len(fams), "/".join(sorted(fams)) or "固定")})


def _ct15_same_dur(items, key, ref_of, out, where):
    """相邻 N 个时长完全一样 → 一个速度走到底（49 §二 D）。"""
    durs = []
    for it in items or []:
        try:
            durs.append(round(float(it.get(key) or 0), 2))
        except (TypeError, ValueError):
            durs.append(0.0)
    run = 1
    for k in range(1, len(durs)):
        if durs[k] > 0 and durs[k] == durs[k - 1]:
            run += 1
            if run == 3:
                out.append({"level": "warning", "code": "CT15", "ref": ref_of(items[k]),
                            "msg": "{}连续 3 个以上时长都是 {} 秒——49 §二 要求快慢交替，别一个速度走到底".format(
                                where, durs[k])})
                return
        else:
            run = 1


# ---------------------------------------------------------------- 分镜层

def check_storyboard(data):
    """分镜层校验：CT01/CT03/CT05/CT06/CT07/CT08/CT11/CT12/CT15。返回列表。"""
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
            _ct12_units(cam + " " + con, sid, out, "机位与画面")
            for w in HOOK_IN_MOVE:
                if w in cam:
                    out.append({"level": "warning", "code": "CT11", "ref": sid,
                                "msg": "『{}』是手法定式，写进『画面内容』，不写进机位列（46 §6）".format(w)})
                    break

    units = data.get("units") or []
    if units:
        uid0 = _s(units[0].get("id")) or "U01"
        head = _head_text(units[0], 2.0)
        if head and not any(w in head for w in HOOK_FEATURE):
            out.append({"level": "warning", "code": "CT11", "ref": uid0,
                        "msg": "首单元前 2 秒没有钩子特征（微距/黑场炸光/高速入画/撞/摔/耳光…）"
                               "——46 要求第一个画面就有异常，首镜压到 ≤2 秒"})
    _ct15_same_dur(units, "duration", lambda u: _s(u.get("id")) or "?", out, "单元")
    return out


# ---------------------------------------------------------------- 关键词层

def check_keyword(data):
    """关键词层校验：CT01/CT02/CT03/CT05/CT06/CT07/CT08/CT09/CT10/CT11/CT12。返回列表。"""
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

        # CT09/CT10/CT11/CT12：运镜量化、光影四件套、钩子落位、单位
        _ct09_move(p.get("movement"), gid, out, "运镜")
        _ct10_light(p.get("light"), gid, out, "光影")
        _ct11_hook(p.get("movement"), gid, out, "运镜")
        _ct12_units(_s(p), gid, out, "参数")

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
            _ct12_units(cam + " " + pic, sid, out, "分镜文本")

        _check_ref(p.get("reference"), "CT06", gid, out, "组 {}".format(gid))
        _ct13_tail(gid, g, out)

    # CT14 全集运动轴太少 / CT15 相邻组时长雷同（49 §二、§五）
    _ct14_axes(data.get("groups"), out)
    _ct15_same_dur(data.get("groups"), "duration",
                   lambda g: _s(g.get("no")) or "?", out, "组")

    # CT11 首组前 2 秒：钩子要落在第一个画面里，不是落在整片任何角落
    groups = data.get("groups") or []
    if groups:
        head = _head_text(groups[0], 2.0)
        if head and not any(w in head for w in HOOK_FEATURE):
            out.append({"level": "warning", "code": "CT11", "ref": groups[0].get("no") or "-",
                        "msg": "首组前 2 秒没有钩子特征（黑场/微距/移焦/静默/高速入画/撞/摔/耳光…）——48 要求第一个画面就有异常"})
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
