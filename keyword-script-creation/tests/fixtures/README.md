# tests/fixtures · 本地素材放这里（不进仓库）

`tests/run_all.py` 第一步要用**关键词脚本规范文档**来重建四套技法库（`lib/att3..att6`）。
该文档有版权、不适合随仓库分发，所以仓库里只留这个空目录说明。

两种给法，任选其一：

1. 放到这里：`tests/fixtures/关键词脚本生成规范.docx`
2. 或用环境变量指过去：

   ```bash
   set KW_SPEC_DOCX=D:\你的规范\关键词脚本生成规范.docx     # Windows
   export KW_SPEC_DOCX=/path/to/规范.docx                  # macOS / Linux
   ```

两者都没有时，第一步会打印「跳过四库重建」并继续跑后面的步骤——不算失败。
`lib/` 里已经带了构建好的库，日常校验不需要重建。
