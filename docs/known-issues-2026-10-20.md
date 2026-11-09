# 已知问题清单（2026-10-20 实测记录）

来源：写一篇「Qoder + WorkBuddy 免费模型盘点」福利文时的实际返工。这不是设想，
是同一篇稿子被用户打回两次的真实过程。

**状态（2026-10-20 晚更新）**：

- 一、写作端 —— 已修（长度语义已改为上限，见第五节）
- 二、封面端 —— 部分修复：配色闸门与「别复用上一篇脚本」已落地，`cover_style`
  失效字段仍未修，见 3.1
- 三、仍待处理 —— 三条未修，见第三节
- 四、已完成 —— 存档
- 五、二次复盘：长度闸门失真 —— 已修

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

> 以下描述的是**问题发生当时**的状态（2026-10-20 之前），不是现状。
> 哪些已修、哪些没修，见第四节清单。

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

### 改法

实施状态见第四节清单。

| 位置 | 改什么 |
|---|---|
| `skills/wewrite-write/references/article-brief.md` | 增加体裁字段（如 `content_type: announcement \| tutorial \| analysis \| story`）。`announcement` 类允许 `desired_length: "600-900 字"`，且明确「不因字数不足而扩展议题」 |
| `skills/wewrite-write/references/frameworks-quick.md` | 增加「发布声明」框架：目标 → 事实清单 → 边界与例外 → 截止时间。不设「再深一层」的推进逻辑 |
| `skills/wewrite-review/SKILL.md` | 五项判断增加第六项「**守界**」：逐条核对 `brief.constraints.must_avoid`，命中即改稿，不给分 |
| `skills/wewrite-write/references/editorial-quality.md` | 「无关段落删除」改成可判定的表述：读者读完这一段，是否知道了新的、原本不知道的**且他本来想知道的事**？否则删 |
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

**3. `style.yaml` 的 `cover_style` 是失效字段（未修，见 3.1）**

现在写的是「简洁科技感，深青色调，扁平化设计」—— 正是用户想摆脱的那套。
`skills/wewrite-style/references/style-template.md:34` 说它是「封面风格描述」，
但**全项目没有任何代码读它**。

这就是「不是都改过吗」的由来：改过的是 artcraft 那篇的封面实现，
没改的是这个没人读的字段。

**4. 配色撞车没有机器可检**

现有闸门只比字节。配色重复、版式重复、同账号封面看起来一样 —— 全都检测不到。

### 改法

实施状态见第四节清单。

| 位置 | 改什么 |
|---|---|
| `skills/wewrite-visual/SKILL.md` | 补一条：**不要把上一篇文章目录里的 `make_cover.py` 当模板**；封面脚本只有 `skills/wewrite-visual/scripts/make_cover.py` 一份是权威的 |
| `skills/wewrite-visual/references/visual-guide.md` | 补一条「**看历史封面再定配色**」：写 `cover-design.json` 前先扫项目内近 5 篇封面的主色，选一个没撞的 |
| `skills/wewrite-visual/scripts/make_cover.py` | 去重闸门增加**配色维度**：成品主色与项目内已有封面主色相同（且非同一文章）时报警（`--check-palette`） |
| `.wewrite/style.yaml` | `cover_style` 改成实际生效的规范，或删掉换成 `cover_palette` 字段。**一个没人读的字段比没有字段更危险** —— 它会让 Agent 以为已经设过 |
| 文档层 | 把「artcraft 那篇刻意不用深青」的教训从文章目录提到 skill 顶层，别再只存在某一篇里 |

---

## 三、仍待处理的问题

这一节列的是**还没解决的问题**，格式与前两节一致。修完一条就划掉。

### 3.1 `style.yaml` 的 `cover_style` 是失效字段

**现象**

`style.yaml` 里写着 `cover_style: "简洁科技感，深青色调，扁平化设计"`——正是用户
想摆脱的那套。但换封面配色时改这个字段没有任何效果。

**根因**

`skills/wewrite-style/references/style-template.md:34` 说它是「封面风格描述」，
但**全项目没有任何代码读它**。它是文档里存在、实现里不存在的一个字段。

这正是「不是都改过吗」的由来：改过的是 artcraft 那篇的封面实现（10-12），
没改的是这个没人读的字段（还是 8-20 的老值）。

