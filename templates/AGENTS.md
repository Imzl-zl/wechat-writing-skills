# 公众号写作项目

本目录是微信公众号内容生产工作区。所有 AI 写作、排版、去 AI 味任务在此完成。

> 用法：把本文件拷到你的内容项目根目录，改掉 `<SKILLS_DIR>` 和 `<HOME>` 两处占位符。
> `<SKILLS_DIR>` 是你的 Agent 放 skills 的目录（`.agents/skills` / `.claude/skills` / `.pi/skills`），
> `<HOME>` 指本项目的 `.wewrite`。

## 已安装的 Skills（位于 `<SKILLS_DIR>/`）

| Skill | 用途 | 触发语 |
|---|---|---|
| `wewrite` | 主入口：选题→写作→审稿→排版→草稿箱全流程 | "写一篇公众号文章"、"写公众号" |
| `wewrite-write` | 写作（7 层去 AI 味 + 写作人格） | "就这个选题写一篇" |
| `wewrite-topic` | 热点抓取 + 选题评分 | "今天写什么" |
| `wewrite-review` | 审稿 + 质量评分（11 项检测） | "检查一下这篇" |
| `wewrite-publish` | 模板库排版（先模板后主题）→ 微信兼容 HTML → 草稿箱 | "排版"、"推到草稿箱" |
| `wewrite-visual` | 封面 + 文内配图 | "给这篇配个封面" |
| `wewrite-learn` | 学习用户修改、范文风格库、偷师主题 | "学习我的修改" |
| `wewrite-style` | 公众号风格设置（首跑必做） | "重新设置风格" |
| `wewrite-rewrite` | 一稿多发：小红书/抖音改写 | "改写成小红书版" |
| `wewrite-stats` | 阅读数据回填、选题建议 | "看看文章数据" |
| `humanizer-zh` | 纯去 AI 味（任何稿子过一遍） | "去一下 AI 味" |

## 关键约定

- **一篇一个目录**：每篇文章一个独立目录，位于项目根目录（如 `my-first-post/`），素材图放
  `assets/`，正文和 HTML 放目录根。项目根目录只放系统文件（`<SKILLS_DIR>/`、`<HOME>/`、
  本文件）和文章目录；旧产物归 `_archive/`。写新文章前先建目录，素材先归位。
- **状态目录在项目内**：`WEWRITE_HOME` 指向本项目的 `<HOME>/`，style / config / 主题 / 历史 /
  runs 全在项目里，项目自包含。换终端不生效时手动指一次：
  `export WEWRITE_HOME=<项目绝对路径>/.wewrite`。
- **Windows 编码**：所有 `wewrite` 命令加前缀 `PYTHONIOENCODING=utf-8`，否则 GBK 终端会报
  UnicodeEncodeError。
- **主题 ≠ 模板，两层别混**：主题 = CSS 皮肤（`<HOME>/themes/*.yaml`，CLI 原生）；模板 = 皮肤 +
  版式结构，结构由 `<SKILLS_DIR>/wewrite-publish/scripts/apply_template.py` 在渲染前做确定性变换。
  **选了带模板层的排版，必须先跑脚本再 `preview`**，否则退化成换色主题。
- **排版自动选模板**：用户没点名时，先读成稿判型（教程/体验记/分析/清单/福利/问答/日志/科普），
  **先定模板（结构）、再定主题（配色）**，只出一张最终预览。决策表在
  `<SKILLS_DIR>/wewrite-publish/references/theme-selection.md`，可视化矩阵用仓库里的
  `themes/showcase.html`（浏览器直接打开，点色卡换色；它不随项目安装）。
- **首次使用**：先让用户说"设置公众号风格"（触发 wewrite-style onboard），之后每次只需一句话。
- **写一篇 ≠ 发布**：默认只交付本地审过的稿子；只有用户明确说"推到草稿箱/发布"才调发布，
  发布需要微信 appid/secret（存 `<HOME>/config.yaml`，永不入仓库）。
- **手动粘贴用一键复制**：没配凭证时用 `<SKILLS_DIR>/wewrite-publish/scripts/copy_page.py`
  生成带「复制全文」按钮的页面，点按钮复制，去公众号编辑器 Ctrl+V（正文全内联样式，粘贴不乱）。
- **配图**：需要图片 API key（`<HOME>/config.yaml` 的 `image.providers`）；没配时自动降级为
  本地 HTML + 图片提示词。
- **升级 CLI 后**：`uv tool upgrade wewrite` 会覆盖打过补丁的 site-packages，先跑补丁目录里的
  `*.py --check`（仓库 `tools/patches/`），报未应用就重跑，别以为补丁还在。

## 排版决策速查

先判型，再选模板，最后配主题。模板决定结构，主题只换配色：

| 体裁 | 默认模板 | 默认主题 |
|---|---|---|
| 教程 / 工具实操 | `tutorial-dashboard` | `emerald-tutorial` |
| 体验记 / 观点 / 踩坑 | `kazk-editorial` | `kazk-editorial` |
| 深度分析 | `press` | `press` |
| 福利 / 活动 / 安利 | `muppet-editorial` 或 `chengzi-benefit` | `muppet-editorial` / `chengzi-orange` |
| 问答 / 测评 | `qa-bubble` | `qa-bubble` |
| 过程日志 | `timeline-log` | `timeline-log` |
| 干货科普 | `knowledge-card` | `knowledge-card` |
| 清单 / 资源汇总 | 通用极简（无结构层） | `sspai` |

完整决策表（含备选模板与信号识别）见 `<SKILLS_DIR>/wewrite-publish/references/theme-selection.md`。
