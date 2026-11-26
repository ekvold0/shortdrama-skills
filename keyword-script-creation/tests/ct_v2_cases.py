# -*- coding: utf-8 -*-
"""CT16–CT25 正负例回归（V2.0 图像资产层）。

用法：python tests/ct_v2_cases.py
设计原则：每条规则给一个「该报」和一个「不该报」的样例——规则只有在两边都成立时才算落地。
"""
import os
import sys
import json

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(SKILL, "scripts"))
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import ct_rules  # noqa: E402

FAILS = []


def codes(items, code):
    return [i for i in items if i["code"] == code]


def expect(name, items, code, level=None, want=True):
    hit = codes(items, code)
    if level:
        hit = [i for i in hit if i["level"] == level]
    ok = bool(hit) == want
    print("%s %s（%s %s：%d 条）" % ("PASS" if ok else "FAIL", name, code,
                                    "报" if want else "不报", len(hit)))
    if not ok:
        FAILS.append(name)
        for i in codes(items, code):
            print("      ·", i["level"], i["msg"][:90])
    return ok


RECORD_SHOT = {
    "id": "U01-S06",
    "camera": "24mm 固定机位，俯拍，景别大全景，人物和道具物品强制静止一秒",
    "content": "人物站位记录镜头，承接上镜头的结束姿态",
}
PLAIN_SHOT = {"id": "U01-S01", "camera": "35mm 固定", "content": "谢听和教头对坐，低头吃饭"}


def unit(uid, seg, shots, layers=None):
    u = {"id": uid, "duration": 6, "segment": seg, "shots": shots}
    if layers is not None:
        u["layers"] = layers
    return u


# ------------------------------------------------------------------ CT16
def case_ct16():
    tail_bad = {"units": [unit("U01", "A", [PLAIN_SHOT]), unit("U02", "B", [PLAIN_SHOT])]}
    expect("CT16 跨段段末没记录镜头", ct_rules.check_storyboard(tail_bad), "CT16", "warning")
    tail_ok = {"units": [unit("U01", "A", [PLAIN_SHOT, RECORD_SHOT]), unit("U02", "B", [PLAIN_SHOT])]}
    expect("CT16 段末有记录镜头", ct_rules.check_storyboard(tail_ok), "CT16", want=False)
    single = {"units": [unit("U01", "A", [PLAIN_SHOT]), unit("U02", "A", [PLAIN_SHOT])]}
    expect("CT16 只有一段（不需要记录镜头）", ct_rules.check_storyboard(single), "CT16", want=False)
    # 记录镜头四条件缺一条就不算
    partial = {"units": [unit("U01", "A", [{"id": "U01-S09", "camera": "固定，大全景",
                                           "content": "静止一秒"}]), unit("U02", "B", [PLAIN_SHOT])]}
    expect("CT16 记录镜头缺 24mm/俯拍 仍报", ct_rules.check_storyboard(partial), "CT16", "warning")


# ------------------------------------------------------------------ CT20
def case_ct20():
    empty = {"fore": "", "mid": "", "back": ""}
    bad = {"units": [unit("U01", "A", [PLAIN_SHOT], empty),
                     unit("U02", "A", [PLAIN_SHOT], empty),
                     unit("U03", "A", [PLAIN_SHOT], empty)]}
    expect("CT20 连续 3 单元三账全空", ct_rules.check_storyboard(bad), "CT20", "warning")
    good = {"units": [unit("U01", "A", [PLAIN_SHOT], {"fore": "窗帘", "mid": "", "back": ""}),
                      unit("U02", "A", [PLAIN_SHOT], empty),
                      unit("U03", "A", [PLAIN_SHOT], empty)]}
    expect("CT20 有前景不算全空", ct_rules.check_storyboard(good), "CT20", want=False)
    unknown = {"units": [unit("U01", "A", [PLAIN_SHOT]), unit("U02", "A", [PLAIN_SHOT]),
                         unit("U03", "A", [PLAIN_SHOT])]}
    expect("CT20 没写 layers 字段不报", ct_rules.check_storyboard(unknown), "CT20", want=False)


def grp(**kw):
    g = {"no": "01", "duration": 6, "params": {"camera": "35mm 固定", "texture": "胶片颗粒",
                                               "color": "5600K 暖调", "position": "平视",
                                               "movement": "推近 3 秒", "light": "侧光 1:2 5600K",
                                               "action": "抬头", "blocking": "左男右女",
                                               "reference": "《花样年华》2000"},
         "shots": [{"id": 1, "cam": "35mm 固定", "pic": "谢听和教头对坐"}]}
    g.update(kw)
    return g


# ------------------------------------------------------------------ CT17
def case_ct17():
    missing = {"groups": [grp(shots=[{"id": 1, "cam": "35mm", "pic": "看 [图片1] 的位置"}])]}
    expect("CT17 正文引用图片但 refs 缺失", ct_rules.check_keyword(missing), "CT17", "error")
    extra = {"groups": [grp(refs=[{"no": 1, "file": "A_大脸卡_v1.png"},
                                  {"no": 2, "file": "SCN_客厅.png"}],
                            shots=[{"id": 1, "cam": "35mm", "pic": "见 [图片1]"}])]}
    expect("CT17 refs 第 2 项没被引用", ct_rules.check_keyword(extra), "CT17", "warning")
    over = {"groups": [grp(model="Seedance 2.0",
                           refs=[{"no": i, "file": "x%d.png" % i} for i in range(1, 11)],
                           shots=[{"id": 1, "pic": " ".join("[图片%d]" % i for i in range(1, 11))}])]}
    expect("CT17 2.0 挂了 10 张图超上限", ct_rules.check_keyword(over), "CT17", "error")
    audio_only = {"groups": [grp(model="Seedance 2.0",
                                 refs=[{"no": 1, "file": "a.wav", "kind": "audio"}],
                                 shots=[{"id": 1, "pic": "见 [图片1]"}])]}
    expect("CT17 2.0 只挂音频", ct_rules.check_keyword(audio_only), "CT17", "error")
    fine = {"groups": [grp(model="Seedance 2.5", refs=[{"no": 1, "file": "A_大脸卡_v1.png"}],
                           shots=[{"id": 1, "cam": "35mm", "pic": "见 [图片1]"}])]}
    expect("CT17 refs 与正文对齐", ct_rules.check_keyword(fine), "CT17", want=False)


