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

## 安装：把这一节整段发给你的 AI

人类不用逐条执行。把本节从「你的任务」到「交付清单」整段复制给 Agent，它会自己装完，
中途只问你两三个必须由人决定的问题。

---

**你的任务**：在这台机器上把本仓库装成一个能写公众号文章的工作区。逐条执行，每条都带验收
命令；验收不通过就停下报错，不要跳过，也不要先写文章回头再补装。

**执行约束**

- 只有三件事需要用户决定：写作项目目录、你的 skills 目录约定（`.claude/skills` /
  `.agents/skills` / `.pi/skills`）、现在要不要配微信凭证。其余自己判断，不要反复确认。
- 命令按当前系统改写。Windows 上 `cp -r` → `Copy-Item -Recurse`，`mkdir -p` →
  `New-Item -ItemType Directory -Force`，`export X=Y` → `$env:X='Y'`。
- Windows 上所有 `wewrite` 命令都加前缀 `PYTHONIOENCODING=utf-8`，否则中文输出会因 GBK 编码报错。
- 每步把验收输出贴给用户，不要只说"装好了"。

### 1. 环境盘点

打印：操作系统、shell、写作项目目录、`uv --version`、`python --version`。

验收：五项都有值。`uv` 缺失就让用户装（<https://docs.astral.sh/uv/> 或
`winget install astral-sh.uv`），**不要**用 pip 装 wewrite。

### 2. 装 CLI（唯一不在仓库里的依赖）

```bash
uv tool install wewrite      # 本仓库在 4.2.1 上验证
```

版本低于 4.2.1 就升级；装到的版本更高、但命令参数对不上（报 `unrecognized arguments` 之类），
用 `uv tool install wewrite==4.2.1` 回到验证过的版本，别改 skill 去迁就 CLI。

验收：`wewrite --version` 打印出版本号。失败按顺序处理：

1. 提示命令不存在 → `uv tool dir --bin` 返回的目录必须在 PATH 里，不在就告诉用户加。
2. 目录在 PATH 里但仍找不到 → `uv tool install --force wewrite` 重建启动器（shim）。
3. 还不行 → 用 `uv tool dir --bin` 拼出 `wewrite.exe` 全路径，后续命令都用全路径。
4. **这台机器此前给 wewrite 打过补丁时**（`uv tool dir` 下的
   `wewrite/Lib/site-packages/wewrite/` 里存在 `*.orig`）优先别用 `--force`——它会重建 venv、
   抹掉补丁。改成把 `wewrite/Scripts/wewrite.exe` 复制进 `uv tool dir --bin` 指的目录，
   入口就回来了，包不动。真要重装，装完必须重跑 `tools/patches/` 里的三个脚本（见第 9 步）。

### 3. 拷 skills

```bash
git clone https://github.com/Imzl-zl/wechat-writing-skills.git   # 本机还没有仓库时才需要
mkdir -p <项目>/<skills目录>
cp -r wechat-writing-skills/skills/* <项目>/<skills目录>/
```

验收：目标目录下 **12 个子目录**，且 `<项目>/<skills目录>/wewrite/SKILL.md` 存在。

### 4. 写项目 AGENTS.md

把仓库里的 `templates/AGENTS.md` 拷成 `<项目>/AGENTS.md`，替换两个占位符：
`<SKILLS_DIR>`（第 3 步用的 skills 目录）、`<HOME>`（`.wewrite`）。这份文件装了目录约定、
Windows 编码前缀、模板≠主题、写≠发布这些规则——**没有它，后面每一步都得靠你临时解释**。

验收：`<项目>/AGENTS.md` 存在，且里面不再出现 `<SKILLS_DIR>` / `<HOME>` 字样。
用户项目已有 AGENTS.md 时不要覆盖，只合并缺少的条目，冲突处以用户现有内容为准。

### 5. 建状态目录 + 主题

```bash
mkdir -p <项目>/.wewrite/themes
cp wechat-writing-skills/themes/*.yaml <项目>/.wewrite/themes/
```

再把 `WEWRITE_HOME` 持久化指向 `<项目>/.wewrite`（Windows：
`[Environment]::SetEnvironmentVariable('WEWRITE_HOME','<项目>/.wewrite','User')`；
macOS/Linux 写进 shell rc 文件）。

验收：**新开一个 shell** 跑 `wewrite home`，输出必须等于 `<项目>/.wewrite`。
style / config / history / runs / 主题全在这个目录里，仓库里没有也不该有。

