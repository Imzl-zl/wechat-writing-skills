# 文章任务书与主张清单

正文动笔前必须先保存 `brief.yaml` 和 `claims.yaml`。它们让“写得像一篇文章”变成
“解决一个明确的读者问题”。字段可补充，但不能省略核心项。

## brief.yaml

```yaml
version: 1
content_type: "analysis"       # announcement | tutorial | analysis | story | listicle
audience:
  who: "具体读者"
  context: "读者在什么情境下阅读"
  question: "读者真正要解决的问题"
goal:
  takeaway: "读完能复述的一个结论"
  action: "读完可以采取的行动；纯观点文可写判断方法"
thesis:
  statement: "全文核心判断"
  novelty: "相较常见说法新增了什么"
  boundary: "结论在什么条件下成立"
  counterpoint: "最强反方或替代解释"
personal_materials:
  available: false
  items: []                 # 只记录用户在本次任务明确提供的经历、观察或原话
framework: "观点"
sections:
  - purpose: "本节推进什么"
    claim_ids: [C1]
constraints:
  desired_length: "1200-2500 字"
  must_include: []
  must_avoid: []
```

`novelty` 不是强行唱反调。找不到可靠的新角度时，缩小问题、补充适用条件或提供更好用的
判断框架。`action` 必须与题目相称，不为凑“干货”制造步骤。

## content_type：体裁决定长度与推进方式

不同体裁的“完整”长度差一个量级。写任务书时先定体裁，它决定 `desired_length`，
也决定每一节允许写什么。

| content_type | 适用 | 建议长度 | 推进方式 |
|---|---|---|---|
| `announcement` | 福利播报、活动公告、发布声明、限免盘点 | 600-900 字 | 事实清单 → 边界与例外 → 截止时间。**不设“再深一层”的推进逻辑** |
| `tutorial` | 教程、工具实操 | 1200-2500 字 | 场景 → 步骤 → 验证 → 常见问题 |
| `analysis` | 深度分析、行业解读 | 1800-2500 字 | 结论 → 证据 → 反方 → 边界 |
| `story` | 体验记、踩坑记录 | 1500-2500 字 | 冲突 → 选择 → 结果 → 含义 |
| `listicle` | 清单、资源汇总 | 1000-1800 字 | 目标 → 条目 → 用法 → 避坑 |

### announcement 类写作纪律

福利公告只回答三件事：**哪里免费 / 怎么免费 / 有啥免费**。以下内容属于自行扩展，
`must_avoid` 里应逐条写明：

- 自部署、算力、框架适配、开源权重下载等“用不上的技术细节”
- 选型建议（“A 类用户该选 X，Y 类用户该选 Z”）
- 模型能力评测、基准跑分对比
- 任何“顺便提一句”的补充

**体裁不匹配时长时，先削议题，再削字数。** 不因为 `desired_length` 到了下限就给
一个公告类文章硬塞内容——读者要的是把免费信息说清楚，多写的部分只会让人划走。

## must_avoid 会被逐条核对

`must_avoid` 不是装饰。审稿阶段（`wewrite-review`）会把它当成硬约束逐条检查，
命中即改稿，不因“其他维度分数高”而放过。写任务书时把用户明确说过不要的东西逐条列进去，
包括用户在本轮对话里点过名的（“不要加自部署”“不要写选型建议”）。

## claims.yaml

```yaml
version: 1
claims:
  - id: C1
    text: "正文准备表达的主张"
    type: fact              # fact / inference / opinion / user_experience
    source_ids: []          # 对应 sources.yaml 的 id；意见可为空
    status: supported       # supported / bounded / unsupported
    boundary: "适用范围或不确定性"
```

- `fact` 必须有能直接支持它的来源；否则删除或标为 `unsupported`，不得进入正文。
- `inference` 要列出依据并明确这是推断；`opinion` 不伪装成共识。
- `user_experience` 只能来自本次任务里用户明确提供的材料，并在来源账本标为
  `user_provided`。范文、模型记忆和人格示例都不是用户经历。
- 每一节至少服务一个主张；无法对应主张的段落默认删除。

## 个人材料边界

`personal_materials.available=false` 时，可以写“我认为”“我的判断是”这类作者判断，不能写
作者经历过的事件、朋友或同事、现场对话、动作、时间地点和感官细节。人格要求私人开场或
故事开场时，自动改为观察、问题或核心判断开场，不得补造材料。