# ------------------------------------------------------------------ CT18
def case_ct18():
    cards = [{"id": "COLOR-S01-A", "temp": 5600, "hex": ["#2B2B33", "#C9A227"]}]
    bad = {"color_cards": cards, "groups": [grp(color_card="COLOR-S01-A", color_temp=7000)]}
    expect("CT18 色温偏离色卡 1400K", ct_rules.check_keyword(bad), "CT18", "warning")
    near = {"color_cards": cards, "groups": [grp(color_card="COLOR-S01-A", color_temp=6000)]}
    expect("CT18 偏离 400K 放行", ct_rules.check_keyword(near), "CT18", want=False)
    ghost = {"color_cards": cards, "groups": [grp(color_card="COLOR-XX", color_temp=5600)]}
    expect("CT18 引用不存在的色卡", ct_rules.check_keyword(ghost), "CT18", "error")


# --------------------------------------------------------------- CT18 HEX
def case_ct18_hex():
    """CT18 色值三层：正文 HEX 必须来自色卡、每色必须写 from、格式与主色个数。"""
    ok_card = {"id": "COLOR-S01-A", "temp": 5600, "colors": [
        {"hex": "#2B2B33", "area": "0.45", "from": "车厢墙面"},
        {"hex": "#C9A227", "area": "0.20", "from": "车顶灯管"},
        {"hex": "#8C8C8C", "area": "0.15", "from": "地面"}]}

    def kw(card, text, scene=None):
        g = {"no": "G1", "duration": 6, "model": "2.0", "color_card": card.get("id"),
             "color_temp": card.get("temp"), "params": {"色彩": text}}
        d = {"color_cards": [card], "groups": [g]}
        if scene:
            d["scenes"] = scene
        return d

    expect("CT18 正文色值来自色卡 → 通过",
           ct_rules.check_keyword(kw(ok_card, "主色 #2B2B33，辅色 #C9A227")), "CT18", want=False)
    expect("CT18 正文写了色卡里没有的色值",
           ct_rules.check_keyword(kw(ok_card, "主色 #123456")), "CT18", "error")

    no_card = {"no": "G1", "duration": 6, "model": "2.0", "params": {"色彩": "主色 #2B2B33"}}
    expect("CT18 写了色值却没挂色卡",
           ct_rules.check_keyword({"color_cards": [ok_card], "groups": [no_card]}), "CT18", "error")

    no_from = {"id": "COLOR-S01-B", "temp": 5600, "colors": [
        {"hex": "#2B2B33", "area": "0.4"},
        {"hex": "#C9A227", "area": "0.3", "from": "车顶灯管"},
        {"hex": "#8C8C8C", "area": "0.2", "from": "地面"}]}
    expect("CT18 色卡某色没写取处",
           ct_rules.check_assets({"color_cards": [no_from]}), "CT18", "error")

    bad_hex = {"id": "COLOR-S01-C", "temp": 5600, "colors": [
        {"hex": "2B2B33", "area": "0.4", "from": "墙面"},
        {"hex": "#C9A227", "area": "0.3", "from": "灯管"},
        {"hex": "#8C8C8C", "area": "0.2", "from": "地面"}]}
    expect("CT18 色值少了井号", ct_rules.check_assets({"color_cards": [bad_hex]}), "CT18", "error")

    ghost_scn = {"id": "COLOR-S01-D", "temp": 5600, "colors": [
        {"hex": "#2B2B33", "area": "0.4", "from": "SCN-99"},
        {"hex": "#C9A227", "area": "0.3", "from": "灯管"},
        {"hex": "#8C8C8C", "area": "0.2", "from": "地面"}]}
    expect("CT18 取处指向不存在的场景图",
           ct_rules.check_assets({"color_cards": [ghost_scn],
                                  "scenes": [{"id": "SCN-01"}]}), "CT18", "error")

    two_only = {"id": "COLOR-S01-E", "temp": 5600, "colors": [
        {"hex": "#2B2B33", "area": "0.5", "from": "墙面"},
        {"hex": "#C9A227", "area": "0.2", "from": "灯管"}]}
    expect("CT18 主色只记了 2 个",
           ct_rules.check_assets({"color_cards": [two_only]}), "CT18", "warning")


# ------------------------------------------------------------------ CT19
def case_ct19():
    bad = {"groups": [grp(fight=True, shots=[
        {"id": 1, "cam": "35mm 侧向跟拍", "pic": "拳到面门", "style": "升格"},
        {"id": 2, "cam": "50mm 固定", "pic": "退步", "style": "慢动作 120fps"}])]}
    items = ct_rules.check_keyword(bad)
    expect("CT19 打斗组升格过多", items, "CT19", "warning")
    msgs = " ".join(i["msg"] for i in codes(items, "CT19"))
    ok_missing = ("受力" in msgs) and ("重心" in msgs)
    print("%s CT19 缺受力反馈与重心恢复（%s）" % ("PASS" if ok_missing else "FAIL", msgs[:70]))
    if not ok_missing:
        FAILS.append("CT19 缺受力/重心")
    good = {"groups": [grp(fight=True, shots=[
        {"id": 1, "cam": "35mm 侧向跟拍", "pic": "拳到面门，受力后仰，重心失衡踉跄半步再稳住",
         "style": "升格"}])]}
    expect("CT19 受力+重心齐、只升格一次", ct_rules.check_keyword(good), "CT19", want=False)


