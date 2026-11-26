# 模板 · 数据文件 schema（kwdata.json）

> 唯一数据源。`build_xlsx.py` 与 `verify.py` 都读它；**不要直接改 Excel**。
> 键名区分大小写；带 `?` 的可选。

```json
{
  "schema": "kwdata/1",
  "meta": {
    "title": "剧名",
    "episode": 3,
    "mode": "vertical | horizontal | shortfilm",
    "aspect": "9:16 | 4:3",
    "resolution": "1080x1920 | 1920x1440",
    "default_model": "2.0",
    "target_total_sec": 120,
    "source_script": "剧本.docx",
    "source_storyboard": "分镜.xlsx",
    "version": "V1.0",
    "date": "2026-10-26",
    "author": "AI辅助",
    "based_on": "竖屏V2.5",
    "chars_per_sec": 2.25
  },

  "story": {
    "summary": "本集故事（200–400字）",
    "hook": "反转/钩子",
    "timeline": "时间线、地点",
    "curve": "情绪曲线：加压→被无视→…",
    "props": "贯穿道具及其状态变化",
    "link": "与上下集衔接"
  },

  "anchors": {
    "characters": [
      {"name": "林晓", "look": "24岁女，163cm偏瘦，鹅蛋脸，内双…深蓝涤棉工服…", "voice": "成年女声，清亮偏软，语速每秒约2字"}
    ],
    "props": [{"name": "黑布包", "note": "拉链头缺一半；本集脱手、散开、塞回"}],
    "visual": {
      "palette": "冷青灰为底，钠灯暖橙点缀",
      "texture": "写实电影感，柯达5219颗粒",
      "motif": "吊环、黑布包、药盒、抬起的手",
      "subtitle": "全部后期叠加",
      "transition": "全片硬切"
    },
    "space": "车厢坐标系：车头在画面深处；林晓坐左侧靠窗；王桂兰站其右侧过道；男乘客在她右侧靠立柱"
  },

  "acts": [
    {"act": "M1", "name": "建置", "ratio": "20-25%",
     "scenes": [{"no": "C01", "name": "城市清晨街道", "note": "建立镜头"}]}
  ],

  "groups": [
    {
      "no": "S03-XZ-001",
      "unit": "U1",
      "model": "2.0",
      "act": "M1",
      "scene_no": "C01",
      "scene_name": "城市公交晚高峰车厢",
      "duration": 12.3,
      "params": {
        "camera": "ARRI ALEXA 65，竖屏9:16（1080×1920），定焦 35，f/2.8，ISO800，1/50秒，LogC，14档动态范围",
        "texture": "柯达5219，颗粒中等偏细、暗部可见，锐度中高边缘不过锐，院线级色彩分级",
        "color": "主色冷青灰（5600K偏青），钠灯暖橙点缀（3000K），饱和度-8%，对比度+12%",
        "position": "平视，机位高1.4米，距主体0.8米，中景",
        "movement": "固定；末段极慢推近0.2米，速度约2厘米/秒",
        "light": "顶光硬光，主光左上45度，光比1:3，窗外钠灯侧逆补光",
        "action": "右手抬起约15度扶窗框，小臂发力，肩随呼吸起伏约1.5厘米",
        "blocking": "王桂兰站过道右侧、身体朝车尾；林晓坐左侧靠窗；竖屏中心安全区给嘴与眼",
        "ref": ["通用", 5, "第二声之后立刻切林晓的无反应，用0.5秒反应镜把落空钉住"]
      },
      "makeup": "场景：…；人物：林晓（24岁…）；王桂兰（55岁…）",
      "shots": [
        {
          "id": "001",
          "size": "ECU",
          "dur": 3.0,
          "cam": "主观视角(POV)／平视／定焦 35／f2.8／浅景深／固定",
          "pic": "吊环占画面上缘，王桂兰的嘴在下方，低头对着座位方向",
          "act": "下唇先动、上唇后跟，说完即闭；下颌抬着",
          "emo": "皱眉肌收缩约1.5毫米，眼裂收窄20%，咬肌绷紧",
          "dialogue": "王桂兰（中高音，语速约每秒2.5字）：我说，让个座。",
          "sfx": "车厢引擎低频；0.6秒衣料摩擦",
          "note": "背景乘客肩随呼吸起伏（非聚焦微动态）；本段末硬切",
          "style": "柯达5219粗颗粒，暗部可见；顶光压出下颌阴影；冷青灰底，饱和度-10%；唇部干纹清晰；金属吊环冷反光；焦点在唇，背景虚化",
          "breath": 19,
          "ref": ["通用", 1, "包下坠方向与药盒滚出方向对齐"]
        }
      ],
      "audio": {
        "note": "本组台词量6.0秒，落在5—12秒区间。",
        "whitespace": 0.5,
        "silence": 0
      },
      "sfx_layers": {
        "voice": "王桂兰干声，中高音，语速快，句尾上扬，无混响",
        "core": "0.6秒衣料摩擦，轻，-18dB",
        "ambient": "引擎低频、吊环轻碰，极低",
        "reverb": "车厢0.4秒短混响"
      },
      "neg": {
        "plot": "王桂兰坐下、林晓抬头、吊环静止、车厢空荡",
        "extra": ""
      }
    }
  ],

  "selfcheck": {
    "round1": [{"item": "所有组时长4–15秒", "result": "通过", "issue": "", "fix": ""}],
    "round2": [],
    "round3": [],
    "summary": {"problems": 0, "fixed": 0, "conclusion": "通过", "notes": ""}
  }
}
```

