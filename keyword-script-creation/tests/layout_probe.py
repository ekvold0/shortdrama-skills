# -*- coding: utf-8 -*-
"""检查生成的主表行高是否够放换行文本（用 build_xlsx 同一套估算）。"""
import os
import sys

import openpyxl
from openpyxl.utils import get_column_letter

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(SKILL, "scripts"))
import build_xlsx as B  # noqa: E402

p = os.path.join(SKILL, "examples", "示例_关键词脚本.xlsx")
wb = openpyxl.load_workbook(p)
ws = wb["关键词脚本"]
widths = [ws.column_dimensions[get_column_letter(i)].width or 10 for i in range(1, ws.max_column + 1)]
print("widths", widths)
bad = 0
for r in range(2, ws.max_row + 1):
    vals = [ws.cell(r, c).value for c in range(1, ws.max_column + 1)]
    need = B.est_height(vals, widths)
    h = ws.row_dimensions[r].height or 15
    flag = "" if h >= need - 1 else "  <-- 偏矮"
    if flag:
        bad += 1
    print("row %d  height %s  need %s  ratio %.2f%s" % (r, h, need, h / need, flag))
print("偏矮行数:", bad)
if bad:
    sys.exit(1)
