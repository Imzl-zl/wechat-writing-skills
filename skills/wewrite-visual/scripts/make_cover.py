#!/usr/bin/env python3
"""封面生成器：从设计规格渲染 1200x510 公众号封面，并拦截重复封面。

解决的问题
----------
1. 过去没有封面生成器，每次现写 HTML，配色随手沿用 ai-practice 的深青
   (#0f766e) + 琥珀，深色大面积铺开偏绿，且风格趋同。
2. 更严重的是出现过整张封面 PNG 被复制到别的文章（多篇文章封面 SHA256 相同）。

因此本脚本做三件事：
- 把"设计规格 (JSON) -> 封面 PNG"变成确定性流程，字体由本机渲染，不交给生图模型。
- 渲染前扫描项目内所有已存在封面，若本次成品与任何一张历史封面逐字节相同，
  直接报错并拒绝写出，除非显式传 --allow-duplicate。
- 额外做配色撞车检测：成品主色与历史封面主色接近时也报警（见 --check-palette）。

用法
----
    python make_cover.py design.json -o assets/cover.png
    python make_cover.py design.json -o assets/cover.png --thumb assets/cover-thumb.png
    python make_cover.py design.json -o assets/cover.png --dry-run   # 只出 HTML，不渲染
    python make_cover.py design.json -o assets/cover.png --check-palette

设计规格（design.json）字段
--------------------------
    kicker      左上角小标（可省）
    title       主标题，字符串或字符串数组（每个元素一行）
    title_accent 需要高亮成强调色的子串（可省）
    subtitle    副标题，字符串或字符串数组
    metrics     [{value, label, tone?}]  数值条；tone: "accent"|"ink"|"muted"
    footnote    左下角脚注（可省）
    stamp       右下角署名（可省）
    palette     {bg, ink, body, muted, accent, line} 十六进制色值

只要 palette 不写，就用本文件内置的中性暖灰默认（不含任何绿色）。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

W, H = 1200, 510
THUMB_W = 360

# 中性暖灰默认配色（刻意不含绿色；深色只用于文字与强调块）
DEFAULT_PALETTE = {
    "bg": "#F5F1EA",      # 暖米底
    "panel": "#FFFFFF",   # 卡片底
    "ink": "#1C1B19",     # 标题墨黑
    "body": "#57534E",    # 正文灰
    "muted": "#8A857D",   # 弱化文字
    "accent": "#D9480F",  # 强调朱橙
    "line": "#DED8CE",    # 细线
}

FONT_CANDIDATES_BOLD = ["msyhbd.ttc", "msyh.ttc", "simhei.ttf"]
FONT_CANDIDATES_REG = ["msyh.ttc", "simhei.ttf", "simsun.ttc"]
FONT_CANDIDATES_SERIF_BOLD = ["NotoSerifSC-VF.ttf", "msyhbd.ttc"]
FONT_DIR = Path("C:/Windows/Fonts")


def _project_root() -> Path:
    """定位内容项目根（文章目录所在处）。

    本文件随 skill 仓库分发，实际调用点在内容项目里，两处路径不同：
      - skill 仓库内：<repo>/skills/wewrite-visual/scripts/make_cover.py
      - 内容项目内：  <project>/.agents/skills/wewrite-visual/scripts/make_cover.py
    不能靠固定的 parents 层级，要按优先级探测。
    """
    here = Path(__file__).resolve()
    candidates: list[Path] = []

    env_home = os.environ.get("WEWRITE_HOME")
    if env_home:
        candidates.append(Path(env_home).resolve().parent)

    for parent in here.parents:
        candidates.append(parent)
        if (parent / ".wewrite").is_dir():
            break

    for cand in candidates:
        if not cand.is_dir():
            continue
        # skill 仓库根不是内容项目：它有 skills/ 目录但没有 .wewrite/
        if (cand / "skills").is_dir() and not (cand / ".wewrite").is_dir():
            continue
        return cand

    if env_home:
        return Path(env_home).resolve().parent
    return here.parents[3]


PROJECT_ROOT = _project_root()


def _hex(c: str) -> tuple[int, int, int]:
    c = c.lstrip("#")
    return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


def _font(names: list[str], size: int, weight: int | None = None) -> ImageFont.FreeTypeFont:
    for n in names:
        p = FONT_DIR / n
        if not p.exists():
            continue
        try:
            f = ImageFont.truetype(str(p), size)
        except OSError:
            continue
        if weight is not None:
            try:
                f.set_variation_by_axes([weight])
            except Exception:
                pass
        return f
    return ImageFont.load_default(size)


def _tracked(d: ImageDraw.ImageDraw, xy, text: str, f, fill, spacing: float) -> float:
    """带字距绘制（PIL 无原生 letter-spacing），返回结束 x。"""
    x, y = xy
    for ch in text:
        d.text((x, y), ch, font=f, fill=fill, anchor="la")
        x += d.textlength(ch, font=f) + spacing
    return x


def _draw_rich_line(d: ImageDraw.ImageDraw, xy, line: str, accent: str,
                    f, ink, accent_color) -> None:
    """绘制一行，命中 accent 子串的部分换强调色。"""
    x, y = xy
    if accent and accent in line:
        head, _, tail = line.partition(accent)
        if head:
            d.text((x, y), head, font=f, fill=ink, anchor="la")
            x += d.textlength(head, font=f)
        d.text((x, y), accent, font=f, fill=accent_color, anchor="la")
        x += d.textlength(accent, font=f)
        if tail:
            d.text((x, y), tail, font=f, fill=ink, anchor="la")
    else:
        d.text((x, y), line, font=f, fill=ink, anchor="la")


def build_html(spec: dict) -> str:
    """生成同版式的 HTML（存档用，也可用于浏览器渲染对照）。"""
    p = {**DEFAULT_PALETTE, **(spec.get("palette") or {})}
    title = spec.get("title") or []
    if isinstance(title, str):
        title = [title]
    sub = spec.get("subtitle") or []
    if isinstance(sub, str):
        sub = [sub]
    accent = spec.get("title_accent") or ""
    metrics = spec.get("metrics") or []

    def rich(line: str, cls: str) -> str:
        if accent and accent in line:
            return line.replace(accent, f'<span class="hl">{accent}</span>')
        return line

    title_html = "".join(f"<div>{rich(l, 'h')}</div>" for l in title)
    sub_html = "".join(f"<div>{l}</div>" for l in sub)
    metrics_html = "".join(
        f'<div class="m {m.get("tone","ink")}"><b>{m.get("value","")}</b>'
        f'<span>{m.get("label","")}</span></div>'
        for m in metrics
    )
    return f"""<!doctype html>