## V2.0 新增字段（图像资产层，CT16–CT25）

顶层加三个配置块，每个 group 里加 `refs` / `layers` / `bg_basis` / `fight` / `color_card` / `color_temp`：

```json
{
  "scenes": [
    {"id": "SCN-S03-客厅", "file": "assets/场景/SCN-S03-客厅_v2.png", "note": "无人、覆盖全部入镜墙面"}
  ],

  "color_cards": [
    {"id": "COLOR-S03-A", "temp": 3800,
     "colors": [{"hex": "#8A93A6", "area": 42, "from": "墙面左侧"},
                {"hex": "#B98A5E", "area": 23, "from": "木质餐桌"}]}
  ],

  "assets": {
    "characters": [
      {"id": "佐伊",
       "cards": {
         "face":   {"id": "卡-佐伊-脸", "file": "assets/角色/佐伊-脸_v1.png", "chain": "identity"},
         "cloth":  {"id": "卡-佐伊-衣", "file": "assets/角色/佐伊-无头衣_v1.png", "chain": "identity"},
         "back":   {"id": "卡-佐伊-背", "file": "assets/角色/佐伊-背面_v1.png", "chain": "identity"}
       }}
    ],
    "items": [
      {"id": "卡-搪瓷杯", "kind": "prop", "file": "assets/道具/搪瓷杯_v1.png", "chain": "identity"}
    ],
    "staging": [
      {"id": "站位-客厅-01", "file": "assets/站位/staging-客厅-01.png",
       "scene_ref": "SCN-S03-客厅", "chain": "spatial"}
    ],
    "boards": [
      {"id": "KB-S03-U01", "unit": "U01", "path": "assets/分镜图/KB_S03_U01_v1.png",
       "scene_ref": "SCN-S03-客厅"}
    ]
  },

  "groups": [
    {
      "no": "S03-XZ-001",
      "tier": "2.0",
      "color_card": "COLOR-S03-A",
      "color_temp": 3800,
      "layers": {"fore": "垂下的纱帘虚影", "mid": "佐伊与沙发", "back": "走廊门与挂衣钩"},
      "bg_basis": {"scene": "SCN-S03-客厅", "note": "背景人物各做各的事，不同步"},
      "fight": false,
      "refs": [
        {"no": 1, "kind": "scene",   "file": "assets/场景/SCN-S03-客厅_v2.png", "role": "空间"},
        {"no": 2, "kind": "staging", "file": "assets/站位/staging-客厅-01.png", "role": "站位"},
        {"no": 3, "kind": "face",    "file": "assets/角色/佐伊-脸_v1.png",     "role": "身份"},
        {"no": 4, "kind": "face",    "file": "assets/角色/大卫-脸_v1.png",     "role": "身份"}
      ]
    }
  ]
}
```

