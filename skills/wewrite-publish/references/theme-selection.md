# 自动选模板（theme-selection）

> 排版前由 AI 阅读成稿，判断内容类型 → 直接选定主题，不等用户指定。
> 用户明确指定主题时，用户优先，本表让位。

## 1. 判型信号（读成稿正文，不读标题党）

按顺序检查，命中即停；前 3 条都不命中再看兜底规则。

| 信号 | 特征（在正文里找） | 判定类型 |
|---|---|---|
| **教程/测评** | 编号步骤、命令块/代码块、"打开→点击→设置"路径、截图引用、参数表格 | tutorial |
| **体验记/叙事** | 第一人称贯穿、时间线（"那天/后来/刚开始"）、情绪词、踩坑转折、无代码或代码只是点缀 | story |
| **深度分析** | 引用数据/来源、多段落长论证、对比表格、行业术语密度高、观点层递进 | analysis |
| **清单/资源** | 条目数 ≥8、每条含链接或工具名、段落短促、"整理/汇总/合集" | listicle |
| **福利/活动** | 出现额度、领取条件、截止时间、报名链接 | promo |
| **问答/测评** | 小节是疑问句、一问一答结构、自问自答 | faq |
| **过程日志** | Day N / 第X天 / 时间标记贯穿、流水式记录 | log |
| **干货科普** | 小节多且短、每节一个知识点、定义/概念密集 | knowledge |

兜底：信号混杂时，看**前 40% 篇幅**的主导类型（读者对模板的第一印象在前几屏形成）；
仍拿不准 → 按 `analysis` 处理（最不容易出错的版式）。

## 2. 选定顺序：先模板（结构），再主题（配色）

两个独立的决定，**永远先定模板、再配配色**：

- **模板（结构）**= apply_template.py 的注册名，决定标题形态、分隔线、图片框：
  `kazk-editorial` / `bold-contrast` / `qa-bubble` / `timeline-log` / `knowledge-card` / `press`；
  无结构层的类型走纯 CSS 骨架（通用极简 / 卡片标题）。
- **主题（配色）**= 任意主题 yaml 的名字，只管颜色。默认用与模板同名的原生配色；
  模板名 ≠ 主题名即可任意组合（如 `--template press --theme kazk-editorial`）。

| 类型 | 模板（结构） | 默认配色 | 备选模板 |
|---|---|---|---|
| story（体验记/观点/踩坑） | `kazk-editorial` | `kazk-editorial` 翠绿琥珀 | `timeline-log`、warm-editorial |
| tutorial（教程/工具实操） | `knowledge-card` | `knowledge-card` 知识蓝 | 通用极简 + `github`（代码极多、追求最素时） |
| analysis（深度分析/行业） | `press` | `press` 墨黑朱砂 | newspaper、impeccable（纯 CSS） |
| listicle（清单/资源汇总） | 通用极简（无结构层） | `sspai` 少数派红 | `knowledge-card` |
| promo（福利/活动） | 卡片标题（无结构层） | `token-rhythm-benefit` 朱红金 | red-pastel |
| faq（问答/测评） | `qa-bubble` | `qa-bubble` 微信绿 | `knowledge-card` |
| log（过程日志/踩坑记录） | `timeline-log` | `timeline-log` 靛蓝 | `kazk-editorial` |
| knowledge（干货科普） | `knowledge-card` | `knowledge-card` 知识蓝 | 通用极简 + sspai |
| 节日/情感/品牌向软文 | 卡片标题（无结构层） | `red-pastel` 正红 | `bold-contrast` |

用户说"结构不变换个颜色"→ 只改 `--theme`；说"换个版式"→ 换 `--template`（配色沿用
当前主题或回落原生配色）。模板 × 配色可视化：
`.wewrite/output/theme-gallery/showcase.html`（8 模板 × 15 配色，点色卡即换）。

本号专属主题（.wewrite/themes/ 下的 yaml，9 个）：`ai-practice`（默认兜底，hero 标题卡）、
`kazk-editorial`（编辑部杂志风）、`bold-contrast`（演讲金句风）、`qa-bubble`（问答气泡）、
`timeline-log`（时间线日志）、`knowledge-card`（知识点卡）、`press`（报刊墨渍）、
`red-pastel`、`token-rhythm-benefit`。
内置主题（编译在 CLI 里）：`github`、`tech-modern`、`newspaper`、`impeccable`、
`professional-clean`、`sspai`、`minimal`、`warm-editorial` 等 18 个。

判型全部落空时 → 兜底：`ai-practice`（卡片标题结构，深青琥珀配色）。

## 3. 主题 vs 模板（两层，别混）

- **主题（theme）**：`.wewrite/themes/*.yaml`，纯 CSS 皮肤（base_css），CLI 原生支持。
  只管字号/颜色/引用块样式这类文字排版。所有主题的裸 markdown 渲染出来骨架都一样——
  这不是 bug，是主题这一层的定义。
- **模板（template）**：主题皮肤 + 版式结构。结构（幽灵数字小节号、三色圆点线、图片
  裁切框、编号标题）由 `{skill_dir}/scripts/apply_template.py` 在渲染前对 markdown 做
  确定性变换实现，渲染器透传内联 HTML。**选了带模板层的主题必须跑脚本**，跳过脚本 =
  又变回"换色主题"。目前注册了模板层的主题（6 个）：
  - `kazk-editorial`：h2→幽灵数字小节（自动 01/02 编号），`---`→三色圆点线，
    独立成段的图→四角裁切框 + FIG 编号 + 图说
  - `bold-contrast`：h2→等宽琥珀色「01 /」编号前缀；金句卡/短黑线靠 CSS 自动
  - `qa-bubble`：h2→「问」徽章 + 聊天气泡
  - `timeline-log`：h2→时间轴节点（圆点 + 下垂轴线）
  - `knowledge-card`：h2→浅底圆角知识卡 + 数字章
  - `press`：h2→「一、二、三」中文编号（衬线/双细线靠 CSS）

新增模板层：在 apply_template.py 的 TEMPLATES 注册表加一个变换函数 + theme-selection.md
本节登记一行。图片 URL 未配图 API 时可先留占位，配图后重跑变换即可。

## 4. 交互规则

- 排版时**按第 2 节先定模板、再定配色，直接出最终预览**，不再默认生成 2 张备选对比图（用户说过默认模板+反复预览太死板）。
- 用户看预览后说"换个感觉"→ 按"备选"列换；说"太花/太素"→ 同类型内降/升一档装饰度
  （story: kazk-editorial ↔ warm-editorial；tutorial: github ↔ tech-modern）。
- 用户点名主题 → 用点名主题，判型结果只写在回复里做说明。
- 连续 2 次被用户换掉同一类型的主题 → 在回复里建议用户改 style.yaml 默认主题或本表的映射。
