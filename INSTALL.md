# 安装与首次跑通

三个技能就是三个带 YAML frontmatter 的 `SKILL.md` 目录，没有构建步骤、没有 npm 包、不需要联网。把它们放到你 agent 的技能目录里，重启会话即可生效。

- `storyboard-creation/`　剧本 → 分镜头脚本
- `keyword-script-creation/`　分镜 → 序列组关键词脚本
- `drama-pipeline-gate/`　交付前验收闸门（`gate.py` 六个子命令）

---

## 0. 前置

| 项 | 是否必需 | 说明 |
|---|---|---|
| Python 3.10+ | **必需** | 脚本全用标准库 + `openpyxl` |
| `pip install openpyxl` | **必需** | 读写 xlsx |
| `ffmpeg` | 可选 | 只有 `gate.py assets`（素材回读）要用；找不到时该命令会明说「没验」 |
| `pip install scenedetect opencv-python-headless` | 可选 | 切镜更准；没装则退回 ffmpeg 场景分数，报告里会写明走的哪条引擎 |

Windows 上如果 `python` 不在 PATH（比如只有微软商店那个占位符，跑起来报 *Python was not found*），用解释器的绝对路径调用即可，例如：

```powershell
$py = "C:\Users\<你>\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe"
& $py keyword-script-creation\scripts\verify.py keyword-script-creation\examples\example_kwdata.json --strict
```

pip 装包慢或卡住时换镜像：

```powershell
& $py -m pip install -i https://pypi.tuna.tsinghua.edu.cn/simple openpyxl
```

---

## 1. 装（选一个）

### A0. 一行装（Windows PowerShell，不依赖 git，实测 3.8 秒）

```powershell
$z="$env:TEMP\sd.zip"; $d="$env:TEMP\sd"
iwr https://codeload.github.com/ekvold0/shortdrama-skills/zip/refs/heads/main -OutFile $z
Expand-Archive $z $d -Force
Copy-Item -Recurse "$d\shortdrama-skills-main\storyboard-creation","$d\shortdrama-skills-main\keyword-script-creation","$d\shortdrama-skills-main\drama-pipeline-gate" "$env:USERPROFILE\.dsh\skills\" -Force
Remove-Item -Recurse -Force $z,$d
```

只拷三个技能目录，仓库根的 README / CHANGELOG / INSTALL / RELEASE 不会进你的技能目录。

macOS / Linux 对应：

```bash
tmp=$(mktemp -d); curl -sL https://codeload.github.com/ekvold0/shortdrama-skills/tar.gz/refs/heads/main | tar xz -C "$tmp"
mkdir -p ~/.dsh/skills && cp -r "$tmp"/shortdrama-skills-main/{storyboard-creation,keyword-script-creation,drama-pipeline-gate} ~/.dsh/skills/ && rm -rf "$tmp"
```

### A. 下载压缩包，手工拷目录（想先看看里面有什么）

1. 打开 <https://github.com/ekvold0/shortdrama-skills>，`Code → Download ZIP`，解压。
2. 把三个目录整体拷进技能目录：

```powershell
# DeepSeek Harness（用户级，跨项目可用）
Copy-Item -Recurse .\storyboard-creation,.\keyword-script-creation,.\drama-pipeline-gate "$env:USERPROFILE\.dsh\skills\"

# Claude Code（个人技能）
Copy-Item -Recurse .\storyboard-creation,.\keyword-script-creation,.\drama-pipeline-gate "$env:USERPROFILE\.claude\skills\"
```

macOS / Linux 用 `cp -r storyboard-creation keyword-script-creation drama-pipeline-gate ~/.dsh/skills/`。

只想给某一个项目用，就放到该项目的 `.claude/skills/` 或 `.dsh/skills/` 下。

### B. 用 git clone 后拷（要升级时 `git pull` 再拷）

```powershell
git clone https://github.com/ekvold0/shortdrama-skills.git
Copy-Item -Recurse .\shortdrama-skills\storyboard-creation,.\shortdrama-skills\keyword-script-creation,.\shortdrama-skills\drama-pipeline-gate "$env:USERPROFILE\.dsh\skills\"
```

### C. 用 DSH Skills Manager 订阅本仓库（装了该插件 + 本机有 git 才行）

