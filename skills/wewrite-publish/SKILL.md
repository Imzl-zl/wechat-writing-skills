---
name: wewrite-publish
description: |
  WeWrite 排版发布模块：把 Markdown 做成微信预览，或在用户明确授权后推入公众号草稿箱；
  也支持主题画廊和图片帖。只处理微信公众号。
allowed-tools:
  - Bash
  - Read
  - Write
  - Edit
  - Glob
---

# wewrite-publish — 排版、预览、草稿箱

## 前置

用户指定文章时使用该文件；否则 `wewrite run show`。如果
`artifacts.illustrated_article` 存在且非空就使用它，否则使用 `artifacts.article`；读取标题、
摘要、封面、预览路径、发布权限和降级标记。已完成文章可以直接排版或发布，不要恢复写作
任务。**主题不要默认取 style.yaml**：按下方「自动选模板」判型选定，style.yaml 的 `theme`
只在判型落空时兜底。

排版和发布不得自动调用 `wewrite-visual`。没有封面时照常生成本地预览；只有用户另行要求
配图时才进入视觉模块。

用户本轮明确要求“推到草稿箱/发布”时，有任务先运行
`wewrite run permission publish allow`；用户撤回时运行 `wewrite run permission publish deny`。
只排版、预览或“完整制作”都不能授予发布权限。

有任务时进入：

```bash
wewrite run step publish in_progress
```

## 预检

- 标题存在且符合微信限制；摘要不超过 120 字节；正文 200-20000 字。
- 正文图片不超过 10 张且实际可读；表格不超过 4 列。
- **图片文件名不要中英混排**（如 `允许使用的agent.png`）：渲染器会给属性值里的中西文边界
  插空格，导致 src 对不上文件而裂图。apply_template.py 已对裁切框图片自动做百分号编码；
  走普通 markdown 图片引用时遇到混排文件名先改名（纯中文或纯英文）。
- 发布草稿必须有封面。没有封面不能假设微信会补默认图，改走本地预览。
- 发布必须同时满足：`permissions.publish=true`、`flags.skip_publish=false`、用户本轮没有撤回。

## 动作

### 1. 自动选模板并预览

**用户明确指定了主题 → 直接用指定主题**，跳过判型。用户没指定时，AI 按文章内容自动选，
不要反问、不要默认套同一个主题：

1. **判型 → 先选模板、再选配色**：读成稿正文，按 `{skill_dir}/references/theme-selection.md`
   第 1 节信号表判定类型（tutorial / story / analysis / listicle / promo / faq / log /
   knowledge），再按第 2 节映射**先定模板（版式结构）、再定主题（配色）**——默认配色随模板，
   用户想换色随时只换 `--theme`。判型结果（类型 + 模板 + 配色 + 一句话理由）要在回复里
   告诉用户。
2. **套模板结构**：主题 ≠ 模板。主题只是 CSS 皮肤；`kazk-editorial`、`bold-contrast`
   注册了模板层（标题装饰/分隔线/图片框的确定性问题变换）。选了带模板层的主题时，先跑
   `{skill_dir}/scripts/apply_template.py` 把 markdown 重写成版式结构再渲染，**不许跳过、
   也不许手工即兴改**，否则模板就退化成"换个颜色的普通主题"：

```bash
PYTHONIOENCODING=utf-8 python {skill_dir}/scripts/apply_template.py {article} \
  --template {选定主题} [--theme {配色主题}] --labels '{"小节标题": "ENGLISH / LABEL", ...}' -o {decorated_md}
wewrite preview {decorated_md} --theme {选定主题} --no-open -o {preview}
```

`--theme` 可让模板结构穿任意配色（如 `--template kazk-editorial --theme ai-practice` =
编辑部版式 × 深青琥珀配色），省略时用模板原生配色。用户说"结构不变换个颜色"就只改
`--theme`。`--labels` 的英文小标签由 AI 按各小节主旨拟定（这是判断活，脚本不编）；拿不准
就省略，脚本用 SECTION 0N 兜底。没注册模板层的主题（内置 8 个 + red-pastel 等）直接用
原 markdown。模板库可视化展示页（模板 × 配色矩阵，给用户挑选用）：
`.wewrite/output/theme-gallery/showcase.html`。
3. **渲染最终预览**，有任务时保存到 `artifacts.preview`；任务外文章保存到原文件旁：