<html lang="zh"><head><meta charset="utf-8"><style>
  *{{margin:0;padding:0;box-sizing:border-box}}
  html,body{{width:{W}px;height:{H}px;overflow:hidden}}
  body{{background:{p['bg']};color:{p['ink']};
    font-family:"Microsoft YaHei","PingFang SC",sans-serif;position:relative}}
  .wrap{{position:absolute;left:64px;top:52px;right:64px}}
  .kicker{{font-size:16px;font-weight:700;letter-spacing:5px;color:{p['muted']}}}
  .rule{{height:3px;background:{p['ink']};margin:14px 0 0}}
  .rule2{{height:2px;background:{p['accent']};margin-top:5px;width:132px}}
  h1{{font-size:66px;font-weight:800;line-height:1.16;letter-spacing:-1px;margin-top:26px}}
  h1 .hl{{color:{p['accent']}}}
  .sub{{margin-top:18px;font-size:22px;line-height:1.5;color:{p['body']}}}
  .metrics{{position:absolute;left:64px;right:64px;bottom:74px;display:flex;gap:44px}}
  .m b{{display:block;font-size:34px;font-weight:800;letter-spacing:-.5px}}
  .m span{{font-size:15px;color:{p['muted']}}}
  .m.accent b{{color:{p['accent']}}}
  .m.muted b{{color:{p['muted']}}}
  .foot{{position:absolute;left:64px;bottom:30px;font-size:15px;color:{p['muted']}}}
  .stamp{{position:absolute;right:64px;bottom:28px;background:{p['ink']};color:{p['bg']};
    font-size:15px;font-weight:700;padding:7px 16px;border-radius:4px;letter-spacing:1px}}
</style></head><body>
  <div class="wrap">
    {f'<div class="kicker">{spec["kicker"]}</div>' if spec.get('kicker') else ''}
    <div class="rule"></div><div class="rule2"></div>
    <h1>{title_html}</h1>
    <div class="sub">{sub_html}</div>
  </div>
  <div class="metrics">{metrics_html}</div>
  {f'<div class="foot">{spec["footnote"]}</div>' if spec.get('footnote') else ''}
  {f'<div class="stamp">{spec["stamp"]}</div>' if spec.get('stamp') else ''}
