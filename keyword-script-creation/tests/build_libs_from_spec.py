# -*- coding: utf-8 -*-
"""从规范 DOCX 抽取附件3/4/5/6 共 280 条库，生成 lib/att*.py。

用法：
    python tests/build_libs_from_spec.py "F:\\AI短剧\\ai关键词生成规范\\即梦AI横屏短剧关键词脚本生成规范V1.5.docx"

说明：三份规范（横屏V1.5 / 竖屏V2.5 / 短篇V1.2）的四个附件逐字相同，
以 V1.5 为抽取源；若源文件缺失，脚本报错退出，不做降级。
"""
import os
import re
import sys
import json
from docx import Document
from docx.table import Table
from docx.text.paragraph import Paragraph

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass
from docx.oxml.ns import qn

HERE = os.path.dirname(os.path.abspath(__file__))
LIB = os.path.join(os.path.dirname(HERE), "lib")

ATT = {
    "十六、附件3：表情与微表情提示词标准库": ("att3_face.py", "ATT3", "face"),
    "十七、附件4：对话与台词提示词标准库": ("att4_dialogue.py", "ATT4", "dialogue"),
    "十八、附件5：声音设计提示词标准库": ("att5_sound.py", "ATT5", "sound"),
    "十九、附件6：分镜与切镜逻辑标准库（网剧·电视剧·动漫·电影）": ("att6_edit.py", "ATT6", "edit"),
}
ATT6_GENRE = ["网剧", "电视剧", "动漫", "通用"]
NUM_PREFIX = re.compile(r"^\s*\d+\s*[\.\、]\s*")


def iter_blocks(doc):
    for child in doc.element.body.iterchildren():
        if child.tag == qn("w:p"):
            yield Paragraph(child, doc)
        elif child.tag == qn("w:tbl"):
            yield Table(child, doc)


def norm_key(text):
    t = text.strip()
    # 四套库对“AI 执行”的写法不统一：AI执行 / AI台词执行 / AI音效执行 / AI技术执行
    if "执行" in t:
        return "AI执行"
    for k in ("定义", "情绪功能", "叙事功能", "适用场景", "代表作品"):
        if t.startswith(k):
            return k
    return None


def split_kv(text):
    for sep in ("：", ":"):
        if sep in text:
            k, v = text.split(sep, 1)
            key = norm_key(k)
            if key:
                return key, v.strip()
    return None, None


def parse(doc):
    """-> {att_title: [ {name, entries:[{n,title,...}]} ]}

    附件3 的条目格式并不统一：前四节有 定义/AI执行/情绪功能/适用场景，
    后六节只有一行特征描述。两种都保留：有标签的按标签存，无标签的存进“内容”。
    """
    out = {k: [] for k in ATT}
    cur_att = None
    cur_sec = None
    cur_entry = None
    last_key = None
    loose = []

    def flush_entry():
        nonlocal cur_entry, last_key, loose
        if cur_entry and cur_sec is not None:
            labeled = [k for k in cur_entry if k not in ("n", "title")]
            if labeled:
                if loose:
                    cur_entry["备注"] = " ".join(loose).strip()
            else:
                cur_entry["内容"] = " ".join(loose).strip()
            if len(cur_entry) > 2:
                cur_sec["entries"].append(cur_entry)
        cur_entry = None
        last_key = None
        loose = []

    for block in iter_blocks(doc):
        if not isinstance(block, Paragraph):
            continue
        text = block.text.strip()
        if not text:
            continue
        style = (block.style.name or "") if block.style is not None else ""
        if style.startswith("Heading") or style.startswith("标题"):
            level = style.replace("Heading", "").strip()
            title = text.strip()
            if level == "1":
                continue
            if level == "2":
                flush_entry()
                cur_sec = None
                cur_att = None
                for key in ATT:
                    if title.startswith(key.split("：")[0]) or key[:12] in title:
                        cur_att = key
                        break
                continue
            if level == "3" and cur_att:
                flush_entry()
                cur_sec = {"name": title, "entries": []}
                out[cur_att].append(cur_sec)
                continue
            if level == "4" and cur_sec is not None:
                flush_entry()
                cur_entry = {"n": len(cur_sec["entries"]) + 1,
                             "title": NUM_PREFIX.sub("", title).strip()}
                continue
            continue
        if cur_entry is None:
            continue
        # 一个段落里可能用软换行塞了多个字段（定义：…\nAI执行：…），逐行解析
        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            key, val = split_kv(line)
            if key:
                cur_entry[key] = (cur_entry.get(key, "") + val).strip()
                last_key = key
            elif last_key:
                cur_entry[last_key] = (cur_entry[last_key] + line).strip()
            else:
                loose.append(line)
    flush_entry()
    return out


def py_repr(obj, indent=0):
    pad = "    " * indent
    if isinstance(obj, dict):
        items = []
        for k, v in obj.items():
            items.append('%s    %r: %s' % (pad, k, py_repr(v, indent + 1)))
        return "{\n" + ",\n".join(items) + "\n" + pad + "}"
    if isinstance(obj, list):
        items = ['%s    %s' % (pad, py_repr(v, indent + 1)) for v in obj]
        return "[\n" + ",\n".join(items) + "\n" + pad + "]"
    return repr(obj)


HEADER = '''# -*- coding: utf-8 -*-
# 自动生成，勿手改：python tests/build_libs_from_spec.py <规范docx>
# 来源：%s
# 条目数：%d
'''


def main():
    if len(sys.argv) > 1:
        src = sys.argv[1]
    else:
        src = r"F:\AI短剧\ai关键词生成规范\即梦AI横屏短剧关键词脚本生成规范V1.5.docx"
    if not os.path.isfile(src):
        sys.exit("找不到规范文件：%s" % src)
    doc = Document(src)
    data = parse(doc)

    total = 0
    for att, (fname, varname, kind) in ATT.items():
        secs = data.get(att, [])
        n_all = sum(len(s["entries"]) for s in secs)
        if n_all == 0:
            sys.exit("附件抽取失败：%s" % att)
        for i, s in enumerate(secs):
            s["index"] = i + 1
            if kind == "edit":
                s["genre"] = ATT6_GENRE[i] if i < len(ATT6_GENRE) else "通用"
            for e in s["entries"]:
                e["section"] = s["name"]
                if kind == "edit":
                    e["genre"] = s["genre"]
        payload = {"source": os.path.basename(src), "kind": kind, "count": n_all, "sections": secs}
        body = HEADER % (os.path.basename(src), n_all) + "\n%s = %s\n" % (varname, py_repr(payload, 0))
        out = os.path.join(LIB, fname)
        with open(out, "w", encoding="utf-8") as f:
            f.write(body)
        print("%-14s %3d 条  %d 节  -> %s" % (varname, n_all, len(secs), fname))
        total += n_all

    # 索引：标题 -> (kind, section, n)
    idx = []
    for att, (fname, varname, kind) in ATT.items():
        for s in data.get(att, []):
            for e in s["entries"]:
                idx.append({"kind": kind, "genre": e.get("genre"), "section": s["name"],
                            "n": e["n"], "title": e["title"]})
    with open(os.path.join(LIB, "index.json"), "w", encoding="utf-8") as f:
        json.dump(idx, f, ensure_ascii=False, indent=1)
    print("合计 %d 条；索引 %d 条 -> lib/index.json" % (total, len(idx)))
    assert total == 280, "条目数不是 280，抽取有问题：%d" % total


if __name__ == "__main__":
    main()