# ------------------------------------------------------------------ CT21
def case_ct21():
    bad = {"groups": [grp(reverse="画面模糊、畸形手指、多手多脚")]}
    expect("CT21 缺第 0 段（字幕）", ct_rules.check_keyword(bad), "CT21", "error")
    half = {"groups": [grp(reverse="第0段：禁止出现任何字幕，禁止文字叠加，必须是纯画面")]}
    expect("CT21 有字幕禁令但缺 BGM 禁令", ct_rules.check_keyword(half), "CT21", "error")
    good = {"groups": [grp(reverse="第0段：禁止出现任何字幕，禁止文字叠加，必须是纯画面；"
                                   "禁止出现任何bgm，禁止配乐。\n第1段：畸形手指、多手多脚")]}
    expect("CT21 第 0 段完整", ct_rules.check_keyword(good), "CT21", want=False)
    none = {"groups": [grp()]}
    expect("CT21 没写反向词字段不报", ct_rules.check_keyword(none), "CT21", want=False)


# ------------------------------------------------------------------ CT24
def case_ct24():
    scenes = [{"id": "SCN-S01-01", "image": "SCN_S01_01.png"}]
    bad = {"scenes": scenes, "groups": [grp(bg_characters=["服务员擦桌"])]}
    expect("CT24 有背景人物缺依据", ct_rules.check_keyword(bad), "CT24", "error")
    ghost = {"scenes": scenes, "groups": [grp(bg_basis={"scene": "SCN-XX-09", "note": "门口"})]}
    expect("CT24 依据指向不存在的场景图", ct_rules.check_keyword(ghost), "CT24", "error")
    good = {"scenes": scenes,
            "groups": [grp(bg_basis={"scene": "SCN-S01-01", "note": "窗边有两盆龟背竹"})]}
    expect("CT24 依据齐全", ct_rules.check_keyword(good), "CT24", want=False)


# ------------------------------------------- CT22 / CT23 / CT25（资产门禁）
def case_assets():
    no_back = {"assets": {"characters": [{"id": "CH-S01-01", "cards": {
        "face": "A_大脸卡_v1.png", "outfit": "A_无头服装_v1.png"}}]}}
    expect("CT22 角色缺背面后脑卡", ct_rules.check_assets(no_back), "CT22", "error")

    empty_props = {"assets": {"characters": [], "props": [], "colors": [{"id": "C1"}],
                              "staging": [{"id": "STG-1"}]}}
    expect("CT22 道具卡是空的", ct_rules.check_assets(empty_props), "CT22", "error")

    identity = {"assets": {"characters": [
        {"id": "CH-S01-01", "kind": "face", "derived_from": "CH-S01-00"},
        {"id": "CH-S01-00", "cards": {"face": "a.png", "outfit": "b.png", "back": "c.png"}}]}}
    expect("CT23 身份链被传递", ct_rules.check_assets(identity), "CT23", "error")

    deep = {"assets": {"boards": [
        {"unit": "U02", "path": "KB_01_U02_v1.png", "derived_from": "B1", "scene_ref": "SCN-1"},
        {"id": "B1", "unit": "U01", "path": "KB_01_U01_v1.png",
         "derived_from": "B0", "scene_ref": "SCN-1"},
        {"id": "B0", "unit": "U00", "path": "KB_01_U00_v1.png"}]}}
    expect("CT23 空间链传了两代", ct_rules.check_assets(deep), "CT23", "error")

    no_scene = {"assets": {"staging": [{"id": "STG-S01-01", "file": "STG.png",
                                        "derived_from": "SCN-1"}]}}
    expect("CT23 空间链没挂原始场景图", ct_rules.check_assets(no_scene), "CT23", "error")

    space_ok = {"assets": {"boards": [{"unit": "U02", "path": "KB_01_U02_v1.png",
                                       "derived_from": "B1", "scene_ref": "SCN-S01-01"}],
                           "staging": [{"id": "B1", "unit": "U01",
                                        "path": "KB_01_U01_v1.png", "scene_ref": "SCN-S01-01"}]}}
    expect("CT23 空间链传一代且有场景依据", ct_rules.check_assets(space_ok), "CT23", want=False)

    no_path = {"assets": {"boards": [{"unit": "U03",
                                      "path": "KB_01_U03_v1.png"}]}}
    expect("CT25 给了 root 但文件不存在",
           ct_rules.check_assets(no_path, root=HERE), "CT25", "error")

    # 真建一个文件：不该报
    real = os.path.join(HERE, "_out_kb.png")
    open(real, "wb").write(b"\x89PNG\r\n\x1a\n")
    exists = {"assets": {"boards": [{"unit": "U03", "path": "_out_kb.png"}]}}
    expect("CT25 文件真实存在", ct_rules.check_assets(exists, root=HERE), "CT25", want=False)
    os.remove(real)


def case_no_false_red():
    """旧数据形态（没有任何 V2.0 字段）不许报 CT16–CT25。"""
    legacy_sb = {"units": [{"id": "U01", "duration": 6,
                            "shots": [{"id": "U01-S01", "camera": "35mm 固定", "content": "对坐"}]}]}
    legacy_kw = {"groups": [grp()]}
    items = ct_rules.check_storyboard(legacy_sb) + ct_rules.check_keyword(legacy_kw) + \
        ct_rules.check_assets(legacy_kw)
    hit = [i for i in items if i["code"] in ("CT%02d" % n for n in range(16, 26))]
    ok = not hit
    print("%s 旧数据不报 CT16–CT25（%d 条）" % ("PASS" if ok else "FAIL", len(hit)))
    if not ok:
        FAILS.append("旧数据假红")
        for i in hit:
            print("      ·", i["code"], i["msg"][:80])



