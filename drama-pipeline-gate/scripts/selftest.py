"""闸门自检：用 ffmpeg 现造几段假素材，验证切镜/黑帧/账目这三条还能用。

    python scripts/selftest.py

为什么要有它：切镜靠 PySceneDetect / ffmpeg 两套引擎，阈值一改、依赖一升级，
判定的口径就可能悄悄漂走。这个脚本不依赖任何真实素材，每次跑都从零造视频。

退出码：0 = 全过；1 = 有断言失败；2 = 没有 ffmpeg，什么都没验（不算通过）。
"""
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import gate  # noqa: E402

COLORS = ["red", "green", "blue", "white"]
FAILS = []


def check(name, ok, detail=""):
    print("%s %s%s" % ("[ok]" if ok else "[FAIL]", name, ("  " + detail) if detail else ""))
    if not ok:
        FAILS.append(name)


def make_video(out, segments):
    """segments = [(颜色, 秒数), ...]"""
    ins, filt = [], []
    for i, (color, sec) in enumerate(segments):
        ins += ["-f", "lavfi", "-i", "color=c=%s:s=1080x1920:d=%.3f:r=24" % (color, sec)]
        filt.append("[%d:v]" % i)
    fc = "".join(filt) + "concat=n=%d:v=1:a=0,format=yuv420p" % len(segments)
    subprocess.run([gate.FF, "-y", "-hide_banner", "-loglevel", "error"] + ins
                   + ["-filter_complex", fc, "-c:v", "libx264", "-preset", "ultrafast", out],
                   check=True)


def main():
    if subprocess.run([gate.FF, "-version"], capture_output=True).returncode != 0:
        print("没有可用的 ffmpeg（装 imageio-ffmpeg 或设 GATE_FFMPEG），本次什么都没验。")
        return 2

    tmp = tempfile.mkdtemp(prefix="gate_selftest_")
    print("引擎：%s｜ffmpeg：%s" % (gate.shot_engine(), os.path.basename(gate.FF)))

    even = os.path.join(tmp, "even.mp4")
    make_video(even, [(c, 2.0) for c in COLORS])
    shots = gate.shot_durations(even)
    check("4 段等长素材切成 4 镜", len(shots) == 4, "实测 %d 镜 %s" % (len(shots), shots))
    check("每镜约 2 秒", all(abs(s - 2.0) < 0.3 for s in shots), str(shots))
    check("正常素材无黑帧", gate.black_frames(even) == [], str(gate.black_frames(even)))

    gap = os.path.join(tmp, "gap.mp4")
    make_video(gap, [("red", 2.0), ("black", 0.5), ("blue", 2.0)])
    blacks = gate.black_frames(gap)
    check("黑场能被抓到", len(blacks) >= 1, "%d 处 %s" % (len(blacks), blacks))

    # 账目：一个 2 组的关键词表 × 两段素材
    kw = os.path.join(tmp, "kw.xlsx")
    _make_kw(kw, [("S09-XZ-001", 4.0, 2), ("S09-XZ-002", 4.0, 2)])
    vroot = os.path.join(tmp, "videos", "09集")
    os.makedirs(vroot)
    make_video(os.path.join(vroot, "S09-XZ-001_仿真.mp4"), [("red", 2.0), ("blue", 2.0)])
    make_video(os.path.join(vroot, "S09-XZ-002_仿真.mp4"), [("green", 2.0), ("black", 0.5), ("white", 1.5)])
    summary, rows = gate.check_assets(os.path.join(tmp, "videos"), kw)
    check("素材齐、账目对", summary["缺素材"] == 0 and summary["时长超差"] == 0, str(summary))
    check("镜数：干净那组不该报待核", rows[0]["实际镜数"] == 2 and not rows[0]["镜数待核"], str(rows[0]["镜数差"]))
    # 0.5 秒黑场刚好够一镜，所以第二组会多切出一镜 —— 这是「待核」而不是「不合格」，
    # 镜数只提示人看一眼，真正判 FAIL 的是下面的黑帧。
    check("镜数：带黑场那组多切一镜 → 待核 1（预期）", summary["镜数待核"] == 1, str(summary["镜数待核"]))
    check("黑帧被判 FAIL", summary["有黑帧"] == 1 and summary["FAIL"] == 1, str(summary))

    print()
    if FAILS:
        print("自检未通过：%d 项 —— %s" % (len(FAILS), "；".join(FAILS)))
        return 1
    print("自检通过：切镜、黑帧、账目三条都在工作。")
    return 0


def _make_kw(path, groups):
    """造一份最小可用的关键词 xlsx（只填闸门要读的几列）。"""
    import openpyxl
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "关键词脚本"
    ws.append(["序列组编号", "时长", "微观分镜", "风格细节描述补充", "音频与对白设计", "反向提示词"])
    for gid, dur, n in groups:
        micro = "\n".join("%03d｜镜%d：测试画面" % (i + 1, i + 1) for i in range(n))
        style = "\n".join("%03d｜主光5600K，浅景深" % (i + 1) for i in range(n))
        ws.append([gid, "%.1f秒" % dur, micro, style, "本组无对白。", "【基础】文字、水印。"])
    wb.save(path)


if __name__ == "__main__":
    sys.exit(main())
