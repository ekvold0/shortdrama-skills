# 发版流程

这个仓库里的三个技能没有构建产物，所谓「发版」= **让 main 上的内容和 Release 页面对得上**。三步:改 CHANGELOG → 提交 → 打 tag 建 Release。看着简单，但漏一步就会出现「代码更新了、Releases 还停在上个月」的情况。

## 0. 什么时候该发一次

满足任一条就发:

- 新增或删除了 `references/` 下的文件
- 改了 `scripts/`（规则码、校验逻辑、模板生成）
- 改了任一 `SKILL.md` 的工作流、硬规则、加载顺序
- 修了会让别人照着做走不通的问题（错路径、假引用）

只改错别字、只补注释，攒着下次一起发。

## 1. 先跑校验

两个技能都有自带样例，红着就不要发:

```powershell
$py = "C:\Users\22718\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe"

# 关键词
cd C:\Users\22718\.dsh\skills\keyword-script-creation
& $py scripts\verify.py examples\example_kwdata.json --strict   # 期望 error 0
& $py tests\run_all.py                                          # 期望「全部回归通过」

# 分镜
cd C:\Users\22718\.dsh\skills\storyboard-creation
& $py scripts\verify.py scripts\example_storyboard.json          # 期望结论:通过
```

改过 `ct_rules.py` 的，还要确认两份副本一致:

```powershell
Get-FileHash C:\Users\22718\.dsh\skills\*\scripts\ct_rules.py -Algorithm SHA256 |
  Select-Object Hash, Path
```

两个 Hash 不一样就是漏同步了。

## 2. 改 CHANGELOG.md

在 `# Changelog` 下面、旧条目上面插一节新的，日期用落盘那天（UTC+8）:

```markdown
## 2026-12-01 — 一句话说清这版的主线

### 新增 / ### 变更 / ### 修复 / ### 验证

### 已知局限与待定
```

规矩:

- **按事实写**，别写「优化了若干细节」这种。改了什么文件、原来什么样、现在什么样。
- **不编版本号**。技能内部版本号（分镜 `SKILL.md` 的版本行）和 Git tag 是两件事，tag 用日期。
- **字节数、文件行数不要写进正文**——一提交就过期。
- 修掉的问题放进「修复」表:位置 / 原来什么样 / 现在。这条最能防止同一个坑踩第二次。
- 验证数字写真数（`error 0`、`82 份里 55 份告警`），并注明测量口径的局限。

## 3. 提交

### 方式 A:网页手工（不装 git 也能做）

GitHub 网页 → 进入目录 → `Add file` → `Upload files` → 把改过的文件拖进去 → Commit changes。
缺点:一次只能提一个目录，文件多了容易漏。改 5 个以上文件建议用方式 B。

### 方式 B:走 REST API（本机常用）

本机**没有 git、没有 gh**，但 Windows 凭据管理器里存着 GitHub token（`cmdkey /list` 里那条 `GitHub - https://api.github.com/ekvold0`）。流程:

```
GET  /git/ref/heads/main            → head
GET  /git/commits/{head}            → base_tree
POST /git/blobs  (base64)           → 每个文件一个 blob sha
POST /git/trees  (base_tree + 条目) → tree sha
POST /git/commits (parents=[head])  → commit sha
PATCH /git/refs/heads/main          → 指向新 commit
```

一次性提交任意多个文件，也不会产生无意义的合并。

**坑**:

- **每次调用都是新进程**，token 要重新从凭据管理器读出来塞进 `$env:GH_TOKEN`，不能跨调用复用；也不要把 token 打进日志或提交到文件。
- 读出来的 blob 要按 **UTF-8** 解（`[Text.Encoding]::UTF8.GetString`），按 Unicode 解得 20 个乱码汉字。
- PowerShell 里调用静态方法必须带方括号:`[Cred]::Read(...)`，不写方括号会被当成命令名。
- **匿名 API 会限流**（`API rate limit exceeded`），查询也用带 token 的请求。
- 推之前先比对本地和远端，只推真正变化的文件；用 git blob 格式算哈希（`sha1("blob %d\0" + 内容)`）才能和远端 tree 的 sha 对上。

## 4. 打 tag 建 Release

tag 命名:**`vYYYY.MM.DD`**。同一天发两次就 `v2026.11.11.2`。

最省事的做法是直接建 Release 时填 tag 名——GitHub 会自动在该 commit 上建 tag:

```json
POST /repos/{owner}/{repo}/releases
{
  "tag_name": "v2026.11.11",
  "target_commitish": "<提交得到的 commit sha>",
  "name": "2026-11-11 写法层与 CT09–CT12",
  "body": "<从 CHANGELOG 里那一节抠出来>",
  "draft": false,
  "prerelease": false
}
```

发布说明直接从 CHANGELOG 抠，别另写一份——两处内容不一样的时候，没人知道该信哪个。末尾补一句:

```
完整记录见 CHANGELOG.md（链到 GitHub 上的文件）。
```

### 网页做法

Releases → `Draft a new release` → `Choose a tag` 输入新 tag 名 → 目标选 `main` 最新 commit → 标题填 `YYYY-MM-DD 主线一句话` → 说明粘贴 CHANGELOG 里那一节 → Publish。

## 5. 发完自检

```powershell
# 带上 token 的请求，否则会被限流
GET /repos/{owner}/{repo}/releases/latest      # tag/name/published 对不对
GET /repos/{owner}/{repo}/git/ref/tags/v...    # 解出来是不是那个 commit
GET /repos/{owner}/{repo}/git/trees/main       # 文件数对不对，新增文件在不在
```

再抽一个新文件用 raw 地址打开(`https://raw.githubusercontent.com/{owner}/{repo}/main/{path}`)，确认内容不是旧版。

## 6. 别推的东西

| 东西 | 原因 |
|---|---|
| `work/`、`tests/_out/`、`__pycache__/`、`~$*.xlsx` | 中间产物，且带本机路径 |
| `tests/` 整个目录 | 依赖 `F:\AI短剧\` 下的原始素材，别人跑不了 |
| `drama-pipeline-gate/SKILL.md`（本机改过时） | 本机那份指向 `F:\AI短剧\流程\`，推上去别人照着做会失败。保留远端版本 |
| 任何含 token、绝对路径、真实剧本原文的文件 | — |

## 7. 发错了怎么回滚

- 只错在说明文字:改 Release，tag 不动。
- 错在一个文件:重新走一遍提交流程覆盖它，再发一个补丁 tag（`vYYYY.MM.DD.2`）。
- tag 打错 commit:删 Release → 删 tag → 重新建。已经有人 clone 过的话，别强推重写历史，发新 tag。