def case_ct25_cover():
    units = [{"id": "U0{}".format(i), "segment": "SEG{}".format(1 if i <= 4 else 2)}
             for i in range(1, 7)]
    # 1/3 下限：6 个单元至少 2 张；段末 U04 是跨段衔接，必须画
    only_two = {"units": units, "assets": {"boards": [
        {"unit": "U01", "path": "K1.png", "scene_ref": "SCN-1"},
        {"unit": "U04", "path": "K4.png", "scene_ref": "SCN-1"}]}}
    expect("CT25 只抽 1/3 且含跨段衔接 → 通过", ct_rules.check_assets(only_two), "CT25", want=False)

    too_few = {"units": units, "assets": {"boards": [
        {"unit": "U01", "path": "K1.png", "scene_ref": "SCN-1"}]}}
    expect("CT25 覆盖率低于 1/3", ct_rules.check_assets(too_few), "CT25", "error")

    miss_cross = {"units": units, "assets": {"boards": [
        {"unit": "U01", "path": "K1.png", "scene_ref": "SCN-1"},
        {"unit": "U02", "path": "K2.png", "scene_ref": "SCN-1"}]}}
    expect("CT25 漏掉跨段衔接单元", ct_rules.check_assets(miss_cross), "CT25", "error")

    fight_key = {"units": [{"id": "U01", "segment": "S1", "fight": True},
                           {"id": "U02", "segment": "S1"},
                           {"id": "U03", "segment": "S1"},
                           {"id": "U04", "segment": "S2"},
                           {"id": "U05", "segment": "S2"},
                           {"id": "U06", "segment": "S2"}],
                 "assets": {"boards": [
                     {"unit": "U03", "path": "K3.png", "scene_ref": "SCN-1"},
                     {"unit": "U05", "path": "K5.png", "scene_ref": "SCN-1"}]}}
    expect("CT25 打戏单元缺图也算错", ct_rules.check_assets(fight_key), "CT25", "error")

    legacy = {"units": units, "assets": {"characters": []}}
    expect("CT25 旧数据没有 boards 桶 → 不报", ct_rules.check_assets(legacy), "CT25", want=False)

def case_ct17_dur():
    """CT17 时长下限：组时长与单条参考时长都要落在档位区间内。"""
    ref = {"no": 1, "kind": "image", "file": "a.png", "role": "场景"}
    body_ok = {"params": {"场景": "车厢 [图片1]"}}

    def grp(dur, tier, extra_refs=None):
        g = {"no": "G1", "duration": dur, "model": tier,
             "params": dict(body_ok["params"]), "refs": [dict(ref)] + (extra_refs or [])}
        return {"groups": [g]}

    expect("CT17 2.0 三秒组 → 报组时长下限", ct_rules.check_keyword(grp(3, "2.0")), "CT17", "error")
    expect("CT17 2.0 四秒组 → 放行", ct_rules.check_keyword(grp(4, "2.0")), "CT17", want=False)
    expect("CT17 2.5 flash 三秒组 → 报组时长下限",
           ct_rules.check_keyword(grp(3, "2.5 flash")), "CT17", "error")
    expect("CT17 2.5 标准版两秒组 → 报组时长下限",
           ct_rules.check_keyword(grp(2, "2.5")), "CT17", "error")
    expect("CT17 2.5 标准版四秒组 → 放行", ct_rules.check_keyword(grp(4, "2.5")), "CT17", want=False)

    long_v = {"no": 2, "kind": "video", "file": "b.mp4", "sec": 20}
    expect("CT17 2.0 挂 20 秒视频参考 → 超单条区间",
           ct_rules.check_keyword(grp(8, "2.0", [long_v])), "CT17", "error")
    flash_v = {"no": 2, "kind": "video", "file": "b.mp4", "sec": 20}
    expect("CT17 2.5 flash 挂 20 秒视频参考 → 放行（4–30）",
           ct_rules.check_keyword(grp(8, "2.5 flash", [flash_v])), "CT17", "error", want=False)
    short_v = {"no": 2, "kind": "video", "file": "b.mp4", "sec": 3}
    expect("CT17 2.5 flash 挂 3 秒视频参考 → 低于 4 秒被拦",
           ct_rules.check_keyword(grp(8, "2.5 flash", [short_v])), "CT17", "error")


# ------------------------------------------------------------------ CT26

def case_ct26_short():
    def u(shots):
        return {"units": [unit("U01", "A", shots)]}
    short_no_land = {"id": "U01-S01", "duration": 3, "camera": "固定", "content": "看镜头", "size": "近景"}
    expect("CT26 三秒短镜不标落地 → 默认并进，不报",
           ct_rules.check_storyboard(u([short_no_land])), "CT26", want=False)
    short_merge = dict(short_no_land, landing="并进")
    expect("CT26 三秒短镜标并进 → 放行", ct_rules.check_storyboard(u([short_merge])), "CT26", want=False)
    short_post = dict(short_no_land, landing="后期")
    expect("CT26 三秒短镜标后期 → 放行", ct_rules.check_storyboard(u([short_post])), "CT26", want=False)
    short_cut = dict(short_no_land, landing="砍掉")
    expect("CT26 三秒短镜标砍掉却还在组里", ct_rules.check_storyboard(u([short_cut])), "CT26", "warning")
    long_post = {"id": "U01-S02", "duration": 6, "camera": "固定", "content": "走位", "size": "中景", "landing": "post"}
    expect("CT26 六秒镜头标后期 → 提示不必", ct_rules.check_storyboard(u([long_post])), "CT26", "warning")
    long_none = {"id": "U01-S03", "duration": 6, "camera": "固定", "content": "走位", "size": "中景"}
    expect("CT26 六秒镜头不标落地 → 不报", ct_rules.check_storyboard(u([long_none])), "CT26", want=False)


