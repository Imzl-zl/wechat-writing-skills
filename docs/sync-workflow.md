# 双工作区同步流程

本仓库是 **skill 的唯一来源**。内容项目（写作工作区）里有一份副本供 Agent 直接读取。

```
D:\sudy\myproject\wechat-writing-skills     ← 源（git 管，改这里）
        │
        │  skills/*          →  内容项目/.agents/skills/*
        │  themes/*.yaml     →  内容项目/.wewrite/themes/
        │
        ▼
C:\Users\zhanglu\Desktop\公众号              ← 内容项目（写文章、配图、发草稿）
```

**写文章在内容项目，改 skill 在本仓库。** 两者都要动时，先改本仓库，再同步过去。

## 为什么需要这份流程

2026-09 到 10-20 期间，内容项目里的 skill 被改了 5 个文件、加了 2 个模板、2 套主题、
1 份测试，**全部没回灌仓库**。结果仓库停在 9 月初的初始状态，连「福利文该用什么版式」
都答不出来，别人 clone 下来用不了。

**漂移是默认结果，不是意外。** 没有同步步骤，就一定会漂。所以同步要成一个显式动作，
而不是靠记性。

## 同步方向一：仓库 → 内容项目（日常用）

改了本仓库的 skill 后，让内容项目用上新版：

```powershell
python tools\sync_skills.py --to project
```

## 同步方向二：内容项目 → 仓库（改完 skill 要回灌）

在内容项目里直接改了 skill 之后：

```powershell
python tools\sync_skills.py --to repo
cd D:\sudy\myproject\wechat-writing-skills; git status
```

**回灌后一定看 `git status`**，确认没有把工作区私有文件带进仓库。
脚本已经排除了 `__pycache__`、`*.pyc`、`*.bak` 和运行时状态文件
（如 `.aihot-actor-id`），但 `git status` 是最后一道确认。

## 一致性检查

两边不该有差异：

```powershell
python tools\sync_skills.py --check    # 退出码 0 = 一致
```

输出形如：

```
[skills] 一致（48 个文件）
[themes] 一致（11 个文件）
```

想先看会改动什么而不真的写文件，加 `--dry-run`。

## 什么时候必须回灌

| 触发条件 | 动作 |
|---|---|
| 改了 `skills/` 下任何文件 | 回灌 + 提交 |
| 改了 `themes/` 下任何 yaml | 回灌 + 提交 |
| 新增了模板（改 `apply_template.py` 的 TEMPLATES） | 回灌 + 提交 + 跑测试 |
| 在内容项目里临时改了 skill 试效果 | 试完回灌，别留在工作区 |
| 只是写文章、配图、发草稿 | **不用**回灌，内容项目不碰 skill 就不会漂 |

**提交前跑测试：**

```powershell
cd "D:\sudy\myproject\wechat-writing-skills"
$env:PYTHONIOENCODING="utf-8"
python -m pytest skills/wewrite-publish/tests/ -q
python tools\sync_skills.py --check      # 确认两侧一致
```

## 各自独有的东西，不要混

**只在内容项目（不要进仓库）**

```
.wewrite/            状态目录：config.yaml（凭证）、style.yaml、history.yaml、playbook.md
.wewrite/tools/      项目级工具
```

`aihot` 是同一套的一部分，已纳入仓库同步。

**只在仓库**

```
README.md            面向使用者
docs/                已知问题与流程文档
tools/sync_skills.py 同步脚本
themes/showcase.html 模板 × 配色可视化矩阵
```

## 凭证与隐私

`.wewrite/config.yaml` 里有微信 appid/secret，**任何时候都不要复制进仓库**。
仓库的 `.gitignore` 已经排除了 `config.yaml`，但 `git add -A` 之前仍要看一眼
`git status` 确认没有误加。

## 提 issue 时的信息格式

发现 skill 的问题时，文档写进 `docs/known-issues-YYYY-MM-DD.md`，包含：

1. **现象** —— 具体到能复现，最好带用户原话
2. **根因** —— 定位到具体文件和行号，说明为什么现有规则拦不住
3. **建议改法** —— 改哪个文件、改成什么
4. **改动清单** —— 可勾选的 checkbox

这样切到仓库工作区时可以直接照着改，不用重新查一遍。
