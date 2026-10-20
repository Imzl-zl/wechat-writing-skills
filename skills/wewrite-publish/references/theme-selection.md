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
  `kazk-editorial` / `bold-contrast` / `qa-bubble` / `timeline-log` / `knowledge-card` / `press` /
  `tutorial-dashboard` / `muppet-editorial`；无结构层的类型走纯 CSS 骨架（通用极简 / 卡片标题）。

  `tutorial-dashboard` 可选用 `tutorial_dashboard` YAML frontmatter 补全 Hero、路线图、问题卡、标签云、流程条、
  连接参数卡、提醒清单和收尾行动区；组件内容放在 `blocks`，正文用
  `<!-- tutorial-dashboard:<block> -->` 定位。未提供时仍会从文章的 `#` / `##` / `###` 标题，
  以及展平来源中的 `PART` / `STEP` 标记生成 Hero、路线图、章节和步骤。
- **主题（配色）**= 任意主题 yaml 的名字，只管颜色。默认用与模板同名的原生配色；
  模板名 ≠ 主题名即可任意组合（如 `--template press --theme kazk-editorial`）。

| 类型 | 模板（结构） | 默认配色 | 备选模板 |
|---|---|---|---|
| story（体验记/观点/踩坑） | `kazk-editorial` | `kazk-editorial` 翠绿琥珀 | `timeline-log`、warm-editorial |
| tutorial（教程/工具实操） | `tutorial-dashboard` | `emerald-tutorial` 翠绿教程 | `knowledge-card`、`github`（代码极多、追求最素时） |
| analysis（深度分析/行业） | `press` | `press` 墨黑朱砂 | newspaper、impeccable（纯 CSS） |
| listicle（清单/资源汇总） | 通用极简（无结构层） | `sspai` 少数派红 | `muppet-editorial`、`knowledge-card` |
| promo（福利/活动） | `muppet-editorial` | `muppet-editorial` 暖灰炭橙 | `token-rhythm-benefit`、卡片标题 + `red-pastel` |
| faq（问答/测评） | `qa-bubble` | `qa-bubble` 微信绿 | `knowledge-card` |
| log（过程日志/踩坑记录） | `timeline-log` | `timeline-log` 靛蓝 | `kazk-editorial` |
| knowledge（干货科普） | `knowledge-card` | `knowledge-card` 知识蓝 | 通用极简 + sspai |
| 节日/情感/品牌向软文 | 卡片标题（无结构层） | `red-pastel` 正红 | `bold-contrast` |

用户说"结构不变换个颜色"→ 只改 `--theme`；说"换个版式"→ 换 `--template`（配色沿用
当前主题或回落原生配色）。模板 × 配色可视化：
`.wewrite/output/theme-gallery/showcase.html`（10 模板 × 16 配色，点色卡即换）。