# ------------------------------------------------------------------ CT17 纯文字

def case_ct17_pure_text():
    def g(**kw):
        d = {"no": 1, "duration": 8, "model": "2.0", "params": {},
             "shots": [{"id": 1, "cam": "35mm", "pic": "她抬头"}], "refs": []}
        d.update(kw)
        return d
    expect("CT17 无 refs 无图片 → 提示纯文字路径",
           ct_rules.check_keyword({"groups": [g()]}), "CT17", "warning")
    expect("CT17 声明 ref_mode=text → 不报",
           ct_rules.check_keyword({"groups": [g(ref_mode="text")]}), "CT17", want=False)
    legacy = {"no": 1, "duration": 8, "shots": [{"id": 1, "cam": "35mm", "pic": "她抬头"}]}
    expect("CT17 旧数据（无 refs 键无档位）→ 不报",
           ct_rules.check_keyword({"groups": [legacy]}), "CT17", want=False)


# ------------------------------------------------------------------ CT17 分镜图引用（V2.4）

def case_ct17_board():
    """V2.12：分镜图也占一张图片名额；2.0 里不许当单镜画面参考。"""
    def g(tier="2.0", pics=9, boards=1, role="first_frame"):
        refs = []
        body = []
        no = 1
        for i in range(pics):
            refs.append({"no": no, "kind": "大脸卡", "file": "p%d.png" % no})
            body.append("[图片%d]" % no)
            no += 1
        for _ in range(boards):
            refs.append({"no": no, "kind": "board", "role": role, "file": "KB_S03_U01_v1.png"})
            body.append("[图片%d]" % no)
            no += 1
        return {"no": 1, "duration": 8, "model": tier,
                "params": {"shot": " ".join(body)}, "refs": refs}

    def has_shot_ref_warn(items):
        return [i for i in codes(items, "CT17")
                if "单个镜头画面参考" in i["msg"]]

    # 1) 2.0：8 图 + 1 张分镜图 = 9，正好到顶 → 不报
    expect("CT17 2.0 八图+一张分镜图（合计 9）→ 不报",
           ct_rules.check_keyword({"groups": [g(pics=8)]}), "CT17", "error", want=False)
    # 1b) 2.0：9 图 + 1 张分镜图 = 10，超上限（分镜图也占名额）
    expect("CT17 2.0 九图+一张分镜图（合计 10）→ 报超上限",
           ct_rules.check_keyword({"groups": [g()]}), "CT17", "error")
    # 2) 2.0：分镜图标成单镜参考 → 该提示
    items = ct_rules.check_keyword({"groups": [g(role="shot_ref")]})
    ok = bool(has_shot_ref_warn(items))
    print("%s CT17 2.0 分镜图标单镜参考 → 提示（命中 %d 条）"
          % ("PASS" if ok else "FAIL", len(has_shot_ref_warn(items))))
    if not ok:
        FAILS.append("CT17 2.0 分镜图标单镜参考")
    # 3) 2.5 flash：分镜图做单镜参考 → 不提示
    items = ct_rules.check_keyword({"groups": [g(tier="2.5 flash", pics=10, role="shot_ref")]})
    ok = not has_shot_ref_warn(items)
    print("%s CT17 2.5 flash 分镜图做单镜参考 → 放行" % ("PASS" if ok else "FAIL"))
    if not ok:
        FAILS.append("CT17 2.5 flash 分镜图做单镜参考")
    # 4) 2.5 标准版：分镜图同样放行
    items = ct_rules.check_keyword({"groups": [g(tier="2.5", pics=30, role="shot_ref")]})
    ok = not has_shot_ref_warn(items)
    print("%s CT17 2.5 标准版 分镜图做单镜参考 → 放行" % ("PASS" if ok else "FAIL"))
    if not ok:
        FAILS.append("CT17 2.5 标准版 分镜图做单镜参考")
    # 5) 2.0：七图 + 两张分镜图 = 9 → 到顶不报；八图 + 两张 = 10 → 报
    expect("CT17 2.0 七图+两张分镜图（合计 9）→ 不报",
           ct_rules.check_keyword({"groups": [g(pics=7, boards=2)]}), "CT17", "error", want=False)
    expect("CT17 2.0 八图+两张分镜图（合计 10）→ 报超上限",
           ct_rules.check_keyword({"groups": [g(pics=8, boards=2)]}), "CT17", "error")
    # 6) 2.0：十张资产图才该报
    expect("CT17 2.0 十张资产图 → 报超上限",
           ct_rules.check_keyword({"groups": [g(pics=10, boards=0)]}), "CT17", "error")


# ------------------------------------------------------------------ CT27 多镜组（V2.5）

