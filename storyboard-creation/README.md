# storyboard-creation · 分镜头脚本生成

把剧本变成分镜头脚本，并且把「图」这一层也管起来：站位图、色卡、角色设计卡、分镜图提示词。

- 版本：**V2.12**｜校验规则 **CT16–CT33**（图像资产层/记录镜头/分镜图/多镜组/数据契约）
- 交付物：分镜 `data.json`（`sbdata/1`）+ Excel 渲染件 + 图像资产清单

## 怎么用

```
剧本 + 用户需求
  ↓ 第 1 步 梗概（停车点 1，等人确认）
  ↓ 第 2 步 叙事结构方案（停车点 2，含候选来源 references/49-方案候选索引.md）
  ↓ 第 3 步 角色与空间锚点（停车点 3）
  ↓ 第 4 步 图像资产：场景图 → 色卡 → 角色卡 → 站位图 → 分镜图提示词
  ↓ 第 5 步 逐单元写镜头（动作单独成列，短镜落地三选一）
  ↓ 第 6 步 自检 + verify.py 跑绿
```

三个停车点不能跳：梗概、结构方案、锚点卡。用户没点头别往下写。

## 依赖

`openpyxl`（读写 xlsx）。跑 `adapt_xlsx.py` 迁移存量分镜表也只要它。

## 自检

```bash
python scripts/verify.py scripts/example_storyboard.json      # 期望：失败 0，结论通过
python scripts/verify.py <你的分镜.json> --assets-root <资产目录>   # 带资产落盘校验
```

`--assets-root` 给项目的 `资产/` 目录本身，JSON 里 `path` 写含子目录的相对路径
（`boards/KB_S03_U01_v1.png`）。

## 目录

| 路径 | 内容 |
|---|---|
| `SKILL.md` | 工作流、硬规则 1–47、文件地图 |
| `references/00-通用内核.md` | 列定义（含 4.5b 动作列、4.5c 短镜落地） |
| `references/05-落地要求-覆盖层.md` | 规则落到哪、闸门怎么卡（A1–A9） |
| `references/43-运镜选型.md` | 运镜 + §2.3 机位最小库 + §6.5 记录镜头定式 |
| `references/49-方案候选索引.md` | 情绪/题材 → 候选方案（候选怎么来） |
| `references/53-武打动作组.md` | 打戏：六阶段、轴线、八种拍法 |
| `templates/01–12` | 梗概、结构、空间图、声线常量、生成单元、自检、站位图、色卡、角色设计卡、分镜图提示词、武打组、资产登记表 |
| `scripts/` | `verify.py` / `adapt_xlsx.py` / `build_xlsx.py` / `crosscheck.py` / `ct_rules.py` |

`scripts/ct_rules.py` 与 `keyword-script-creation/scripts/ct_rules.py` **必须一模一样**，
改一边记得同步另一边。

## 已知限制

- 分镜阶段不校验声线（只查关键词层）。
- 「一单元一张关键帧」只对单镜组成立；多镜组按镜各出一张，见 `templates/10-分镜图提示词.md`。
