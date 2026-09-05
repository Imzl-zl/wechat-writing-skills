# 学习人工修改

学习的目标是减少重复修改，不是把一次改稿变成所有文章的永久模板。

## 1. 获取原稿与终稿

原稿优先使用用户点名的文件；否则使用历史里该任务的 `draft_file`。终稿由用户提供。多个
候选时必须确认，不能按文件修改时间猜测。

```bash
wewrite learn-edits --draft {draft_path} --final {final_path}
```

## 2. 记录 pattern

每个有意义的修改写入生成的 lesson YAML：

```yaml
patterns:
  - type: expression        # word_sub / para_delete / para_add / structure / title / tone / expression
    key: shorter_paragraphs
    description: "这次把教程中的长段拆短"
    rule: "教程说明段每段只处理一个操作"
    scope: content_type     # global / content_type / framework / persona
    scope_value: tutorial   # global 时留空
    confirmed: false        # 只有用户明确说这是长期偏好时才设 true
```

优先选择最窄且真实的范围。文章结构、标题和语气的单次修改通常与题型有关，不应默认全局。
相同 `key + scope + scope_value` 才累计次数。

### 强调标记的识别

用户在改稿时对句子添加、删除或移动强调标记（`**` / `*` / `>`）属于可学习信号，但默认按
软参考处理，绝不因为一次改动就变成“全文都加粗”：

- 每次出现的规则写成 `key: emphasis_markers`，rule 记录具体行为，例如
  `key: emphasis_markers` / `rule: "只给核心收益句加粗，全文不超过 2-3 处"`。
- scope 默认 `content_type` 或 `framework`；只有当用户在多个不同类型文章里反复加删同类
  强调，或明确说“以后都这样”，才允许升级为 global 或 `confirmed=true`。
- 判断是否采纳时参考 wewrite-write 的金句与重要句强调规则（每篇 2-3 处、三类句子对应
  不同渲染），不要把用户单次调整直接固化成机械规则。

## 3. 生效规则

运行 `wewrite learn-edits --summarize --json` 获取按当前日期重新计算的结果：

- 一次出现始终是软参考，近期也不能自动成为硬约束。
- 同一范围重复至少两次且 `confidence >= 5`，或用户明确 `confirmed=true`，才有 `hard=true`。
- 旧规则按最后出现时间衰减；低于 2 时不再使用。
- 写作时只应用 global 或与当前 content_type/framework/persona 匹配的规则。

`playbook.md` 可以保存结果方便人查看，但写作前必须重新 summarize，不能沿用缓存分数。更新
时以 `key + scope + scope_value` 为唯一键；summarize 已衰减或消失的规则不能永久保留。

## 4. 范文安全

人工终稿自动进入范文库时标为 `ownership=user`、`authenticity=user_edited`。从 URL 或普通
文件导入默认视为第三方；只有用户明确说明是本人创作时才使用 `--user-authored`。

所有范文的 `allowed_uses` 仅为 style 和 structure，`personal_materials_reusable=false`。即使是
用户自己的旧文，也不能把其中的个人经历直接搬到新文章；需要用户在本次任务重新提供或确认。
缺少元数据的旧范文按第三方、未验证处理。