```bash
wewrite preview {article} --theme {自动选定的主题} --no-open -o {preview}
```

只出这一张最终预览，不再默认生成备选对比图（用户反馈默认模板+反复换预览太死板）。
用户看后说"换个感觉"→ 按 theme-selection.md 映射表的备选列换；说"太花/太素"→ 同类型
内降/升一档装饰度；说"换成 xxx"→ 直接换。换完重新 preview，`artifacts.preview` 写最终
选定主题的路径；只有再次明确要求才重新 publish。

确认预览产物存在且通过兼容性校验。若没有明确发布权限，流程到此结束；"写一篇""完整制作"
都不等于允许发布。

### 2. 一键复制（未配置 appid/secret，或用户想自己粘贴时）

用户没有配置草稿箱凭证、或明确想手动粘贴时：

```bash
PYTHONIOENCODING=utf-8 python {skill_dir}/scripts/copy_page.py {preview} -o {preview_copy}
```

打开 `{preview_copy}`，用户点右上角「复制全文」按钮 → 去公众号编辑器 Ctrl+V。

排版不乱的原理：微信编辑器粘贴时只保留元素内联 style，丢弃 `<style>` 块和复杂布局；
wewrite 的 preview 正文全部内联样式，所以粘贴后样式保留。若用户反馈粘贴后变乱，优先
检查正文是否混入了 `<style>` 依赖（如 flex、绝对定位、class 引用），用 `wewrite validate`
校验并换更简单的主题。

### 3. 草稿箱发布（已配置 appid/secret）

#### 公众号名称与文章作者

- `style.yaml` 的 `author` 是写作署名偏好，不自动映射为微信草稿的 `author` 字段。
- 默认发布命令**不要传 `--author`**。公众号扫码预览会自动显示账号名称，传入 `--author` 会额外显示一个文章作者名。
- 只有用户明确要求额外显示文章作者时，才传入 `--author "..."`。

用户问“怎么配凭证/找不到 AppSecret”时，按以下指引（微信 2025 年起已迁移）：

1. AppSecret 不在公众平台旧路径了，去**微信开发者平台** developers.weixin.qq.com：
   扫码登录 → 我的业务/我的业务与服务 → 公众号 → 基础信息 → 开发密钥 → 启用/重置。
2. 个人号提示“该账号尚未完成实名”→ 微信公众平台 → 设置与开发 → 人员设置 →
   管理员信息，确认管理员已完成实名后再回来启用。
3. 拿到后写入 `{home}/config.yaml` 的 `wechat.secret`（appid 已存），或设环境变量
   `WECHAT_SECRET`。只存本地。
4. 调用 access_token 接口要求 API IP 白名单：报错 61004 时去开发者平台「开发密钥」
   把本机公网 IP 加入白名单；家用宽带 IP 会变，变了再报 61004 就更新白名单。

只有用户明确要求草稿箱且预检全部通过时执行：

```bash
wewrite publish {article} --cover {cover} --theme {theme} --title "{title}" --digest "{digest}"
```

发布失败时保留预览，不自动重试产生外部动作。有任务时更新 `publish.preview_html`；成功时再写
`publish.media_id`，随后：

```bash
wewrite run step publish completed
```

## 辅助功能

| 用户说 | 动作 |
|---|---|
| 看模板/换配色 | 打开 `.wewrite/output/theme-gallery/showcase.html`（8 模板 × 15 配色，点色卡即换）；`wewrite gallery` 只是裸 markdown 对比，看不出结构层，别拿它当模板库 |
| 换主题 | 重新 preview；只有再次明确要求才重新 publish |
| 做图片帖 | 先确认用户确实要推草稿箱，再执行 `wewrite image-post` |
| 只排版 | 只 preview |
