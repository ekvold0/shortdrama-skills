# shortdrama-skills

把一个剧本变成"喂给 AI 视频工具能照着生成"的交付物，并且能验收它到底有没有照着生成——三个 agent skill，串起来是一条完整产线。

| 技能 | 一句话 | 输入 → 输出 |
|---|---|---|
| [`storyboard-creation`](storyboard-creation/SKILL.md) | 剧本 → 分镜头脚本 | 剧本文档 → 分镜 xlsx（含故事梗概、结构方案、角色/空间锚点、AI 生成单元、时长账目、自检记录） |
| [`keyword-script-creation`](keyword-script-creation/SKILL.md) | 分镜 → 序列组关键词脚本 | 剧本 + 分镜 → 关键词 xlsx（十字段、一体化视频提示词、物理化动作情绪、四层音效、五段反向提示词） |
| [`drama-pipeline-gate`](drama-pipeline-gate/SKILL.md) | 交付前验收闸门 | 关键词脚本 / 素材目录 → 红灯数、回读报告、人评表 |

```
剧本 ──storyboard-creation──▶ 分镜脚本 ──keyword-script-creation──▶ 关键词脚本 ──即梦/Seedance──▶ 素材
                                    ▲                                      ▲                        │
                                    └────────── drama-pipeline-gate ───────┴────────────────────────┘
                                          lint / anchors / readback / assets / verdict
```

闸门是三个里唯一"会拦人"的：红灯 ≠ 0 不许交付，也不许先交付后补跑。

## 安装

这些技能就是带 YAML frontmatter 的 `SKILL.md` 目录，任何按该约定加载技能的 agent 都能用（DSH、Claude Code 等）。把三个目录整体拷到你的技能目录即可：

```powershell
# DSH
Copy-Item -Recurse .\storyboard-creation,.\keyword-script-creation,.\drama-pipeline-gate "$env:USERPROFILE\.dsh\skills\"

# Claude Code（个人技能）
Copy-Item -Recurse .\storyboard-creation,.\keyword-script-creation,.\drama-pipeline-gate "$env:USERPROFILE\.claude\skills\"
```

也可以只放到某个项目的 `.claude/skills/` 下，跟着仓库走。

## 依赖

- Python 3.10+，`openpyxl`（生成/读取 xlsx）
- 素材回读（`gate.py assets`）需要 `ffmpeg`：取 `GATE_FFMPEG` 环境变量 → `imageio-ffmpeg` → PATH
- 画布回读（`gate.py readback`）需要能访问即梦画布链接的网络环境

## 快速开始

1. **出分镜**：把剧本丢给 agent，说"出分镜"或"按 storyboard-creation 做第 1 集"。它会先给 2—3 个叙事结构方案让你选，选定后才写镜头。
2. **出关键词**：把分镜交给 agent，说"按关键词技能做第 1 集"。它会先对齐账目（组数/时长/台词秒），对不上不写。
3. **交付前跑闸门**：

   ```powershell
   # 把闸门脚本复制进项目，形成 流程/ 目录
   Copy-Item .\drama-pipeline-gate\scripts\*.py .\流程\

   python 流程\gate.py lint    "work\《剧名》08集关键词脚本.xlsx"
   python 流程\gate.py anchors "work\《剧名》08集关键词脚本.xlsx"
   # 素材生成之后
   python 流程\gate.py assets  "work\视频素材\《剧名》" "work\《剧名》08集关键词脚本.xlsx"
   python 流程\gate.py verdict "work\流程\人评表_08.xlsx"
   ```

   退出码非 0 就是有红灯，逐条修完再跑。

## 目录结构

```
storyboard-creation/
  SKILL.md              技能主体：何时用、怎么做、交付物清单
  references/           内核、覆盖层、竖屏/横屏/短篇三种模式、表情与台词库、技法 300 条、范例、自检清单
  templates/            六份交付物模板（梗概/结构/座位图/角色声线/生成单元/自检）
  scripts/              build_xlsx.py、verify.py、ct_rules.py、cine_tech.json（技法库副本）

keyword-script-creation/
  SKILL.md
  references/           总纲红线、裁决要求、三种模式、画面参数、技法到参数、正向/反向提示词、音效、自检
  templates/            序列组字段模板、总览表、自检清单、数据 schema、交付物清单
  lib/                  att3_face/att4_dialogue/att5_sound/att6_edit 四个生成库 + cine_tech
  scripts/              ingest.py、build_xlsx.py、verify.py
  examples/             一个竖屏短剧的完整示例（数据 + xlsx）

drama-pipeline-gate/
  SKILL.md              什么时候必须跑、阈值、交付说明要写什么、已知边界
  scripts/              gate.py（六个子命令）、anchors.py（人物锚点单一源模板）
```

## 两个先要知道的事

- **`anchors.py` 是模板**。里面是占位人物，换成你的角色锚点；人物外貌只在这写一次，所有集逐字复刻——这是防止"第 5 集男主换脸"的唯一有效手段。若角色名不是林晓/王桂兰/老周/陈姐，`gate.py` 里 `anchors_check` 的名字映射也要同步改。
- **闸门只证明文档自洽，不证明画面正确**。`assets` 回读和人评（`sheet` → `verdict`）才是外部验收；两者要分开汇报，不许混为一谈。

## 数据来源与许可

`cine_tech.json`（300 条技法）整理自 grokfilm 技法库，作为只读副本随技能分发。若来源方有授权限制，请按你的实际情况决定是否随仓库公开。

本仓库**尚未附 License**；在补上之前，默认保留所有权利。想开源的话，常见选择是代码/脚本用 MIT、文档与提示词用 CC BY 4.0。

## 说明

- 技能里提到的"第 X 集"没有固定格式，按你的项目命名来。
- 原开发时的 `tests/` 目录依赖本机路径与原始素材，未包含在仓库里；改脚本后请自行用真实项目跑一遍。
