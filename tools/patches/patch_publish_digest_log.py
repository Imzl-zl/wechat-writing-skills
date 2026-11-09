#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""修 wewrite `publish` 的摘要日志：打印的值与实际发送的值不一致。

问题
----
`cmd_publish` 里，摘要分两步定：

    print(f"Digest: {result.digest}")      # 第 82 行：先打印转换器的值
    ...
    digest = args.digest or result.digest  # 第 121 行：才决定真正发什么

只要命令行传了 `--digest`，第 82 行打印的那个值就永远不会被发送，控制台却把它
摆在 "Digest:" 名下，看起来就是最终值。实际危害是误导操作者判断发布结果——
本次即因此误判"摘要被污染"，多发了两篇草稿又删掉。

注意：这不是发送错误。`args.digest or result.digest` 的取值逻辑是对的，
`--digest` 被正确采用；错的只是日志打印的是解析前的值。

顺带说明另一处相似代码（`cmd_preview` 里的同名 print）没有问题：那条路径没有
`--digest` 参数，打印的就是唯一值，不要动它。所以本补丁用带上下文的锚点定位，
只改 `cmd_publish`。

改法
----
把打印从"转换之后、取 token 之前"挪到"digest 定案之后、取 token 之前"，
让它反映真实发送值，又不必等网络调用：

    -    print(f"Title: {result.title}")
    -    print(f"Digest: {result.digest}")
    -    print(f"Images found: {len(result.images)}")
    +    print(f"Title: {result.title}")
    +    print(f"Images found: {len(result.images)}")
    ...
         # Get access token
         token = get_access_token(appid, secret)
    ...
         # Create draft
         title = args.title or result.title or Path(args.input).stem
         digest = args.digest or result.digest
    +    print(f"Digest: {digest}")
         draft = create_draft(

注意打印点仍位于 get_access_token 之前，否则凭据无效时日志会被一起吞掉。

`uv tool upgrade wewrite` 会覆盖 site-packages，升级后重跑本脚本即可。

用法
----
    python patch_publish_digest_log.py           # 应用（幂等）
    python patch_publish_digest_log.py --check    # 只检查状态
    python patch_publish_digest_log.py --restore  # 还原备份

（在本补丁目录下运行；文件定位见同目录的 `_locate.py`，各平台通用。）
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import _locate

# 已打补丁后应出现的标记
MARKER = 'digest = args.digest or result.digest\n    print(f"Digest: {digest}")'

# cmd_publish 里独有的上下文（cmd_preview 那条没有这些行），用来锚定
EARLY_BLOCK_OLD = (
    '    _print_validation(result.html)\n'
    '\n'
    '    print(f"Title: {result.title}")\n'
    '    print(f"Digest: {result.digest}")\n'
    '    print(f"Images found: {len(result.images)}")\n'
)

EARLY_BLOCK_NEW = (
    '    _print_validation(result.html)\n'
    '\n'
    '    print(f"Title: {result.title}")\n'
    '    print(f"Images found: {len(result.images)}")\n'
)

LATE_BLOCK_OLD = (
    '    # Get access token\n'
    '    token = get_access_token(appid, secret)\n'
    '    print("Access token obtained.")\n'
)

LATE_BLOCK_NEW = (
    '    digest = args.digest or result.digest\n'
    '    print(f"Digest: {digest}")\n'
    '\n'
    '    # Get access token\n'
    '    token = get_access_token(appid, secret)\n'
    '    print("Access token obtained.")\n'
)

# digest 已上移，原来 # Create draft 处的重复赋值要删掉
DUP_BLOCK_OLD = (
    '    title = args.title or result.title or Path(args.input).stem\n'
    '    digest = args.digest or result.digest\n'
    '    draft = create_draft(\n'
)

DUP_BLOCK_NEW = (
    '    title = args.title or result.title or Path(args.input).stem\n'
    '    draft = create_draft(\n'
)


def find_cli_py() -> Path:
    return _locate.find("wewrite/toolkit/cli.py")


def _read_keep_ending(path: Path) -> tuple[str, str]:
    """读文件并返回 (文本, 主行尾符)，避免把 LF 文件写成 CRLF。"""
    raw = path.read_bytes()
    crlf = raw.count(b"\r\n")
    lf = raw.count(b"\n") - crlf
    ending = "\r\n" if crlf > lf else "\n"
    return raw.decode("utf-8").replace("\r\n", "\n"), ending


def apply_patch(text: str) -> str:
    if EARLY_BLOCK_OLD not in text:
        raise SystemExit("找不到 cmd_publish 的早段锚点，wewrite 版本可能已变，请人工检查")
    if LATE_BLOCK_OLD not in text:
        raise SystemExit("找不到 digest 定案锚点，wewrite 版本可能已变，请人工检查")
    if EARLY_BLOCK_OLD.count('print(f"Digest') != 1:
        raise SystemExit("早段锚点不唯一，中止以避免误改 cmd_preview")

    text = text.replace(EARLY_BLOCK_OLD, EARLY_BLOCK_NEW, 1)
    text = text.replace(LATE_BLOCK_OLD, LATE_BLOCK_NEW, 1)
    text = text.replace(DUP_BLOCK_OLD, DUP_BLOCK_NEW, 1)

    # 自检：publish 路径里应当先定 digest 再打印；preview 路径不受影响
    if MARKER not in text:
        raise SystemExit("替换未生效")
    if text.count('print(f"Digest: {result.digest}")') != 1:
        raise SystemExit("cmd_preview 的打印被误改，中止")
    if text.count('digest = args.digest or result.digest') != 1:
        raise SystemExit("digest 赋值次数异常，中止")
    # 打印必须早于取 token，否则凭据无效时日志会被吞掉
    if text.index('print(f"Digest: {digest}")') > text.index('get_access_token(appid, secret)'):
        raise SystemExit("Digest 打印被放到了取 token 之后，中止")
    return text


def main() -> int:
    ap = argparse.ArgumentParser(description="修 wewrite publish 的摘要日志")
    ap.add_argument("--check", action="store_true", help="只报告状态，不修改")
    ap.add_argument("--restore", action="store_true", help="还原 .orig 备份")
    args = ap.parse_args()

    target = find_cli_py()
    text, ending = _read_keep_ending(target)
    patched = MARKER in text

    if args.restore:
        backup = target.with_suffix(".py.orig")
        if not backup.exists():
            raise SystemExit(f"没有备份可还原: {backup}")
        target.write_bytes(backup.read_bytes())
        print(f"已还原: {target}")
        return 0

    if args.check:
        print(f"目标文件: {target}")
        print(f"补丁状态: {'已应用' if patched else '未应用'}")
        return 0

    backup = target.with_suffix(".py.orig")
    if not backup.exists():
        backup.write_bytes(text.replace("\n", ending).encode("utf-8"))
        print(f"已备份原始文件: {backup}")

    if patched:
        print("补丁已存在，无需重复应用。")
        return 0

    new_text = apply_patch(text)
    target.write_bytes(new_text.replace("\n", ending).encode("utf-8"))
    print(f"补丁已应用: {target}")
    print("效果: `wewrite publish --digest ...` 控制台打印的 Digest 与实际发送值一致。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
