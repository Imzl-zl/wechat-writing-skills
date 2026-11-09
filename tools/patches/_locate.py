"""定位 uv tool 装出来的 wewrite 包文件。

三个补丁脚本共用。wewrite 是用 `uv tool install` 装到独立 venv 里的，
它的 site-packages 不在系统 Python 的搜索路径上，所以定位有两条路：

1. 在 wewrite 自己的解释器下跑 —— 直接 `import` 拿 `__file__`；
2. 在系统 Python 下跑 —— 问 `uv tool dir` 要工具目录，再递归 glob。

第 2 条不能拼死 `Lib/site-packages`：Windows 是 `Lib/site-packages`，
macOS/Linux 是 `lib/python3.x/site-packages`，所以用 `**` 递归匹配。
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path


def _tool_root() -> Path | None:
    """返回 uv 的 wewrite 工具目录，找不到就回 None。"""
    try:
        done = subprocess.run(
            ["uv", "tool", "dir"], capture_output=True, text=True, timeout=20
        )
    except (OSError, subprocess.SubprocessError):
        done = None
    if done is not None and done.returncode == 0 and done.stdout.strip():
        candidate = Path(done.stdout.strip()) / "wewrite"
        if candidate.is_dir():
            return candidate

    # uv 不在 PATH 上时按各平台默认工具目录兜底
    for base in (os.environ.get("APPDATA"), Path.home() / ".local" / "share"):
        if not base:
            continue
        candidate = Path(base) / "uv" / "tools" / "wewrite"
        if candidate.is_dir():
            return candidate
    return None


def find(rel: str) -> Path:
    """按包内相对路径找文件，例如 `wewrite/runs.py`、`wewrite/toolkit/cli.py`。"""
    module_name = rel.replace("/", ".").removesuffix(".py")
    try:
        module = __import__(module_name, fromlist=["__file__"])
    except ImportError:
        pass
    else:
        module_file = getattr(module, "__file__", None)
        if module_file:
            return Path(module_file)

    root = _tool_root()
    if root is not None:
        for candidate in root.glob(f"**/site-packages/{rel}"):
            return candidate
    raise SystemExit(
        f"找不到 {rel}。先确认 `uv tool install wewrite` 装好了，"
        "并且 `uv tool dir` 能正常输出。"
    )
