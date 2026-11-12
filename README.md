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

- 跨表校验：分镜稿与关键词稿都有时，跑 `python scripts/crosscheck.py --storyboard 分镜.json --keyword kwdata.json` —— X01–X07 查跨表错位（漏镜/多镜/秒数/景别/台词）。

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

## 两个写法层：分镜层不写数，关键词层必须写数

这是这套技能里最容易写串的一处，也是返工最多的来源：

| | 分镜层（storyboard-creation） | 关键词层（keyword-script-creation） |
|---|---|---|
| 运镜 | 只写「轴 + 方向与落点 + 起止景别」 | 必须给四要素：方向 / 幅度（米）/ 速度（秒）/ 时长 |
| 打光 | 只写「光源与方向 + 光质 + 冷暖关系」 | 必须给四件套：光位 / 光质 / 色温（K）/ 光比（1:n） |
| 开场钩子 | 写在首镜**画面内容**列，时长 ≤ 2 秒 | 写进 0.0—2.0 秒那一段的七字段正文 |
| 时长 | 单元 4–15 秒，单镜上限按模式 | 组 4–15 秒，时间轴 0.0 起、0.1 秒精度 |
| 技法名 | 中文技法名，不写英文、不写典故 | 先按写法库定写法，再按档位降维成参数 |
| 节奏 | 整集单元时长曲线；单镜节奏锚（45/48） | 整集组时长曲线＋台词余量＋运动轴种类（49） |
| 表演 | 动作三拍落在「画面内容」，不写参数 | 动作三拍物理化拆解，接触点与支撑脚写进正文（52） |

分镜层写数字会把导演该定的表演写成死参数，关键词层不写数字则模型就是随机打光、随机推镜。

## 目录结构

```
storyboard-creation/
  SKILL.md              技能主体：何时用、怎么做、交付物清单
  references/           内核、覆盖层、竖屏/横屏/短篇三种模式、表情与台词库、技法 300 条、范例、自检清单
                        写法库：43 运镜选型 / 44 打光选型 / 45 表演与动作衔接 /
                                46 开场钩子 / 47 类型分镜配比 / 48 节奏与剪辑（分镜层口径）
  templates/            六份交付物模板（梗概/结构/座位图/角色声线/生成单元/自检）
  scripts/              build_xlsx.py、verify.py、ct_rules.py、cine_tech.json（技法库副本）

keyword-script-creation/
  SKILL.md
  references/           总纲红线、裁决要求、三种模式、画面参数、技法到参数、正向/反向提示词、音效、自检
                        写法库：41 运镜库 / 42 打光库 / 48 开场钩子 / 49 节奏与可读性 /
                                52 表演三拍与道具 / 55 类型成品提示词（关键词层口径）
  templates/            序列组字段模板、总览表、自检清单、数据 schema、交付物清单
  lib/                  att3_face/att4_dialogue/att5_sound/att6_edit 四个生成库 + cine_tech
  scripts/              ingest.py、build_xlsx.py、verify.py、ct_rules.py
  examples/             一个竖屏短剧的完整示例（数据 + xlsx）

drama-pipeline-gate/
  SKILL.md              什么时候必须跑、阈值、交付说明要写什么、已知边界
  scripts/              gate.py（六个子命令）、anchors.py（人物锚点单一源模板）
```

## 机器校验：CT01—CT15

两个技能各带一份同源的 `scripts/ct_rules.py`，由 `verify.py` 调用，`--strict` 时只有 error 会让退出码变 1，warning 不挡交付。

| 码 | 查什么 | 级别 | 作用层 |
|---|---|---|---|
| CT01 | 空泛词（电影感/氛围感/高级感…） | error | 两层 |
| CT02 | 九子参数齐全且按序 | error / 顺序 warning | 关键词 |
| CT03 | 一镜一主运镜、辅轴不同族 | warning | 两层 |
| CT05 / CT06 | 典故不进正文；参考电影《片名》年份、≤1 部 | error | 两层 |
| CT07 / CT08 | 英文技法名；T4 禁投技法 | error | 两层 |
| CT09 | 运镜无轴无「固定」→ error；有轴没量化 → warning | 混合 | 关键词 |
| CT10 | 光影缺色温 K 或光比 → error；缺光位/光质 → warning | 混合 | 关键词 |
| CT11 | 首组（首单元）前 2 秒没有钩子特征；钩子写进运镜/机位列 | warning | 两层 |
| CT12 | 出现英制单位（ft/inch/mph） | error | 两层 |
| CT13 | 台词说完到组末不足 0.6 秒 | warning | 关键词 |
| CT14 | 一集运动轴种类 <4（给了很多组却只用一种运镜） | warning | 关键词 |
| CT15 | 相邻 3 个组/单元时长完全一样（一个速度走到底） | warning | 两层 |

改了 `ct_rules.py` 记得两边同步复制，否则一边过的稿子另一边被拦。

## 两个先要知道的事

- **`anchors.py` 是模板**。里面是占位人物，换成你的角色锚点；人物外貌只在这写一次，所有集逐字复刻——这是防止"第 5 集男主换脸"的唯一有效手段。若角色名不是林晓/王桂兰/老周/陈姐，`gate.py` 里 `anchors_check` 的名字映射也要同步改。
- **闸门只证明文档自洽，不证明画面正确**。`assets` 回读和人评（`sheet` → `verdict`）才是外部验收；两者要分开汇报，不许混为一谈。

## 更新记录

见 [CHANGELOG.md](CHANGELOG.md)。最近一次是 **2026-11-12**：从 lemo-opuscar 补四份写法库（关键词 49 节奏与可读性、52 表演三拍；分镜 45 表演与动作衔接、48 节奏与剪辑），机器校验扩到 CT13–CT15。上一次 **2026-11-11**：接入八份写法库（关键词 41/42/48/55、分镜 43/44/46/47），扩到 CT09–CT12。发版与打 tag 的流程见 [RELEASE.md](RELEASE.md)。

## 数据来源与许可

`cine_tech.json`（300 条技法）整理自 grokfilm 技法库，作为只读副本随技能分发。若来源方有授权限制，请按你的实际情况决定是否随仓库公开。

本仓库**尚未附 License**；在补上之前，默认保留所有权利。想开源的话，常见选择是代码/脚本用 MIT、文档与提示词用 CC BY 4.0。

## 说明

- 技能里提到的"第 X 集"没有固定格式，按你的项目命名来。
- 原开发时的 `tests/` 目录依赖本机路径与原始素材，未包含在仓库里；改脚本后请自行用真实项目跑一遍。
