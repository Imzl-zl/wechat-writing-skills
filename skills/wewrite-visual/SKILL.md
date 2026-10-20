---
name: wewrite-visual
description: |
  WeWrite 视觉模块：为公众号文章生成封面和必要的内文配图，或只交付提示词。触发词：
  封面图、公众号配图、给文章配图、换封面。通用绘图和 logo 设计不触发。
allowed-tools:
  - Bash
  - Read
  - Write
  - Edit
  - Glob
---

# wewrite-visual — 封面与配图

## 前置

用户指定文章时使用该文件；否则 `wewrite run show`，读取当前任务的 `artifacts.article`、
`artifacts.illustrated_article`、`artifacts.image_prompts`、`artifacts.images_manifest`、
`visual`、`flags` 和任务目录。已完成的文章也可以直接配图，不要恢复或新建写作任务。

有任务时运行 `wewrite run step visual in_progress`。用户直接给了任务外文章时独立执行，
不写任务状态；提示词和图片放进文章同目录的 `<文件名>-assets/`，带图副本写成
`<文件名>-illustrated.md`。

根据本轮原话确定模式并用 `wewrite run update` 记录：只要封面用 `cover`，封面和必要内文图
用 `full`，只要提示词用 `prompts`。不要沿用写作模式猜测用户想生图。`prompts` 或
`skip_image_gen=true` 时仍要完成提示词，但不调用付费图片服务。

完整读取：

```text
读取: {skill_dir}/references/visual-guide.md
```

## 执行

0. **封面必须你自己设计，不能只交提示词。** 生图模型画不准中文，标题必须由本机渲染：
   读完文章先写一句话说清“这张封面只讲哪一件事”，从正文里挑出那个数字或短句当主角，
   其余文字全部让位。**封面统一走 `{skill_dir}/scripts/make_cover.py` 渲染（写
   `cover-design.json` 再跑脚本），不要手写 HTML，也不要复制上一篇文章目录里的脚本**
   （那会把旧配色一起带过来）。该脚本带两道闸门：成品与任何已有封面逐字节相同会报错
   退出；加 `--check-palette` 还能检测主色与历史封面接近的情况——同一套配色换文案，
   逐字节不同但看起来一样，只有这道闸门拦得住。撞车时改设计、不要用 `--allow-duplicate`
   绕过。配色按文章内容另定，**不要默认套 `ai-practice` 的深青 + 琥珀**（大面积铺开偏绿
   发闷，且会让所有封面长得一样）。

1. 从终稿提取 3-5 个具体实体和文章主情绪，形成统一色板、构图与质感。
2. 写一个封面提示词。`cover` 模式到此为止；`full` 模式只为确实需要解释或缓冲阅读的
   段落补图，不按固定数量凑图。
3. 将提示词和目标路径写到 `artifacts.image_prompts`；批量清单写到
   `artifacts.images_manifest`。
4. 数量必须不超过任务的 `visual.max_images`。调用时同时传入数量和费用上限：

```bash
wewrite image-gen --manifest {run_dir}/images.json --max-images {max_images} --max-cost {max_cost}
```

`max_cost` 为空时省略该参数。预算预检不通过就减少内文图，不能绕过上限。图片服务失败时
保留完整提示词并继续流程。

5. 一次性检查所有实际文件：能打开、格式与扩展名一致、核心实体可辨、风格连贯。只重试
   明显失败的单张一次。封面另做一次缩略图检查：把成品缩到 360px 宽，主标题还读得出来
   才算过；读不出来就加大字号、减少元素重渲染。`full` 模式先复制原始正文到
   `artifacts.illustrated_article`，再把采用的内文图插到副本相应段落；封面不插入正文。
   任何模式都不得覆盖原始正文。

完成后更新 `images.cover`、`images.figures`，再执行：

```bash
wewrite run step visual completed
```

只有提示词时同样标 completed，并明确说明未产生费用、没有实际图片。
