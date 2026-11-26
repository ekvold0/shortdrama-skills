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

    图像资产层（V2.0 新增，依据需求文档 v2.0 §GT-01，口径已与使用方敲定）：
    CT16 跨段记录镜头           —— 存在段边界时，段末最后一格不是记录镜头（warning）
    CT17 图片编号表             —— [图片N] 无 refs 项（error）；refs 项没被引用（warning）；
                                   图片数超档位上限、音频单独使用、组时长低于档位下限、
                                   单条参考视频/音频超出档位区间（error）。时长口径
                                   （使用方 2026-11-26 平台侧实测）：三档**组下限都是 4 秒**；
                                   2.0 组 4–15 秒、单条参考 4–15 秒；2.5 flash 与 2.5 标准版
                                   组 4–30 秒、单条参考 4–30 秒
    CT18 色温漂移               —— 关键词色温与色卡差 > 800K（warning）
    CT19 打斗组受力与升格        —— 缺受力反馈/重心恢复、单组升格 ≥2 次（warning）
    CT20 层次三账               —— 连续 3 个单元前景/中景/背景全空（warning）
    CT21 反向第 0 段            —— 反向提示词缺「禁止字幕/文字」「禁止 BGM/配乐」（error）
    CT22 资产齐备               —— 角色卡三类拆分/道具卡/色卡/站位草图缺项（error）
    CT23 参考链代际             —— 身份链被传递、空间链未挂原始场景图、链深 > 1（error）
    CT24 背景元素依据           —— 缺字段或指向不存在的场景图（error）
    CT17 分镜图引用         —— 分镜图占一张图片名额；只在 >15 秒的组里用；2.0 里不许当单镜参考；[图锚 KB_x] 必须能落到 refs（V2.4–V2.12）
CT25 分镜图缺失/覆盖率        —— 有编号无路径、文件不存在、低于 1/3 或关键单元缺图（error）
    CT26 短镜落地方式             —— <4 秒的镜头没写 landing（并进/后期/砍掉，默认并进）（warning）
    CT27 多镜组提示词            —— 单组 >6 镜、镜数与 prompt 的「镜N：」不符、镜里用「两人/三人」代替角色名（warning）（V2.5）

    CT28 风格包                   —— style_pack 不在三套枚举里（error）、出了分镜图却没写风格包（warning）（V2.6）
CT29 原生配音资产 —— 抽出来的配音要登记、挂版本、可被追踪（V2.8）
CT31 引用角色 —— 首帧唯一、分镜图可兼首帧、资产图 role 走枚举（V2.10–V2.12）
CT32 提示词字数 —— 软 900／硬 1400，超了多半被截断（V2.11）
CT33 数据契约 —— schema 字段、meta 键名白名单、资产 id 唯一（V2.11）
CT30 声线锚点 —— 台词角色的音色要在锚点里写、人声层要复写（V2.9）
    CT16/CT20 只在分镜层；CT17/CT18/CT19/CT21/CT24 只在关键词层；
    CT22/CT23/CT25 在 check_assets（资产门禁，由 gate.py 或 verify.py 显式调用）。
    这些规则一律「字段不存在就跳过」——旧数据没进入图像资产层时不报，避免假红。

    分层说明：CT09/CT10 只作用于关键词层（keywords 的 params/movement/light/shots），
    分镜层按 45 §4「分镜层禁量化」不查运镜量化与光影数值。
    CT11 两层都查但口径不同：关键词层看 groups[0] 的 0–2 秒，分镜层看 units[0] 的 0–2 秒
    （镜头时长字段 keyword 层叫 dur、storyboard 层叫 duration，_head_text 两者都认）。
    CT13 只在关键词层（台词挂在镜头 dialogue 上）；CT14 只在关键词层（movement 是参数槽）；
    CT15 两层都查（关键词看 groups[].duration，分镜看 units[].duration）。
