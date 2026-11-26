# shortdrama-skills

把一个剧本变成"喂给 AI 视频工具能照着生成"的交付物，并且能验收它到底有没有照着生成——三个 agent skill，串起来是一条完整产线。

| 技能 | 一句话 | 输入 → 输出 |
|---|---|---|
| [`storyboard-creation`](storyboard-creation/SKILL.md) | 剧本 → 分镜头脚本 | 剧本文档 → 分镜 xlsx（含故事梗概、结构方案、角色/空间锚点、AI 生成单元、时长账目、自检记录） |
| [`keyword-script-creation`](keyword-script-creation/SKILL.md) | 分镜 → 序列组关键词脚本 | 剧本 + 分镜 → 关键词 xlsx（十字段、一体化视频提示词、物理化动作情绪、四层音效、五段反向提示词 + 全片固定禁用第 0 段） |
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

完整的安装 / 自检 / 换剧 / 升级说明见 **[INSTALL.md](INSTALL.md)**（含 pip 镜像、Python 不在 PATH 时怎么调、四种验证命令）。

## 依赖

- Python 3.10+，`openpyxl`（生成/读取 xlsx）、`python-docx`（`ingest.py` 读剧本文档）
- 素材回读（`gate.py assets`）需要 `ffmpeg`：取 `GATE_FFMPEG` 环境变量 → `imageio-ffmpeg` → PATH
- 切镜更准要 `pip install scenedetect opencv-python-headless`（可选；没装则退回 ffmpeg 场景分数，报告里会写明走的哪条引擎）
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

   `assets` 回读四件事：时长偏差、画幅、**黑帧/空白帧（FAIL）**、**镜数与镜长（待核）**。
   镜数是切镜算出来的，AI 生成的运动会让它偏多，所以只作提示不判 FAIL；黑帧是客观缺陷，直接 FAIL。
   改过阈值或升级过依赖，跑 `python drama-pipeline-gate/scripts/selftest.py`（自己造素材验切镜/黑帧/账目）。

## 两个写法层：分镜层不写数，关键词层必须写数

这是这套技能里最容易写串的一处，也是返工最多的来源：

| | 分镜层（storyboard-creation） | 关键词层（keyword-script-creation） |
|---|---|---|
| 运镜 | 只写「轴 + 方向与落点 + 起止景别」 | 必须给四要素：方向 / 幅度（米）/ 速度（秒）/ 时长 |
| 打光 | 只写「光源与方向 + 光质 + 冷暖关系」 | 必须给四件套：光位 / 光质 / 色温（K）/ 光比（1:n） |
| 开场钩子 | 写在首镜**画面内容**列，时长 ≤ 2 秒 | 写进 0.0—2.0 秒那一段的七字段正文 |
| 时长 | 单元 4–15 秒（2.0）／写在单元里标 `tier: 2.5` 才允许到 30 秒 | 组 4–15 秒（2.0）／4–30 秒（2.5 flash、2.5 标准版），下限一律 4 秒 |
| 技法名 | 中文技法名，不写英文、不写典故 | 先按写法库定写法，再按档位降维成参数 |
| 节奏 | 整集单元时长曲线；单镜节奏锚（45/48） | 整集组时长曲线＋台词余量＋运动轴种类（49） |
| 表演 | 动作三拍落在「画面内容」，不写参数 | 动作三拍物理化拆解，接触点与支撑脚写进正文（52） |

分镜层写数字会把导演该定的表演写成死参数，关键词层不写数字则模型就是随机打光、随机推镜。

## 目录结构

