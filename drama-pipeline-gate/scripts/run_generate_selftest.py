#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""run_generate.py 自检：造一份带 refs 的夹具，跑正反两个方向。

正向：3 张图都引用、时长合规 → exit 0
反向：超图上限 / 正文引用不存在的编号 / 音频单独用 / 文件不存在 / 超组时长 → exit 1 且逐类报出
档位时长：2.5 flash 单条参考 4–30 秒；2.0 生成时长与单条参考都是 4–15 秒
另测 --live → exit 2（尚未实现）

用法：python run_generate_selftest.py
"""
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
RUN = os.path.join(HERE, "run_generate.py")
OK = []
BAD = []


def check(name, cond, detail=""):
    (OK if cond else BAD).append(name)
    print("[%s] %s %s" % ("ok" if cond else "XX", name, detail))


def build(root, groups, meta=None):
    data = {"schema": "kwdata/1", "meta": meta or {"title": "ziJian", "episode": "01"}, "groups": groups}
    p = os.path.join(root, "kw.json")
    with open(p, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
    return p


def refs(n, kind="image"):
    if kind == "image":
        return [{"no": i, "kind": "image", "file": "img%d.png" % i} for i in range(1, n + 1)]
    return [{"no": i, "kind": kind, "file": "%s%d.bin" % (kind, i)} for i in range(1, n + 1)]


def run(kw, *extra):
    p = subprocess.run([sys.executable, RUN, kw] + list(extra), capture_output=True,
                       text=True, encoding="utf-8", errors="replace")
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def main():
    tmp = tempfile.mkdtemp(prefix="run_gen_")
    assets = os.path.join(tmp, "assets")
    os.makedirs(assets)
    for i in range(1, 13):
        open(os.path.join(assets, "img%d.png" % i), "wb").write(b"x")
    open(os.path.join(assets, "a.mp3"), "wb").write(b"x")
    open(os.path.join(assets, "a.mp4"), "wb").write(b"x")

    # 正向
    kw = build(tmp, [{"no": "U01", "duration": 10, "model": "2.0",
                      "prompt": " ".join("[图片%d]" % i for i in range(1, 4)),
                      "refs": refs(3)}])
    code, out = run(kw, "--assets", assets)
    check("正向可投喂 exit 0", code == 0, "(exit %d)" % code)
    check("正向不报阻塞", "[阻塞]" not in out)

    # 反向：五类阻塞一次给全
    bad = [
        {"no": "U02", "duration": 10, "model": "2.0",
         "prompt": " ".join("[图片%d]" % i for i in range(1, 11)), "refs": refs(10)},
        {"no": "U03", "duration": 10, "model": "2.0",
         "prompt": "[图片9]", "refs": [{"no": 1, "kind": "audio", "file": "no_such_audio.mp3"}]},
        {"no": "U04", "duration": 40, "model": "2.0",
         "prompt": "[图片1]", "refs": refs(1)},
    ]
    kw2 = build(tmp, bad)
    code, out = run(kw2, "--assets", assets)
    check("反向 exit 1", code == 1, "(exit %d)" % code)
    check("报超图上限", "上限 9 张" in out)
    check("报引用不存在编号", "[图片9]" in out)
    check("报音频单独用", "不能单独用" in out)
    check("报文件不存在", "文件不存在" in out)
    check("报超组时长", "拆组" in out)

    # --live 必须拒绝
    code, out = run(kw, "--live")
    check("--live 拒绝 exit 2", code == 2, "(exit %d)" % code)
    check("--live 列出待确认项", "尚未实现" in out)

    # 2.5 flash：单条参考 4–30 秒
    short = build(tmp, [{"no": "U05", "duration": 10, "model": "2.5 flash",
                         "prompt": "[图片1] [音频2]",
                         "refs": [{"no": 1, "kind": "image", "file": "img1.png"},
                                  {"no": 2, "kind": "audio", "file": "a.mp3", "sec": 3}]}])
    code, out = run(short, "--assets", assets)
    check("flash 3 秒参考被拦", code == 1 and "4–30 秒" in out, "(exit %d)" % code)

    ok4 = build(tmp, [{"no": "U06", "duration": 10, "model": "2.5 flash",
                       "prompt": "[图片1] [音频2]",
                       "refs": [{"no": 1, "kind": "image", "file": "img1.png"},
                                {"no": 2, "kind": "audio", "file": "a.mp3", "sec": 4}]}])
    code, out = run(ok4, "--assets", assets)
    check("flash 4 秒参考放行", code == 0, "(exit %d)" % code)

    # 2.0：生成时长 4–15 秒
    short20 = build(tmp, [{"no": "U07", "duration": 3, "model": "2.0",
                           "prompt": "[图片1]", "refs": refs(1)}])
    code, out = run(short20, "--assets", assets)
    check("2.0 三秒组被拦", code == 1 and "下限 4 秒" in out, "(exit %d)" % code)

    ok20 = build(tmp, [{"no": "U08", "duration": 4, "model": "2.0",
                        "prompt": "[图片1]", "refs": refs(1)}])
    code, out = run(ok20, "--assets", assets)
    check("2.0 四秒组放行", code == 0, "(exit %d)" % code)

    # 2.0：单条参考 4–15 秒
    ref20 = build(tmp, [{"no": "U09", "duration": 10, "model": "2.0",
                         "prompt": "[图片1] [视频2]",
                         "refs": [{"no": 1, "kind": "image", "file": "img1.png"},
                                  {"no": 2, "kind": "video", "file": "a.mp4", "sec": 3}]}])
    code, out = run(ref20, "--assets", assets)
    check("2.0 三秒参考被拦", code == 1 and "4–15 秒" in out, "(exit %d)" % code)

    # 2.5 三档同口径：组下限也是 4 秒（使用方 2026-11-26 平台侧实测更正）
    short25 = build(tmp, [{"no": "U10", "duration": 3, "model": "2.5",
                           "prompt": "[图片1]", "refs": refs(1)}])
    code, out = run(short25, "--assets", assets)
    check("2.5 三秒组被拦", code == 1 and "下限 4 秒" in out, "(exit %d)" % code)

    ok25 = build(tmp, [{"no": "U11", "duration": 4, "model": "2.5",
                        "prompt": "[图片1]", "refs": refs(1)}])
    code, out = run(ok25, "--assets", assets)
    check("2.5 四秒组放行", code == 0, "(exit %d)" % code)

    # --- V2.10 版本自动递增 ---
    import run_generate as RG
    vdir = os.path.join(tmp, "out_v")
    os.makedirs(vdir, exist_ok=True)
    open(os.path.join(vdir, "这位置我不让_S03-XZ-001_v1.mp4"), "w").close()
    open(os.path.join(vdir, "这位置我不让_S03-XZ-002_v3.mp4"), "w").close()
    check("版本扫描取最大值", RG._scan_max_version(vdir, "这位置我不让") == 3,
          str(RG._scan_max_version(vdir, "这位置我不让")))
    check("目录空 → 0", RG._scan_max_version(os.path.join(tmp, "none"), "这位置我不让") == 0)

    print("\n通过 %d 项，失败 %d 项" % (len(OK), len(BAD)))
    return 1 if BAD else 0


if __name__ == "__main__":
    sys.exit(main())