如果装了 [`@michengai/dsh-skills-manager`](https://github.com/MichengAI/dsh-skills-manager)：打开它的面板 → **发现** → **添加仓库** → 填 `ekvold0/shortdrama-skills` → 整仓扫描到三个含 `SKILL.md` 的目录 → 选择写入目标（用户目录或某个工作区）→ 安装。之后点「刷新」可看增量 diff，确认后更新，且能「恢复上一版」。

注意它的边界：仓库来源统一走 **git 按需检出**，本机没有 git 就装不了；它只写 DSH 技能目录、`~/.agents/skills`、工作区 `.dsh/skills`，不会写进 Claude Code 目录。

---

## 2. 装完先验一遍（两分钟）

在仓库根目录（或把三个目录都拷到同一层后的目录）执行：

```powershell
# ① 关键词技能：样例应当 0 error 0 warning
python keyword-script-creation\scripts\verify.py keyword-script-creation\examples\example_kwdata.json --strict

# ② 分镜技能：附录样例应当「失败 0 项」
python storyboard-creation\scripts\verify.py storyboard-creation\scripts\example_storyboard.json

# ③ 闸门：样例应当「红灯 0 条」
python drama-pipeline-gate\scripts\gate.py lint keyword-script-creation\examples\示例_关键词脚本.xlsx

# ④ 闸门自检：自己造假素材验切镜/黑帧/账目，9 项全 ok
python drama-pipeline-gate\scripts\selftest.py

# ⑤ 生成前投喂清单自检（不需要登录平台），应当 19 项 0 失败
python drama-pipeline-gate\scripts\run_generate_selftest.py
```

五条都过（⑤ 可选），说明解释器、依赖、路径都对。第 ④ 条在没有 ffmpeg 时会返回 2（什么都没验），那不是通过，是缺依赖。

想看全量回归（会重建四库、跑竖屏与短篇样例、跑跨表正负例、跑 CT16–CT33 正负例、比对两个技能里的 `ct_rules.py` 副本）：

```powershell
cd keyword-script-creation
python tests\run_all.py
```

它要求本机有生成规范 docx（放在 `tests/fixtures/关键词脚本生成规范.docx`，或用环境变量 `KW_SPEC_DOCX` 指过去），缺失时**自动跳过四库重建**，用仓库自带的 `lib/index.json`（280 条）继续跑。第 5 步「真实分镜 ingest」默认跳过，要跑就设 `KW_REAL_STORYBOARD` 与 `KW_REAL_SCRIPT`。短篇夹具是深拷贝首组克隆出来的假片，会有 2 条 `CT14/CT15` warning，那是夹具的必然结果，不是你的稿子有问题。

---

## 3. 换你自己的剧时要改的地方

| 位置 | 改什么 | 不改会怎样 |
|---|---|---|
| 项目根的 `角色锚点.json`（V2.12 起，外貌唯一真值源） | `python 流程\anchors.py init --script 剧本.docx` 只登记名字；`harvest --kw 关键词.xlsx` 回捞外貌锚点；`check` 查重复/空锚点 | 人物跨集换脸；没有这张表时 `gate.py anchors` 直接报红 |
| `drama-pipeline-gate/scripts/gate.py` 的人物特征表 | 改由 `anchors.py` 的 `features` 提供，**不用再改源码**（旧的 `NAMES`／`FEAT` 硬编码已删） | —— |
| 关键词脚本的 `prompt` 风格包 | 整集只用一种：`modern_live`／`ancient_period`／`3d_stylized`（正文照抄 `ct_rules.style_prefix()`），用别的会报 CT28 | 每组的质感各写各的，整集不成片 |
| `keyword-script-creation/tests/build_libs_from_spec.py` 用的规范 docx | 放 `tests/fixtures/` 或设 `KW_SPEC_DOCX` | 只有重建四库时才需要，跑回归时缺了会自动跳过 |

---

## 4. 升级

- 方式 A/B 装的：重新下载/`git pull`，再拷一次三个目录覆盖。
- 方式 C 装的：面板里「刷新」→「查看更新」，确认后自动备份并更新。
- 按版本取：<https://github.com/ekvold0/shortdrama-skills/releases>。每个 release 的说明就是当次的改动清单，与 `CHANGELOG.md` 单一真源。

覆盖前留意一件事：`角色锚点.json` 在**你的项目目录**里、不在技能目录里，覆盖技能不会冲掉它；但如果你改过技能里的脚本（`ct_rules.py`／`gate.py`／`anchors.py`），覆盖会把这些改动冲掉，先备份。

---

## 5. 常见坑

1. **两份 `ct_rules.py` 必须同步**。`storyboard-creation/scripts/` 与 `keyword-script-creation/scripts/` 各一份，内容同源；只改一边，会出现「分镜稿在关键词技能里被拦」这种诡异现象。校验方法：

   ```powershell
   (Get-FileHash storyboard-creation\scripts\ct_rules.py).Hash -eq (Get-FileHash keyword-script-creation\scripts\ct_rules.py).Hash
   ```

2. **warning 不挡交付，error 才拦**。`verify.py --strict` 只在有 error 时退出码为 1。旧片回查时 `CT11`（前 2 秒没钩子）几乎必然告警，那是规范升级后的正常现象。
3. **技能目录名可以中文，但 `SKILL.md` 里 `name` 必须是 ASCII kebab-case**（这三个都是），否则宿主可能不加载。
4. **闸门自检不过先查 ffmpeg**。`selftest.py` 返回 2 意味着没找到 ffmpeg：设环境变量 `GATE_FFMPEG` 指向可执行文件，或 `pip install imageio-ffmpeg`（会自带一份）。
5. **闸门只证明文档自洽，不证明画面正确**。素材要另外跑 `gate.py assets` 回读、人评走 `gate.py sheet` → `verdict`，两者分开汇报。