```
storyboard-creation/
  SKILL.md              技能主体：何时用、怎么做、交付物清单
  references/           内核、覆盖层、竖屏/横屏/短篇三种模式、表情与台词库、技法 300 条、范例、自检清单
                        写法库：43 运镜选型（含机位最小库、记录镜头定式） / 44 打光选型 /
                                45 表演与动作衔接 / 46 开场钩子 / 47 类型分镜配比 /
                                48 节奏与剪辑（分镜层口径） / 49 方案候选索引 / 53 武打动作组
  templates/            十二份交付物模板（梗概/结构/座位图/角色声线/生成单元/自检 +
                        07 站位图资产规范 / 08 色卡规范 / 09 角色设计卡 / 10 分镜图提示词 /
                        11 武打动作组模板 / 12 资产登记表）
  scripts/              build_xlsx.py、verify.py、ct_rules.py、adapt_xlsx.py、cine_tech.json（技法库副本）

keyword-script-creation/
  SKILL.md
  references/           总纲红线、裁决要求、三种模式、画面参数、技法到参数、正向/反向提示词、音效、自检
                        写法库：41 运镜库 / 42 打光库 / 48 开场钩子 / 49 节奏与可读性 /
                                52 表演三拍与道具 / 56 武打物理参数与音效对齐 /
                                55 类型成品提示词（关键词层口径）
  templates/            序列组字段模板、总览表、自检清单、数据 schema、交付物清单、06 角色卡生成单
  lib/                  att3_face/att4_dialogue/att5_sound/att6_edit 四个生成库 + cine_tech
  scripts/              ingest.py、build_xlsx.py、verify.py、ct_rules.py
  examples/             一个竖屏短剧的完整示例（数据 + xlsx）
  tests/                回归：run_all.py、ct_v2_cases.py（CT16–CT35 正负例）、fixtures/

drama-pipeline-gate/
  SKILL.md              什么时候必须跑、阈值、交付说明要写什么、已知边界
  references/           短剧生成流程_v1（六阶段五闸门）/ 角色锚点两阶段_v1 /
                        外部验收核对表_v1 / 改判记录_v1
  templates/            角色锚点表.json（三级 stage 示例）
  scripts/              gate.py（子命令 lint/anchors/assets/readback/sheet/verdict）、
                        anchors.py（角色锚点单一源：init/harvest/check/diff/render）、
                        run_generate.py（投喂清单 dry-run）、run_generate_selftest.py、
                        selftest.py（切镜/黑帧/账目自检）
```

## 机器校验：CT00—CT35

两个技能各带一份同源的 `scripts/ct_rules.py`，由 `verify.py` 调用，`--strict` 时只有 error 会让退出码变 1，warning 不挡交付。

### CT01—CT15（写法层：语言与技法）

| 码 | 查什么 | 级别 | 作用层 |
|---|---|---|---|
| CT01 | 空泛词（电影感/氛围感/高级感…） | error | 两层 |
| CT02 | 九子参数齐全且按序 | error / 顺序 warning | 关键词 |
| CT03 | 一镜一主运镜、辅轴不同族 | warning | 两层 |
| CT05 / CT06 | 典故不进正文；参考电影《片名》年份、1 主 + ≤2 辅（辅标要写「（辅）」） | error | 两层 |
| CT07 / CT08 | 英文技法名；T4 禁投技法 | error | 两层 |
| CT09 | 运镜无轴无「固定」→ error；有轴没量化 → warning | 混合 | 关键词 |
| CT10 | 光影缺色温 K 或光比 → error；缺光位/光质 → warning | 混合 | 关键词 |
| CT11 | 首组（首单元）前 2 秒没有钩子特征；钩子写进运镜/机位列 | warning | 两层 |
| CT12 | 出现英制单位（ft/inch/mph） | error | 两层 |
| CT13 | 台词说完到组末不足 0.6 秒 | warning | 关键词 |
| CT14 | 一集运动轴种类 <4（给了很多组却只用一种运镜） | warning | 关键词 |
| CT15 | 相邻 3 个组/单元时长完全一样（一个速度走到底） | warning | 两层 |

### CT16—CT35（图像资产层与投喂层，V2.0—V2.13）

| 码 | 查什么 | 级别 |
|---|---|---|
| CT16 | 有跨段就必须在段末收一镜「人物站位记录镜头」（24mm／大全景／固定／俯拍／静止一秒，五条全中） | error |
| CT17 | 正文 `[图片N]`／`[图锚]` 与 refs 双向对齐；图片数按档位上限（2.0 = 9，2.5 flash = 10，2.5 = 30，**分镜图也占名额**）；组时长 ≤15 秒不必挂分镜图；音频不能单独用于 2.0 | error / warning |
| CT18 | 色值必须来自所引色卡（不许现编）；色卡色温与组内色温偏差 >800K | error / warning |
| CT19 | 打戏缺受力反馈或重心恢复；一组里升格超过一次 | warning |
| CT20 | 三层画面账（前景/中景/背景）连续 3 个单元全空 | warning |
| CT21 | 反向提示词缺「第 0 段固定禁用句」（禁字幕/禁 BGM） | error |
| CT22 / CT23 / CT25 | 角色卡三类未拆；身份链被逐代传递（链深 >1）；分镜图覆盖不足 ⌈总数÷3⌉ 或缺关键单元/关键镜 | error |
| CT24 | 背景依据 `bg_basis.scene` 指向不存在的场景图 | error |
| CT26 | 短镜（<4 秒）标了「砍掉」却还留在组里；≥4 秒的镜标了「后期/砍掉」 | warning |
| CT27 | 多镜组超过 6 镜；`镜N：` 标记数 ≠ shots 数；镜内用「两人/众人」代替角色名 | warning |
| CT28 | 风格包不在枚举里（modern_live / ancient_period / 3d_stylized）；出了分镜图却没写风格包 | error / warning |
| CT29 | 音频资产没登记、文件不存在、或被引用却没进 `assets.audios` | error |
| CT30 | 有台词的角色在锚点里没有音色；`sfx_layers.voice` 没提到说话人 | warning |
| CT31 | 首帧超过一张；首帧标在资产图上（应标分镜图）；>15 秒的组没有首帧；role 写了不认识的词 | error / warning |
| CT32 | 提示词字数按档位：2.0 上限 4000 字、2.5 含 flash 上限 10000 字（软预算 3/4） | warning |
| CT33 | 数据契约：缺 `schema`、`meta` 键名像笔误（如 `epsoide`）、资产 id 重复 | error / warning |
| CT34 | 场景卡：场景没写光线从哪来（光源类型/来向/色温/光比）、只写「光线柔和」这类无来源的光、没写拍摄规格（写实装 ARRI） | warning |
| CT35 | 节奏反模式：连续 4 个单元同一景别开场（景别强迫症）、单元内 ≥3 镜而时长极差 ≤0.3 秒（平均切镜）、单组超 8 镜 | warning |