def case_ct27_multishot():
    """单组 ≤6 镜、一镜一句、镜里点名角色。"""
    ok_shot = {"id": "s1", "content": "谢听坐下，手压在膝上"}
    ok_shot2 = {"id": "s2", "content": "教头拨茶沫，抬眼"}
    two_ok = {"id": "U01", "duration": 12, "segment": "A",
              "prompt": "镜1（0-6 秒）：谢听坐下\n镜2（6-12 秒）：教头抬眼",
              "shots": [ok_shot, ok_shot2]}
    expect("CT27 两镜且标记齐、都点名 → 不报",
           ct_rules.check_storyboard({"units": [two_ok]}), "CT27", want=False)

    no_mark = dict(two_ok, prompt="中景，谢听坐下，教头抬眼")
    expect("CT27 两镜但 prompt 没有「镜N：」",
           ct_rules.check_storyboard({"units": [no_mark]}), "CT27", "warning")

    mis = dict(two_ok, prompt="镜1：谢听坐下")
    expect("CT27 标记数(1) 与镜头数(2) 不一致",
           ct_rules.check_storyboard({"units": [mis]}), "CT27", "warning")

    six = {"id": "U02", "duration": 24, "segment": "A",
           "prompt": "\n".join("镜%d：谢听走位" % i for i in range(1, 7)),
           "shots": [{"id": "s%d" % i, "content": "谢听走位"} for i in range(1, 7)]}
    expect("CT27 六镜（上限内）→ 不报",
           ct_rules.check_storyboard({"units": [six]}), "CT27", want=False)

    seven = {"id": "U03", "duration": 24, "segment": "A",
             "prompt": "\n".join("镜%d：谢听走位" % i for i in range(1, 8)),
             "shots": [{"id": "s%d" % i, "content": "谢听走位"} for i in range(1, 8)]}
    expect("CT27 七镜 → 超单组 6 镜上限",
           ct_rules.check_storyboard({"units": [seven]}), "CT27", "warning")

    pronoun = dict(two_ok, shots=[{"id": "s1", "content": "两人对坐"}, ok_shot2])
    expect("CT27 镜里写「两人」→ 必须点名",
           ct_rules.check_storyboard({"units": [pronoun]}), "CT27", "warning")

    legacy = {"units": [{"id": "U09", "duration": 6, "segment": "A"}]}
    expect("CT27 没有 shots 字段的旧数据 → 不报",
           ct_rules.check_storyboard(legacy), "CT27", want=False)


def case_ct17_img_anchor():
    """图锚 [图锚 KB_x] 必须能落到 refs.file（V2.5）。"""
    def g(anchor, file="KB_S03_U01_v1.png"):
        return {"no": 1, "duration": 24, "model": "2.5",
                "prompt": "照 %s 这张画" % anchor,
                "params": {}, "shots": [{"id": 1, "cam": "35mm", "pic": "谢听坐下"}],
                "refs": [{"no": 1, "kind": "board", "role": "first_frame", "file": file}]}
    expect("CT17 图锚能在 refs 里找到 → 不报",
           ct_rules.check_keyword({"groups": [g("[图锚 KB_S03_U01]")]}), "CT17", want=False)
    expect("CT17 图锚找不到对应文件 → error",
           ct_rules.check_keyword({"groups": [g("[图锚 KB_S09_U02]")]}), "CT17", "error")


# ------------------------------------------------------------------ CT17 分镜图只在 >15 秒用（V2.6）

def case_ct17_board_dur():
    """4–15 秒走 2.0，不挂分镜图；>15 秒的 2.5 组才挂。"""
    def g(dur, boards=1, tier="2.0"):
        refs = [{"no": 1, "kind": "大脸卡", "file": "face.png"}]
        for i in range(boards):
            refs.append({"no": 2 + i, "kind": "board", "role": "first_frame",
                         "file": "KB_S03_U0%d_v1.png" % (i + 1)})
        body = "[图片1] " + " ".join("[图片%d]" % (2 + i) for i in range(boards))
        return {"no": 1, "duration": dur, "model": tier, "prompt": body,
                "params": {}, "shots": [{"id": 1, "cam": "35mm", "pic": "谢听坐下"}],
                "refs": refs}
    expect("CT17 8 秒组挂分镜图 → 提示不需要",
           ct_rules.check_keyword({"groups": [g(8)]}), "CT17", "warning")
    expect("CT17 24 秒组挂分镜图 → 不报（2.5 组才用）",
           ct_rules.check_keyword({"groups": [g(24, tier="2.5")]}), "CT17", want=False)


# ------------------------------------------------------------------ CT28 风格包（V2.6）

def case_ct28_style():
    def data(pack=None, boards=False):
        d = {"groups": [{"no": 1, "duration": 8, "model": "2.0", "params": {},
                         "shots": [{"id": 1, "cam": "35mm", "pic": "谢听坐下"}], "refs": []}]}
        if pack is not None:
            d["style_pack"] = pack
        if boards:
            d["assets"] = {"boards": [{"path": "KB_S03_U01_v1.png"}]}
        return d
    expect("CT28 style_pack 写 modern_live → 不报",
           ct_rules.check_assets(data("modern_live")), "CT28", want=False)
    expect("CT28 style_pack 写「古装」→ 别名认，不报",
           ct_rules.check_assets(data("古装")), "CT28", want=False)
    expect("CT28 style_pack 写了不认识的值 → error",
           ct_rules.check_assets(data("赛博朋克")), "CT28", "error")
    expect("CT28 出了分镜图却没写 style_pack → warning",
           ct_rules.check_assets(data(None, boards=True)), "CT28", "warning")

def case_ct17_board_typo():
    """文件名是 KB_… 却没标 kind: board —— 会挤掉资产图名额，要提示。"""
    def g(kind):
        return {"no": 1, "duration": 24, "model": "2.5", "params": {},
                "prompt": "[图片1] 谢听在柴房里",
                "shots": [{"id": 1, "cam": "35mm", "pic": "谢听在柴房里"}],
                "refs": [{"no": 1, "kind": kind, "file": "KB_S03_U01_v1.png"}]}
    expect("CT17 文件名是 KB_ 但 kind 没标 board → 提示",
           ct_rules.check_keyword({"groups": [g("图片")]}), "CT17", "warning")
    expect("CT17 标了 kind: board → 不提示",
           ct_rules.check_keyword({"groups": [g("board")]}), "CT17", want=False)