</body></html>"""


def render_png(spec: dict) -> Image.Image:
    """用 PIL 确定性渲染，避免依赖浏览器。"""
    p = {**DEFAULT_PALETTE, **(spec.get("palette") or {})}
    bg, ink = _hex(p["bg"]), _hex(p["ink"])
    body, muted, accent = _hex(p["body"]), _hex(p["muted"]), _hex(p["accent"])

    img = Image.new("RGB", (W, H), bg)
    d = ImageDraw.Draw(img)

    title = spec.get("title") or []
    if isinstance(title, str):
        title = [title]
    sub = spec.get("subtitle") or []
    if isinstance(sub, str):
        sub = [sub]
    accent_str = spec.get("title_accent") or ""
    metrics = spec.get("metrics") or []

    pad = 64
    y = 52

    if spec.get("kicker"):
        _tracked(d, (pad, y), spec["kicker"], _font(FONT_CANDIDATES_REG, 16), muted, 5)
        y += 32

    # 双细线
    d.rectangle([pad, y, W - pad, y + 2], fill=ink)
    d.rectangle([pad, y + 7, pad + 132, y + 8], fill=accent)
    y += 30

    # 主标题
    f_title = _font(FONT_CANDIDATES_BOLD, 66)
    for line in title:
        _draw_rich_line(d, (pad, y), line, accent_str, f_title, ink, accent)
        y += 78

    # 副标题：与主标题留出一行呼吸位
    y += 18
    f_sub = _font(FONT_CANDIDATES_REG, 22)
    for line in sub:
        d.text((pad, y), line, font=f_sub, fill=body, anchor="la")
        y += 33

    # 数值条：数字列左对齐成栏，避免右侧拥挤
    if metrics:
        f_val = _font(FONT_CANDIDATES_BOLD, 32)
        f_lbl = _font(FONT_CANDIDATES_REG, 15)
        base_y = H - 118
        col_gap = 56
        col_w = max(
            max(d.textlength(str(m.get("value", "")), font=f_val),
                d.textlength(str(m.get("label", "")), font=f_lbl))
            for m in metrics
        )
        x = pad
        for m in metrics:
            tone = m.get("tone", "ink")
            tc = accent if tone == "accent" else (muted if tone == "muted" else ink)
            d.text((x, base_y), str(m.get("value", "")), font=f_val, fill=tc, anchor="la")
            d.text((x, base_y + 40), str(m.get("label", "")), font=f_lbl, fill=muted, anchor="la")
            x += col_w + col_gap
        # 数值与页脚之间的细分隔线
        d.rectangle([pad, H - 62, W - pad, H - 61], fill=_hex(p["line"]))

    # 页脚
    if spec.get("footnote"):
        d.text((pad, H - 44), spec["footnote"], font=_font(FONT_CANDIDATES_REG, 15),
               fill=muted, anchor="la")
    if spec.get("stamp"):
        f_st = _font(FONT_CANDIDATES_BOLD, 15)
        tw = d.textlength(spec["stamp"], font=f_st)
        bx2 = W - pad
        bx1 = bx2 - (tw + 32)
        d.rectangle([bx1, H - 52, bx2, H - 18], fill=ink)
        d.text(((bx1 + bx2) / 2, H - 35), spec["stamp"], font=f_st, fill=bg, anchor="mm")

    return img


def find_existing_covers(skip: Path | None = None) -> dict[str, list[str]]:
    """扫描项目内已存在的封面 PNG，返回 {sha256: [相对路径, ...]}。"""
    seen: dict[str, list[str]] = {}
    patterns = ["*.png", "*.jpg"]
    skip_res = skip.resolve() if skip else None
    for base in [PROJECT_ROOT]:
        for pat in patterns:
            for f in base.rglob(pat):
                low = f.name.lower()
                if "cover" not in low:
                    continue
                if skip_res and f.resolve() == skip_res:
                    continue
                if any(part in {".git", "node_modules", ".agents"} for part in f.parts):
                    continue
                try:
                    h = hashlib.sha256(f.read_bytes()).hexdigest()
                except OSError:
                    continue
                seen.setdefault(h, []).append(str(f.relative_to(PROJECT_ROOT)))
    return seen


def _dominant_colors(img: Image.Image, count: int = 3) -> list[tuple[int, int, int]]:
    """取封面出现最多的几个颜色，用来判断两张封面是不是同一套配色。"""
    small = img.convert("RGB").resize((60, 26))
    buckets: dict[tuple[int, int, int], int] = {}
    for y in range(small.height):
        for x in range(small.width):
            r, g, b = small.getpixel((x, y))
            key = (r // 24 * 24, g // 24 * 24, b // 24 * 24)
            buckets[key] = buckets.get(key, 0) + 1
    return [c for c, _ in sorted(buckets.items(), key=lambda kv: -kv[1])[:count]]


def _color_distance(a: tuple[int, int, int], b: tuple[int, int, int]) -> float:
    return sum((x - y) ** 2 for x, y in zip(a, b)) ** 0.5


def find_palette_collisions(img: Image.Image, skip: Path | None = None) -> list[str]:
    """找出与本次封面主色接近的历史封面。

    字节级去重拦不住「同一套配色换文案」——那正是封面看起来千篇一律的原因。
    这里按主色距离判断，阈值 60（约等于换一个色阶的差距）。
    """
    mine = _dominant_colors(img)
    skip_res = skip.resolve() if skip else None
    hits: list[str] = []
    for pat in ("*.png", "*.jpg"):
        for f in PROJECT_ROOT.rglob(pat):
            low = f.name.lower()
            if "cover" not in low:
                continue
            if skip_res and f.resolve() == skip_res:
                continue
            if any(part in {".git", "node_modules", ".agents"} for part in f.parts):
                continue
            try:
                with Image.open(f) as hist:
                    hist.load()
                    theirs = _dominant_colors(hist)
            except OSError:
                continue
            for tc in theirs:
                for mc in mine:
                    if _color_distance(tc, mc) < 60:
                        hits.append(str(f.relative_to(PROJECT_ROOT)))
                        break
                else:
                    continue
                break
    return sorted(set(hits))


def main() -> int:
    ap = argparse.ArgumentParser(description="渲染 1200x510 公众号封面并拦截重复")
    ap.add_argument("spec", help="设计规格 JSON 路径")
    ap.add_argument("-o", "--output", required=True, help="输出 PNG 路径")
    ap.add_argument("--thumb", help="同时输出 360px 缩略图（检查信息流可读性）")
    ap.add_argument("--html", help="同时写出 HTML 存档")
    ap.add_argument("--dry-run", action="store_true", help="只出 HTML，不渲染 PNG")
    ap.add_argument("--allow-duplicate", action="store_true",
                    help="允许与历史封面重复（默认拒绝）")
    ap.add_argument("--check-palette", action="store_true",
                    help="检测配色是否与历史封面撞车（默认只警告，不阻断）")
    args = ap.parse_args()

    spec = json.loads(Path(args.spec).read_text(encoding="utf-8"))
    out = Path(args.output)
    if not out.is_absolute():
        out = PROJECT_ROOT / out

    if args.html:
        Path(args.html).write_text(build_html(spec), encoding="utf-8")
        print(f"html  {args.html}")
    if args.dry_run:
        if not args.html:
            print(build_html(spec))
        return 0

    img = render_png(spec)
    out.parent.mkdir(parents=True, exist_ok=True)

    # 去重闸门：先把成品写到临时缓冲，比对历史封面
    import io
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    digest = hashlib.sha256(buf.getvalue()).hexdigest()
    existing = find_existing_covers(skip=out)
    if digest in existing and not args.allow_duplicate:
        print("拒绝写出：本次封面与已有封面逐字节相同。", file=sys.stderr)
        for rel in existing[digest]:
            print(f"  已存在于 {rel}", file=sys.stderr)
        print("这说明复用了旧封面，请改设计规格让封面从本文内容长出来。", file=sys.stderr)
        return 2

    # 配色撞车检测：同一套配色换文案，逐字节不同但看起来一样
    if args.check_palette:
        collisions = find_palette_collisions(img, skip=out)
        if collisions:
            print("警告：本次配色与以下历史封面接近（换个底色或强调色再渲一次）：", file=sys.stderr)
            for rel in collisions:
                print(f"  {rel}", file=sys.stderr)
            print("同一账号的封面应保持字体与版式骨架一致，但底色与强调色随文章主题变化。",
                  file=sys.stderr)

    out.write_bytes(buf.getvalue())
    print(f"png   {out}  {img.width}x{img.height}  sha256={digest[:12]}")

    if args.thumb:
        tp = Path(args.thumb)
        if not tp.is_absolute():
            tp = PROJECT_ROOT / tp
        tp.parent.mkdir(parents=True, exist_ok=True)
        img.resize((THUMB_W, int(H * THUMB_W / W)), Image.LANCZOS).save(tp, optimize=True)
        print(f"thumb {tp}  {THUMB_W}px 宽")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
