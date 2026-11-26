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
# 规范文档（用来重建四库）默认找 tests/fixtures/ 下这份；也可用环境变量指过去。
# 找不到就跳过第一步，其余步骤不受影响。
SPEC = os.environ.get("KW_SPEC_DOCX") or os.path.join(HERE, "fixtures", "关键词脚本生成规范.docx")
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


def run(*args, expect=0):
    print("\n>>> %s" % " ".join(os.path.basename(a) if a.startswith(SKILL) else a for a in args))
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    p = subprocess.run([PY] + list(args), cwd=SKILL, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", env=env)
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

    # 5. 真实分镜 ingest（给了路径才跑；仓库里不带真实剧本）
    sb = os.environ.get("KW_REAL_STORYBOARD", "")
    sc = os.environ.get("KW_REAL_SCRIPT", "")
    if sb and sc and os.path.exists(sb) and os.path.exists(sc):
        p = run(os.path.join(SKILL, "scripts", "ingest.py"), "--script", sc,
                "--storyboard", sb, "--allow-drop",
                "--out", os.path.join(OUT, "source_03.json"))
        assert "单元列 有" in p.stdout
        print("ingest 真实分镜通过")
    else:
        print("跳过真实分镜 ingest：要跑就设 KW_REAL_STORYBOARD（分镜 xlsx）与 KW_REAL_SCRIPT（剧本 docx）")

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

    # 7. CT16–CT33 正负例（图像资产层 / 分镜图 / 多镜组 / 数据契约）
    run(os.path.join(HERE, "ct_v2_cases.py"))

    # 8. 两个技能共用的文件必须一致（引擎与技法库各带一份只读副本，漂移就会出错）
    import hashlib

    def _md5(p):
        with open(p, "rb") as fh:
            return hashlib.md5(fh.read()).hexdigest()

    pairs = [
        (os.path.join(SKILL, "scripts", "ct_rules.py"),
         os.path.join(os.path.dirname(SKILL), "storyboard-creation", "scripts", "ct_rules.py")),
        (os.path.join(SKILL, "lib", "cine_tech.json"),
         os.path.join(os.path.dirname(SKILL), "storyboard-creation", "scripts", "cine_tech.json")),
    ]
    for a, b in pairs:
        if not (os.path.exists(a) and os.path.exists(b)):
            print("跳过一致性检查（只装了一个技能）：%s" % os.path.basename(a))
            continue
        assert _md5(a) == _md5(b), "两份 %s 不一致：%s vs %s" % (os.path.basename(a), a, b)
    print("跨技能副本一致：ct_rules.py / cine_tech.json")

    print("\n全部回归通过。")


if __name__ == "__main__":
    main()