**改法**

二选一：

- 改成实际生效的规范（现在用的是暖米底 + 墨黑 + 朱橙，数值条版式）
- 或删掉，换成 `cover_palette` 字段，让它有明确的消费方

**一个没人读的字段比没有字段更危险**——它会让 Agent 以为已经设过。

**位置**：内容项目 `.wewrite/style.yaml`，属工作区状态，不进仓库。

---

### 3.2 `playbook.md` 缺失，个人修改没被沉淀

**现象**

`wewrite diagnose` 长期报 `playbook: not found → no learned style`，
`wewrite learn-edits --summarize --json` 返回 `total_lessons: 0`。

用户在 2026-10-20 同一场会话里纠正了三次（掰开揉碎 / 太玄幻 / 别加私活），
全部只存在于对话上下文。换个会话，同样的错会再犯一遍。

**根因**

`wewrite learn-edits` 需要 `--draft` / `--final` 两个文件做 diff。而用户的纠正
是**口头给的**（"太玄幻了"「一句话能说清的别拆开揉碎」），没落成文件改动，
所以学习机制没东西可学。

**改法**

需要用户手动改一次稿子，再跑「学习我的修改」，规则才能落盘。
这一条不能靠改 skill 解决。

**边界**：`article-brief.md` 新增的「must_avoid 会被逐条核对」只能保证**单篇**不越界
（`brief.constraints.must_avoid` 写什么就禁什么）。跨会话的偏好要靠 playbook 沉淀。

**位置**：内容项目 `.wewrite/playbook.md`，属工作区状态，不进仓库。

---

### 3.3 `content_eval.py` 的字符数口径与闸门不一致

**现象**

`review-report.json` 里的 `draft_chars` / `final_chars` 是 `len(text)`
（`content_eval.py:71`），把 markdown 表格、图片说明和标点都算成字。同一篇稿子，
闸门报 1297 正文汉字，报告写 2859。

**根因**

`content_eval.py` 属于已安装的 wewrite 包，不在本仓库，直接改会在升级时丢失。

**改法**

以 `check_prose.py` 的口径为准：审稿结论引用闸门的正文汉字数，不引用 `content_eval`
的 `draft_chars`。要修根就得给 wewrite 包打补丁，并按 `tools/patch_*.py` 的惯例在
升级后重跑。

**位置**：`wewrite/commands/content_eval.py:71`，属外部包。

---

## 四、已完成（存档）

### 仓库回灌

仓库此前停在 9-05 的初始版本，9 月之后工作区的演化全部没回灌。
2026-10-20 一次性同步完毕（commit `d89f3d2`）：

| 项 | 内容 |
|---|---|
| skill 文件 | 回灌 5 个：`wewrite-visual/SKILL.md`、`visual-guide.md`、`wewrite-publish/SKILL.md`、`theme-selection.md`、`apply_template.py` |
| 模板层 | 补 `muppet-editorial`、`tutorial-dashboard` 两个模板实现（`apply_template.py` +1800 行） |
| 主题 | 补 `emerald-tutorial.yaml`、`muppet-editorial.yaml` |
| 测试 | 补 `skills/wewrite-publish/tests/test_tutorial_dashboard.py`（20 passed） |
| 封面脚本 | `make_cover.py` 从工作区 `.wewrite/tools/` 收进 `skills/wewrite-visual/scripts/`，不再依赖工作区路径 |
| aihot | 纳入仓库同步范围（原为工作区独有） |

同步后仓库与工作区 0 处不一致，模板 8 个、主题 11 套。
回灌脚本在 `tools/sync_skills.py`（`--to repo` / `--to project` / `--check`）。

### 改动清单

**写作端**
- [x] `article-brief.md` 增加 `content_type` 字段与 announcement 类的长度区间
- [x] `frameworks-quick.md` 增加「发布声明」框架
- [x] `wewrite-review/SKILL.md` 增加第六项判断「守界」
- [x] `editorial-quality.md` 把「无关段落」改成可判定表述
- [x] `wewrite-write/SKILL.md:106` 长度按体裁取值

