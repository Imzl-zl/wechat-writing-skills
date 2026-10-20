# 已知问题清单（2026-10-20 实测记录）

来源：写一篇「Qoder + WorkBuddy 免费模型盘点」福利文时的实际返工。这不是设想，
是同一篇稿子被用户打回两次的真实过程。

---

## 一、写作端：内容扩展 / 掰开揉碎

### 现象

福利文只该讲三件事：**哪里免费、怎么免费、有啥免费**。实际产出里混进了：

- 「到期之后还有条后路」——自部署、vLLM/SGLang 部署、MIT 许可、HuggingFace 权重
- 「DeepSeek 这次对 WorkBuddy 做了框架适配」
- 「WorkBuddy 办公 / CodeBuddy 开发，编程用户优先选 Qoder」

用户原话：「谁让你后面又加带私活，还自部署，你搞笑呢，有多少人会自部署」。

初稿 1138 字 → 用户要求砍 → 876 字。砍掉的 262 字全是上述扩展内容，
正文信息量没有损失。

### 根因

**1. 长度下限是硬编码的，与内容类型无关**

- `skills/wewrite-write/SKILL.md:106`：「正文通常 1200-2500 字」
- `skills/wewrite-write/references/article-brief.md` 默认 `desired_length: "1200-2500 字"`

福利播报类内容天然短。三个到期日 + 一张表 + 几条注意事项，876 字已经完整。
**字数下限本身在制造扩展动机** —— 差额只能从读者用不上的地方长出来。

**2. `must_avoid` 字段没有任何地方检查它**

`article-brief.md` 定义了 `constraints.must_avoid`，但：

- `wewrite-review/SKILL.md` 的五项编辑判断（准确/观点/有用/合声/好读）没有一项
  检查「有没有超出 brief 范围」
- `editorial-quality.md` 只有一句「无关段落删除」，而"无关"对"自部署"这种内容是
  模糊的 —— 它确实相关于 DeepSeek 这个模型，确实有信息量

**3. 「发布声明 / 福利播报」这个体裁在写作模块里没有定义**

- `wewrite-publish/references/theme-selection.md` 里有 `promo` 类型（福利/活动），
  但那是**排版判型**，只管版式不管内容
- `wewrite-write/references/frameworks-quick.md` 的 7 种框架（痛点/故事/清单/对比/
  热点解读/观点/复盘）里**没有「发布声明」或「福利播报」**

结果：只能拿「清单」去套。清单框架天然会想「再多讲一条」，因为清单的价值
本来就来自条目数量。

**4. `playbook.md` 不存在，个人修改没被沉淀**

`wewrite diagnose` 长期报 `playbook: not found → no learned style`。
`wewrite learn-edits --summarize --json` 返回 `total_lessons: 0`。

用户在同一场会话里纠正了三次（掰开揉碎 / 太玄幻 / 别加私活），全部只存在于
对话上下文，没有落成规则文件。**每次新会话都要重新犯一遍。**

### 建议改法

| 位置 | 改什么 |
|---|---|
| `skills/wewrite-write/references/article-brief.md` | 增加体裁字段（如 `content_type: announcement \| tutorial \| analysis \| story`）。`announcement` 类允许 `desired_length: "600-900 字"`，且明确「不因字数不足而扩展议题」 |
| `skills/wewrite-write/references/frameworks-quick.md` | 增加「发布声明」框架：目标 → 事实清单 → 边界与例外 → 截止时间。不设「再深一层」的推进逻辑 |
| `skills/wewrite-review/SKILL.md` | 五项判断增加第六项「**守界**」：逐条核对 `brief.constraints.must_avoid`，命中即改稿，不给分 |
| `skills/wewrite-review/references/editorial-quality.md` | 「无关段落删除」改成可判定的表述：读者读完这一段，是否知道了新的、原本不知道的**且他本来想知道的事**？否则删 |
| `skills/wewrite-write/SKILL.md:106` | 「正文通常 1200-2500 字」改为按体裁取值，并补一句「体裁不匹配时长时，先削议题再削字数」 |

---

## 二、封面端：配色 / 风格重复

### 现象

用户看到新封面第一反应：「怎么又是这个配色啊？你不觉得丑吗？为啥老是这种配色啊？
**不是都改过吗？**」