改了 `ct_rules.py` 记得两边同步复制（`tests/run_all.py` 第 8 步会自动比对两侧 hash），否则一边过的稿子另一边被拦。

## 两个先要知道的事

- **人物外貌只有一个真值源：项目根的 `角色锚点.json`**（V2.12 起）。两阶段用法：先用 `scripts/anchors.py init --script <剧本>` 只登记名字，再 `harvest --kw <关键词xlsx>` 把外貌锚点回捞进表；分三级 `names → look → full`，`check` 抓重复、空锚点、两人锚点完全相同。人物外貌只在这写一次，所有集逐字复刻——这是防止"第 5 集男主换脸"的唯一有效手段。`anchors.py` 里内置的林晓/王桂兰/老周/陈姐只是示例，不在 `角色锚点.json` 里跑时会直接报红。
- **闸门只证明文档自洽，不证明画面正确**。`assets` 回读和人评（`sheet` → `verdict`）才是外部验收；两者要分开汇报，不许混为一谈。

## 更新记录

见 [CHANGELOG.md](CHANGELOG.md)。最近一次是 **2026-11-26（V2.12）**：图像资产层落地——站位图/色卡/角色设计卡/分镜图四类资产、记录镜头定式、参考链拆成身份链与空间链、机器校验扩到 CT16–CT33；分镜图按组时长决定是否挂（≤15 秒走 2.0 不用、>15 秒才挂）；素材上限与提示词字数按平台实测写死（9/10/30 图、4000/10000 字）。上一次 **2026-11-19**：闸门脚本装回仓库、素材回读真的能回读——切镜改用 PySceneDetect（HSV 加权，「红→绿」这种亮度几乎相同的切点不再漏）、新增黑帧判定与 `selftest.py`、`build_xlsx.py` 改 EP07 音频口径（样例 11 条红降到 0）、41 运镜库补「速度／缓动」十词。上一次 **2026-11-12**：从 lemo-opuscar 补四份写法库（关键词 49 节奏与可读性、52 表演三拍；分镜 45 表演与动作衔接、48 节奏与剪辑），机器校验扩到 CT13–CT15。上一次 **2026-11-11**：接入八份写法库（关键词 41/42/48/55、分镜 43/44/46/47），扩到 CT09–CT12。发版与打 tag 的流程见 [RELEASE.md](RELEASE.md)。

## 数据来源与许可

`cine_tech.json`（300 条技法）整理自 grokfilm 技法库，作为只读副本随技能分发。若来源方有授权限制，请按你的实际情况决定是否随仓库公开。

代码与脚本用 **MIT**（见 [LICENSE](LICENSE)）；文档、模板与提示词建议按 CC BY 4.0 使用。

## 说明

- 技能里提到的"第 X 集"没有固定格式，按你的项目命名来。
- 回归测试在 `keyword-script-creation/tests/`：`python tests/run_all.py`。它会重建四库（需本机有规范 docx，没有就设 `KW_SPEC_DOCX`，缺失时自动跳过）、构建并校验竖屏与短篇样例、检验台词覆盖、跨表正负例、CT16–CT35 正负例，并比对两个技能里 `ct_rules.py` 的副本是否一致。真实剧本的 ingest 产物不在仓库里；要跑真实分镜那一步，设 `KW_REAL_STORYBOARD` 与 `KW_REAL_SCRIPT`。
- 依赖：Python 3.10+、`openpyxl`、`python-docx`；闸门侧另需 `ffmpeg`（`GATE_FFMPEG` 可指定路径），切镜推荐再装 `scenedetect` + `opencv-python-headless`（没装则退回 ffmpeg 灰度+彩色差并集）。
