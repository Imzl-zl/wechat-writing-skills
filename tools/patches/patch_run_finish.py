#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""修 wewrite 的 `run finish` 幂等短路：让来源计数在已封存后也能刷新。

为什么需要这个脚本
-----------------
wewrite 通过 `uv tool install` 安装，`finish_run` 写在
`site-packages/wewrite/runs.py` 里，没有插件入口。

原来的行为：`finish_run` 第一行就是

    if state.get("status") == "completed":
        return state

状态一旦封存，后面从 sources.yaml 重算 `verified_sources` /
`unverified_sources` 的逻辑就永远走不到。后果是：写完文章、补录
sources.yaml 的 `status` 字段之后再 `wewrite run finish`，计数仍是旧的
（本次实际遇到的是 12 条已核实来源被记成 0 verified / 13 unverified）。

`uv tool upgrade wewrite` 会覆盖 site-packages，所以这里把补丁做成可重复
执行的脚本：升级后重跑一次即可。

改动要点
-------
1. 抽出 `_refresh_provenance(state)`，把重复的计数逻辑收敛成一处
   （原来 finish 路径和本次新增路径各有一份相同实现）。
2. 已封存时不再直接返回，而是刷新派生计数后落盘。正文、编辑结论、
   步骤状态一律不动——来源计数是派生值，不属于封存内容。

用法
----
    python patch_run_finish.py           # 应用（幂等）
    python patch_run_finish.py --check    # 只检查状态
    python patch_run_finish.py --restore  # 还原备份

（在本补丁目录下运行；文件定位见同目录的 `_locate.py`，各平台通用。）
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import _locate

MARKER = "_refresh_provenance(state)"

# 已打补丁的 finish_run 函数体（含新增的 _refresh_provenance 辅助函数）
PATCHED = '''def _refresh_provenance(state: dict) -> None:
    """从 sources.yaml 重算来源计数（派生值，不随封存冻结）。"""
    sources_file = run_dir(state["run_id"]) / "sources.yaml"
    if not sources_file.exists():
        return
    try:
        source_data = yaml.safe_load(sources_file.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError):
        return
    sources = source_data.get("sources", []) if isinstance(source_data, dict) else []
    provenance = state.setdefault("provenance", {})
    provenance["verified_sources"] = sum(
        1 for item in sources if item.get("status") == "verified"
    )
    provenance["unverified_sources"] = sum(
        1 for item in sources if item.get("status") != "verified"
    )


def finish_run(patch: dict | None = None, run_id: str | None = None) -> dict:
    state = load_run(run_id)
    if state.get("status") == "completed":
        # 已封存：正文与编辑结论冻结，但来源计数是派生值，补录 sources.yaml 后应能刷新
        _refresh_provenance(state)
        _write_state(state)
        upsert_article(_history_entry(state))
        return state
    if patch:
        blocked = PROTECTED_FIELDS.intersection(patch)
        if blocked:
            raise ValueError(
                "Protected run fields cannot be changed: " + ", ".join(sorted(blocked))
            )
        artifact_patch = patch.get("artifacts", {})
        if isinstance(artifact_patch, dict) and PROTECTED_ARTIFACTS.intersection(artifact_patch):
            raise ValueError("Core artifact paths are immutable")
        _deep_merge(state, patch)
    article_rel = (state.get("artifacts") or {}).get("article")
    article_path = home() / article_rel if article_rel else None
    if not article_path or not article_path.is_file() or not article_path.read_text(encoding="utf-8").strip():
        raise ValueError("Cannot finish run before a non-empty article is saved")
    draft_rel = (state.get("artifacts") or {}).get("draft")
    draft_path = home() / draft_rel if draft_rel else None
    if draft_path and draft_path.is_file() and draft_path.read_text(encoding="utf-8").strip():
        editorial = state.get("editorial") or {}
        report_rel = (state.get("artifacts") or {}).get("review_report")
        report_path = home() / report_rel if report_rel else None
        try:
            report = json.loads(report_path.read_text(encoding="utf-8")) if report_path else {}
        except (OSError, json.JSONDecodeError):
            report = {}
        if (
            editorial.get("decision") != "pass"
            or editorial.get("publishable") is not True
            or report.get("decision") != "pass"
            or report.get("publishable") is not True
        ):
            raise ValueError("Cannot finish a drafted article before editorial review passes")
    _refresh_provenance(state)
    state["status"] = "completed"
    state["last_error"] = None
    _write_state(state)
    upsert_article(_history_entry(state))
    return state'''