追查发现：深青底 (#08191C) + 琥珀 (#D9A441) 这套是 **9-18 上一篇 Qoder 文章**
的封面样式，被直接复制到了 10-20 这篇。

而 10-12 的 artcraft 那篇已经明确放弃了这套。`artcraft-adobe-rust-rewrite/
cover-design.md` 里写着：

> **刻意不用深青配琥珀。** 那是 `ai-practice` 排版主题的配色，过去被反复套到
> 封面上，深色大面积铺开偏绿发闷，而且几篇不同文章的封面因此长得一模一样。

**这条教训只存在于一篇文章的目录里，不在 skill 里。**

### 根因

**1. skill 文档写得对，但只管「怎么生成」，不管「参考谁」**

`skills/wewrite-visual/SKILL.md` 已经写了：

> **封面统一走 `.wewrite/tools/make_cover.py` 渲染（写 `cover-design.json` 再跑脚本），
> 不要手写 HTML。** ……配色按文章内容另定，**不要默认套 `ai-practice` 的深青 + 琥珀**

`skills/wewrite-visual/references/visual-guide.md` 还给了分类配色建议
（调查类暖米+朱橙 / 事件类冷白+深蓝 / 教程福利类浅纸底+深绿深棕）。

但 skill 没有一条规则说「**不要拿上一篇文章目录里的脚本当模板**」。
同目录下有 `make_cover.py` 时，Agent 看到「上一篇就是这么做的」就复用了。

**2. 项目里有 3 份 `make_cover.py`，skill 只指了其中一份**

```
.wewrite\make_cover.py                    2839 bytes  09-18  ← 旧的，无去重闸门
.wewrite\tools\make_cover.py              12964 bytes  10-20  ← skill 指的这份，有闸门
qoder-qwen38-flash-free\make_cover.py     2960 bytes  09-18  ← 这次被复用的来源
```

去重闸门只在 `tools/` 那份里有，且它拦的是「整张 PNG 逐字节相同」。
**复用配色 ≠ 复用文件，闸门根本不触发。**

**3. `style.yaml` 的 `cover_style` 是失效字段**

现在写的是「简洁科技感，深青色调，扁平化设计」—— 正是用户想摆脱的那套。
`skills/wewrite-style/references/style-template.md:34` 说它是「封面风格描述」，
但**全项目没有任何代码读它**。

这就是「不是都改过吗」的由来：改过的是 artcraft 那篇的封面实现，
没改的是这个没人读的字段。

**4. 配色撞车没有机器可检**

现有闸门只比字节。配色重复、版式重复、同账号封面看起来一样 —— 全都检测不到。

### 建议改法

| 位置 | 改什么 |
|---|---|
| `skills/wewrite-visual/SKILL.md` | 补一条：**不要把上一篇文章目录里的 `make_cover.py` 当模板**；封面脚本只有 `.wewrite/tools/make_cover.py` 一份是权威的 |
| `skills/wewrite-visual/references/visual-guide.md` | 补一条「**看历史封面再定配色**」：写 `cover-design.json` 前先扫项目内近 5 篇封面的主色，选一个没撞的 |
| `.wewrite/tools/make_cover.py` | 去重闸门增加**配色维度**：成品主色与项目内已有封面主色相同（且非同一文章）时报警；可选 `--palette` 强制指定 |
| `.wewrite/style.yaml` | `cover_style` 改成实际生效的规范，或删掉换成 `cover_palette` 字段。**一个没人读的字段比没有字段更危险** —— 它会让 Agent 以为已经设过 |
| 文档层 | 把「artcraft 那篇刻意不用深青」的教训从文章目录提到 skill 顶层，别再只存在某一篇里 |

---

## 三、仓库同步状态（切工作区时先看这里）

### 仓库落后于工作区

`D:\sudy\myproject\wechat-writing-skills` 只有 3 个提交，最后一个是 9-05
左右的初始版本。**9 月之后工作区的全部演化都没回灌仓库。**

逐文件比对（`skills/` 下，排除 `__pycache__`），5 个文件内容不一致，
**全部是工作区比仓库新**：

| 文件 | 仓库 | 工作区 | 差异要点 |
|---|---|---|---|
| `wewrite-visual/SKILL.md` | 09-05 | 10-12 | 工作区新增「封面必须走 make_cover.py」整段 + 「不要默认套深青」+ 去重闸门说明 |
| `wewrite-visual/references/visual-guide.md` | 09-05 | 10-12 | 工作区新增「封面必须走生成器」整节 + 分类配色建议 |
| `wewrite-publish/SKILL.md` | 09-05 | 09-09 | 模板层从「2 个注册」更新为「8 个注册」，新增 tutorial-dashboard 说明 |
| `wewrite-publish/references/theme-selection.md` | 09-05 | 09-16 | 新增 promo 类型映射、muppet-editorial、tutorial-dashboard 段落 |
| `wewrite-publish/scripts/apply_template.py` | 09-05 | 09-16 | 新增 muppet-editorial、tutorial-dashboard 两个模板实现 |

### 仓库完全缺失的东西

**模板层（`apply_template.py` 的 TEMPLATES 注册表）**

```
仓库：  kazk-editorial, bold-contrast, qa-bubble, timeline-log, knowledge-card, press        （6 个）
工作区：kazk-editorial, muppet-editorial, bold-contrast, qa-bubble, timeline-log,
        knowledge-card, press, tutorial-dashboard                                            （8 个）
```

缺 `muppet-editorial`（福利/活动首选）和 `tutorial-dashboard`（教程首选）两个模板。
**这两个是 9-16 之后加的，仓库里根本没有** —— 也就是说仓库当前状态连
「福利文该用什么版式」都无法回答。

**主题层（`themes/`）**

```
仓库缺：emerald-tutorial.yaml, muppet-editorial.yaml
```

`emerald-tutorial` 是 tutorial-dashboard 的默认配色，两者配套，缺一不可。

**测试**

`skills/wewrite-publish/tests/test_tutorial_dashboard.py` 只在工作区有，仓库没有。
tutorial-dashboard 模板带插槽校验（缺配置/漏放/重复都会报错），这块有测试保护，
仓库里没有测试 = 没有保护。

**工作区独有（不属于本仓库，不要往仓库塞）**

```
skills/aihot/            AI 资讯查询，独立 skill，与 wewrite 流水线无关
.wewrite/tools/          项目级工具（make_cover.py 等），属于工作区而非 skill 仓库
.wewrite/config.yaml     微信凭证，只存本地
```

**注意**：`make_cover.py` 现在住在 `.wewrite/tools/`（工作区），
但 skill 文档让 Agent 去用它。这是个**跨仓库的依赖**：skill 仓库里没有这个脚本，
别人 clone 下来按 skill 文档操作会直接失败。要么把脚本挪进 `skills/wewrite-visual/scripts/`，
要么在 skill 文档里说明它从哪来。

### 建议的同步顺序

1. 先把工作区 5 个更新的文件回灌到仓库（内容已经验证过能用）
2. 补 `emerald-tutorial.yaml` + `muppet-editorial.yaml` 两个主题
3. 补 `tests/test_tutorial_dashboard.py`
4. 再做上面第一节、第二节的规则修订
5. 决定 `make_cover.py` 的归属：进 skill 仓库，还是留在工作区

---

## 四、本次改动清单（供 review）

在 `D:\sudy\myproject\wechat-writing-skills` 下实施：

**写作端**
- [ ] `article-brief.md` 增加 `content_type` 字段与 announcement 类的长度区间
- [ ] `frameworks-quick.md` 增加「发布声明」框架
- [ ] `wewrite-review/SKILL.md` 增加第六项判断「守界」
- [ ] `editorial-quality.md` 把「无关段落」改成可判定表述
- [ ] `wewrite-write/SKILL.md:106` 长度按体裁取值

**封面端**
- [ ] `wewrite-visual/SKILL.md` 补「不要拿上一篇的脚本当模板」
- [ ] `visual-guide.md` 补「先看历史封面再定配色」
- [ ] `make_cover.py` 闸门加配色维度检测
- [ ] `style.yaml` 的 `cover_style` 修正或删除

**仓库同步**
- [ ] 回灌 5 个工作区更新的文件
- [ ] 补 2 个主题 yaml
- [ ] 补 tutorial-dashboard 测试
- [ ] 决定 `make_cover.py` 归属
