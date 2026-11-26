# drama-pipeline-gate · 流程闸门与素材验收

不是「写内容」的技能，是**卡流程**的技能：六阶段五闸门、切镜读数、角色锚点核对、
投喂清单 dry-run、外部验收核对表。

- 版本：**V2.12**（技能自身序列自 v1.0 起；与两个内容技能同版号）
- 原则：**红灯 0 才可交付**；闸门数字写进交付说明，没验的项要明写「未验」

## 六阶段五闸门

```
①剧本 → ②分镜(+资产) → ③关键词 → ④投喂 → ⑤生成 → ⑥验收
        ↑闸门1        ↑闸门2     ↑闸门3   ↑闸门4   ↑闸门5
```

- 闸门 1：剧本 ↔ 分镜对齐，漏台词即红（`ingest.py` 不带 `--allow-drop` 会 exit 1）
- 闸门 2：分镜 `verify.py --assets-root` 跑绿，资产文件真在盘上
- 闸门 3：关键词 `verify.py` 跑绿（CT00–CT33）
- 闸门 4：`run_generate.py` 投喂清单 dry-run 无阻塞
- 闸门 5：`gate.py readback` + 外部验收核对表

## 依赖

| 依赖 | 必需性 | 用在哪 |
|---|---|---|
| `ffmpeg` / `ffprobe` | 必需（切镜、回读） | `gate.py`、`selftest.py`；可用 `GATE_FFMPEG` 指定 |
| `openpyxl` | 必需 | 读关键词 xlsx、写回读表 |
| `python-docx` | 必需 | `anchors.py init` 抽剧本人物表 |
| `scenedetect` + `opencv-python` | 可选 | 更敏感的切镜；没装自动退回 ffmpeg 并集路径 |

## 常用命令

```bash
# 角色锚点（两阶段：先登记名字，后补外貌/服装/道具）
python scripts/anchors.py init --script "<剧本.docx>" --project "《剧名》" --out "角色锚点.json"
python scripts/anchors.py harvest --kw "<关键词.xlsx>"
python scripts/anchors.py check
python scripts/anchors.py diff --script "<剧本.docx>"

# 验收
python scripts/gate.py anchors  <关键词.xlsx>
python scripts/gate.py readback <画布链接> <关键词目录>
python scripts/gate.py assets   <关键词目录>

# 投喂清单（不真发单）
python scripts/run_generate.py <关键词.json> --assets-root <资产目录> --out <输出目录>

# 自检
python scripts/selftest.py            # 切镜引擎自检（需 ffmpeg）
python scripts/run_generate_selftest.py
```

角色锚点找不到时会**显式报红**（不许静默空跑）。环境变量 `GATE_ANCHORS` 可指到别的锚点表；
画布节点组号正则可用 `GATE_GROUP_PATTERN` 覆盖（默认 `S(\d+)-XZ-(\d+)`）。

## 目录

| 路径 | 内容 |
|---|---|
| `SKILL.md` | 六阶段、五闸门、命令块、改判规则（v2.12） |
| `references/短剧生成流程_v1.md` | 流程单页（并行生成、成品落库、配音链路、镜数口径） |
| `references/角色锚点两阶段_v1.md` | 锚点表怎么建、怎么验、已知限制 |
| `references/外部验收核对表_v1.md` | 人评抽帧表、readback 比对、交付说明必备五件 |
| `references/改判记录_v1.md` | 触发线变更怎么记 |
| `templates/角色锚点表.json` | 三档 stage（names/look/full）示例，本身过 check |
| `scripts/` | `gate.py` / `anchors.py` / `run_generate.py` / `selftest.py` |

## 已知限制

- 镜数只能给「至少几镜」的判据，多切不提示、少切才报（`镜数待核`）。
- 画幅识别补了横屏 16:9 / 4:3，但 4:3 两档是按 16:9 等比推的，没有真片验证。
- `run_generate.py` 的 `--live` **未实现**（只做 dry-run），真发单需要账号授权与风控评估。
