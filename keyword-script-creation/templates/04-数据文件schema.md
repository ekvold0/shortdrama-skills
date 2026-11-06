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

## 命名与落盘

- 路径：`work/{剧名}_S{集}_kwdata.json`（与交付 Excel 同目录一份）
- 编码 UTF-8；不要 BOM；不要注释
- 改一句台词只改这里，然后重跑 `build_xlsx.py`