"""

import difflib
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
#: 技法库条目引用：附件6 通用第5条【反应镜头节奏】…（老流程一直这么写）
TECH_REF = re.compile(r"附件\s*\d+[^\n]{0,12}第\s*\d+\s*条【[^】]+】")
#: 辅对标标注：（辅）/(辅)/（辅助）/aux
AUX_REF = re.compile(r"[（(]\s*辅[助]?\s*[）)]|\(\s*aux\s*\)|aux", re.I)

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

META_KEYS = ("title", "episode", "ep", "mode", "aspect", "resolution", "target_seconds",
             "era", "weather", "tier", "model", "version", "style_pack", "project",
             "source", "chars_per_sec", "notes", "date", "author", "based_on",
             "source_script", "source_storyboard", "default_model", "target_total_sec")
PROMPT_LIMITS = {"2.0": (3000, 4000), "2.5-flash": (7500, 10000), "2.5": (7500, 10000)}
# 平台实测（用户 2026-11-26 给）：2.0 上限 4000 字，2.5（含 flash）10000 字以内。
# 软预算取上限的 3/4，过了就提醒拆组；认不出档位按 2.0 算（保守）。
PROMPT_SOFT, PROMPT_HARD = PROMPT_LIMITS["2.0"]
SCHEMA_KNOWN = ("sbdata/1", "kwdata/1")


def meta_typos(data):
    """V2.11：只报「长得像拼错」的 meta 键。拼错 episode 会静默变成 01 集。"""
    meta = data.get("meta") or {}
    if not isinstance(meta, dict):
        return []
    out = []
    for k in meta:
        if k in META_KEYS:
            continue
        # cutoff 0.8：epsoide→episode 会命中；author→weather 这种乱配不会冒出来
        near = difflib.get_close_matches(k, META_KEYS, n=1, cutoff=0.8)
        if not near:
            continue
        out.append("meta.%s 像 `%s` 的笔误——它会被忽略，缺的值会静默走默认（V2.11）" % (k, near[0]))
    return out


def _prompt_limits(g):
    """V2.12：按档位取提示词字数区间（软, 硬）。2.0 = 4000 字，2.5/flash = 10000 字。"""
    tier = _tier_of(g)
    tl = (tier or "").lower()
    if "2.5" in tl or "flash" in tl:
        return PROMPT_LIMITS["2.5"]
    return PROMPT_LIMITS["2.0"]


def _ct32_prompt(gid, g, out):
    """V2.12：提示词字数预算，按档位判。超硬线多半被平台截断，表现是后半截镜头不生成。"""
    txt = _s(g.get("prompt"))
    if not txt:
        return
    soft, hard = _prompt_limits(g)
    n = len(re.sub(r"\s", "", txt))
    tier = _tier_of(g) or "2.0"
    if n > hard:
        out.append({"level": "warning", "code": "CT32", "ref": gid,
                    "msg": "提示词 %d 字，超过 %s 的平台上限 %d 字（软预算 %d）——超出部分会被截断，"
                           "表现是后半截镜头不生成；拆成两组，或把镜头描述压短" % (
                               n, tier, hard, soft)})
    elif n > soft:
        out.append({"level": "warning", "code": "CT32", "ref": gid,
                    "msg": "提示词 %d 字，过了 %s 的软预算 %d（平台上限 %d）——还能发，"
                           "但长组先留意后半截镜头有没有丢" % (n, tier, soft, hard)})


def _dup_ids(assets, out):
    """V2.11：同一资产桶里 id 重复 → error（纯笔误，没有正当场景）。"""
    for bucket in ("scenes", "boards", "items", "audios", "characters", "staging"):
        rows = assets.get(bucket)
        if not isinstance(rows, list):
            continue
        seen = {}
        for r in rows:
            if not isinstance(r, dict):
                continue
            i = _s(r.get("id"))
            if not i:
                continue
            if i in seen:
                out.append({"level": "error", "code": "CT33", "ref": bucket,
                            "msg": "%s 里 id「%s」出现了两次——引用会指向不确定的那一张，改名或加版本号" % (
                                bucket, i)})
            seen[i] = 1


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
    # 技法库条目（附件 N … 第 M 条【技法名】）也是合法引用，与《片名》年份二选一
    if TECH_REF.search(text) and not REF_PAT.search(text):
        return
    found = REF_PAT.findall(text)
    if not found:
        out.append({"level": "error", "code": code, "ref": ref,
                    "msg": "{}的参考电影应写成《片名》年份，实际为：{}".format(where, text[:40])})
        return
    if len(found) > 1:
        # V2.1 口径：1 部主对标 + 最多 2 部辅对标（辅只提供节奏/调度，不参与风格合成）
        if len(found) > 3:
            out.append({"level": "warning", "code": code, "ref": ref,
                        "msg": "{}挂了 {} 部参考影片，超过 1 主 + 2 辅上限——再多模型会把风格平均成四不像".format(
                            where, len(found))})
        elif not AUX_REF.search(text):
            out.append({"level": "warning", "code": code, "ref": ref,
                        "msg": "{}挂了 {} 部参考影片：第 1 部算主对标，其余视为辅对标，建议显式标「（辅）」".format(
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
def _ct10_light(value, ref, out, where, extra=""):
    text = _s(value).strip()
    if not text:
        return
    # 色温常写进「色彩参数」段（主光 5600K 偏青/钠灯 3000K），合并判，避免假红
    scope = text + " " + _s(extra)
    hard, soft = [], []
    if not LIGHT_K.search(scope):
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
    # CT16 跨段记录镜头 / CT20 层次三账（V2.0）
    _ct16_record(units, out)
    _ct26_short(units, out)
    _ct27_multishot(units, out)
    _ct20_layers(units, out)
    return out


# ---------------------------------------------------------------- 关键词层

def check_keyword(data):
    """关键词层校验：CT01/CT02/CT03/CT05/CT06/CT07/CT08/CT09/CT10/CT11/CT12 + CT17/CT18/CT19/CT21/CT24。返回列表。"""
    out = []
    # 色卡与场景图索引（CT18 / CT24 的依据表）
    cards = {}
    for c in (data.get("color_cards") or []):
        if isinstance(c, dict) and _s(c.get("id")):
            cards[_s(c.get("id"))] = c
    scene_ids = set()
    for s in (data.get("scenes") or []):
        if isinstance(s, dict) and _s(s.get("id")):
            scene_ids.add(_s(s.get("id")))
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
        _ct10_light(p.get("light"), gid, out, "光影", p.get("color"))
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

        # V2.0 图像资产层
        _ct17_refs(gid, g, out)
        _ct31_roles(gid, g, out)  # V2.10
        _ct32_prompt(gid, g, out)  # V2.11
        _ct27_multishot([g], out)
        _ct18_color(gid, g, cards, out)
        _ct19_fight(gid, g, out)
        _ct21_reverse(gid, g, out)
        _ct24_bg(gid, g, scene_ids, out)

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
    _ct30_voice(data, out)
    return out


# ------------------------------------------------- 图像资产层（CT16–CT25）

#: CT16 记录镜头定式（需求文档附录 B.1，逐条对应「24mm／大全景／固定／俯拍／静止 1 秒」）。
STILL_HINT = ("静止一秒", "静止 1 秒", "强制静止", "完全静止", "静止不动", "定格一秒")
#: CT17 正文里的图片引用写法。
PIC_REF = re.compile(r"[\[【]\s*图片\s*(\d+)\s*[\]】]")

#: CT18 正文里出现的十六进制色值。
HEX_RE = re.compile(r"#[0-9a-fA-F]{6}\b")
#: CT19 受力反馈 / 重心恢复 / 升格。
FEEDBACK_HIT = ("受力", "反馈", "被打", "吃痛", "震")
RECOVER_HIT = ("重心", "踉跄", "卸力", "稳住", "找回平衡", "恢复站姿")
SLOWMO_HIT = ("升格", "慢动作", "slow motion", "slow-mo", "120fps", "240fps", "高帧")
FIGHT_HIT = ("武打", "打斗", "动作戏", "决斗", "格斗", "对招", "厮杀")
#: CT21 反向提示词第 0 段（需求文档 KW-05）。
NO_TEXT_HIT = ("字幕", "文字叠加", "文字", "水印")
NO_BGM_HIT = ("bgm", "BGM", "配乐", "背景音乐")


def _image_limit(tier):
    """CT17 图片上限随档位（需求文档 §FL-04，使用方 2026-11-26 确认数字）。

    Seedance 2.0 系列 9 图 / 2.5 flash 10 图 / 2.5 标准版 30 图；未写档位返回 0（不校验）。
    """
    t = (tier or "").lower()
    if not t:
        return 0
    if "flash" in t and "2.5" in t:
        return 10
    if "2.5" in t:
        return 30
    if "2.0" in t or "seedance" in t or t.strip() in ("2", "2.0"):
        return 9
    return 0


def _tier_of(g):
    p = g.get("params") or {}
    for v in (g.get("model"), g.get("tier"), g.get("model_tier"), p.get("model"), p.get("tier")):
        if _s(v).strip():
            return _s(v)
    return ""


def _min_group_sec(tier):
    """CT17 组时长下限随档位（使用方 2026-11-26 平台侧实测后的终版）。

    三档的本组生成都是 4–30／4–15 秒区间，**下限一律 4 秒**——没有哪个档位能生成 2–3 秒的组。
    """
    t = (tier or "").lower()
    if not t:
        return 0
    if "2.5" in t or "2.0" in t or "seedance" in t:
        return 4
    return 0


def _ref_sec_range(tier):
    """单条参考视频/音频的合法秒数区间（三档都是 4–30／4–15，下限 4）。"""
    t = (tier or "").lower()
    if "2.5" in t:
        return (4, 30)
    if "2.0" in t or "seedance" in t:
        return (4, 15)
    return None


def _is_record_shot(sh):
    """段末记录镜头：24mm 广角 + 大全景 + 固定机位 + 俯拍 + 人物道具强制静止一秒。

    缺一条就不算——这一格的用途是「截得出干净锚点图」，少一条截出来就是糊的。
    """
    if sh.get("record") is True or sh.get("record_shot") is True:
        return True
    blob = " ".join(_s(sh.get(k)) for k in ("camera", "content", "note", "cam", "pic"))
    ok_lens = bool(re.search(r"2[0-9]\s*(mm|毫米)", blob, re.I))
    ok_scale = "大全景" in blob or "全景" in blob
    ok_fix = "固定" in blob
    ok_down = "俯拍" in blob or "俯视" in blob or "高空" in blob
    ok_still = any(w in blob for w in STILL_HINT)
    return ok_lens and ok_scale and ok_fix and ok_down and ok_still


def _ct16_record(units, out):
    """CT16 存在段边界时，段末最后一格必须是记录镜头（使用方定：只在跨段必做）。"""
    order = []
    by_seg = {}
    for u in units:
        seg = _s(u.get("segment")) or _s(u.get("seg")) or _s(u.get("act"))
        if not seg:
            continue
        if not order or order[-1] != seg:
            order.append(seg)
        by_seg.setdefault(seg, []).append(u)
    if len(order) < 2:
        return
    for i in range(1, len(order)):
        prev = order[i - 1]
        tail = by_seg[prev][-1]
        shots = tail.get("shots") or []
        if not any(_is_record_shot(sh) for sh in shots):
            out.append({"level": "warning", "code": "CT16",
                        "ref": _s(tail.get("id")) or prev,
                        "msg": "第 {} 段末那格不是记录镜头——跨段衔接处必须收 24mm 大全景俯拍固定、"
                               "人物道具强制静止一秒，否则下一段的人会漂（附录 B.1）".format(prev)})


# 风格包：整集唯一，分镜图/视频提示词的第一句都从这里取（V2.8 单一真值源）
# label 给人看，prefix 直接抄进提示词第 0 段
STYLE_PACKS = {
    "modern_live": {
        "label": "现代真人写实（35mm 电影镜头 · 实景）",
        "prefix": ("电影剧组的现场剧照。像剧组摄影师在实景里用中画幅数码相机和 35mm 电影镜头拍的："
                   "高分辨率但成像柔和，皮肤与衣料按真实光线自然呈现，整体干净通透；"
                   "没有后期修图，也没有刻意强化任何细节。"),
    },
    "ancient_period": {
        "label": "古装年代（40mm · 织物木石旧痕）",
        "prefix": ("电影剧组的现场剧照，年代戏实拍。像剧组摄影师在棚内实景里用中画幅数码相机和 40mm 镜头拍的："
                   "高分辨率但成像柔和，织物纹理、木石旧痕按真实光线自然呈现，整体干净通透；"
                   "没有后期修图，也没有刻意强化任何细节。"),
    },
    "3d_stylized": {
        "label": "3D 漫风格化（UE5 · Nanite/Lumen）",
        "prefix": ("32mm胶片质感，虚幻引擎5.3，Nanite虚拟几何体，lumen全局光照，光线追踪全局光照，全局反射，路径追踪，"
                   "富士REALA 500D RED Komodo，HDR 10-BIT色深，宽广动态范围，电影级风格化写实三维CGI。"),
    },
}


def style_prefix(value):
    """把 style_pack（或中文别名）换成可直接抄进提示词的第一句；认不出返回空串。"""
    raw, pack = _style_pack({"style_pack": value})
    if pack:
        return STYLE_PACKS[pack]["prefix"]
    v = _s(value).strip().lower()
    return STYLE_PACKS[v]["prefix"] if v in STYLE_PACKS else ""


def style_label(value):
    raw, pack = _style_pack({"style_pack": value})
    if pack:
        return STYLE_PACKS[pack]["label"]
    v = _s(value).strip().lower()
    return STYLE_PACKS[v]["label"] if v in STYLE_PACKS else ""
AUDIO_KINDS = ("audio", "音频", "voice", "旁白", "配音", "music", "bgm", "soundtrack")


STYLE_PACK_ALIAS = {
    "现代": "modern_live", "真人": "modern_live", "写实": "modern_live",
    "现代真人": "modern_live", "modern": "modern_live", "live": "modern_live",
    "古装": "ancient_period", "年代": "ancient_period", "古装年代": "ancient_period",
    "ancient": "ancient_period", "period": "ancient_period",
    "3d": "3d_stylized", "3d漫": "3d_stylized", "漫": "3d_stylized",
    "风格化": "3d_stylized", "ue5": "3d_stylized", "stylized": "3d_stylized",
}


def _style_pack(data):
    v = _s(data.get("style_pack") or (data.get("meta") or {}).get("style_pack")).strip().lower()
    if not v:
        return "", ""
    return v, STYLE_PACK_ALIAS.get(v, v if v in STYLE_PACKS else "")


def _ct28_style(data, assets, out):
    """CT28 风格包（V2.6）：整集只能有一套风格前缀，写 data.style_pack。

    - 写了但不在三套枚举里 → error；
    - 出了分镜图（boards 非空）却没有 style_pack → warning（风格前缀没有真值源）。
    """
    raw, pack = _style_pack(data)
    boards = assets.get("boards") or []
    if raw and not pack:
        out.append({"level": "error", "code": "CT28", "ref": "style_pack",
                    "msg": "style_pack 写了「{}」，只能是 modern_live／ancient_period／3d_stylized 之一".format(raw)})
    elif not raw and isinstance(boards, list) and boards:
        out.append({"level": "warning", "code": "CT28", "ref": "style_pack",
                    "msg": "出了分镜图却没写 data.style_pack——风格前缀要有真值源，"
                           "整集只能选一套（modern_live／ancient_period／3d_stylized）"})


def _ct27_multishot(items, out):
    """CT27 多镜组提示词（V2.5）：一镜一句、单组最多 6 镜、镜里点名角色。

    三条都只报 warning（写法问题，不是硬错）：
      1) 单元/组内镜头数 > MULTI_MAX(6) —— 拆成两组；
      2) 写了多镜但 prompt 里没有「镜1：」这类标记，或标记数与镜头数不一致；
      3) 任一镜的画面描述里用「两人/三人/他们/大家」代替角色名。
    字段不存在就跳过（旧数据不报假红）。
    """

    # prompt 还没写（分镜阶段）不算违规，只在写了的 prompt 上判
    if all(not (it.get("prompt") or "").strip() for it in items):
        return
    if not isinstance(items, list):
        return
    for it in items:
        if not isinstance(it, dict):
            continue
        uid = (_s(it.get("id")) or _s(it.get("no")) or _s(it.get("unit")) or "?")
        shots = it.get("shots")
        shots = [x for x in shots if isinstance(x, dict)] if isinstance(shots, list) else []
        prompt = _s(it.get("prompt"))
        marks = SHOT_MARK_RE.findall(prompt)
        if len(shots) > MULTI_MAX:
            out.append({"level": "warning", "code": "CT27", "ref": uid,
                        "msg": "本单元 {} 镜，超过单组 {} 镜上限——拆成两组，每组 ≤{} 镜".format(
                            len(shots), MULTI_MAX, MULTI_MAX)})
        if len(shots) >= 2:
            if not marks:
                out.append({"level": "warning", "code": "CT27", "ref": uid,
                            "msg": "本单元 {} 镜，但 prompt 里没有「镜1：」这类分镜标记——"
                                   "一段 prompt 要自带分镜，否则模型会自行合并".format(len(shots))})
            elif len(marks) != len(shots):
                out.append({"level": "warning", "code": "CT27", "ref": uid,
                            "msg": "prompt 里有 {} 个「镜N：」标记，但单元写了 {} 个镜头——两边要一致".format(
                                len(marks), len(shots))})
        for n, sh in enumerate(shots, 1):
            blob = " ".join([_s(sh.get("pic")), _s(sh.get("content")),
                             _s(sh.get("act")), _s(sh.get("action"))])
            m = GROUP_PRONOUN_RE.search(blob)
            if m:
                out.append({"level": "warning", "code": "CT27",
                            "ref": "{}#{}".format(uid, _s(sh.get("id")) or n),
                            "msg": "镜 {} 用了「{}」——镜里角色必须点名（写「谢听和教头」，不写「两人」）".format(
                                n, m.group(0))})


def _ct20_layers(units, out):
    """CT20 连续 3 个单元层次三账全空（只对写了 layers 的数据生效）。"""
    streak = 0
    for u in units:
        if "layers" not in u:
            streak = 0
            continue
        ls = u.get("layers") or {}
        empty = not any(_s(ls.get(k)).strip() for k in ("fore", "mid", "back", "前景", "中景", "背景"))
        streak = streak + 1 if empty else 0
        if streak >= 3:
            out.append({"level": "warning", "code": "CT20", "ref": _s(u.get("id")) or "?",
                        "msg": "连续 {} 个单元的层次三账（前景/中景/背景）全空——画面会糊成一张纸".format(streak)})
            streak = 0


#: CT26 短镜落地：<4 秒的镜头必须说清怎么落地，默认并进
LANDING_ALIAS = {"并进": "merge", "并入": "merge", "merge": "merge", "merge_in": "merge",
                 "后期": "post", "post": "post", "after": "post",
                 "砍掉": "cut", "删": "cut", "删除": "cut", "cut": "cut"}


#: 分镜图（关键帧）作为参考时的写法：占一张图片名额、不参与身份链；可以兼首帧（V2.12）
# ---- V2.5 多镜组与图锚 ----
MULTI_MAX = 6                                   # 单组最多 6 镜（用户 2026-11-26 定）
SHOT_MARK_RE = re.compile(
    r"镜\s*([0-9０-９一二三四五六七八九十]+)\s*(?:[（(][^）)]{0,24}[）)])?\s*[：:．.、]")
GROUP_PRONOUN_RE = re.compile(r"两人|二人|仨人|三人|四人|数人|众人|一群人|他们|她们|大家")
IMG_ANCHOR_RE = re.compile(r"\[图锚\s*([A-Za-z0-9_\-]+)\s*\]")

BOARD_KINDS = ("board", "boards", "分镜图", "关键帧", "kb", "kb_", "keyframe")
BOARD_ROLES = ("first_frame", "firstframe", "首帧", "生成起点", "生成输入", "起点",
               "shot_ref", "shotref", "镜头参考", "单镜参考", "单镜")
#: 2.0 里不许把分镜图当单镜画面参考（使用方 2026-11-26 定）
SHOT_REF_ROLES = ("shot_ref", "shotref", "镜头参考", "单镜参考", "单镜")


ASSET_ROLES = ("look_ref", "lookref", "造型参考", "长相参考",
               "cloth_ref", "clothref", "服装参考", "服装卡",
               "item_ref", "itemref", "道具参考", "道具卡",
               "scene_ref", "sceneref", "场景参考", "场景图")
FIRST_FRAME_ROLES = ("first_frame", "firstframe", "首帧", "生成起点", "生成输入", "起点")


def _is_board_ref(r):
    # 是不是分镜图（关键帧）。V2.10：只认 kind，不看 role。
    # 以前只要 role 里带 first_frame 就算分镜图，后果是角色卡标了
    # role: first_frame（意思是「这张当首帧」）会被当成不占名额的分镜图，
    # 名额就少算一张。首帧是分镜图的角色，不是分镜图的定义。
    kind = (_s(r.get("kind")) or _s(r.get("type"))).strip().lower()
    if kind:
        return any(t in kind for t in BOARD_KINDS)
    role = (_s(r.get("role")) or _s(r.get("as"))).strip().lower()
    return any(t in role for t in BOARD_KINDS)


def _landing(sh):
    raw = _s(sh.get("landing")) or _s(sh.get("fallback"))
    return LANDING_ALIAS.get(raw.strip().lower(), "") or LANDING_ALIAS.get(raw.strip(), "")


def _ct26_short(units, out):
    """CT26 短镜落地：<4 秒的镜头要么标并进/后期/砍掉，要么人不知道该拿它怎么办。"""
    for u in units:
        for sh in (u.get("shots") or []):
            try:
                d = float(sh.get("duration") or sh.get("dur") or 0)
            except (TypeError, ValueError):
                continue
            if not d:
                continue
            sid = _s(sh.get("id")) or "?"
            kind = _landing(sh)
            if d < 4.0:
                # 短镜并进相邻单元是常态，不标就是默认并进，不报；只报自相矛盾的写法
                if kind == "cut":
                    out.append({"level": "warning", "code": "CT26", "ref": sid,
                                "msg": "短镜 {} 秒标了砍掉却还留在 shots 里——生成时会被拍出来".format("%g" % d)})
            elif kind in ("post", "cut"):
                out.append({"level": "warning", "code": "CT26", "ref": sid,
                            "msg": "{} 秒的镜头标了{}——超过 4 秒的镜头一般在组内生成，不用走后处理".format(
                                "%g" % d, "后期" if kind == "post" else "砍掉")})


def _ct17_refs(gid, g, out):
    """CT17 图片编号表：正文 [图片N] ↔ refs 双向对齐，并盯档位图片上限、时长下限与音频单独使用。"""
    p = g.get("params") or {}
    body = " ".join([_s(v) for v in p.values()] +
                    [_s(g.get("makeup")), _s(g.get("shots")), _s(g.get("prompt")), _s(g.get("scene"))])
    used = set(int(n) for n in PIC_REF.findall(body))
    refs = g.get("refs")
    tier = _tier_of(g)
    floor = _min_group_sec(tier)
    try:
        gdur = float(g.get("duration") or g.get("dur") or 0)
    except (TypeError, ValueError):
        gdur = 0
    if floor and gdur and gdur < floor:
        out.append({"level": "error", "code": "CT17", "ref": gid,
                    "msg": "本组 {} 秒，低于 {} 的组时长下限 {} 秒——平台不接这么短的组，"
                           "拆短镜的做法见 references/40-画面参数.md §短镜头".format(
                               ("%g" % gdur), tier, floor)})
    if not refs:
        if used:
            out.append({"level": "error", "code": "CT17", "ref": gid,
                        "msg": "正文写了 {} 个 [图片N]，但 refs 整段缺失——编号必须能追到具体文件".format(len(used))})
            return
        mode = (_s(g.get("ref_mode")) or _s(g.get("path_mode"))).strip().lower()
        if mode in ("text", "纯文字", "pure_text", "prompt_only"):
            return
        if not (("refs" in g) or _tier_of(g)):
            return  # 旧数据没有 refs 也没有档位，不报假红
        out.append({"level": "warning", "code": "CT17", "ref": gid,
                    "msg": "本组既没 refs 也没 [图片N]——纯文字路径能出片，但长相与场景全靠提示词兜。"
                           "若这是刻意的，请在组头写 ref_mode: 『text』；否则至少挂一张脸卡和一张场景图"})
        return
    have = {}
    for i, r in enumerate(refs or [], 1):
        if not isinstance(r, dict):
            continue
        no = r.get("no", i)
        try:
            no = int(no)
        except (TypeError, ValueError):
            no = i
        have[no] = r
        if not _s(r.get("file")).strip():
            out.append({"level": "error", "code": "CT17", "ref": gid,
                        "msg": "refs 第 {} 项缺 file——编号表必须落到文件名".format(no)})
        rng = _ref_sec_range(tier)
        rsec = r.get("sec", r.get("duration", r.get("dur")))
        rkind = (_s(r.get("kind")) or _s(r.get("type"))).lower()
        if rng and rsec is not None and rkind in ("video", "视频", "audio", "音频", "voice", "mp3", "mp4"):
            try:
                rsec = float(rsec)
            except (TypeError, ValueError):
                rsec = 0
            if rsec and not (rng[0] <= rsec <= rng[1]):
                out.append({"level": "error", "code": "CT17", "ref": gid,
                            "msg": "refs 第 {} 项参考时长 {} 秒，超出 {} 的单条参考区间 {}-{} 秒".format(
                                no, ("%g" % rsec), tier, rng[0], rng[1])})
    tier = _tier_of(g)
    limit = _image_limit(tier)
    boards = [r for r in have.values() if _is_board_ref(r)]
    pics = len(have)      # V2.12：分镜图也占图片名额（用户平台实测）
    for no, r in have.items():
        fname = _s(r.get("file")) or _s(r.get("path"))
        if "KB_" in fname.upper() and not _is_board_ref(r):
            out.append({"level": "warning", "code": "CT17", "ref": gid,
                        "msg": "refs 第 {} 项文件名像分镜图（{}），但 kind 没标 board——"
                               "它照样占一张图片名额，标错会让预算与实际不一致（V2.12）".format(
                                   no, fname[:28])})
    if limit and pics > limit:
        out.append({"level": "error", "code": "CT17", "ref": gid,
                    "msg": "refs 有 {} 张图（含分镜图），但 {} 单次最多 {} 张——减图或换档位".format(
                        pics, tier, limit)})
    if boards and tier:
        tl = tier.lower()
        is20 = ("2.0" in tl or "seedance" in tl) and "2.5" not in tl
        if is20:
            for r in boards:
                role = (_s(r.get("role")) or _s(r.get("as"))).strip().lower()
                if any(t in role for t in SHOT_REF_ROLES):
                    out.append({"level": "warning", "code": "CT17", "ref": gid,
                                "msg": "{} 不按「单个镜头画面参考」用分镜图——分镜图在 2.0 里是整组的生成起点；"
                                       "要给单镜画面参考请用 2.5 flash 或 2.5 标准版".format(tier)})
                    break
    if boards and gdur and gdur <= 15:
        out.append({"level": "warning", "code": "CT17", "ref": gid,
                    "msg": "本组 {} 秒（≤15 秒走 2.0），不需要分镜图——分镜图只在 >15 秒的 2.5 组里"
                           "当画面参考（V2.6）".format("%g" % gdur)})
    kinds = [_s(r.get("kind")).lower() or _s(r.get("type")).lower() for r in have.values()]
    if kinds and all(k in ("audio", "音频", "voice") for k in kinds if k):
        if tier and "2.5" not in tier.lower():
            out.append({"level": "error", "code": "CT17", "ref": gid,
                        "msg": "只挂了音频参考——{} 的音频不能单独使用，必须配至少 1 图或 1 视频".format(tier or "Seedance 2.0")})
    anchors = IMG_ANCHOR_RE.findall(body)
    if anchors:
        files = {}
        for no, r in have.items():
            f = _s(r.get("file")) or _s(r.get("path"))
            if f:
                files[no] = f
        for a in anchors:
            hit = set(no for no, f in files.items() if a and a in f)
            if hit:
                used |= hit          # 图锚就是一次引用，别再说它白占位
            else:
                out.append({"level": "error", "code": "CT17", "ref": gid,
                            "msg": "正文写了 [图锚 {}]，但 refs 里没有文件名含这个编号的分镜图——"
                                   "图锚必须能落到 refs.file（V2.5）".format(a)})
    for no in sorted(used - set(have)):
        out.append({"level": "error", "code": "CT17", "ref": gid,
                    "msg": "正文引用了 [图片{}]，但 refs 里没有第 {} 项".format(no, no)})
    for no in sorted(set(have) - used):
        out.append({"level": "warning", "code": "CT17", "ref": gid,
                    "msg": "refs 第 {} 项（{}）全文没被引用——白占一个素材位（2.0 一共只有 9 个位）".format(
                        no, _s(have[no].get("file"))[:28])})


def _ct18_color(gid, g, cards, out):
    """CT18 色温与色卡一致性。

    两层：① 组色温与所引色卡差 > 800K（warning）；② 正文里写的具体色值必须来自所引色卡
    （error）——色值只能从无人场景图取，不能在关键词里现编一个"看起来差不多"的 HEX。
    """
    temp = g.get("color_temp")
    if temp is None:
        temp = (g.get("params") or {}).get("color_temp")
    card_id = _s(g.get("color_card")) or _s((g.get("params") or {}).get("color_card"))
    card = cards.get(card_id) if card_id else None

    body = " ".join(_s(v) for v in (g.get("params") or {}).values()) + " " + _s(g.get("shots"))
    used_hex = set(h.upper() for h in HEX_RE.findall(body))
    if used_hex:
        if not card_id:
            out.append({"level": "error", "code": "CT18", "ref": gid,
                        "msg": "正文写了 {} 个色值（如 {}），但没挂 color_card——色值必须追到色卡".format(
                            len(used_hex), sorted(used_hex)[0])})
        elif not card:
            out.append({"level": "error", "code": "CT18", "ref": gid,
                        "msg": "引用了不存在的色卡 {}".format(card_id)})
            return
        else:
            allowed = set()
            for c in (card.get("colors") or []):
                h = _s(c.get("hex") if isinstance(c, dict) else c).upper()
                if h:
                    allowed.add(h)
            for h in sorted(used_hex - allowed):
                out.append({"level": "error", "code": "CT18", "ref": gid,
                            "msg": "正文写了色值 {}，但色卡 {} 里没有——色值要从场景图取，不能现编".format(
                                h, card_id)})

    if temp is None or not card_id:
        return
    if not card:
        out.append({"level": "error", "code": "CT18", "ref": gid,
                    "msg": "引用了不存在的色卡 {}".format(card_id)})
        return
    try:
        t1 = float(temp)
        t2 = float(card.get("temp"))
    except (TypeError, ValueError):
        return
    if abs(t1 - t2) > 800:
        out.append({"level": "warning", "code": "CT18", "ref": gid,
                    "msg": "本组色温 {}K 与色卡 {} 的 {}K 差 {}K（>800K 判越界）".format(
                        t1, card_id, t2, int(abs(t1 - t2)))})


def _ct19_fight(gid, g, out):
    """CT19 打斗组：缺受力反馈/重心恢复、单组升格 ≥2 次。"""
    shots = g.get("shots") or []
    slow = 0
    for s in shots:
        blob = " ".join(_s(s.get(k)) for k in ("style", "pic", "cam", "note", "content"))
        if any(w.lower() in blob.lower() for w in SLOWMO_HIT):
            slow += 1
    if slow >= 2:
        out.append({"level": "warning", "code": "CT19", "ref": gid,
                    "msg": "单组升格/慢动作 {} 次——一个打斗组只升格一次，其余靠剪辑".format(slow)})
    head = _s(g.get("genre")) + _s(g.get("title")) + _s(g.get("fight"))
    is_fight = g.get("fight") is True or any(w in head for w in FIGHT_HIT)
    if not is_fight:
        return
    text = _s(shots)
    if not any(w in text for w in FEEDBACK_HIT):
        out.append({"level": "warning", "code": "CT19", "ref": gid,
                    "msg": "打斗组没有受力反馈——挨打的一方得有反应，否则像两片纸在碰"})
    if not any(w in text for w in RECOVER_HIT):
        out.append({"level": "warning", "code": "CT19", "ref": gid,
                    "msg": "打斗组没有重心恢复——动作收不回来，镜尾会飘"})


def _ct21_reverse(gid, g, out):
    """CT21 反向提示词固定第 0 段：禁字幕/文字、禁 BGM/配乐。"""
    if "reverse" not in g and "reverse_prompt" not in g:
        return
    txt = _s(g.get("reverse") if "reverse" in g else g.get("reverse_prompt"))
    if not txt.strip():
        out.append({"level": "error", "code": "CT21", "ref": gid,
                    "msg": "反向提示词是空的——至少要有第 0 段的禁止句"})
        return
    if not any(w in txt for w in NO_TEXT_HIT):
        out.append({"level": "error", "code": "CT21", "ref": gid,
                    "msg": "反向提示词缺第 0 段：禁止出现任何字幕、禁止文字叠加、必须是纯画面"})
    if not any(w.lower() in txt.lower() for w in NO_BGM_HIT):
        out.append({"level": "error", "code": "CT21", "ref": gid,
                    "msg": "反向提示词缺第 0 段：禁止出现任何 BGM、禁止配乐"})


def _ct24_bg(gid, g, scene_ids, out):
    """CT24 背景元素依据：有背景人物就必须挂依据，且指向存在的场景图。"""
    bg = g.get("bg_basis")
    if bg is None:
        if g.get("bg_characters") or (g.get("params") or {}).get("bg"):
            out.append({"level": "error", "code": "CT24", "ref": gid,
                        "msg": "写了背景人物/背景元素，但缺 bg_basis 依据——背景里的人也得有出处"})
        return
    if isinstance(bg, dict):
        sid = _s(bg.get("scene")) or _s(bg.get("id"))
        note = _s(bg.get("note"))
    else:
        sid, note = _s(bg), ""
    if not sid:
        out.append({"level": "error", "code": "CT24", "ref": gid,
                    "msg": "bg_basis 缺 scene 字段——要指到具体场景图编号"})
        return
    if scene_ids and sid not in scene_ids:
        out.append({"level": "error", "code": "CT24", "ref": gid,
                    "msg": "bg_basis 指向的场景图 {} 不存在（现有：{}）".format(
                        sid, "/".join(sorted(scene_ids)[:6]))})
    elif not note:
        out.append({"level": "warning", "code": "CT24", "ref": gid,
                    "msg": "bg_basis 只给了编号没写依据（背景里有什么、为什么有）"})


IDENTITY_KINDS = ("face", "face_card", "outfit", "outfit_card", "back", "back_card",
                  "脸", "大脸卡", "服装卡", "背面卡")


FIGHT_WORDS = ("武打", "打斗", "搏斗", "拳", "踢", "刀", "剑", "棍", "摔", "擒")

def _ct25_coverage(data, assets, out):
    """CT25 分镜图覆盖率（V2.2 放宽版：允许只抽 1/3 关键帧）。

    规则（三条同时成立才算过）：
      1) 覆盖单元数 >= ceil(总单元数 / 3)；
      2) 跨段衔接处（段末且后面还有段）的单元必须都有分镜图；
      3) 打戏单元、B 级情绪峰值单元必须有分镜图。
    其余单元缺图不报——那是预算选择，不是错。
    旧数据没有 units 或没有 boards 桶时整段跳过，不报假红。
    """
    units = data.get("units") or data.get("shots")
    if not isinstance(units, list) or not units:
        return
    if "boards" not in assets:
        return
    ulist = []
    for u in units:
        if not isinstance(u, dict):
            continue
        uid = _s(u.get("id")) or _s(u.get("unit")) or _s(u.get("shot_id"))
        if uid:
            ulist.append((uid, u))
    if not ulist:
        return

    def _seg(u):
        return _s(u.get("segment")) or _s(u.get("seg")) or _s(u.get("act"))

    key = {}
    for i, (uid, u) in enumerate(ulist):
        seg = _seg(u)
        if seg and i + 1 < len(ulist) and _seg(ulist[i + 1][1]) != seg:
            key[uid] = "跨段衔接"
            continue
        blob = _s(u.get("action")) + _s(u.get("content")) + _s(u.get("title"))
        if u.get("fight") or any(w in blob for w in FIGHT_WORDS):
            key[uid] = "打戏"
            continue
        if _s(u.get("emotion_level")).upper() == "B" or _s(u.get("emotion")).startswith("B"):
            key[uid] = "情绪峰值"

    covered = set()
    per_unit = {}                      # 单元 -> 已出图的镜号集合（V2.9）
    for b in assets.get("boards") or []:
        if isinstance(b, dict):
            uid = _s(b.get("unit")) or _s(b.get("id"))
            if uid:
                covered.add(uid)
                sh = _s(b.get("shot"))
                if sh:
                    per_unit.setdefault(uid, set()).add(sh)
    ids = [uid for uid, _ in ulist]
    total = len(ids)
    need = max(1, (total + 2) // 3)
    hit = len([i for i in ids if i in covered])
    if hit < need:
        out.append({"level": "error", "code": "CT25", "ref": "boards",
                    "msg": "分镜图只覆盖 {}/{} 个单元，低于 1/3 下限（至少 {} 张）".format(hit, total, need)})
    missing = [(uid, why) for uid, why in key.items() if uid not in covered]
    for uid, why in missing:
        out.append({"level": "error", "code": "CT25", "ref": uid,
                    "msg": "{} 属于{}单元，必须有分镜图（降级也不许省）".format(uid, why)})
    if len(missing) > 8:
        out[-1]["msg"] += " …共 {} 个关键单元缺图".format(len(missing))

    # V2.9：多镜组要逐镜各出一张——单元维度算「覆盖了」不算完
    for uid, u in ulist:
        shots = [x for x in (u.get("shots") or []) if isinstance(x, dict)]
        if len(shots) < 2 or uid not in covered:
            continue
        want = [(_s(x.get("id")) or _s(x.get("no"))) for x in shots]
        want = [w for w in want if w]
        if not want:
            continue
        got = per_unit.get(uid) or set()
        lack = [w for w in want if w not in got]
        if not lack:
            continue
        if uid in key:
            out.append({"level": "error", "code": "CT25", "ref": uid,
                        "msg": "单元 {} 是多镜组（{} 镜）又属于{}，缺第 {} 镜的分镜图——"
                               "关键单元必须逐镜各一张（boards 里加 shot 字段）".format(
                                   uid, len(want), key[uid], "、".join(lack))})
        else:
            out.append({"level": "warning", "code": "CT25", "ref": uid,
                        "msg": "单元 {} 是多镜组（{} 镜），boards 里只认到 {} 张单镜图——"
                               "多镜组要逐镜各出一张，否则同一张图会被模型用到每一镜里".format(
                                   uid, len(want), len(got))})


def _ct18_cards(data, out):
    """CT18 色卡自身的可核性：每色写清取自场景图哪一处、HEX 合法、主色 3–5 个。

    这三条是「色卡从无人场景图取色」唯一能机器判的部分——取的那一处对不对，机器不知道，
    但「有没有写取处」「HEX 格式对不对」「主色个数够不够」是确定的。
    """
    scene_ids = set()
    for s in (data.get("scenes") or []):
        if isinstance(s, dict) and _s(s.get("id")):
            scene_ids.add(_s(s.get("id")))
    for card in (data.get("color_cards") or []):
        if not isinstance(card, dict):
            continue
        cid = _s(card.get("id")) or "?"
        colors = [c for c in (card.get("colors") or [])]
        if 0 < len(colors) < 3:
            out.append({"level": "warning", "code": "CT18", "ref": cid,
                        "msg": "色卡 {} 只记了 {} 个主色——规范是 3–5 个（少于 3 个定不住画面）".format(
                            cid, len(colors))})
        elif len(colors) > 5:
            out.append({"level": "warning", "code": "CT18", "ref": cid,
                        "msg": "色卡 {} 记了 {} 个主色——超过 5 个就分不清主次，挑最像的 5 个".format(
                            cid, len(colors))})
        for c in colors:
            h = _s(c.get("hex") if isinstance(c, dict) else c)
            src = _s(c.get("from")) if isinstance(c, dict) else ""
            if h and not re.match(r"^#[0-9a-fA-F]{6}$", h):
                out.append({"level": "error", "code": "CT18", "ref": cid,
                            "msg": "色卡 {} 里的色值 {} 不是 #RRGGBB 格式".format(cid, h[:12])})
            if isinstance(c, dict) and not src:
                out.append({"level": "error", "code": "CT18", "ref": cid,
                            "msg": "色卡 {} 里的 {} 没写 from——必须注明取自场景图哪一处（墙/沙发/车窗）".format(
                                cid, h or "?")})
            elif src.upper().startswith("SCN") and scene_ids and src not in scene_ids:
                out.append({"level": "error", "code": "CT18", "ref": cid,
                            "msg": "色卡 {} 的 from 指向不存在的场景图 {}".format(cid, src)})


def _anchors_voice(data):
    """取声线锚点：anchors.characters[].voice 或顶层 characters[].voice。"""
    out = {}
    blocks = []
    an = data.get("anchors")
    if isinstance(an, dict):
        blocks.append(an.get("characters"))
    blocks.append(data.get("characters"))
    for b in blocks:
        for c in (b or []):
            if not isinstance(c, dict):
                continue
            name = _s(c.get("name"))
            if not name:
                continue
            v = c.get("voice")
            if isinstance(v, dict):
                out[name] = v
            elif _s(v):
                out[name] = {"timbre": _s(v)}
            else:
                out[name] = {}      # 登记了角色但没写声线——正是要报的那种
    return out


def _ct31_roles(gid, g, out):
    # V2.10：首帧唯一性、首帧只认分镜图、资产图 role 枚举。
    refs = g.get("refs")
    if not isinstance(refs, list):
        return
    try:
        gdur = float(g.get("duration") or 0)
    except (TypeError, ValueError):
        gdur = 0.0
    firsts = 0
    for r in refs:
        if not isinstance(r, dict):
            continue
        no = r.get("no")
        kind = (_s(r.get("kind")) or _s(r.get("type"))).strip().lower()
        role = (_s(r.get("role")) or _s(r.get("as"))).strip().lower()
        if not role:
            continue
        is_first = any(t in role for t in FIRST_FRAME_ROLES)
        is_board = any(t in kind for t in BOARD_KINDS) if kind else False
        if is_first and kind and not is_board:
            out.append({"level": "warning", "code": "CT31", "ref": gid,
                        "msg": "refs 第 {} 项是资产图（kind={}）却标了 first_frame——首帧建议用分镜图，"
                               "2.0 里分镜图就是整组生成起点，标在资产图上模型会拿错起点（V2.12）".format(no, kind)})
        if is_first and (is_board or not kind):
            firsts += 1
        if not is_first and not is_board:
            ok = (any(t in role for t in ASSET_ROLES)
                  or any(t in role for t in SHOT_REF_ROLES))
            if not ok:
                out.append({"level": "warning", "code": "CT31", "ref": gid,
                            "msg": "refs 第 {} 项的 role「{}」不在枚举里，平台会忽略它".format(no, role)})
    if firsts > 1:
        out.append({"level": "error", "code": "CT31", "ref": gid,
                    "msg": "本组标了 {} 张首帧——一组只能有一张，多的大概率是笔误".format(firsts)})
    if not firsts and gdur > 15:
        out.append({"level": "warning", "code": "CT31", "ref": gid,
                    "msg": "本组 {} 秒（>15 秒走 2.5），没标首帧——模型会自己挑起点，位置容易和上一段接不上".format(
                        "%g" % gdur)})

def _ct30_voice(data, out):
    """CT30 声线锚点（V2.9）：台词的角色必须写清音色，且本组人声层要复写。

    配音走平台原生（V2.7），音色是平台按台词自己匹配的——不写锚点，同一个角色
    换一集就换嗓子，跨组也会各念各的。所以：

    - 组里有台词的角色，声线锚点里没有 timbre → warning；
    - 有人声层（sfx_layers.voice）却没提到该角色名 → warning。
    旧数据没有 anchors/characters 时整段跳过。
    """
    voice = _anchors_voice(data)
    if not voice:
        return
    for g in (data.get("groups") or []):
        if not isinstance(g, dict):
            continue
        gid = _s(g.get("no")) or _s(g.get("id")) or "?"
        speakers = []
        for sh in (g.get("shots") or []):
            if not isinstance(sh, dict):
                continue
            for d in (sh.get("dialogue") or []):
                if not isinstance(d, dict):
                    continue
                nm = _s(d.get("who")) or _s(d.get("name"))
                if not nm:
                    txt = _s(d.get("text"))
                    if "：" in txt:
                        nm = txt.split("：", 1)[0].strip()
                if nm and nm not in speakers:
                    speakers.append(nm)
        if not speakers:
            continue
        layer = _s(((g.get("sfx_layers") or {}).get("voice")))
        for nm in speakers:
            v = voice.get(nm) or {}
            if not _s(v.get("timbre")) and not _s(v.get("音色")):
                out.append({"level": "warning", "code": "CT30", "ref": gid,
                            "msg": "{} 有台词，但声线锚点没写音色——平台会自己挑一个，"
                                   "换一集就换嗓子".format(nm)})
            if layer and nm not in layer:
                out.append({"level": "warning", "code": "CT30", "ref": gid,
                            "msg": "本组人声层没提到 {}——音色/语速/口音照抄锚点，别现编".format(nm)})


def _ct29_audios(data, assets, out, root_dir=""):
    """CT29 原生配音资产（V2.8）：抽出来的配音也是一份资产，要登记、要挂版本。

    V2.7 的流程是「平台原生配音 → 抽成 AUD_<集号>_<组号>_v{n}.mp3 → 喂给后续组」。
    抽出来的音频同样是资产，得有地方记录它属于哪一组、第几版、被哪些组引用——
    否则同一句台词会被重抽三次，没人分得清哪一版最终用。

    - assets.audios 里 file 为空 → error；
    - 给了 root 而文件不存在 → error；
    - refs 里引用了音频（kind=audio/音频），但 audios 里没登记这个文件名 → error；
    - audios 里登记了却没有任何 refs 用它 → warning（白抽一条）。
    """
    if not isinstance(assets, dict):
        return
    audios = [a for a in (assets.get("audios") or []) if isinstance(a, dict)]
    reg = {}
    for a in audios:
        aid = _s(a.get("id")) or _s(a.get("group")) or "?"
        f = _s(a.get("file")) or _s(a.get("path"))
        if not f:
            out.append({"level": "error", "code": "CT29", "ref": aid,
                        "msg": "audios 里 {} 没写 file——原生配音要落到文件名才能被引用".format(aid)})
            continue
        reg[f.split("/")[-1].lower()] = aid
        if root_dir:
            import os
            full = f if os.path.isabs(f) else os.path.join(root_dir, f)
            if not os.path.exists(full):
                out.append({"level": "error", "code": "CT29", "ref": aid,
                            "msg": "原生配音文件不存在：{}".format(f)})
    used = {}
    for g in (data.get("groups") or []):
        if not isinstance(g, dict):
            continue
        gid = _s(g.get("no")) or _s(g.get("id")) or "?"
        for r in (g.get("refs") or []):
            if not isinstance(r, dict):
                continue
            if _s(r.get("kind")).lower() not in AUDIO_KINDS:
                continue
            f = _s(r.get("file"))
            if not f:
                continue
            key = f.split("/")[-1].lower()
            if key not in reg:
                out.append({"level": "error", "code": "CT29", "ref": gid,
                            "msg": "refs 引用了音频 {}，但 assets.audios 里没登记——抽出来的配音要先登记再引用".format(f)})
            else:
                used[key] = gid
    for key, aid in reg.items():
        if key not in used:
            out.append({"level": "warning", "code": "CT29", "ref": aid,
                        "msg": "audios 登记了 {}，但没有任何组引用它——白抽一条".format(key)})


def check_assets(data, root=None):
    """资产门禁校验：CT22 资产齐备 / CT23 参考链代际 / CT25 分镜图存在。返回列表。

    data["assets"] 形状（缺哪个桶就跳过哪个桶，旧数据不报假红）：
        characters: [{id, kind, cards:{face,outfit,back}, derived_from?, chain?}]
        props:      [{id, file}]
        colors:     [{id, temp, hex}]
        staging:    [{id, file, scene_ref}]
        boards:     [{unit, path}]
        scenes:     [{id, image}]

    root 给出时才做 CT25 的文件存在性检查（相对路径按 root 解析）。
    """

    out = []
    assets = data.get("assets") or {}
    if not isinstance(assets, dict):
        assets = {}
    _dup_ids(assets, out)
    if not _s(data.get("schema")):
        out.append({"level": "warning", "code": "CT33", "ref": "schema",
                    "msg": "这份数据没有 schema 字段（分镜写 sbdata/1、关键词写 kwdata/1）——"
                           "以后规则变了，分不出旧文件该不该迁移（V2.11）"})
    elif _s(data.get("schema")) not in SCHEMA_KNOWN:
        out.append({"level": "error", "code": "CT33", "ref": "schema",
                    "msg": "schema「%s」不认识（只认 %s）" % (
                        _s(data.get("schema")), "／".join(SCHEMA_KNOWN))})
    for _m in meta_typos(data):
        out.append({"level": "warning", "code": "CT33", "ref": "meta", "msg": _m})
    _ct18_cards(data, out)
    _ct28_style(data, data.get("assets") or {}, out)
    assets = data.get("assets")
    if not isinstance(assets, dict):
        return out


    for c in assets.get("characters") or []:
        if not isinstance(c, dict):
            continue
        cid = _s(c.get("id")) or _s(c.get("name")) or "?"
        cards = c.get("cards") or {}
        if "cards" in c or any(k in c for k in ("face", "outfit", "back")):
            src = cards if cards else c
            missing = [k for k in ("face", "outfit", "back") if not _s(src.get(k)).strip()]
            if missing:
                out.append({"level": "error", "code": "CT22", "ref": cid,
                            "msg": "角色 {} 缺 {} ——三类卡（大脸卡／无头服装卡／背面后脑卡）必须拆开开".format(
                                cid, "/".join(missing))})

    for bucket, label in (("props", "道具卡"), ("colors", "色卡"), ("staging", "站位草图"),
                          ("scenes", "场景图")):
        if bucket in assets and not [x for x in (assets.get(bucket) or []) if x]:
            out.append({"level": "error", "code": "CT22", "ref": bucket,
                        "msg": "资产清单里 {} 是空的——分镜图之前这些必须齐".format(label)})

    items = []
    for bucket in ("characters", "scenes", "props", "staging", "boards", "colors"):
        for it in assets.get(bucket) or []:
            if isinstance(it, dict):
                it = dict(it)
                it["_bucket"] = bucket
                items.append(it)
    idx = {}
    for it in items:
        aid = _s(it.get("id")) or _s(it.get("name"))
        if aid:
            idx[aid] = it

    for it in items:
        src = _s(it.get("derived_from"))
        aid = _s(it.get("id")) or _s(it.get("name")) or "?"
        kind = (_s(it.get("kind")) + _s(it.get("card_type"))).lower()
        is_identity = (_s(it.get("chain")).lower() == "identity"
                       or any(k.lower() in kind for k in IDENTITY_KINDS))
        if src and is_identity:
            out.append({"level": "error", "code": "CT23", "ref": aid,
                        "msg": "{} 属于身份链，却从 {} 派生——长相/发型/服装永远引原始大脸卡，禁传递".format(aid, src)})
        if src:
            depth = 1
            cur = src
            seen = set()
            while cur and cur not in seen:
                seen.add(cur)
                nxt = _s((idx.get(cur) or {}).get("derived_from"))
                if not nxt:
                    break
                depth += 1
                cur = nxt
            if depth > 1:
                out.append({"level": "error", "code": "CT23", "ref": aid,
                            "msg": "参考链深 {} 代（{}）——超一代即报错，越传越糊".format(depth, src)})
            if it["_bucket"] in ("staging", "boards") and not _s(it.get("scene_ref")):
                out.append({"level": "error", "code": "CT23", "ref": aid,
                            "msg": "空间链的 {} 没挂原始场景图（scene_ref）——站位能传，场景依据不能断".format(aid)})

    root_dir = _s(root)
    _ct29_audios(data, assets, out, root_dir)
    for b in assets.get("boards") or []:
        if not isinstance(b, dict):
            continue
        uid = _s(b.get("unit")) or _s(b.get("id")) or "?"
        path = _s(b.get("path")) or _s(b.get("file"))
        if not path:
            out.append({"level": "error", "code": "CT25", "ref": uid,
                        "msg": "单元 {} 写了分镜图编号但没有文件路径".format(uid)})
            continue
        if root_dir:
            import os
            full = path if os.path.isabs(path) else os.path.join(root_dir, path)
            if not os.path.exists(full):
                out.append({"level": "error", "code": "CT25", "ref": uid,
                            "msg": "分镜图文件不存在：{}".format(path)})
    _ct25_coverage(data, assets, out)
    if (assets.get("boards") or assets.get("scenes")) and not root_dir:
        out.append({"level": "warning", "code": "CT00", "ref": "assets",
                    "msg": "资产落盘校验没跑——没给资产目录。校验时加 --root <资产根目录>，"
                           "才会核对 KB_/SCN_ 这些文件是否真的存在（V2.7）"})
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
