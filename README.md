# WeChat Writing Skills — 公众号写作 Skills 合集

一套跑在 AI Agent（Claude Code / ZCode 等，兼容 SKILL.md 规范）里的公众号内容生产流水线：
**选题 → 写作 → 去 AI 味 → 审稿 → 模板库排版 → 草稿箱发布**，一句话跑通。

基于 [imraywang/wewrite](https://github.com/imraywang/wewrite)（MIT）深度定制：重写了排版模板体系（模板 × 主题两层架构 + 自动判型选模板），融合[数字生命卡兹克](https://github.com/KKKKhazix/khazix-skills)的「活人感写作」方法论（living-voice 写作人格），并补充了中文去 AI 味模块。

## Skills 总览

| Skill | 用途 | 触发语 |
|---|---|---|
| `wewrite` | 主入口：选题→写作→审稿→排版→草稿箱全流程 | "写一篇公众号文章" |
| `wewrite-write` | 写作（7 层去 AI 味 + 3 种写作人格） | "就这个选题写一篇" |
| `wewrite-topic` | 热点抓取 + 选题评分 | "今天写什么" |
| `wewrite-review` | 审稿 + 质量评分（11 项检测） | "检查一下这篇" |
| `wewrite-publish` | **模板库排版** → 微信兼容 HTML → 草稿箱 | "排版"、"推到草稿箱" |
| `wewrite-visual` | 封面 + 文内配图 | "给这篇配个封面" |
| `wewrite-learn` | 学习用户修改、范文风格库、偷师主题 | "学习我的修改" |
| `wewrite-style` | 公众号风格设置（首跑必做） | "设置公众号风格" |
| `wewrite-rewrite` | 一稿多发：小红书/抖音改写 | "改写成小红书版" |
| `wewrite-stats` | 阅读数据回填、选题建议 | "看看文章数据" |
| `humanizer-zh` | 纯去 AI 味（任何稿子过一遍） | "去一下 AI 味" |

## 模板体系：模板（结构）× 主题（配色）

排版的核心设计是**两个正交维度**，先定模板、再配主题：

- **模板 = 版式结构**：6 个带确定性结构变换的模板（由 `skills/wewrite-publish/scripts/apply_template.py`
  在渲染前把 markdown 重写成版式）+ 2 个纯 CSS 骨架：
  | 模板 | 结构特征 | 适合 |
  |---|---|---|
  | 编辑部杂志风 `kazk-editorial` | 幽灵数字小节号、荧光笔强调、宋体引言、图片裁切框、圆点分隔线 | 体验记/观点文 |
  | 演讲金句风 `bold-contrast` | 编号标题、黑底金句卡 | 观点密集 |
  | 问答气泡 `qa-bubble` | 「问」徽章 + 聊天气泡 | FAQ/测评 |
  | 时间线日志 `timeline-log` | 时间轴节点 | 踩坑记录/连载 |
  | 知识点卡 `knowledge-card` | 编号知识卡 | 干货科普/教程 |
  | 报刊墨渍 `press` | 衬线居中标题、双细线、一二三编号 | 深度分析 |
- **主题 = 配色**：`themes/` 内置 9 套专属配色（含各模板原生配色），`--theme` 一键换色，
  结构不变；微信兼容（全内联样式，粘贴不乱）。
- **自动判型**：AI 读成稿识别 8 种内容类型（教程/体验记/分析/清单/福利/问答/日志/科普），
  按决策表自动选模板和配色，只出一张最终预览。
- **可视化矩阵**：`themes/showcase.html`——8 模板 × 15 配色，点色卡即换，直接在浏览器打开。

想从别人的公众号文章偷样式：`wewrite learn-theme --name <名字> <URL>`（自动学配色骨架，
装饰性排版需人工修 yaml + 补结构变换）。

## 安装

```bash
# 1. 安装上游 CLI 运行时（skills 的确定性操作都走它）
uv tool install wewrite

# 2. 把 skills 拷进你的 Agent skills 目录（按你所用 Agent 的约定，如 .pi/skills/ 或 .claude/skills/）
git clone https://github.com/Imzl-zl/wechat-writing-skills.git
cp -r wechat-writing-skills/skills/* <你的项目>/.pi/skills/

# 3. 初始化状态目录（文章任务、主题、历史都在这里，项目自包含）
mkdir -p <你的项目>/.wewrite/themes && export WEWRITE_HOME=<你的项目>/.wewrite
cp wechat-writing-skills/themes/*.yaml <你的项目>/.wewrite/themes/

# 4. 首次使用：对 Agent 说"设置公众号风格"
```

草稿箱发布需要微信公众号 appid/secret（只存本地 `config.yaml`，不要提交到任何仓库）。
不配凭证也能用：本地预览 + 一键复制页面，手动粘贴到公众号编辑器。

## 致谢

- [imraywang/wewrite](https://github.com/imraywang/wewrite)（MIT）—— 上游全流程框架与 CLI
- [数字生命卡兹克 KKKKhazix/khazix-skills](https://github.com/KKKKhazix/khazix-skills)（MIT）—— 活人感写作方法论（living-voice 人格与审稿分层）

## License

MIT（见 LICENSE；包含上游 wewrite 的原始 MIT 版权声明）