# 原始 finish_run（从 def 到下一个顶层 def 前），用于定位与还原
ORIGINAL_START = "def finish_run(patch: dict | None = None, run_id: str | None = None) -> dict:"


def find_runs_py() -> Path:
    return _locate.find("wewrite/runs.py")


def _replace_function(text: str, start_anchor: str, replacement: str) -> str:
    """替换从 start_anchor 所在行开始，到下一个顶层 def/class 之前的函数体。

    必须保留原函数末尾到下一个顶层定义之间的空行，否则会拼出
    `return statedef xxx` 这种语法错误（实测踩过）。
    """
    if start_anchor not in text:
        raise SystemExit(f"找不到锚点 {start_anchor!r}，wewrite 版本可能已变，请人工检查")
    start = text.index(start_anchor)
    rest = text[start + len(start_anchor):]

    # 下一个顶层定义的起点（列 0 的 def / class）
    boundary = len(rest)
    for pat in ("\ndef ", "\nclass "):
        p = rest.find(pat)
        if p != -1:
            boundary = min(boundary, p)
    if boundary >= len(rest):
        raise SystemExit("找不到函数结束边界，请人工检查")

    # rest[boundary] 是函数末尾换行后的第一个 '\n'，留给后续内容；
    # 再补一个空行以符合 PEP8 顶层函数间两个空行
    tail = rest[boundary + 1:]
    return text[:start] + replacement + "\n\n\n" + tail


def _read_text_keep_ending(path: Path) -> tuple[str, str]:
    """读文件并返回 (文本, 主行尾符)。

    用二进制读再解码，避免 write_text/read_text 在 Windows 上把 LF 统一成 CRLF，
    否则打补丁会把整份文件行尾翻一遍，diff 里混入大量无关噪声。
    """
    raw = path.read_bytes()
    crlf = raw.count(b"\r\n")
    lf = raw.count(b"\n") - crlf
    ending = "\r\n" if crlf > lf else "\n"
    text = raw.decode("utf-8").replace("\r\n", "\n")
    return text, ending


def main() -> int:
    parser = argparse.ArgumentParser(description="修 wewrite run finish 的幂等短路")
    parser.add_argument("--check", action="store_true", help="只报告状态，不修改")
    parser.add_argument("--restore", action="store_true", help="还原 .orig 备份")
    args = parser.parse_args()

    target = find_runs_py()
    text, ending = _read_text_keep_ending(target)
    patched = "def _refresh_provenance(" in text

    if args.restore:
        backup = target.with_suffix(".py.orig")
        if not backup.exists():
            raise SystemExit(f"没有备份可还原: {backup}")
        # 写字节而非文本：write_text 在 Windows 会把 LF 统一成 CRLF，
        # 导致"还原"后整份文件行尾变化，与原始文件逐字节不一致。
        target.write_bytes(backup.read_bytes())
        print(f"已还原: {target}")
        return 0

    if args.check:
        print(f"目标文件: {target}")
        print(f"补丁状态: {'已应用' if patched else '未应用'}")
        return 0

    backup = target.with_suffix(".py.orig")
    if not backup.exists():
        backup.write_bytes(text.encode("utf-8"))
        print(f"已备份原始文件: {backup}")

    if patched:
        print("补丁已存在，无需重复应用。")
        return 0

    new_text = _replace_function(text, ORIGINAL_START, PATCHED)
    if "_refresh_provenance(state)" not in new_text:
        raise SystemExit("替换未生效，请人工检查")

    target.write_bytes(new_text.replace("\n", ending).encode("utf-8"))
    print(f"补丁已应用: {target}")
    print("效果: `wewrite run finish` 在已封存任务上会重新统计 sources.yaml 的来源计数。")
    print("升级 wewrite 后重跑本脚本即可。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