### 6. 自检

```bash
wewrite diagnose
```

验收：`Python Packages` 不报 FAIL，退出码 0。全新机器上会看到这些 **WARN，全部正常**，
不要停下来"修"：
`Config File`（还没 config.yaml）、`Wechat Credentials`、`Image Api Key`、`Style File`
（第 8 步才生成）、`Playbook`、`History Articles`。**只有 FAIL 才需要处理**。
Windows 上 `Config Permissions` 的 `chmod 600` 警告同样可忽略。

### 7. 跑通排版（模板层是否真生效的判据）

```bash
python <项目>/<skills目录>/wewrite-publish/scripts/apply_template.py <临时>.md --template kazk-editorial -o <临时>-deco.md
wewrite preview <临时>-deco.md --theme kazk-editorial --no-open -o <项目>/_setup-check.html
```

验收：`_setup-check.html` 存在、大于 2KB、内容里搜得到 `style="` 内联样式。
**只跑 `preview` 不跑 `apply_template.py` 不算通过**——那样出来的是纯换色主题，结构没生效。
验收后删掉临时文件和 `_setup-check.html`。

### 8. 首次风格设置（必须和用户对话）

读 `<项目>/<skills目录>/wewrite-style/SKILL.md` 与 `references/onboard.md`，按 Phase 1–4
问用户，写入 `<项目>/.wewrite/style.yaml`。

验收：`style.yaml` 存在，`wewrite diagnose` 不再报 style 缺失。

### 9. 可选：打补丁（用户要那两个免费图源，或机器以前打过补丁时才做）

`tools/patches/` 里三个脚本改的是 CLI 的 site-packages：新增 sensenova / modelscope 两个免费
图源、修 `run finish` 的来源计数、修 `publish` 的摘要日志。不打也能正常写和排版。

```bash
python tools/patches/patch_image_providers.py --check
python tools/patches/patch_run_finish.py --check
python tools/patches/patch_publish_digest_log.py --check
```

验收：三条都打印「补丁状态: 已应用」。报「未应用」就去掉 `--check` 重跑（幂等）。
报「找不到锚点」说明 CLI 改了函数结构，停下来人工核对，**不要**硬改或绕过。
用户不需要那两个免费图源时跳过本步，并在交付清单里写明"未打补丁"。

### 10. 可选：发布与配图

- 发布：微信公众号 appid/secret 写进 `<项目>/.wewrite/config.yaml` 的 `wechat` 段。
- 配图：图片 provider 的 key 写进 `image.providers`；没配就降级成只给提示词。
- 两项都不配也能用：写稿、审稿、模板排版、本地预览、`copy_page.py` 生成一键复制页手动粘贴进公众号编辑器。

### 禁止事项

- 不把 appid / secret / api key 写进仓库文件或任何提交（`.gitignore` 已排除 `config.yaml`）。
- 用户没明确说"推到草稿箱"就不执行 `wewrite publish`。
- 不跑 `tools/sync_skills.py --to project`：它会用仓库覆盖项目里更新的 skill 和主题。
- 不擅自 `uv tool upgrade wewrite`：升级会覆盖 site-packages 里的本地补丁。升完必须跑
  `tools/patches/*.py --check`，报未应用就重跑，别假装补丁还在。

### 交付清单

装完把这些结果一次性给用户：

| 项 | 怎么取证 |
|---|---|
| CLI 版本 | `wewrite --version` 的输出 |
| 状态目录 | `wewrite home` 的输出 |
| skills / 主题数量 | 12 个 skill 目录、12 个主题 yaml |
| 项目约定 | `<项目>/AGENTS.md` 已生成，占位符已替换 |
| 排版链路 | `_setup-check.html` 生成过且含内联样式 |
| 风格配置 | `style.yaml` 已生成 |
| 补丁状态 | 三个 `--check` 都是"已应用"，或明确写"未打补丁" |
| 能不能发布 | 凭证配了 / 没配（没配就走手动粘贴） |

---

## 仓库里还有什么

