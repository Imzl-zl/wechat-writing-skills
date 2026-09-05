#!/usr/bin/env python3
"""给 wewrite 预览 HTML 注入「复制全文」按钮，一键复制富文本到剪贴板。

用法:
    python copy_page.py preview.html -o preview-copy.html

原理:
    微信公众号编辑器粘贴时只保留元素内联 style，丢弃 <style> 块和复杂布局。
    本脚本保留正文所有内联样式，注入一个固定在右上角的按钮，
    点击后用 Range 选中正文复制（富文本），去公众号编辑器 Ctrl+V 即可。

Windows 编码: PYTHONIOENCODING=utf-8
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

COPY_BUTTON_HTML = """
<div id="ww-copy-btn" style="position:fixed;top:16px;right:16px;z-index:99999;
  font-family:-apple-system,'Segoe UI','Microsoft YaHei',sans-serif;">
  <button type="button" onclick="wwCopyAll()"
    style="background:#134e4a;color:#fff;border:none;border-radius:8px;
    padding:10px 18px;font-size:14px;cursor:pointer;box-shadow:0 2px 10px rgba(0,0,0,.25);">
    📋 复制全文
  </button>
  <div id="ww-copy-tip" style="display:none;margin-top:6px;padding:6px 10px;
    background:#fef3c7;color:#92400e;border-radius:6px;font-size:12px;"></div>
</div>
<script>
function wwCopyAll() {
  var btn = document.getElementById('ww-copy-btn');
  var tip = document.getElementById('ww-copy-tip');
  var root = btn.parentNode;
  var range = document.createRange();
  range.selectNodeContents(document.body);
  // 排除复制按钮自身
  var nodes = [];
  document.body.childNodes.forEach(function (n) {
    if (n !== root && n.nodeType === 1) { nodes.push(n); }
  });
  var sel = window.getSelection();
  sel.removeAllRanges();
  var r = document.createRange();
  r.setStart(document.body, 0);
  r.setEnd(document.body, document.body.childNodes.length);
  // 用临时 Range 收缩到按钮以外
  r.setEndBefore(root);
  sel.addRange(r);
  var ok = false;
  try { ok = document.execCommand('copy'); } catch (e) { ok = false; }
  sel.removeAllRanges();
  if (ok) {
    btn.innerHTML = '<button onclick="wwCopyAll()" style="background:#047857;color:#fff;border:none;border-radius:8px;padding:10px 18px;font-size:14px;cursor:pointer;box-shadow:0 2px 10px rgba(0,0,0,.25);">✓ 已复制，去公众号 Ctrl+V</button>';
  } else {
    tip.style.display = 'block';
    tip.textContent = '自动复制失败：请手动 Ctrl+A 全选 → Ctrl+C';
  }
}
</script>
"""


def inject_copy_button(html: str) -> str:
    if "ww-copy-btn" in html:
        return html  # 已注入过，不重复
    if "</body>" in html:
        return html.replace("</body>", COPY_BUTTON_HTML + "\n</body>", 1)
    return html + COPY_BUTTON_HTML


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="预览 HTML 注入一键复制按钮")
    parser.add_argument("input", type=Path, help="preview HTML 路径")
    parser.add_argument("-o", "--output", type=Path, help="输出路径（默认输入名加 -copy）")
    args = parser.parse_args(argv)

    src = args.input
    if not src.exists():
        print(f"错误: 文件不存在 {src}", file=sys.stderr)
        return 1

    out = args.output or src.with_name(src.stem + "-copy.html")
    out.write_text(inject_copy_button(src.read_text(encoding="utf-8")),
                   encoding="utf-8")
    print(f"已生成: {out}")
    print("打开该页面 → 点右上角「复制全文」→ 去公众号编辑器 Ctrl+V（样式保留）")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