| 键 | 必填 | 说明 |
|---|---|---|
| `scenes[].id` | 是 | 场景图编号，`bg_basis.scene` 与 `scene_ref` 都指它（CT24/CT23） |
| `color_cards[].temp` | 是 | 色温基准 K；组内 `color_temp` 与它相差 >800K 判 warning（CT18） |
| `assets.characters[].cards` | 是 | 三类卡：`face` / `cloth` / `back`；缺项 error（CT22） |
| `cards.*.chain` | 是 | `identity`＝身份链，**不许有 `derived_from`**；空间类写 `spatial`（CT23） |
| `assets.staging[].scene_ref` | 是 | 站位图必须挂原始场景图；缺即 error（CT23） |
| `assets.boards[].path` | 是 | 分镜图文件；给了 root 时校验存在（CT25） |
| `groups[].tier` | 是 | `"2.0"` / `"2.5 flash"` / `"2.5"`，决定图片上限 9/10/30（CT17）；也可写 `model` |
| `groups[].refs[].no/kind/file` | 是 | 与正文 `[图片N]` 双向对齐；`file` 缺即 error（CT17） |
| `groups[].refs[].sec` | 否 | **V2.3 新增**：视频／音频参考的时长（秒），写 `sec` 或 `duration`。kind=video/audio 时校验区间——2.0 单条 4–15 秒，2.5 flash／2.5 标准版单条 4–30 秒，越界 error（CT17） |
| `groups[].duration` | 是 | 组时长：2.0 4–15 秒、2.5 flash／2.5 标准版 4–30 秒；**下限一律 4 秒**，低于即 error（CT17） |
| `groups[].refs[].role` | 否 | **V2.4 新增**：`first_frame`（2.0 分镜图＝整组生成起点）／`shot_ref`（2.5 flash 与标准版 分镜图＝单镜画面参考） |
| 分镜图 kind | — | **V2.4**：分镜图的 `kind` 写 `board`（或 `分镜图`／`关键帧`）。判别出是分镜图时**不计入图片名额**，且不参与身份链 |
| `groups[].ref_mode` | 否 | **V2.3 新增**：组头写 `text` ＝ 本组刻意走纯文字路径。不写、又既无 refs 也无 `[图片N]` → warning（CT17） |
| `shots[].landing` | 短镜必填 | **V2.3 新增**：`并进`／`后期`／`砍掉`（也认 merge／post／cut）。<4 秒不写 → warning；标 `砍掉` 却仍在组里 → warning；≥4 秒标 `后期/砍掉` → 提示不必（CT26） |
| `groups[].layers` | 否 | `fore/mid/back`；连续 3 组全空 warning（CT20） |
| `groups[].bg_basis` | 场景有背景人物时必填 | `{scene, note}`；只给编号不挂场景判 error（CT24） |
| `groups[].fight` | 否 | `true` 或 genre/title 含武打词时查受力反馈与重心恢复（CT19） |
| `groups[].reverse` | 否 | 反向提示词全文；出现就必须含第 0 段三组词（CT21） |

## 字段说明
| 键 | 必填 | 说明 |
|---|---|---|
| `meta.mode` | 是 | 决定编号格式、反向画幅项、总览 sheet、时长窗口 |
| `meta.aspect` / `resolution` | 是 | 写进画面参数与生成限定词 |
| `meta.chars_per_sec` | 否 | 默认 2.25；允许 2.0–2.5 |
| `anchors.characters[].look` | 是 | 正向提示词每组复写，一字不改 |
| `groups[].duration` | 是 | 0.1 秒精度；必须等于 shots 时长之和（verify 检查） |
| `groups[].params.ref` | 否 | `[体裁, 条号, 本组用法]`，build 时展开为附件6 原文 |
| `shots[].cam` | 是 | 景别/角度/焦段/光圈/景深/运镜 |
| `shots[].act` | 是 | 动作物理化七要素 |
| `shots[].emo` | 是 | 情绪物理化（肌肉参数） |
| `shots[].breath` | 否 | 每分钟呼吸次数；0 = 不写；缺省由 build 追加 |
| `shots[].dialogue` | 否 | 原文台词；无对白留空串 |
| `shots[].sfx` | 是 | 带触发时间的音效 |
| `shots[].note` | 是 | 画面备注：非聚焦微动态/衔接/转场 |
| `groups[].sfx_layers` | 是 | 四层齐全 |
| `groups[].neg.plot` | 是 | 剧情不符禁用项，逐组不同 |
| `groups[].params.reference` | 否 | 参考电影，写《片名》年份，≤1 部；与 `params.ref`（附件6）二选一或并用 |
| `groups[].shots[].tech` | 否 | 技法标签，`"中文名｜落点｜档位｜参数片段"` 或对象；用于生成「技法映射」sheet |
| `acts[]` | 短篇必填 | 幕/场结构，verify 按此核算幕占比 |