**封面端**
- [x] `wewrite-visual/SKILL.md` 补「不要拿上一篇的脚本当模板」
- [x] `visual-guide.md` 补「先看历史封面再定配色」
- [x] `make_cover.py` 闸门加配色维度检测

**仓库同步**
- [x] 回灌 5 个工作区更新的文件
- [x] 补 2 个主题 yaml
- [x] 补 tutorial-dashboard 测试
- [x] 决定 `make_cover.py` 归属

---

## 五、二次复盘：长度闸门失真（2026-10-20 晚）

### 现象

`opencsg-99-credit-burned` 这篇稿子被用户判为「一句话能说明白的事掰开揉碎，像在凑字数」。
核对后发现不是文风问题，是长度从来没被正确度量：

| 口径 | 数值 |
|---|---|
| `brief.yaml` 要求 | 1800–2200 字 |
| `review-report.json` 记录 | 2859 |
| 实际正文汉字（不含表格、图片、标题） | 1297 |

一篇 1297 汉字、比下限少 500 字的稿子，被记成 2859 字，审稿判 pass，`edit_ratio` 为 0。

### 根因

1. **`desired_length` 全代码零消费者。** 整个 wewrite 包里 grep 不到读取它的地方，
   只有 SKILL.md 的文字在要求。它和 `cover_style` 是同一类字段：文档里有、实现里没有。
2. **`content_eval.py:71` 用 `len(draft)` 数「字数」。** markdown 表格、图片说明、
   标点全算进去，1297 汉字记成 2859。
3. **`check_prose.py` 打印汉字数，但不和任何上限比较**，而且把表格、图片说明和标题
   也算进正文。
4. **复述没有任何检查。** 111.67 在正文出现 7 次，结论节整段复述正文数字；六项编辑
   判断里「好读」只写了「无重复」，靠人判断，这篇拿了 4.0。

结果：模型有一个必须自己数、却没有工具帮它数的目标，加一个会把 1297 报成 2859 的
计数器。拿不到可靠反馈时，「多写一点」是唯一保险的动作。凑字数是这个结构的产物，
不是文风问题。

### 改法（已落地）

| 位置 | 改什么 |
|---|---|
| `skills/wewrite-write/scripts/check_prose.py` | `--brief` 传入任务书后比对 `length_cap` 声明的上限（脚本不自带体裁数字）；新增精确数字复述检查（正文 ≤3 次）与结论节复述检查；表格、图片行、标题不计入正文汉字 |
| `skills/wewrite-write/references/article-brief.md` | `desired_length` 改为 `length_cap`；明确「不设下限，低于上限不补内容」 |
| `skills/wewrite-write/SKILL.md` | 长度规则改成上限语义；闸门命令加 `--brief` |
| `skills/wewrite-write/references/editorial-quality.md` | 好读加入「不复述」；超上限与结论复述列为阻断 |
| `skills/wewrite-review/SKILL.md` | 闸门报出的长度与复述问题按阻断处理，改完必须重跑 |
| `skills/wewrite-write/tests/` | 8 个回归测试，样例取自这篇稿子的真实句子 |

闸门对这篇稿子的实际输出：

```text
正文汉字 1297（不含表格、图片说明与标题）
- 精确数字 111.67 在正文出现 5 次（第 5、30、57、67、93 行）
- 结论复述：第 91 行又讲了一遍第 22、59 行已有的事实（2.16、5.49、1521、5.43、29.79）
- 结论复述：第 93 行又讲了一遍第 5、57 行已有的事实（111.67、4.5）
```

### 设计修正（同日）

第一版把体裁上限写死在脚本里（`announcement 900`、其余 `2500`）。这等于用一个新拍的数替换
旧的拍的数：材料足够的长文会被误杀，1200 字的凑字稿照样通过。改成上限只由任务书声明，
脚本只执行声明值；没声明就显式警告，不静默跳过。

**上限管的是失控，不管质量。** 质量由复述检查兜：同一个事实讲几遍，和文章长短无关。

### 边界

- 闸门能判「同一个数字讲了几遍」和「结论有没有复述」，判不了「一句话能说清却拆成三段」。
  后者靠「不设下限」和「结论只写新判断」两条约束压住，仍然要人读。
- `content_eval.py` 的字符数口径仍是 `len()`，与闸门不一致，见 3.3。