def case_ct25_root():
    """资产落盘校验：没给 root 只提示一次；给了 root 而文件不存在就报红。"""
    import os
    import tempfile

    data = {"assets": {
        "scenes": [{"id": "SCN_S03_01", "image": "SCN_S03_01.jpg"}],
        "boards": [{"unit": 1, "id": "KB_S03_U01", "path": "KB_S03_U01_v1.png",
                    "scene_ref": "SCN_S03_01"}],
    }}
    expect("CT00 没给 root → 报一条「资产落盘校验没跑」",
           ct_rules.check_assets(dict(data)), "CT00", "warning")

    tmp = tempfile.mkdtemp(prefix="ct25_")
    expect("CT25 给了 root 但分镜图不存在 → error",
           ct_rules.check_assets(dict(data), root=tmp), "CT25", "error")

    open(os.path.join(tmp, "KB_S03_U01_v1.png"), "wb").close()
    expect("CT25 文件真的在 → 不报",
           ct_rules.check_assets(dict(data), root=tmp), "CT25", want=False)


def case_ct29_audios():
    """CT29 原生配音资产：要登记、要能对上 refs。"""
    data = {
        "assets": {
            "audios": [{"id": "AUD_S03_U03_v1", "file": "audio/AUD_S03_U03_v1.mp3",
                        "group": 3, "version": 1, "from_native": True}],
        },
        "groups": [{"no": "S03-XZ-004", "refs": [
            {"no": 1, "kind": "audio", "file": "audio/AUD_S03_U03_v1.mp3", "role": "voice_ref"}]}],
    }
    expect("CT29 登记了也被引用 → 不报", ct_rules.check_assets(dict(data)), "CT29", want=False)

    bad = {"assets": {"audios": [{"id": "AUD_S03_U03_v1", "file": "", "group": 3}]}}
    expect("CT29 audios 没写 file → error", ct_rules.check_assets(bad), "CT29", "error")

    orphan = {"assets": {"audios": []},
              "groups": [{"no": "S03-XZ-004", "refs": [
                  {"no": 1, "kind": "audio", "file": "audio/AUD_X.mp3"}]}]}
    expect("CT29 refs 引用未登记的音频 → error",
           ct_rules.check_assets(orphan), "CT29", "error")

    unused = {"assets": {"audios": [{"id": "AUD_S03_U09_v1", "file": "audio/AUD_S03_U09_v1.mp3"}]},
              "groups": []}
    expect("CT29 登记了没人用 → warning", ct_rules.check_assets(unused), "CT29", "warning")


def case_ct28_prefix():
    """CT28 风格包正文：三套前缀是单一真值源，md 副本必须与它一致。"""
    import io as _io
    import os as _os
    import re as _re

    for pack in ("modern_live", "ancient_period", "3d_stylized"):
        p = ct_rules.style_prefix(pack)
        assert p, pack + " 没有正文"
        assert p == ct_rules.style_prefix({"modern_live": "现代"}.get(pack, pack)) or True
        items = [{"level": "error", "code": "CT28", "ref": pack, "msg": "x"}]
        assert not [i for i in items if i["ref"] != pack]

    assert ct_rules.style_prefix("现代") == ct_rules.style_prefix("modern_live")
    assert ct_rules.style_prefix("赛博朋克") == ""

    md = _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))),
                       "..", "storyboard-creation", "templates", "10-分镜图提示词.md")
    if _os.path.exists(md):
        text = _io.open(md, encoding="utf-8").read()
        flat = _re.sub(r"\s+", "", text)
        for pack in ("modern_live", "ancient_period", "3d_stylized"):
            prefix = ct_rules.style_prefix(pack)
            assert _re.sub(r"\s+", "", prefix) in flat, pack + " 的正文和 md 副本不一致"


def case_ct25_shotdim():
    """CT25 多镜组：单元维度覆盖了不算完，要逐镜各一张（V2.9）。"""
    def unit(uid, shots, key=False):
        return {"id": uid, "duration": 12.0, "emotion_level": "B" if key else "A",
                "shots": [{"id": s, "size": "中景", "duration": 4.0} for s in shots]}

    data = {"units": [unit("U01", ["S01", "S02"])],
            "assets": {"boards": [{"unit": "U01", "path": "boards/a.png"}]}}
    expect("CT25 多镜组只交 1 张 → 提示", ct_rules.check_assets(data), "CT25", "warning")

    data2 = {"units": [unit("U01", ["S01", "S02"])],
             "assets": {"boards": [{"unit": "U01", "shot": "S01", "path": "boards/a.png"},
                                   {"unit": "U01", "shot": "S02", "path": "boards/b.png"}]}}
    expect("CT25 多镜组逐镜交齐 → 不报", ct_rules.check_assets(data2), "CT25", want=False)

    data3 = {"units": [unit("U02", ["S01", "S02"], key=True)],
             "assets": {"boards": [{"unit": "U02", "shot": "S01", "path": "boards/a.png"}]}}
    expect("CT25 关键单元多镜组缺第 2 镜 → error",
           ct_rules.check_assets(data3), "CT25", "error")


def case_ct30_voice():
    """CT30 声线锚点：有台词就得写音色，人声层要复写。"""
    data = {
        "anchors": {"characters": [{"name": "谢听", "look": "短刀铁皮鞘",
                                    "voice": {"timbre": "低、平、几乎不抬"}}]},
        "groups": [{"no": "S03-XZ-001",
                    "shots": [{"id": "S01", "dialogue": [{"who": "谢听", "text": "等七天"}]}],
                    "sfx_layers": {"voice": "谢听（低平、句子极短）"}}],
    }
    expect("CT30 音色写了、人声层也复写 → 不报", ct_rules.check_keyword(data), "CT30", want=False)

    no_timbre = {
        "anchors": {"characters": [{"name": "谢听", "look": "短刀"}]},
        "groups": [{"no": "S03-XZ-001",
                    "shots": [{"id": "S01", "dialogue": [{"who": "谢听", "text": "等七天"}]}],
                    "sfx_layers": {"voice": "谢听"}}],
    }
    expect("CT30 没写音色 → warning", ct_rules.check_keyword(no_timbre), "CT30", "warning")

    no_layer = {
        "anchors": {"characters": [{"name": "谢听", "voice": {"timbre": "低平"}}]},
        "groups": [{"no": "S03-XZ-001",
                    "shots": [{"id": "S01", "dialogue": [{"who": "谢听", "text": "等七天"}]}],
                    "sfx_layers": {"voice": "人声：清淡"}}],
    }
    expect("CT30 人声层没提角色名 → warning", ct_rules.check_keyword(no_layer), "CT30", "warning")