## V2.8 新增：资产根口径、风格包正文、原生配音 `audios`

**资产根只有一个口径**（V2.8）：校验和投喂都用 `--assets-root`（旧名 `--root`／`--assets` 仍认）。它的值＝项目的 `资产/` 目录本身，不是 `资产/boards/`。所以 json 里所有 `path`／`file` 一律写**含子目录的相对路径**：

```json
"boards":   [{"unit": 1, "path": "boards/KB_S03_U01_v1.png"}]
"scenes":   [{"id": "SCN_S03_01", "image": "scenes/SCN_S03_01.jpg"}]
"audios":   [{"id": "AUD_S03_U03_v1", "file": "audio/AUD_S03_U03_v1.mp3", "group": 3, "from_native": true}]
```

**风格包正文**（V2.8）：`ct_rules.STYLE_PACKS[pack]["prefix"]` 是唯一真值源，分镜图提示词的风格前缀照抄它，`10-分镜图提示词.md` 里那三段只是副本（测试会核对两边一致）。

**原生配音**（V2.8）：平台原生配音抽出来之后进 `assets.audios[]`，字段 `id`／`file`／`group`（属于第几组）／`version`／`from_native`。被组引用时 `refs[].kind` 写 `audio`，文件名必须能在 `audios` 里对上（CT29）。

## V2.12 新增：分镜图占名额、提示词字数按档位、分镜图可兼首帧

| 键 | 取值 | 说明 |
|---|---|---|
| `refs[]` 里 `kind: board` | — | **占一张图片名额**：2.0 的 9 张、2.5 flash 的 10 张、2.5 的 30 张都要扣掉它（CT17 按 `pics = len(have)` 判） |
| `groups[].prompt` | 2.0 ≤ **4000** 字；2.5 flash／2.5 ≤ **10000** 字 | 平台实测上限；软预算取 3/4（3000／7500），超软预算 CT32 warning |
| `refs[].role` | 分镜图可写 `first_frame` ＋ `shot_ref` 复合 | 2.5 里同一张分镜图可以**兼首帧**（既是逐镜参考又是生成起点）；一组只能有一张首帧（CT31） |

## V2.11 新增：schema 字段、meta 白名单、提示词字数预算、资产 id 唯一

| 项 | 规范 | 判定 |
|---|---|---|
| `schema` | 分镜数据写 `"sbdata/1"`，关键词数据写 `"kwdata/1"` | 缺 → CT33 warning（旧文件提示）；写了不认识的值 → error |
| `meta` 键名 | 认识的键见 `ct_rules.META_KEYS`（title/episode/mode/aspect/resolution/target_seconds/era/weather/tier/model/version/style_pack/project/source/chars_per_sec/notes…） | 长得像笔误（如 `epsoide`）→ CT33 warning；不相干的自由字段不报 |
| 提示词字数 | 软预算 900 字、硬线 1400 字（含风格前缀与禁用句） | 超软预算 CT32 warning；超硬线 warning 并建议拆组——**平台上限未实测** |
| 资产 id | `scenes`／`boards`／`items`／`audios`／`characters`／`staging` 各自桶内 id 唯一 | 重复 → CT33 error |

## V2.10 新增：引用角色枚举、首帧唯一、版本自动递增

