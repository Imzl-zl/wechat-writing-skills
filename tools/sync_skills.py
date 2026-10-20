#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""skills 仓库 ↔ 内容项目 同步脚本。

为什么要它
----------
2026-09 到 10-20，内容项目里的 skill 改了 5 个文件、加了 2 个模板、2 套主题、1 份测试，
全部没回灌仓库，仓库停在 9 月初的初始状态。漂移是默认结果，所以同步要做成显式动作。

目录映射
--------
    仓库 skills/*              <->  内容项目 .agents/skills/*
    仓库 themes/*.yaml         <->  内容项目 .wewrite/themes/*.yaml

用法
----
    python sync_skills.py --to project          # 仓库 → 内容项目
    python sync_skills.py --to repo             # 内容项目 → 仓库
    python sync_skills.py --check               # 只检查差异，不写文件
    python sync_skills.py --to repo --dry-run   # 预演，看会覆盖什么

依赖
----
不依赖第三方库，标准库即可运行。默认路径按本机实际布局写死，可用 --repo / --project 覆盖。
"""

from __future__ import annotations

import argparse
import filecmp
import shutil
import sys
from pathlib import Path

DEFAULT_REPO = Path(r"D:\sudy\myproject\wechat-writing-skills")
DEFAULT_PROJECT = Path(r"C:\Users\zhanglu\Desktop\公众号")

SKIP_DIRS = {".git", "__pycache__", "node_modules", ".pytest_cache"}
SKIP_SUFFIX = {".pyc", ".pyo", ".bak"}
# 运行时生成的本地状态文件（每个 skill 自己的 .gitignore 也排除了这些）
SKIP_NAMES = {".aihot-actor-id", ".aihot-actor-disabled"}

# 只在一侧存在、且本就该只在一侧的路径。同步时既不复制也不删除。
#   showcase.html   仓库独有的模板 × 配色展示页，不属于内容项目运行所需
ONLY_ON_PROJECT: set[str] = set()
ONLY_ON_REPO = {"showcase.html"}

# (源根, 目标根, 相对路径) —— 相对仓库或相对内容项目
PAIRS = [
    ("skills", ".agents/skills", "skills"),
    ("themes", ".wewrite/themes", "themes"),
]


def _iter_files(root: Path) -> list[Path]:
    """列出 root 下所有参与同步的文件（相对 root 的路径）。"""
    if not root.is_dir():
        return []
    out: list[Path] = []
    for p in sorted(root.rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(root)
        if any(part in SKIP_DIRS for part in rel.parts):
            continue
        if p.suffix.lower() in SKIP_SUFFIX:
            continue
        # 只在一侧该有的文件，两边都不参与同步
        if rel.parts and rel.parts[0] in ONLY_ON_PROJECT:
            continue
        if len(rel.parts) == 1 and rel.name in ONLY_ON_REPO:
            continue
        if rel.name in SKIP_NAMES:
            continue
        out.append(rel)
    return out


def _same(a: Path, b: Path) -> bool:
    try:
        return filecmp.cmp(a, b, shallow=False)
    except OSError:
        return False


def _plan(src_root: Path, dst_root: Path) -> tuple[list[Path], list[Path], list[Path]]:
    src_files = _iter_files(src_root)
    dst_files = _iter_files(dst_root)

    copy_list: list[Path] = []
    same_list: list[Path] = []
    for rel in src_files:
        s = src_root / rel
        d = dst_root / rel
        if d.exists() and _same(s, d):
            same_list.append(rel)
        else:
            copy_list.append(rel)

    src_set = set(src_files)
    delete_list = [rel for rel in dst_files if rel not in src_set]
    return copy_list, delete_list, same_list


def _apply_pair(label: str, src_root: Path, dst_root: Path, dry_run: bool) -> int:
    if not src_root.is_dir():
        print(f"[{label}] 源目录不存在，跳过：{src_root}")
        return 0
    if not dst_root.is_dir():
        print(f"[{label}] 目标目录不存在，跳过：{dst_root}")
        return 0

    copy_list, delete_list, same_list = _plan(src_root, dst_root)

    if not copy_list and not delete_list:
        print(f"[{label}] 无差异，{len(same_list)} 个文件已一致")
        return 0

    for rel in delete_list:
        target = dst_root / rel
        if dry_run:
            print(f"  将删除  {rel}")
        else:
            target.unlink(missing_ok=True)
            print(f"  已删除  {rel}")

    for rel in copy_list:
        s = src_root / rel
        d = dst_root / rel
        if dry_run:
            print(f"  将复制  {rel}")
        else:
            d.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(s, d)
            print(f"  已复制  {rel}")

    verb = "将" if dry_run else "已"
    print(f"[{label}] {verb}复制 {len(copy_list)} 个，{verb}删除 {len(delete_list)} 个，"
          f"{len(same_list)} 个一致")
    return 0


def _check(repo: Path, project: Path) -> int:
    """检查两侧差异。返回 0 表示一致。"""
    problems = 0
    for repo_rel, proj_rel, label in PAIRS:
        src_root = repo / repo_rel
        dst_root = project / proj_rel
        if not src_root.is_dir() or not dst_root.is_dir():
            print(f"[{label}] 目录缺失（源 {src_root.exists()} / 目标 {dst_root.exists()}）")
            problems += 1
            continue
        copy_list, delete_list, same_list = _plan(src_root, dst_root)
        if copy_list or delete_list:
            problems += 1
            print(f"[{label}] 有差异：")
            for rel in copy_list:
                print(f"  仅在源端    {rel}")
            for rel in delete_list:
                print(f"  仅在目标端  {rel}")
        else:
            print(f"[{label}] 一致（{len(same_list)} 个文件）")
    return 0 if problems == 0 else 1


def main() -> int:
    ap = argparse.ArgumentParser(description="同步 skills 仓库与内容项目")
    ap.add_argument("--repo", default=str(DEFAULT_REPO), help="skills 仓库路径")
    ap.add_argument("--project", default=str(DEFAULT_PROJECT), help="内容项目路径")
    ap.add_argument("--to", choices=["repo", "project"], help="同步方向")
    ap.add_argument("--check", action="store_true", help="只检查差异")
    ap.add_argument("--dry-run", action="store_true", help="预演，不写文件")
    args = ap.parse_args()

    repo = Path(args.repo).resolve()
    project = Path(args.project).resolve()

    if not repo.is_dir():
        print(f"仓库不存在：{repo}", file=sys.stderr)
        return 2
    if not project.is_dir():
        print(f"内容项目不存在：{project}", file=sys.stderr)
        return 2

    if args.check or not args.to:
        return _check(repo, project)

    if args.to == "project":
        for repo_rel, proj_rel, label in PAIRS:
            _apply_pair(label, repo / repo_rel, project / proj_rel, args.dry_run)
    else:
        for repo_rel, proj_rel, label in PAIRS:
            _apply_pair(label, project / proj_rel, repo / repo_rel, args.dry_run)

    return 0


if __name__ == "__main__":
    sys.exit(main())
