# -*- coding: utf-8 -*-
"""
短剧素材链闸门 gate.py（通用版）

六个子命令：
  lint     <关键词xlsx>                        —— 关键词脚本静态体检（文字风险/计数风险/画幅/时长/语速/负向覆盖）
  anchors  <关键词xlsx ...>                    —— 人物锚点是否与 anchors.py 逐字一致
  readback <画布链接> <关键词xlsx|目录>        —— 提示词回读：画布实际提交 vs 脚本（丢字段/特征词/文字风险/分辨率）
  assets   <素材根目录> [关键词xlsx ...]        —— 素材回读（覆盖率/时长/规格），自动判 S1—S3
  sheet    <素材根目录> <关键词xlsx> <输出xlsx> —— 生成人评表（自动列已填，人工列待判）
  verdict  <人评表xlsx>                        —— 闸门判定：任一红灯或未判即 exit 1

用法示例：
  python gate.py lint     "work/《剧名》/《剧名》08集关键词脚本.xlsx"
  python gate.py readback "https://jimeng.jianying.com/ai-tool/ai-canvas/xxxx" "work/《剧名》" --out="work/判决/提示词回读报告.xlsx"
  python gate.py assets   "work/视频素材/《剧名》" "…08集关键词脚本.xlsx"
  python gate.py sheet    "work/视频素材/《剧名》" "…08集关键词脚本.xlsx" "work/流程/人评表_08.xlsx"
"""
import json
import os
import re
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8")

def _find_ffmpeg():
    """跨机器取 ffmpeg：环境变量 → imageio-ffmpeg → PATH → 名字兜底。"""
    env = os.environ.get("GATE_FFMPEG")
    if env and os.path.exists(env):
        return env
    try:
        import imageio_ffmpeg
        p = imageio_ffmpeg.get_ffmpeg_exe()
        if p and os.path.exists(p):
            return p
    except Exception:
        pass
    import shutil
    p = shutil.which("ffmpeg")
    return p or "ffmpeg"


FF = _find_ffmpeg()

DUR_TOL = 0.5          # 单组时长容差（秒）
GROUP_MIN, GROUP_MAX = 4.0, 15.0
CPS_LIMIT = 3.5        # 台词语速上限（字/秒）
W, H = 1080, 1920
# 生成门槛 720×1280，交付门槛 1080×1920（2026-10-27 判决）；480×854 视为不合格
RES_OK = {(1080, 1920), (720, 1280)}

# 要求“生成文字”的风险表达——命中即红灯
TEXT_RISK = re.compile(
    r"(写着|写着字|字样|文字|字幕|时间戳|水印|logo|LOGO|印有|刻着|标签上|牌子上写|日期|"
    r"[0-9]{4}[-年][0-9]{1,2}|[0-9]{2}:[0-9]{2})"
)
# 否定式会误伤：无文字／无 logo／不出现水印（前后两个方向都要剥）
TEXT_NEG = re.compile(
    r"((无|不带|不要|不出现|禁止|避免|不含|去除|零|没有任何)[^。；\n]{0,12}(文字|字符|logo|LOGO|水印|字幕|字样))"
    r"|((文字|字符|logo|LOGO|水印|字幕|字样)[^。；\n]{0,12}(不生成|不做|禁止|不含|留空|空白))"
)
# 计数风险——只盯“座位/人”，避免“一只手/一只眼”误报
COUNT_RISK = re.compile(r"([一二两三四五六七八九十]|\d+)\s*(个空座|个座位|座|排|个人|个人影)")
# 画面里出现“文字载体”时，必须写明空白处理
CARRIER = re.compile(r"(工牌|胸牌|吊牌|牌子|监控|显示屏|屏幕|海报|广告位)")
CARRIER_OK = re.compile(r"(空白|无字|不显示|无内容|纯色|不反光|虚焦)")
BANNED = re.compile(r"(BGM|bgm|淡入淡出|同上|渐变转场|慢动作)")
# “文字后期叠加”这类表述已全项目废止：既无执行价值，又会诱导模型画字
OVERLAY = re.compile(r"(后期叠加|后期合成文字|AI 不生成可读文字)")