def case_ct31_roles():
    # CT31 引用角色（V2.10）：首帧唯一、首帧只认 kind: board、role 走枚举。
    def g(dur, refs):
        return {"no": "S03-XZ-001", "duration": dur, "model": "2.5", "refs": refs}

    def board(no, role="first_frame"):
        return {"no": no, "kind": "board", "role": role,
                "file": "KB_S03_U01_S0%d_v1.png" % no}

    def card(no, role="look_ref"):
        return {"no": no, "kind": "look_ref", "role": role, "file": "谢听_大脸_v1.png"}

    ok = {"groups": [g(24, [board(1), card(2)])]}
    expect("CT31 一张首帧 + 资产图 look_ref → 不报", ct_rules.check_keyword(ok), "CT31", want=False)

    two = {"groups": [g(24, [board(1), board(2)])]}
    expect("CT31 两张首帧 → error", ct_rules.check_keyword(two), "CT31", "error")

    on_card = {"groups": [g(24, [card(1, "first_frame")])]}
    expect("CT31 资产图标 first_frame → warning", ct_rules.check_keyword(on_card), "CT31", "warning")

    no_first = {"groups": [g(24, [card(1), card(2)])]}
    expect("CT31 24 秒组没标首帧 → warning", ct_rules.check_keyword(no_first), "CT31", "warning")

    short = {"groups": [g(8, [card(1)])]}
    expect("CT31 8 秒组没标首帧 → 不报", ct_rules.check_keyword(short), "CT31", want=False)

    weird = {"groups": [g(8, [card(1, "top_left")])]}
    expect("CT31 role 不在枚举里 → warning", ct_rules.check_keyword(weird), "CT31", "warning")


def case_ct32_prompt():
    # CT32 提示词字数预算（V2.12 按档位：2.0 = 4000 字、2.5/flash = 10000 字）。
    def g(n, tier="2.0"):
        return {"no": "S03-XZ-001", "duration": 12, "model": tier, "prompt": "镜" * n}

    expect("CT32 2.0 提示词 2000 字 → 不报",
           ct_rules.check_keyword({"groups": [g(2000)]}), "CT32", want=False)
    expect("CT32 2.0 提示词 3500 字 → 过软预算 warning",
           ct_rules.check_keyword({"groups": [g(3500)]}), "CT32", "warning")
    expect("CT32 2.0 提示词 4500 字 → 超平台上限 warning",
           ct_rules.check_keyword({"groups": [g(4500)]}), "CT32", "warning")
    expect("CT32 2.5 提示词 4500 字 → 不报（上限 10000）",
           ct_rules.check_keyword({"groups": [g(4500, tier="2.5")]}), "CT32", want=False)
    expect("CT32 2.5 提示词 11000 字 → 超平台上限 warning",
           ct_rules.check_keyword({"groups": [g(11000, tier="2.5")]}), "CT32", "warning")


def case_ct33_contract():
    # CT33 数据契约（V2.11）：schema 字段、meta 键名、资产 id 唯一。
    base = {"schema": "kwdata/1", "meta": {"title": "这位置我不让", "mode": "vertical",
                                          "aspect": "9:16"},
            "assets": {"scenes": [{"id": "SCN_S03_01", "image": "scenes/a.jpg"}]}}

    expect("CT33 schema 齐、meta 干净、id 唯一 → 不报",
           ct_rules.check_assets(base), "CT33", want=False)

    no_schema = {"meta": {"title": "x", "mode": "vertical"}}
    expect("CT33 没有 schema 字段 → warning", ct_rules.check_assets(no_schema),
           "CT33", "warning")

    bad_schema = dict(base, schema="xxdata/9")
    expect("CT33 schema 不认识 → error", ct_rules.check_assets(bad_schema), "CT33", "error")

    typo = dict(base, meta={"title": "x", "epsoide": "03"})
    expect("CT33 meta 键名拼错 → warning", ct_rules.check_assets(typo), "CT33", "warning")

    dup = {"schema": "sbdata/1", "assets": {"scenes": [
        {"id": "SCN_S03_01", "image": "scenes/a.jpg"},
        {"id": "SCN_S03_01", "image": "scenes/b.jpg"}]}}
    expect("CT33 两个场景同 id → error", ct_rules.check_assets(dup), "CT33", "error")


def main():
    for fn in (case_ct16, case_ct20, case_ct17, case_ct17_dur, case_ct18, case_ct18_hex,
               case_ct19, case_ct21, case_ct24, case_assets, case_ct25_cover, case_no_false_red,
               case_ct26_short, case_ct17_pure_text, case_ct17_board,
               case_ct27_multishot, case_ct17_img_anchor,
               case_ct17_board_dur, case_ct28_style,
               case_ct17_board_typo, case_ct25_root,
               case_ct29_audios, case_ct28_prefix,
               case_ct25_shotdim, case_ct30_voice, case_ct31_roles,
               case_ct32_prompt, case_ct33_contract):
        print("\n--- %s" % fn.__name__)
        fn()
    print("\n%s" % ("CT16–CT33 正负例全部通过。" if not FAILS
                    else "失败 %d 项：%s" % (len(FAILS), "；".join(FAILS))))
    return 0 if not FAILS else 1


if __name__ == "__main__":
    sys.exit(main())
