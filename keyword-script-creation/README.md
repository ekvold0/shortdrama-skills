# keyword-script-creation · 关键词脚本生成

把分镜转成能直接粘进即梦／Seedance 的序列组关键词脚本：十字段、一体化视频提示词、
物理化动作情绪、四层音效、反向提示词（第 0 段 + 五段）、三次循环自检。

- 版本：**V2.12**｜校验规则 **CT00–CT33**
- 数据契约：`kwdata/1`（JSON 单一真值源，Excel 只是渲染件）

## 怎么用

```
分镜 data.json + 剧本
  ↓ 第 1 步 先算素材预算（三档上限，见 references/40-画面参数.md）
  ↓ 第 2 步 参考图编号表：[图片1]…[图片N] ↔ refs 双向对齐
  ↓ 第 3 步 逐组写十字段（多镜组用「镜N（起-止 秒）：」标记，一组 ≤6 镜）
  ↓ 第 4 步 四层音效 + 反向第 0 段（固定禁用句，逐字照抄）
  ↓ 第 5 步 三次循环自检 + verify.py 跑绿
  ↓ 第 6 步 build_xlsx.py 出 Excel
```

## 依赖

| 依赖 | 用在哪 |
|---|---|
| `openpyxl` | `build_xlsx.py`、`ingest.py` |
| `python-docx` | `ingest.py` 读剧本、`tests/build_libs_from_spec.py` |
| `ffmpeg` | 仅跨技能验收时需要（本技能自检不需要） |

## 自检与回归

```bash
python scripts/verify.py examples/example_kwdata.json            # 期望：error 0 warning 0
python scripts/verify.py <你的kwdata.json> --assets-root <资产目录> --source <剧本或source.json>
python tests/ct_v2_cases.py                                      # CT16–CT33 正负例，期望全 PASS
python tests/run_all.py                                          # 全量回归
```

`tests/run_all.py` 两步可选（缺素材自动跳过）：

- 四库重建：设 `KW_SPEC_DOCX=<规范.docx>` 或放 `tests/fixtures/关键词脚本生成规范.docx`
- 真实分镜 ingest：设 `KW_REAL_STORYBOARD` + `KW_REAL_SCRIPT`

`examples/example_shortfilm.json`（60 组 / 720 秒）是 `tests/make_shortfilm_fixture.py`
生成的夹具，删掉也没关系，跑一次 run_all 就会回来。

## 目录

| 路径 | 内容 |
|---|---|
| `SKILL.md` | 工作流、硬规则 1–43、文件地图 |
| `references/40-画面参数.md` | 素材上限三档、短镜头去路、档位怎么选、提示词字数预算 |
| `references/41/42` | 运镜库、打光库（取值域，别自造词） |
| `references/45` | 技法到参数的降维（英文技法名不得进正向提示词） |
| `references/56-武打物理参数与音效对齐.md` | 击中帧、1/4–1/5 倍速、四层音效与命中帧对齐 |
| `references/80-反向提示词-合规.md` | 第 0 段固定禁用 + 五段 |
| `templates/01–06` | 序列组字段、总览、自检、数据 schema、关键词表、角色卡生成单 |
| `lib/` | 四套技法库（att3/4/5/6）+ `cine_tech.json` 只读副本 |
| `scripts/` | `verify.py` / `build_xlsx.py` / `ingest.py` / `crosscheck.py` / `ct_rules.py` |

## 两个容易踩的坑

1. **档位要显式写**（`tier: "2.0"` / `"2.5-flash"` / `"2.5"`）：不写时名额校验会跳过，而投喂工具按 2.0 排，两边不一致。
2. **分镜图也占图片名额**（2.0 时 9 张里算一张），别按「不占名额」排预算。