# ---------------------------------------------------------------- 读取
def load_kw(path):
    import openpyxl
    wb = openpyxl.load_workbook(path, data_only=True)
    ws = wb["关键词脚本"]
    head = [str(c.value or "").strip() for c in ws[1]]
    groups = []
    for row in ws.iter_rows(min_row=2, values_only=True):
        if not row or not row[0]:
            continue
        rec = dict(zip(head, ["" if v is None else str(v) for v in row]))
        groups.append(rec)
    return head, groups


def parse_dur(s):
    m = re.search(r"([\d.]+)\s*秒", s or "")
    return float(m.group(1)) if m else None


def count_shots(micro):
    n = 0
    for line in (micro or "").split("\n"):
        if re.match(r"^\s*\d{3}\s*[｜|]", line.strip()):
            n += 1
    return n


# ---------------------------------------------------------------- S1—S3 素材回读
def probe(path):
    p = subprocess.run([FF, "-hide_banner", "-i", path], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    s = p.stderr
    d = re.search(r"Duration:\s*(\d+):(\d+):([\d.]+)", s)
    dur = int(d.group(1)) * 3600 + int(d.group(2)) * 60 + float(d.group(3)) if d else None
    v = re.search(r"Video:.*?(\d{2,5})x(\d{2,5})", s)
    w, h = (int(v.group(1)), int(v.group(2))) if v else (None, None)
    f = re.search(r"(\d+(?:\.\d+)?)\s*fps", s)
    fps = float(f.group(1)) if f else None
    return dur, w, h, fps


def scene_cuts(path):
    p = subprocess.run([FF, "-hide_banner", "-i", path, "-filter_complex",
                        "select='gt(scene,0.001)',showinfo", "-f", "null", "-"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    cuts = [float(m) for m in re.findall(r"pts_time:([\d.]+)", p.stderr)]
    cuts = sorted(set(round(c, 2) for c in cuts))
    n = 0
    last = -99.0
    for c in cuts:
        if c - last > 0.4:
            n += 1
            last = c
    return n


def check_assets(video_root, kw_path, json_out=None):
    _, groups = load_kw(kw_path)
    rows = []
    plan_total = act_total = 0.0
    for g in groups:
        gid = g["序列组编号"]
        ep = gid.split("-")[0][1:]           # S01 -> 01
        plan = parse_dur(g.get("时长", ""))
        plan_shots = count_shots(g.get("微观分镜", ""))
        d = os.path.join(video_root, "%s集" % ep)
        if not os.path.isdir(d):
            # 允许直接把某一集的目录当根传进来（如 …\视频素材\《这位置我不让》\05集）
            d = video_root
        hit = None
        if os.path.isdir(d):
            for fn in sorted(os.listdir(d)):
                if fn.startswith(gid) and fn.lower().endswith(".mp4"):
                    hit = os.path.join(d, fn)
                    break
        rec = {"组号": gid, "计划时长": plan, "计划镜数": plan_shots,
               "文件": os.path.basename(hit) if hit else "", "存在": bool(hit)}
        if hit:
            dur, w, hh, fps = probe(hit)
            real_shots = scene_cuts(hit)
            rec.update({"实际时长": round(dur, 2) if dur else None,
                        "偏差": round(dur - plan, 2) if dur and plan else None,
                        "实际镜数": real_shots,
                        "宽": w, "高": hh, "fps": round(fps, 1) if fps else None})
            plan_total += plan or 0
            act_total += dur or 0
        else:
            rec.update({"实际时长": None, "偏差": None, "实际镜数": None, "宽": None, "高": None, "fps": None})
        # 判定
        fails = []
        if not rec["存在"]:
            fails.append("缺素材")
        else:
            if rec["偏差"] is not None and abs(rec["偏差"]) > DUR_TOL:
                fails.append("时长超差")
            # 镜数只做“待核”提示，不计 FAIL：ffmpeg 场景检测对运动/浅景深会过度切分
            # （实测 5 镜的设计被切成 28 个切点），无法作为验收依据，须人评确认。
            rec["镜数待核"] = rec["实际镜数"] != rec["计划镜数"]
            if (rec["宽"], rec["高"]) not in RES_OK:
                fails.append("规格不符")
        rec["自动判定"] = "PASS" if not fails else "FAIL"
        rec["问题"] = "／".join(fails)
        rows.append(rec)

    summary = {
        "组数": len(rows),
        "计划总时长": round(plan_total, 2),
        "实际总时长": round(act_total, 2),
        "总偏差": round(act_total - plan_total, 2),
        "缺素材": sum(1 for r in rows if not r["存在"]),
        "时长超差": sum(1 for r in rows if "时长超差" in r["问题"]),
        "镜数待核": sum(1 for r in rows if r.get("镜数待核")),
        "规格不符": sum(1 for r in rows if "规格不符" in r["问题"]),
        "PASS": sum(1 for r in rows if r["自动判定"] == "PASS"),
        "FAIL": sum(1 for r in rows if r["自动判定"] == "FAIL"),
    }
    if json_out:
        with open(json_out, "w", encoding="utf-8") as f:
            json.dump({"summary": summary, "rows": rows}, f, ensure_ascii=False, indent=1)
    return summary, rows


# ---------------------------------------------------------------- lint
def lint(kw_path):
    head, groups = load_kw(kw_path)
    red, amber = [], []
    for g in groups:
        gid = g.get("序列组编号", "?")
        body = " ".join([g.get("正向提示词", ""), g.get("场景与妆造简述", ""), g.get("风格细节描述补充", "")])
        neg = g.get("反向提示词", "")
        cam = g.get("画面参数", "")
        audio = g.get("音频与对白设计", "")
        dur = parse_dur(g.get("时长", ""))

        # 画幅已全局固定为 9:16｜1080×1920，不再逐组校验（2026-11-04 用户裁定）
        if dur is None:
            red.append((gid, "时长无法解析"))
        elif not (GROUP_MIN <= dur <= GROUP_MAX):
            red.append((gid, "组时长 %.1fs 越界（%.0f—%.0f）" % (dur, GROUP_MIN, GROUP_MAX)))
        # 风格细节列必须写画面质感（颗粒/色温/材质/景深），不是情绪或表演分级
        style = str(g.get("风格细节描述补充", "") or "")
        slines = [x for x in style.split("\n") if x.strip()]
        micro_raw = str(g.get("微观分镜", "") or "")
        mlines = [x for x in micro_raw.split("\n")
                  if x.strip() and not x.strip().startswith("衔接备注")]
        # 混合口径：不要求行数相等，但镜号集合必须一致（兼容一组一格与一镜一行两种写法）
        _mshots = re.findall(r"(?<!\d)(?:S\d{2}-)?(\d{3})｜", micro_raw)
        _sshots = re.findall(r"(?<!\d)(?:S\d{2}-)?(\d{3})｜", style)
        if _mshots and _sshots and set(_mshots) != set(_sshots):
            _msg = "微观分镜与风格细节的镜号集合不一致（微观 %d 个／风格 %d 个）" % (len(set(_mshots)), len(set(_sshots)))
            red.append((gid, _msg))
        elif slines and mlines and not _mshots and len(slines) != len(mlines):
            red.append((gid, "风格细节 %d 行 ≠ 微观分镜 %d 行" % (len(slines), len(mlines))))
        for ln in slines:
            if not re.match(r"^(S\d{2}-\d{3}|\d{3})｜", ln):
                red.append((gid, "风格细节未以「镜号｜…」开头：%s" % ln[:20]))
                break
        if slines:
            if not re.search(r"\d{4}\s*K", style):
                red.append((gid, "风格细节缺色温（应写 5600K／3000K）"))
            if "景深" not in style:
                red.append((gid, "风格细节缺景深"))
            if re.search(r"[（(]\s*[ABC]\s*级|[）)]级", style):
                red.append((gid, "风格细节混入表演分级（A／B／C 级应只留在分镜表）"))
            if re.search(r"情绪|表演|心情", style):
                red.append((gid, "风格细节混入情绪／表演描述，应写颗粒、色温、材质、景深"))
        alines = [x for x in str(audio or "").split("\n") if x.strip()]
        if alines:
            _pos_txt = str(g.get("正向提示词", "") or "")
            _npos = len(re.findall(r"【台词】", _pos_txt))
            _naud = len(re.findall(r"“[^”]*”\s*\d+\s*字", str(audio or "")))
            # R2：正向不写台词时以音频列为准（EP07 写法），写了才要求同数
            if _npos and _npos != _naud:
                red.append((gid, "正向台词 %d 条 ≠ 音频台词 %d 条（两列必须同源同数）" % (_npos, _naud)))
            # EP07 写法：一行一句台词 + 末尾账目行，不要求与镜头行数一致
            _is07 = any(("本组台词字数" in x) or ("组时长" in x and "字；" in x) for x in alines)
            if not _is07 and len(alines) != len(mlines):
                red.append((gid, "音频 %d 行 ≠ 微观分镜 %d 行" % (len(alines), len(mlines))))
            if not _is07:
                for ln in alines:
                    if "【音效】" not in ln:
                        red.append((gid, "音频行缺【音效】：%s" % ln[:16]))
                        break
            if _npos and _naud == 0:
                red.append((gid, "正向写了台词，但音频列没有可识别的台词行——疑似全写成底噪"))
        if "“" in str(g.get("分层音效设计", "") or ""):
            red.append((gid, "分层音效里出现对白引号；台词只能写在音频与对白设计列"))
        # 真实语速：从音频列的（起—止）+“N字”算出，不依赖“每秒 N 字”这种写法
        for m in re.finditer(r"（([\d.]+)—([\d.]+)）【台词】[^；]*?(\d+)字", str(audio or "")):
            s0, s1, c = float(m.group(1)), float(m.group(2)), int(m.group(3))
            span = s1 - s0
            if span > 0 and c / span > CPS_LIMIT + 0.001:
                red.append((gid, "实测语速 %.2f 字/秒（%d字/%.1fs）超上限 %.1f"
                            % (c / span, c, span, CPS_LIMIT)))
        # EP07 写法：（起—止）紧跟角色与台词，同样校验实测语速
        for m in re.finditer(r"([\d.]+)—([\d.]+)\s+[^\n“]{0,12}“[^”]*”\s*(\d+)\s*字", str(audio or "")):
            s0, s1, c = float(m.group(1)), float(m.group(2)), int(m.group(3))
            span = s1 - s0
            if span > 0 and c / span > CPS_LIMIT + 0.001:
                red.append((gid, "实测语速 %.2f 字/秒（%d字/%.1fs）超上限 %.1f"
                            % (c / span, c, span, CPS_LIMIT)))
        for m in re.finditer(r"每秒\s*([\d.]+)\s*字", audio):
            if float(m.group(1)) > CPS_LIMIT:
                red.append((gid, "语速 %s 字/秒超上限 %.1f" % (m.group(1), CPS_LIMIT)))
        clean = TEXT_NEG.sub("", body)
        for m in TEXT_RISK.finditer(clean):
            red.append((gid, "文字风险：「%s」——要求生成文字，应改为“卡面／屏幕留空”" % m.group(0)))
        if CARRIER.search(body) and not CARRIER_OK.search(body):
            red.append((gid, "文字载体（%s）未写“空白／无字”处理"
                        % "、".join(sorted(set(CARRIER.findall(body))))))
        for m in BANNED.finditer(body):
            red.append((gid, "禁用表达：「%s」" % m.group(0)))
        for m in OVERLAY.finditer(body):
            red.append((gid, "废止表述：「%s」——删掉，改写成“卡面留空／无字符”" % m.group(0)))
        if "文字" not in neg or "水印" not in neg:
            red.append((gid, "反向提示词缺「文字」「水印」拦截"))
        if "°" in neg:
            red.append((gid, "反向提示词含半角度数符 °"))
        cnt = COUNT_RISK.findall(body)
        if cnt:
            amber.append((gid, "计数需人评：" + "、".join("".join(c) for c in cnt[:4])))

    print("=" * 60)
    print("关键词体检：%s" % os.path.basename(kw_path))
    print("组数 %d｜红灯 %d 条｜黄灯 %d 条" % (len(groups), len(red), len(amber)))
    for gid, msg in red:
        print("  [红] %s  %s" % (gid, msg))
    for gid, msg in amber:
        print("  [黄] %s  %s" % (gid, msg))
    return red, amber


# ---------------------------------------------------------------- 人评表
def make_sheet(video_root, kw_path, out_xlsx):
    import openpyxl
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.worksheet.datavalidation import DataValidation

    summary, rows = check_assets(video_root, kw_path)
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "人评表"
    cols = ["组号", "文件", "计划时长", "实际时长", "偏差", "计划镜数", "实际镜数",
            "宽", "高", "自动判定", "自动问题", "人物一致", "动作完成", "文字水印", "备注"]
    ws.append(cols)
    for c in ws[1]:
        c.font = Font(bold=True, size=10, color="FFFFFF")
        c.fill = PatternFill("solid", fgColor="305496")
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

    for r in rows:
        ws.append([r["组号"], r["文件"], r["计划时长"], r["实际时长"], r["偏差"],
                   r["计划镜数"], r["实际镜数"], r["宽"], r["高"], r["自动判定"], r["问题"],
                   "未判", "未判", "未判", ""])
    dv = DataValidation(type="list", formula1='"通过,不通过,未判"', allow_blank=False)
    ws.add_data_validation(dv)
    n = len(rows) + 1
    dv.add("L2:N%d" % n)
    for row in ws.iter_rows(min_row=2, max_row=n):
        for c in row:
            c.alignment = Alignment(vertical="center", wrap_text=True)
        if row[9].value == "FAIL":
            row[9].fill = PatternFill("solid", fgColor="FFC7CE")
        else:
            row[9].fill = PatternFill("solid", fgColor="C6EFCE")
    for i, w in enumerate([12, 30, 9, 9, 8, 8, 8, 7, 7, 9, 18, 9, 9, 9, 40], 1):
        ws.column_dimensions[openpyxl.utils.get_column_letter(i)].width = w
    ws.freeze_panes = "A2"

    ws2 = wb.create_sheet("规则")
    notes = [
        ["列", "怎么判", "红灯条件"],
        ["自动判定", "脚本算，不用改", "缺素材／时长偏差>0.5s／镜数不符／非1080×1920"],
        ["人物一致", "同角色跨组是否同一人脸、发型、服装、工牌位", "出现换脸或明显不同人"],
        ["动作完成", "三帧里主体动作是否完成、有没有多余物、计数对不对", "动作缺失／计数不符／出现剧本没有的道具"],
        ["文字水印", "画面里是否出现生成文字、时间戳、水印、logo", "只要是生成进去的字就算不通过"],
        ["备注", "写清楚第几帧、什么问题，便于回改提示词", ""],
        ["", "", ""],
        ["判定", "verdict 子命令：任一 FAIL 或任一列未判/不通过 → exit 1", ""],
        ["修复路径", "文字→删掉提示词里的文字描述并加负向拦截；计数→改描述避免精确数字；规格→检查生成设置", ""],
    ]
    for r in notes:
        ws2.append(r)
    ws2.column_dimensions["A"].width = 14
    ws2.column_dimensions["B"].width = 62
    ws2.column_dimensions["C"].width = 46
    for c in ws2[1]:
        c.font = Font(bold=True)

    wb.save(out_xlsx)
    print("人评表 → %s" % out_xlsx)
    print("自动判定：PASS %d／FAIL %d｜计划 %.1fs 实际 %.1fs（%+.1fs）"
          % (summary["PASS"], summary["FAIL"], summary["计划总时长"], summary["实际总时长"], summary["总偏差"]))
    return summary, rows


# ---------------------------------------------------------------- 闸门判定
def verdict(xlsx_path):
    import openpyxl
    wb = openpyxl.load_workbook(xlsx_path, data_only=True)
    ws = wb["人评表"]
    head = [str(c.value or "") for c in ws[1]]
    idx = {h: i for i, h in enumerate(head)}
    bad = []
    n = 0
    for row in ws.iter_rows(min_row=2, values_only=True):
        if not row or not row[0]:
            continue
        n += 1
        gid = row[idx["组号"]]
        auto = str(row[idx["自动判定"]] or "")
        if auto != "PASS":
            bad.append((gid, "自动：" + str(row[idx["自动问题"]] or auto)))
        for col in ("人物一致", "动作完成", "文字水印"):
            v = str(row[idx[col]] or "未判")
            if v == "未判":
                bad.append((gid, col + " 未判"))
            elif v != "通过":
                bad.append((gid, col + " 不通过"))
    print("=" * 60)
    print("闸门判定：%s" % os.path.basename(xlsx_path))
    print("受检 %d 组｜红灯 %d 条" % (n, len(bad)))
    for gid, msg in bad:
        print("  [红] %s  %s" % (gid, msg))
    if bad:
        print("结论：不放行（红灯 %d 条）" % len(bad))
        return 1
    print("结论：放行")
    return 0


VARIANTS = re.compile(
    r"(深蓝涤棉工服（|黑色双肩包|小方布标|小logo|实习两字|门店圆形标志|银镯子|栗色烫卷短发|栗色枯黄卷发|深蓝发白的)")
NAMES = ("林晓", "王桂兰", "老周", "陈姐")


def anchors_check(paths):
    """逐组核对人物锚点是否与 anchors.py 逐字一致、且无旧措辞残留。"""
    import anchors as A

    total = ok = 0
    bad = []
    for p in paths:
        _, groups = load_kw(p)
        for g in groups:
            prompt = g.get("正向提示词", "")
            scene = g.get("场景与妆造简述", "")
            text = prompt + "\n" + scene
            total += 1
            problems = []
            # 只校验“定义型提及”（林晓（…）／林晓：…）；分镜清单里的“前排陈姐”
            # 这类叙述性提及不计。
            for name in NAMES:
                canon = A.ALL.get({"林晓": "LIN", "王桂兰": "WANG", "老周": "ZHOU", "陈姐": "CHEN"}[name])
                desc = canon.split("，", 1)[1] if "，" in canon else canon
                if re.search(re.escape(name) + r"[（(：:]", text) and canon not in text and desc not in text:
                    problems.append("%s 锚点未逐字复写" % name)
            hits = sorted(set(m.group(0) for m in VARIANTS.finditer(text)))
            if hits:
                problems.append("旧措辞残留：" + "、".join(hits))
            if problems:
                bad.append((os.path.basename(p), g.get("序列组编号", "?"), problems))
            else:
                ok += 1
    print("=" * 60)
    print("锚点单一源校验：%d 集 / %d 组" % (len(paths), total))
    print("逐字一致：%d 组｜不一致：%d 组" % (ok, len(bad)))
    for f, gid, problems in bad[:20]:
        print("  [红] %s %s  %s" % (f, gid, " ｜ ".join(problems)))
    if len(bad) > 20:
        print("  …… 另有 %d 组" % (len(bad) - 20))
    print("结论：%s" % ("通过" if not bad else "不通过"))
    return 0 if not bad else 1


# ---------------------------------------------------------------- 提示词回读
CANVAS_KEY = '{"__aiCanvasDraftBffResponse"'
SUBMIT_FIELDS = ["画面参数", "正向提示词", "场景与妆造简述", "微观分镜",
                 "风格细节补充", "音频与对白设计", "分层音效设计", "反向提示词"]
# 人物外形特征词：脚本里出现该角色，提交文本就必须带上这些词
FEAT = {
    "林晓": ["深蓝", "工牌", "耳机"],
    "王桂兰": ["暗红", "碎花"],
    "陈姐": ["衬衫", "短发"],
    "老周": ["后视镜"],
}
POS_CUT = ("【反向提示词", "【通用禁用项", "禁用项】", "【画面质量禁用项】")


def fetch_canvas(url, cache=None, offline=False):
    """取即梦画布分享页内嵌的 draft_json，返回 (项目信息, {标题: [提交记录]})。"""
    if offline:
        if not cache or not os.path.exists(cache):
            raise SystemExit("--offline 需要已有的缓存文件")
        obj = json.load(open(cache, encoding="utf-8"))
    else:
        import urllib.request
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        html = urllib.request.urlopen(req, timeout=40).read().decode("utf-8", "replace")
        i = html.find(CANVAS_KEY)
        if i < 0:
            raise SystemExit("页面里没有画布数据：链接可能失效，或不是公开分享链接")
        depth = 0
        for j in range(i, len(html)):
            if html[j] == "{":
                depth += 1
            elif html[j] == "}":
                depth -= 1
                if depth == 0:
                    break
        obj = json.loads(html[i:j + 1])
        if cache:
            os.makedirs(os.path.dirname(cache), exist_ok=True)
            json.dump(obj, open(cache, "w", encoding="utf-8"), ensure_ascii=False)
    data = obj["__aiCanvasDraftBffResponse"]["data"]
    proj = data.get("project") or {}
    subs = {}
    for n in json.loads(data["draft_json"]).get("nodes") or []:
        if n.get("type") != "video":
            continue
        d = n.get("data") or {}
        title = (d.get("title") or "").strip()
        m = re.match(r"S(\d+)-XZ-(\d+)", title)
        if not m:
            continue
        gd = d.get("generationDraft") or {}
        cs = gd.get("contentSettings") or {}
        text = "".join(p.get("text", "") for p in (gd.get("parts") or []))
        subs.setdefault(title, []).append({
            "text": text, "len": len(text), "patch": "_补帧" in title,
            "res": cs.get("resolution"), "model": cs.get("modelName"),
            "dur": cs.get("durationSeconds"),
        })
    return proj, subs


def positive_part(txt):
    marks = [i for i in (txt.find(m) for m in POS_CUT) if i > 0]
    return txt[:min(marks)] if marks else txt


def readback(url, kw_paths, out=None, offline=False, cache=None):
    """关键词脚本 vs 画布实际提交：字段有没有丢、锚点有没有带、有没有文字风险、分辨率。"""
    if len(kw_paths) == 1 and os.path.isdir(kw_paths[0]):
        d = kw_paths[0]
        kw_paths = sorted(
            os.path.join(d, f) for f in os.listdir(d)
            if f.endswith("集关键词脚本.xlsx") and not f.startswith("~$")
            and os.path.getsize(os.path.join(d, f)) > 10240)
    proj, subs = fetch_canvas(url, cache=cache, offline=offline)
    print("画布：%s｜可识别编号组 %d 个｜视频节点 %d 个"
          % (proj.get("name"), len(subs), sum(len(v) for v in subs.values())))

    rows, red, amber = [], [], []
    for p in kw_paths:
        _, groups = load_kw(p)
        for g in groups:
            sid = g.get("序列组编号", "")
            cand = subs.get(sid) or []
            main = [c for c in cand if not c["patch"]]
            sub = main[0] if main else (cand[0] if cand else None)
            script_all = sum(len(g.get(h, "")) for h in SUBMIT_FIELDS)
            rec = {"组": sid, "有素材": "是" if cand else "否",
                   "补帧": sum(1 for c in cand if c["patch"]),
                   "脚本字数": script_all,
                   "提交字数": sub["len"] if sub else 0,
                   "长度比": round(sub["len"] / script_all, 3) if (sub and script_all) else 0,
                   "丢字段": "", "特征词": "", "文字风险": "",
                   "分辨率": (sub["res"] if sub else ""), "模型": (sub["model"] if sub else "")}
            if not sub:
                amber.append((sid, "未生成", "画布上没有这一组的视频节点"))
                rows.append(rec)
                continue
            txt, pos = sub["text"], positive_part(sub["text"])
            lost = [h for h in SUBMIT_FIELDS if h not in txt]
            rec["丢字段"] = "、".join(lost)
            for h in lost:
                red.append((sid, "丢字段", h))
            feats = []
            for name, toks in FEAT.items():
                if name in g.get("正向提示词", "") or name in g.get("场景与妆造简述", ""):
                    miss = [t for t in toks if t not in txt]
                    feats.append("%s%s" % (name, "✓" if not miss else "✗" + "".join(miss)))
                    if miss:
                        red.append((sid, "特征词缺失", name + "：" + "、".join(miss)))
            rec["特征词"] = " ".join(feats) or "-"
            risk = [w for w in ("后期叠加", "字样", "文字") if w in pos]
            if risk:
                rec["文字风险"] = "、".join(risk)
                red.append((sid, "文字风险", rec["文字风险"]))
            if sub["res"] not in ("1080p", "1080P", "720p", "720P"):
                amber.append((sid, "分辨率", str(sub["res"])))
            rows.append(rec)

    print("%-16s %-4s %-5s %-7s %-7s %-6s %-8s %s"
          % ("组", "素材", "补帧", "长度比", "丢字段", "文字", "特征词", "分辨率"))
    for r in rows:
        print("%-16s %-4s %-5d %-7s %-7s %-6s %-8s %s"
              % (r["组"], r["有素材"], r["补帧"], r["长度比"],
                 ("缺" + r["丢字段"]) if r["丢字段"] else "齐",
                 r["文字风险"] or "-", r["特征词"], r["分辨率"] or "-"))
    print("\n红灯 %d 条｜黄灯 %d 条" % (len(red), len(amber)))
    for sid, k, v in red[:15]:
        print("  [红] %s %s：%s" % (sid, k, v))
    if len(red) > 15:
        print("  …… 另有 %d 条" % (len(red) - 15))
    kinds = {}
    for sid, k, v in amber:
        kinds.setdefault((k, v), []).append(sid)
    for (k, v), ids in kinds.items():
        print("  [黄] %s（%s）%d 组" % (k, v, len(ids)))

    if out:
        import openpyxl
        from openpyxl.styles import Alignment, Font, PatternFill
        from openpyxl.utils import get_column_letter
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "提示词回读"
        head = ["组", "有素材", "补帧", "脚本字数", "提交字数", "长度比",
                "丢字段", "特征词", "文字风险", "分辨率", "模型"]
        ws.append(head)
        for r in rows:
            ws.append([r.get(h, "") for h in head])
        ws2 = wb.create_sheet("判定口径")
        for ln in [
            "提示词回读：画布实际提交 vs 关键词脚本",
            "",
            "数据来源：即梦画布分享页内嵌 draft_json → video 节点 generationDraft.parts（提交文本）与 contentSettings（分辨率/模型）。",
            "红灯：丢字段（十字段里有、提交里没有）、特征词缺失（角色出现但外形词没带过去）、文字风险（正向段出现“文字/字样/后期叠加”）。",
            "黄灯：该组还没生成；分辨率低于 720p。",
            "分辨率在平台设置里选，提示词管不了——生成门槛 720p，交付再超分到 1080p。",
        ]:
            ws2.append([ln])
        for sheet in (ws, ws2):
            for i in range(1, max(sheet.max_column, 8) + 1):
                sheet.column_dimensions[get_column_letter(i)].width = 16 if i > 1 else 12
        for c in ws[1]:
            c.font = Font(bold=True, color="FFFFFF")
            c.fill = PatternFill("solid", fgColor="44546A")
            c.alignment = Alignment(horizontal="center")
        ws.freeze_panes = "A2"
        os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
        wb.save(out)
        print("报告：", out)
    return 0 if not red else 1


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    cmd = argv[1]
    if cmd == "anchors":
        return anchors_check(argv[2:])
    if cmd == "readback":
        args = [a for a in argv[2:] if not a.startswith("--")]
        opts = dict(a[2:].split("=", 1) if "=" in a else (a[2:], True)
                    for a in argv[2:] if a.startswith("--"))
        if len(args) < 2:
            print("用法：gate.py readback <画布链接> <关键词xlsx|目录> [--out=报告.xlsx] [--offline] [--cache=路径]")
            return 2
        return readback(args[0], args[1:], out=opts.get("out"),
                        offline=bool(opts.get("offline")),
                        cache=opts.get("cache") or os.path.join(
                            os.environ.get("TEMP", "."), "gate_canvas_cache.json"))
    if cmd == "lint":
        red, amber = lint(argv[2])
        return 1 if red else 0
    if cmd == "assets":
        summary, rows = check_assets(argv[2], argv[3] if len(argv) > 3 else None)
        print(json.dumps(summary, ensure_ascii=False, indent=1))
        return 1 if summary["FAIL"] else 0
    if cmd == "sheet":
        make_sheet(argv[2], argv[3], argv[4])
        return 0
    if cmd == "verdict":
        return verdict(argv[2])
    print("未知命令：%s" % cmd)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