| 项 | 规范 | 判定 |
|---|---|---|
| `refs[].role` 枚举 | 分镜图：`first_frame`（2.5 组当生成起点）/ `shot_ref`（2.5 逐镜参考）；资产图：`look_ref`／`cloth_ref`／`item_ref`／`scene_ref` | 不在枚举里 → CT31 warning |
| 首帧唯一 | 一组只能有一张 `first_frame`，而且那张必须是 `kind: board` | 多张 → CT31 error；资产图标 `first_frame` → warning（会被算进图片名额） |
| >15 秒组必须有首帧 | 2.5 组没标首帧，模型自己挑起点，容易和上一段接不上 | CT31 warning |
| 版本号 | `meta.version` 缺省 1；`run_generate.py` 扫输出目录取最大值，回退时自动 +1 并提示 | 旧版移到 `archive/` |
| 组号正则 | 缺省 `S\d+-XZ-\d+`；换编号体系用环境变量 `GATE_GROUP_PATTERN` 覆盖 | 一个组号都认不出时 `gate.py assets` 打红字 |

## V2.9 新增：分镜图 `shot` 维度与声线锚点

| 字段 | 什么时候填 | 说明 |
|---|---|---|
| `assets.boards[].shot` | 多镜组（单元内 ≥2 镜）必填 | 镜号（`S01`/`S02`）。单镜组可不填。多镜组逐镜各出一张，缺哪镜 CT25 会指出来；关键单元（跨段衔接／打戏／B 级峰值）缺镜是 error |
| `anchors.characters[].voice` | 有台词的角色必填 | `{"timbre": "低、平、几乎不抬", "rate": "慢", "accent": "北方口音"}`。平台原生配音按台词自己挑音色，不写锚点换一集就换嗓子（CT30） |
| `groups[].sfx_layers.voice` | 本组有人声时必填 | 照抄声线锚点，并点名角色：「谢听（低平、句子极短）」。没提到角色名 CT30 报 warning |

## V2.6 新增：风格包 `style_pack` 与分镜图的使用条件

| 键 | 必填 | 说明 |
|---|---|---|
| `style_pack`（顶层） | 出分镜图时必填 | 整集唯一：`modern_live`（现代真人写实）／`ancient_period`（古装年代）／`3d_stylized`（3D 漫风格化）。也认中文别名「现代/古装/3D」。不在枚举里 → CT28 error；出了分镜图却没写 → CT28 warning |
| `refs[]` 里的分镜图 | — | **只有组时长 >15 秒（走 2.5）时才挂**；4–15 秒的 2.0 组不需要分镜图（CT17 warning）。分镜图**也占一张图片名额**（V2.12 平台实测，9/10/30 里要扣掉它） |

**分镜图怎么标**：`refs` 项写 `kind: board`（或 `分镜图`／`关键帧`）；文件名建议 `KB_` 开头。文件名是 `KB_…` 却没标 `kind: board` → CT17 warning。

**风格包的作用**：风格前缀（分镜图提示词第 0 段）不再是每张图现编，而是从 `style_pack` 取；单元里的 `style` 字段只能补差异（比如"这一场改冷调"），不许另起一套。

## V2.5 新增：`prompt` 的多镜格式与图锚

| 键 | 必填 | 说明 |
|---|---|---|
| `groups[].prompt` | 是 | 多镜组要自带分镜标记：`镜N（起-止 秒）：景别，动作；切点＝…`。标记数必须等于 `shots` 数量，否则 CT27 warning |
| `groups[].shots` | 是 | 单组最多 **6** 个；镜里 `pic`/`act` 必须点名角色，出现「两人/三人/他们/大家」→ CT27 warning |
| `正文里的 [图锚 KB_xxx]` | 否 | 指名某张分镜图；必须能在 `refs[].file` 里找到，否则 CT17 error。图锚算一次引用（不会报"没被引用"） |

## 命名与落盘

- 路径：`work/{剧名}_S{集}_kwdata.json`（与交付 Excel 同目录一份）
- 编码 UTF-8；不要 BOM；不要注释
- 改一句台词只改这里，然后重跑 `build_xlsx.py`
