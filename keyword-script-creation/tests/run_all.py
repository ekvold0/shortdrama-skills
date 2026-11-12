# -*- coding: utf-8 -*-
"""一键回归：重建四库 → 校验库 → 构建/校验竖屏样例 → 构建/校验短篇夹具 → 覆盖检查。

用法：python tests/run_all.py
"""
import os
import sys
import json
import shutil
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)
PY = sys.executable
OUT = os.path.join(HERE, "_out")
SPEC = r"F:\AI短剧\ai关键词生成规范\即梦AI横屏短剧关键词脚本生成规范V1.5.docx"
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


def run(*args, expect=0):
    print("\n>>> %s" % " ".join(os.path.basename(a) if a.startswith(SKILL) else a for a in args))
    p = subprocess.run([PY] + list(args), cwd=SKILL, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    tail = "\n".join((p.stdout or "").strip().splitlines()[-6:])
    if tail:
        print(tail)
    if p.returncode != expect:
        print(p.stderr)
        raise SystemExit("步骤失败（exit=%d）：%s" % (p.returncode, args))
    return p


def main():
    if os.path.isdir(OUT):
        shutil.rmtree(OUT)
    os.makedirs(OUT)

    # 1. 四库可重建
    if os.path.exists(SPEC):
        run(os.path.join(HERE, "build_libs_from_spec.py"), SPEC, os.path.join(SKILL, "lib"))
        sys.path.insert(0, os.path.join(SKILL, "lib"))
        import refs  # noqa: E402
        counts = {k: refs.count(k) for k in ("att3", "att4", "att5", "att6")}
        assert counts == {"att3": 90, "att4": 70, "att5": 60, "att6": 60}, counts
        print("四库条数：", counts)
        e = refs.get_entry("att6", 5, "通用")
        assert "定义" in e and "AI执行" in e
        print("附件6 通用第5条：", e["title"])
    else:
        print("跳过四库重建：找不到 %s" % SPEC)

    # 2. 竖屏样例
    run(os.path.join(HERE, "make_source_fixture.py"))
    run(os.path.join(SKILL, "scripts", "build_xlsx.py"),
        os.path.join(SKILL, "examples", "example_kwdata.json"),
        "--out", os.path.join(OUT, "竖屏样例.xlsx"))
    run(os.path.join(SKILL, "scripts", "verify.py"),
        os.path.join(SKILL, "examples", "example_kwdata.json"), "--strict")
    run(os.path.join(SKILL, "scripts", "verify.py"),
        os.path.join(SKILL, "examples", "example_kwdata.json"),
        "--source", os.path.join(HERE, "source_example.json"), "--strict")

    # 3. 短篇夹具（60 组 / 720 秒 / 三幕 21.7-55-23.3）
    run(os.path.join(HERE, "make_shortfilm_fixture.py"))
    run(os.path.join(SKILL, "scripts", "build_xlsx.py"),
        os.path.join(SKILL, "examples", "example_shortfilm.json"),
        "--out", os.path.join(OUT, "短篇样例.xlsx"))
    run(os.path.join(SKILL, "scripts", "verify.py"),
        os.path.join(SKILL, "examples", "example_shortfilm.json"), "--strict")

    # 4. 覆盖检查必须能抓出漏掉的台词
    d = json.load(open(os.path.join(SKILL, "examples", "example_kwdata.json"), encoding="utf-8"))
    d["groups"][0]["shots"][0]["dialogue"] = ""
    bad = os.path.join(OUT, "missing_dialogue.json")
    json.dump(d, open(bad, "w", encoding="utf-8"), ensure_ascii=False)
    p = run(os.path.join(SKILL, "scripts", "verify.py"), bad,
            "--source", os.path.join(HERE, "source_example.json"))
    assert "coverage" in p.stdout, "覆盖检查没有报出缺台词"

    # 5. 真实分镜 ingest（存在才跑）
    sb = r"F:\AI短剧\分镜头脚本\《这位置我不让》\《这位置我不让》03集分镜头脚本.xlsx"
    sc = r"F:\AI短剧\剧本\《这位置我不让》\v4\《这位置我不让》20集短剧大纲_v4.docx"
    if os.path.exists(sb) and os.path.exists(sc):
        p = run(os.path.join(SKILL, "scripts", "ingest.py"), "--script", sc,
                "--storyboard", sb, "--out", os.path.join(OUT, "source_03.json"))
        assert "单元列 有" in p.stdout
        print("ingest 真实分镜通过")

    # 6. 跨表校验：分镜 ↔ 关键词 必须逐镜对得上
    cross = os.path.join(SKILL, "scripts", "crosscheck.py")
    p = run(cross, "--storyboard", os.path.join(HERE, "cross", "storyboard.json"),
            "--keyword", os.path.join(HERE, "cross", "kwdata.json"))
    assert "error 0，warning 0" in p.stdout, "跨表正例不该报"
    p = run(cross, "--storyboard", os.path.join(HERE, "cross", "storyboard.json"),
            "--keyword", os.path.join(HERE, "cross_bad", "kwdata.json"), expect=1)
    for code in ("X02", "X04", "X05", "X06", "X07"):
        assert code in p.stdout, "跨表负例漏报 %s" % code
    print("跨表校验正负例通过")

    print("\n全部回归通过。")


if __name__ == "__main__":
    main()
