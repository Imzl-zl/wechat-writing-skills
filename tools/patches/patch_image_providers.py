#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""给 wewrite 的 image_gen.py 补两个免费图像 provider：sensenova / modelscope。

为什么需要这个脚本
------------------
wewrite 通过 `uv tool install` 安装，provider 注册表写死在
`site-packages/wewrite/toolkit/image_gen.py` 里，没有插件入口。
`uv tool upgrade wewrite` 会覆盖 site-packages，所以这里把补丁做成
可重复执行的脚本：升级后重跑一次即可，不需要记手工改了哪几行。

用法
----
    python patch_image_providers.py          # 应用（幂等）
    python patch_image_providers.py --check   # 只检查状态

（在本补丁目录下运行；文件定位见同目录的 `_locate.py`，各平台通用。）

两个 provider 的协议差异（2026-09 实测）
---------------------------------------
- sensenova：OpenAI 图像协议，同步返回 b64；`watermark=false` 去官方 Logo 水印
  （公测免费）；size 需为 32 的倍数，边长 512-4096，宽高比不超过 3:1。
- modelscope：异步任务协议。POST 拿 task_id，再轮询 /v1/tasks/{id}
  （必须带 X-ModelScope-Task-Type: image_generation），成功后取 output_images[0]。
  Z-Image-Turbo 纯免费，无请求水印。
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import _locate

MARKER = "class SenseNovaProvider"

BLOCK_START = "# --- Free-tier providers (added by .wewrite/tools/patch_image_providers.py) ---"

ANCHOR = "# --- Provider registry ---"

REGISTRY_ANCHOR = '    "sub2api": Sub2APIProvider,\n}'

REGISTRY_PATCHED = (
    '    "sub2api": Sub2APIProvider,\n'
    '    "sensenova": SenseNovaProvider,\n'
    '    "modelscope": ModelScopeProvider,\n'
    '}'
)