本号专属主题（.wewrite/themes/ 下的 yaml，11 个）：`ai-practice`（默认兜底，hero 标题卡）、
`kazk-editorial`（编辑部杂志风）、`muppet-editorial`（暖灰炭橙简报风，带模板层）、
`bold-contrast`（演讲金句风）、`qa-bubble`（问答气泡）、
`timeline-log`（时间线日志）、`knowledge-card`（知识点卡）、`press`（报刊墨渍）、
`emerald-tutorial`（翠绿教程皮肤）、`red-pastel`、`token-rhythm-benefit`。
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
  又变回"换色主题"。目前注册的模板层（8 个）：
  - `kazk-editorial`：h2→幽灵数字小节（自动 01/02 编号），`---`→三色圆点线，
    独立成段的图→四角裁切框 + FIG 编号 + 图说
  - `bold-contrast`：h2→等宽琥珀色「01 /」编号前缀；金句卡/短黑线靠 CSS 自动
  - `qa-bubble`：h2→「问」徽章 + 聊天气泡
  - `timeline-log`：h2→时间轴节点（圆点 + 下垂轴线）
  - `knowledge-card`：h2→浅底圆角知识卡 + 数字章
  - `press`：h2→「一、二、三」中文编号（衬线/双细线靠 CSS）
  - `muppet-editorial`：刊头细线与大标题 + 炭黑结论条（chips）+ 可选的 EDITOR'S NOTE 按语卡，
    h2→PART 编号小节（`///`+END 收尾头自动识别「最后/结语/总结」），h3→`### Step N 标题`
    出 Step 徽章、其余出胶囊小标题，独立成行的 `**短句**`→胶囊小标题，引用→浅底提示卡，
    图片→虚线图框，表格→卡片式表格；可选 frontmatter：

    ```yaml
    muppet:
      masthead: TOKENRHYTHM          # 刊名（缺省用 author，再缺省 FIELD NOTES）
      date: "2026.09.16"            # 刊头右侧日期
      kicker: 副标题一句话
      lead: 注册 → 跑一次调用 → 额度到账   # 黑色结论条左侧
      tags: [额度福利, 限时]          # 结论条右侧小标签
      note:                          # EDITOR'S NOTE 按语卡（可省）
        label: EDITOR'S NOTE
        caption: 原文摘录 · 实情见下文
        text: 引言正文
      closing:                       # 收尾卡（可省）
        text: 先注册先落袋：这一笔确定
        label: THANKS FOR READING
    ```
  - `tutorial-dashboard`：Hero 教程信息卡 + PART 横向路线图（等高卡片、可内部横滑）+ h2 / 展平来源的 PART 章节号 +
    h3/h4 / 展平来源的 STEP 标记 + 问题卡、标签云、流程条、连接参数卡、提醒清单、提示卡、截图框、
    按内容分配列宽的表格和行动区；默认皮肤 `emerald-tutorial`，可用 `--theme` 任意换色

  可选 frontmatter（不写也能用）：

  ```yaml
  tutorial_dashboard:
    eyebrow: "TUTORIAL · AI PRACTICE"
    issue: "2026.09"
    question: "读者正在遇到的问题"
    subtitle: "完成这篇教程后能做到什么"
    ribbon: "教程短标题"
    tags: ["零命令行", "可复用"]
    section_labels:
      安装工具: "INSTALL / 2 MIN"
    outcome:
      label: "看完这 5 分钟"
      text: "读者能完成的具体结果"
    closing:
      text: "收尾 CTA 或下一步"
    blocks:
      problem:
        items: ["读者当前的重复操作或痛点"]
        emphasis: "这篇教程要解决的结论"
      flow:
        items:
          - { title: "安装", meta: "启动服务" }
          - { title: "配置", meta: "保存参数" }
      connection:
        items:
          - { title: "接口地址", text: "localhost:3001/v1" }
      truths:
        title: "开始前的 3 个提醒"
        items: ["不公开真实 Key"]
      summary:
        text: "收尾结论"
      cta:
        text: "互动提示"
        button: "收藏教程"
  ```

  `problem`、`tag-cloud`、`stats`、`flow`、`connection`、`truths`、`summary`、`cta` 用对应的
  `<!-- tutorial-dashboard:<block> -->` 注释放入正文；配置项和插槽必须一一对应，缺配置、漏放或重复
  都会直接报错，避免悄悄漏掉模块或改变文章结构。

新增模板层：在 apply_template.py 的 TEMPLATES 注册表加一个变换函数 + theme-selection.md
本节登记一行。图片 URL 未配图 API 时可先留占位，配图后重跑变换即可。

## 4. 交互规则

- 排版时**按第 2 节先定模板、再定配色，直接出最终预览**，不再默认生成 2 张备选对比图（用户说过默认模板+反复预览太死板）。
- 用户看预览后说"换个感觉"→ 按"备选"列换；说"太花/太素"→ 同类型内降/升一档装饰度
  （story: kazk-editorial ↔ warm-editorial；tutorial: github ↔ tech-modern）。
- 用户点名主题 → 用点名主题，判型结果只写在回复里做说明。
- 连续 2 次被用户换掉同一类型的主题 → 在回复里建议用户改 style.yaml 默认主题或本表的映射。
