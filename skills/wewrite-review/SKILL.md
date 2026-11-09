---
name: wewrite-review
description: |
  WeWrite 编辑审稿模块：核对任务、事实来源、观点和实用性，必要时直接改稿，只有通过编辑门槛
  才生成公众号成稿。也响应“检查这篇文章”。通用代码 review 和网站 SEO 不触发。
allowed-tools:
  - Bash
  - Read
  - Write
  - Edit
---

# wewrite-review — 编辑、改稿与成稿

## 前置

用户指定文章时检查该文件；否则运行 `wewrite run show`，优先读取 `artifacts.draft`，并读取
`artifacts.brief`、`artifacts.claims` 和 `artifacts.sources`。旧任务没有初稿产物时才回退
`artifacts.article`。管道内先运行 `wewrite run step review in_progress`。

完整读取：

```text
读取: {skill_dir}/../wewrite-write/references/article-brief.md
读取: {skill_dir}/../wewrite-write/references/editorial-quality.md
读取: {skill_dir}/references/seo-rules.md
```

初稿人格为 `living-voice` 时，额外读取：

```text
读取: {skill_dir}/../wewrite-write/references/living-voice-guide.md
读取: {skill_dir}/../wewrite-write/references/living-voice-revision.md
```

用户只说“检查一下”且给了外部文件时，只给报告；主流程、任务内初稿或用户明确说“优化”时，
必须直接完成必要修改。

## 审稿与改稿

### 1. 对齐任务

检查文章是否真的回答 `audience.question`，核心判断是否与 `thesis` 一致，每节是否推动指定
claim，结尾是否交付 `goal.takeaway/action`。无关段落删除，不用漂亮结构掩盖答非所问。

**逐条核对 `constraints.must_avoid`。** 它是硬约束，不是参考：命中的内容直接删或改写，
不因“其他维度分数高”而放过。用户在本轮对话里点名不要过的东西（“不要加自部署”
“不要写选型建议”），要落到 `must_avoid` 里逐条检查。

**体裁守界。** `brief.content_type` 决定这篇东西该写到哪为止：

- `announcement`（福利播报、发布声明、限免盘点）只回答“哪里免费 / 怎么免费 / 有啥免费”。
  自部署、算力、框架适配、开源权重下载、选型建议、跑分对比都是自行扩展。
- 判断某段是否越界的标准：**读者读完这一段，是否知道了新的、原本不知道的、而且他本来
  就想知道的事？** 否则删。“相关”不等于“该写”——自部署跟 DeepSeek 有关，但没人在
  福利公告里想读这个。

**长度是上限，不是配额。** 没到上限不补内容，超了先删复述，再削议题。不要为了“看起来
完整”给公告类文章硬塞东西。字数不够说明该说的说完了，不说明该加。

### 2. 核对事实与个人材料

运行 `wewrite sources list --json`，把正文中的具体数字、日期、引述、研究结论和时效性事实
逐项对到 `claims.yaml` 与原始来源。来源不支持时优先补查；查不到就删除、缩小或改成明确的
推断。不能用模型记忆补洞。

检查所有第一人称事件、朋友同事、采访、对话、时间地点和感官细节。它们必须来自本次任务
明确记录的用户材料；否则属于阻断问题，直接删除或改成非亲历论述。

### 2.5 闸门与活人感终审

对正文运行闸门（硬禁令、长度上限、数字复述、结论复述）：

```bash
PYTHONIOENCODING=utf-8 python {skill_dir}/../wewrite-write/scripts/check_prose.py {draft_path} --brief {brief_path}
```

脚本标为“需要修改”的项直接修掉，包括禁用标点、黑话、模型路标、翻案句、超过长度上限、
同一数字反复出现、结论节复述正文数字。这些属于阻断问题，改完必须重跑，不能只降分或
写进建议。标为“需辨语境”的逐条判断，确实符合本义就保留并注明。

删复述时删的是重复的那句话，不是信息本身：数字留在它第一次出现的地方，结论只写新判断
和动作。

**核对详略。** 看 `brief.constraints.elaboration`：

- `minimal` 或没写：逐个动作和事实检查后面那句解释——读者不知道它就会做错或误解吗？
  不会就删。读者已经知道的机制（比如 agent 每轮重发上下文）整段删掉。
- `stepwise`：用户明确要求过“详细说明步骤”，这时才允许逐步骤展开，每步给操作和验证方法。

**逐段检查有没有新东西。** 每段必须带来新事实、新动作、新例子、新区别或新后果。同一
观点换说法的段落合并或删掉。这一条与人格无关，不是 `living-voice` 专属。

`living-voice` 人格额外做活人感终审：以读者视角通读全文，回答“这是一个有见识的普通人
在认真聊一件打动他的事，还是一个 AI 在输出信息？”——检查情绪是体感记忆还是知识性描述、
有没有导师姿态、哪段读起来注意力会断掉。

### 3. 六项编辑判断

按“准确、观点、有用、合声、好读、守界”各评 1-5 分，并列出阻断问题和最多 5 个主要问题：

**守界**这一项专门看有没有超出任务书范围：`must_avoid` 有没有命中、`content_type`
允许的内容有没有越界、结论有没有超出受众本来想知道的东西。这一项低于 3 分即为
`revise`，不论其他五项多高。

**好读包含不复述。** 同一精确数字在正文最多 3 次，结论节不复述正文数字。闸门报出的这两类
问题按阻断处理，不能靠调低“好读”分数放过。

- `pass`：平均分至少 4、单项不低于 3、没有阻断问题。
- `revise`：能在现有材料内修正。直接修改后重新执行 1-3，不得只写建议。
- `needs_input`：仅限用户明确要求个人故事而材料不足且无法安全换框架。

最多两轮。第二轮仍有问题时，删掉不可靠内容、缩小承诺，生成能通过的可靠版本；不得给未
通过的文章贴上“可交付”。通过后把最终正文写入 `artifacts.article`。

### 4. 标题、摘要与工具提示

生成一个主标题、两个准确的备选标题、40 字内摘要和 3-5 个标签。关键词自然出现，不按密度
硬塞，也不为打开率虚构数字或承诺。审稿不调用配图。

运行 `wewrite score {article_path} --json`。该分数只帮助定位套话、句式过齐和段落节奏风险，
不设机械及格线，也不为提分反复重写。

## 保存编辑报告

先把编辑判断写为任务目录内临时 `assessment.yaml`：

```yaml
decision: pass
pass_number: 1
dimensions:
  accuracy: 4
  viewpoint: 4
  usefulness: 4
  voice: 4
  readability: 4
  scope: 4              # 守界：must_avoid 与 content_type
blockers: []
major_issues: []
notes: ""
```

再生成 `artifacts.review_report`：

```bash
wewrite content-eval --draft {draft_path} --final {article_path} \
  --assessment {assessment_path} --output {review_report_path} --json
```

只有报告里的 `publishable=true` 才能完成审稿。更新任务并标记完成：

```bash
wewrite run update --patch '{"editorial":{"decision":"pass","pass_number":1,"publishable":true},"seo":{"title":"...","alt_titles":[],"digest":"...","tags":[],"quality_score":0},"provenance":{"verified_sources":0,"unverified_sources":0}}'
wewrite run step review completed
```

自检报告用自然语言，最多列 5 个按影响排序的问题，并说明已经怎样修正。没有硬伤就直说正文
可以交付；如有需要可再单独配图或排版，不输出大段分数表。