BLOCK = '''# --- Free-tier providers (added by .wewrite/tools/patch_image_providers.py) ---

import re  # 顶层未导入，_normalize_size 需要（原模块只在 _sanitize_for_log 里局部导入）

# 各尺寸预设对应的具体像素。两个新 provider 都不走 SIZE_PRESETS，
# 因为那套默认值（如 doubao 的 2952x1256）不满足 32 倍数约束。
FREE_TIER_SIZES = {
    "cover": "2048x864",      # 2.37:1，接近微信封面 2.35:1
    "article": "2048x1152",   # 16:9
    "vertical": "1152x2048",  # 9:16
    "square": "1024x1024",
}


def _snap_to_grid(value: int, minimum: int, maximum: int, factor: int = 32) -> int:
    """把边长对齐到 factor 的倍数，并夹在 [minimum, maximum] 内。"""
    snapped = int(round(value / factor)) * factor
    snapped = max(minimum, min(maximum, snapped))
    return snapped


class SenseNovaProvider(ImageProvider):
    """商汤日日新 SenseNova U1.5 Lite 文生图（OpenAI 图像协议）。

    watermark=False 去掉官方 Logo 水印，公测期间免费；官方文档建议显式传参，
    因为默认值以后可能变。
    """

    provider_key = "sensenova"

    def __init__(self, api_key: str, model: str = "sensenova-u1.5-lite",
                 base_url: str = "https://token.sensenova.cn/v1", **_kw):
        self._api_key = api_key
        self._model = model
        self._base_url = base_url.rstrip("/")

    def resolve_size(self, preset: str) -> str:
        return FREE_TIER_SIZES.get(preset, preset)

    def generate(self, prompt: str, size: str) -> bytes:
        width, height = self._normalize_size(size)
        resp = requests.post(
            f"{self._base_url}/images/generations",
            headers={"Content-Type": "application/json",
                     "Authorization": f"Bearer {self._api_key}"},
            json={
                "model": self._model,
                "prompt": prompt,
                "n": 1,
                "size": f"{width}x{height}",
                "output_format": "png",
                "response_format": "b64_json",
                "watermark": False,
                "prompt_extend": True,
            },
            timeout=180,
        )
        try:
            data = resp.json()
        except ValueError as exc:
            raise ValueError(
                f"SenseNova returned non-JSON ({resp.status_code}): {resp.text[:200]}"
            ) from exc
        if resp.status_code != 200:
            message = data.get("error", {}).get("message") if isinstance(data, dict) else None
            raise ValueError(f"SenseNova error ({resp.status_code}): {message or data}")
        entries = data.get("data") or []
        if not entries:
            raise ValueError(f"SenseNova returned no image: {data}")
        entry = entries[0]
        if entry.get("b64_json"):
            return base64.b64decode(entry["b64_json"])
        if entry.get("url"):
            # 临时链接仅 24 小时有效，立刻下载转存。
            return _download_image(entry["url"])
        raise ValueError(f"SenseNova response has neither b64_json nor url: {entry}")

    @staticmethod
    def _normalize_size(size: str) -> tuple[int, int]:
        """把 "WxH" 对齐到 32 倍数并夹到合法范围；宽高比超过 3:1 时收缩长边。"""
        match = re.match(r"^\\s*(\\d+)\\s*[xX*]\\s*(\\d+)\\s*$", size or "")
        if not match:
            return (2048, 864)
        width = _snap_to_grid(int(match.group(1)), 512, 4096)
        height = _snap_to_grid(int(match.group(2)), 512, 4096)
        if width > height * 3:
            height = _snap_to_grid(width / 3.0, 512, 4096)
        elif height > width * 3:
            width = _snap_to_grid(height / 3.0, 512, 4096)
        return (width, height)


class ModelScopeProvider(ImageProvider):
    """魔搭 ModelScope 免费推理 API（异步任务协议）。

    文生图接口不直接返回图片：先拿 task_id，再轮询任务状态，
    成功后从 output_images 取链接下载。轮询间隔和上限按 2026-09 实测
    （Z-Image-Turbo 单张约 10-20 秒）留了充足余量。
    """

    provider_key = "modelscope"

    def __init__(self, api_key: str, model: str = "Tongyi-MAI/Z-Image-Turbo",
                 base_url: str = "https://api-inference.modelscope.cn", **_kw):
        self._api_key = api_key
        self._model = model
        self._base_url = base_url.rstrip("/")
        self._poll_interval = 3.0
        self._poll_attempts = 60

    def resolve_size(self, preset: str) -> str:
        return FREE_TIER_SIZES.get(preset, preset)

    def generate(self, prompt: str, size: str) -> bytes:
        headers = {"Content-Type": "application/json",
                   "Authorization": f"Bearer {self._api_key}",
                   "X-ModelScope-Async-Mode": "true"}
        body = {"model": self._model, "prompt": prompt}
        if size:
            body["size"] = size
        resp = requests.post(f"{self._base_url}/v1/images/generations",
                             headers=headers, json=body, timeout=120)
        try:
            data = resp.json()
        except ValueError as exc:
            raise ValueError(
                f"ModelScope returned non-JSON ({resp.status_code}): {resp.text[:200]}"
            ) from exc
        if resp.status_code != 200:
            message = data.get("message") if isinstance(data, dict) else None
            raise ValueError(f"ModelScope error ({resp.status_code}): {message or data}")

        task_id = data.get("task_id")
        if not task_id:
            raise ValueError(f"ModelScope returned no task_id: {data}")

        poll_headers = {"Authorization": f"Bearer {self._api_key}",
                        "X-ModelScope-Task-Type": "image_generation"}
        for _ in range(self._poll_attempts):
            status_resp = requests.get(f"{self._base_url}/v1/tasks/{task_id}",
                                       headers=poll_headers, timeout=60)
            status_data = status_resp.json()
            state = status_data.get("task_status")
            if state == "SUCCEED":
                images = status_data.get("output_images") or []
                if not images:
                    raise ValueError(f"ModelScope task succeeded without images: {status_data}")
                return _download_image(images[0])
            if state in ("FAILED", "CANCELED"):
                raise ValueError(f"ModelScope task {state}: {status_data}")
            time.sleep(self._poll_interval)
        raise ValueError(
            f"ModelScope task {task_id} did not finish within "
            f"{int(self._poll_attempts * self._poll_interval)}s"
        )


'''


def find_image_gen() -> Path:
    return _locate.find("wewrite/toolkit/image_gen.py")


def main() -> int:
    parser = argparse.ArgumentParser(description="给 wewrite 补 sensenova / modelscope 图像 provider")
    parser.add_argument("--check", action="store_true", help="只报告状态，不修改")
    args = parser.parse_args()

    target = find_image_gen()
    text = target.read_text(encoding="utf-8")
    patched = MARKER in text

    if args.check:
        print(f"目标文件: {target}")
        print(f"补丁状态: {'已应用' if patched else '未应用'}")
        return 0

    if ANCHOR not in text:
        raise SystemExit(f"找不到锚点 {ANCHOR!r}，wewrite 版本可能已变，请人工检查")

    backup = target.with_suffix(".py.orig")
    if not backup.exists():
        backup.write_text(text, encoding="utf-8")
        print(f"已备份原始文件: {backup}")

    if patched:
        # 重放：把旧版本块整体换成当前 BLOCK，方便修复补丁自身的问题。
        start = text.index(BLOCK_START)
        end = text.index(ANCHOR, start)
        text = text[:start] + BLOCK + text[end:]
        action = "已重放更新"
    else:
        text = text.replace(ANCHOR, BLOCK + ANCHOR, 1)
        action = "已应用"

    if REGISTRY_PATCHED not in text:
        if REGISTRY_ANCHOR not in text:
            raise SystemExit("找不到 PROVIDERS 注册表锚点，请人工检查")
        text = text.replace(REGISTRY_ANCHOR, REGISTRY_PATCHED, 1)

    target.write_text(text, encoding="utf-8")
    print(f"补丁{action}: {target}")
    print("新增 provider: sensenova, modelscope")
    return 0


if __name__ == "__main__":
    sys.exit(main())