| 路径 | 是什么 | 要不要装 |
|---|---|---|
| `skills/` | 12 个 skill | 要，第 3 步 |
| `themes/` | 12 套配色 yaml | 要，第 5 步 |
| `templates/AGENTS.md` | 内容项目的规则模板（目录约定、编码、模板≠主题、写≠发布） | 要，第 4 步 |
| `tools/patches/` | 给 CLI 打的三处补丁（两个免费图源、`run finish` 计数、`publish` 摘要日志） | 可选，第 9 步 |
| `tools/sync_skills.py` | 仓库 ↔ 内容项目的双向同步 | 只在维护本仓库时要 |
| `themes/showcase.html` | 11 模板 × 18 配色的可视化矩阵 | 只看效果时打开 |
| `docs/known-issues-*.md` | 已修与未修问题的实测记录 | 遇到怪现象先翻这个 |

---

## 模板体系：模板（结构）× 主题（配色）

排版的核心设计是**两个正交维度**，先定模板、再配主题：

- **模板 = 版式结构**：9 个带确定性结构变换的模板（由 `skills/wewrite-publish/scripts/apply_template.py`
  在渲染前把 markdown 重写成版式）+ 2 个纯 CSS 骨架：
  | 模板 | 结构特征 | 适合 |
  |---|---|---|
  | 编辑部杂志风 `kazk-editorial` | 幽灵数字小节号、荧光笔强调、宋体引言、图片裁切框、圆点分隔线 | 体验记/观点文 |
  | 简报风 `muppet-editorial` | 刊头细线、炭黑信息条、PART 编号、胶囊小标题、虚线图框 | 福利/活动/清单 |
  | 演讲金句风 `bold-contrast` | 编号标题、黑底金句卡 | 观点密集 |
  | 问答气泡 `qa-bubble` | 「问」徽章 + 聊天气泡 | FAQ/测评 |
  | 时间线日志 `timeline-log` | 时间轴节点 | 踩坑记录/连载 |
  | 知识点卡 `knowledge-card` | 编号知识卡 | 干货科普/教程 |
  | 报刊墨渍 `press` | 衬线居中标题、双细线、一二三编号 | 深度分析 |
  | 教程面板 `tutorial-dashboard` | Hero 信息卡、路线图、问题卡、流程条、行动区 | 教程/工具实操 |
  | 学长橙蓝风 `chengzi-benefit` | 渐变标题条（天蓝→珊瑚橙）+ 圆点编号小节头 | 福利/安利向 |
- **主题 = 配色**：`themes/` 内置 12 套专属配色（含各模板原生配色），`--theme` 一键换色，
  结构不变；微信兼容（全内联样式，粘贴不乱）。
- **自动判型**：AI 读成稿识别 8 种内容类型（教程/体验记/分析/清单/福利/问答/日志/科普），
  按决策表自动选模板和配色，只出一张最终预览。
- **可视化矩阵**：`themes/showcase.html`——11 模板 × 18 配色，点色卡即换，直接在浏览器打开。

想从别人的公众号文章偷样式：`wewrite learn-theme --name <名字> <URL>`（自动学配色骨架，
装饰性排版需人工修 yaml + 补结构变换）。

## 已知问题

见 [`docs/known-issues-2026-10-20.md`](docs/known-issues-2026-10-20.md)——记录了写作端
「内容扩展 / 掰开揉碎」与封面端「配色重复」两类问题的实测根因、修复情况，以及仍待处理的
三项（`cover_style` 是没人读的失效字段、`playbook.md` 缺失导致口头纠正学不到、`content_eval`
字数口径与闸门不一致）。

## 维护这个仓库

这是源码仓，内容项目里的改动要回灌才有意义：

```bash
python tools/sync_skills.py --check       # 只查差异，不写文件
python tools/sync_skills.py --to repo     # 项目 → 仓库（回灌）
python tools/sync_skills.py --to project  # 仓库 → 项目（覆盖项目里的新版，确认仓库更新再用）
```

`themes/showcase.html`、`templates/`、`tools/` 只存在于仓库侧，不参与同步——项目里的
`AGENTS.md` 是从模板派生出去的，`.wewrite/tools/` 那份补丁脚本和 `tools/patches/` 保持同一份内容。

## 致谢

- [imraywang/wewrite](https://github.com/imraywang/wewrite)（MIT）—— 上游全流程框架与 CLI
- [数字生命卡兹克 KKKKhazix/khazix-skills](https://github.com/KKKKhazix/khazix-skills)（MIT）—— 活人感写作方法论（living-voice 人格与审稿分层）

## License

MIT（见 LICENSE；包含上游 wewrite 的原始 MIT 版权声明）
