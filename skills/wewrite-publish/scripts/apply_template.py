#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
apply_template.py — 把标准 markdown 重写成指定模板的版式结构。

模板(template)管结构，主题(theme)管配色，两层任意组合：
  --template 选版式结构；--theme 从主题 yaml 取配色注入结构里的装饰元素。
变换在 wewrite preview 之前做，渲染器会原样保留内联 HTML。

用法:
  PYTHONIOENCODING=utf-8 python apply_template.py in.md --template kazk-editorial -o out.md
  python apply_template.py in.md --template kazk-editorial --theme ai-practice -o out.md
  python apply_template.py in.md --template kazk-editorial --labels labels.json -o out.md

labels.json（可选，英文小标签由人/AI 判断，脚本不编）: {"小节标题": "WRITING / EMOTION"}
未提供时小节标签默认 "SECTION 01/02/..."。--theme 省略时用模板原生配色。

已注册模板:
  kazk-editorial  h2→幽灵数字小节  ---→三色圆点线  独立成段的图→四角裁切框+FIG编号
  bold-contrast   h2→编号前缀「01 /」(等宽强调色)
  qa-bubble       h2→「问」徽章+聊天气泡          适合 FAQ/测评
  timeline-log    h2→时间轴节点+下垂轴线          适合踩坑记录/过程日志
  knowledge-card  h2→编号知识卡（浅底圆角+数字章）  适合干货科普
  press           h2→「一、二、三」中文编号        适合深度分析（衬线版式靠 CSS）
"""

import argparse
import json
import os
import re
import sys
import urllib.parse
import yaml

# ---------------------------------------------------------------- 配色工具

def _mix(c1, c2, t):
    """c1 向 c2 混合 t（0=c1, 1=c2），输入输出都是 #rrggbb。"""
    c1 = c1.lstrip("#"); c2 = c2.lstrip("#")
    r1, g1, b1 = int(c1[0:2], 16), int(c1[2:4], 16), int(c1[4:6], 16)
    r2, g2, b2 = int(c2[0:2], 16), int(c2[2:4], 16), int(c2[4:6], 16)
    r = round(r1 + (r2 - r1) * t); g = round(g1 + (g2 - g1) * t); b = round(b1 + (b2 - b1) * t)
    return "#%02x%02x%02x" % (r, g, b)


def _luminance(c):
    c = c.lstrip("#")
    r, g, b = int(c[0:2], 16) / 255, int(c[2:4], 16) / 255, int(c[4:6], 16) / 255
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _darken_for_text(c, on_white=True):
    """浅色（如 kazk 的琥珀 #fde68a）直接当文字看不清，压深到可读。"""
    if _luminance(c) > 0.72:
        return _mix(c, "#111827" if on_white else "#ffffff", 0.45)
    return c


def _theme_file(name):
    home = os.environ.get("WEWRITE_HOME")
    if not home:
        raise SystemExit("环境变量 WEWRITE_HOME 未设置，无法定位主题目录")
    candidates = [
        os.path.join(home, "themes", name + ".yaml"),
        os.path.join(os.path.dirname(yaml.__file__), "..", "wewrite", "toolkit",
                     "themes", name + ".yaml"),
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    raise SystemExit("主题不存在: %s（找过 %s）" % (name, ", ".join(candidates)))


def load_palette(theme_name):
    """主题 yaml colors → 结构装饰用的调色板（模板层的取色约定）。"""
    with open(_theme_file(theme_name), encoding="utf-8") as f:
        colors = (yaml.safe_load(f).get("colors") or {})
    primary = colors.get("primary", "#059669")
    secondary = colors.get("secondary", "#d97706")
    text = colors.get("text", "#111827")
    caption = colors.get("text_caption") or colors.get("text_light", "#9ca3af")
    highlight = colors.get("highlight_bg") or _mix(secondary, "#ffffff", 0.55)
    return {
        "text": text,
        "heading": colors.get("text_heading", text),
        "caption": caption,
        "primary": primary,
        "secondary": _darken_for_text(secondary),
        "ghost": _mix(primary, "#ffffff", 0.82),
        "dots_mid": _mix(primary, "#ffffff", 0.5),
        "rail": _mix(primary, "#ffffff", 0.72),
        "fm": colors.get("background_light") or _mix(primary, "#ffffff", 0.94),
        "highlight": highlight,
        "quote_title_bg": _luminance(primary) > 0.72 and _darken_for_text(primary) or primary,
    }


# ---------------------------------------------------------------- 结构模板

def dots_divider(pal):
    return (
        '<section style="display:flex;align-items:center;justify-content:center;'
        'gap:10px;margin:28px 0;">'
        '<span style="display:inline-block;width:8px;height:8px;border-radius:50%%;'
        'background:%(primary)s;line-height:0;font-size:0;">&nbsp;</span>'
        '<span style="display:inline-block;width:8px;height:8px;border-radius:50%%;'
        'background:%(dots_mid)s;line-height:0;font-size:0;">&nbsp;</span>'
        '<span style="display:inline-block;width:8px;height:8px;border-radius:50%%;'
        'background:%(secondary)s;line-height:0;font-size:0;">&nbsp;</span>'
        '</section>' % pal
    )


def ghost_section(num, title, label, pal):
    return (
        '<section style="margin-top:48px;margin-bottom:24px;padding:0 12px;">'
        '<section style="display:flex;align-items:center;gap:12px;white-space:nowrap;">'
        '<p style="margin:0;font-size:60px;font-weight:900;font-style:italic;'
        'color:%(ghost)s;line-height:0.9;letter-spacing:-4px;">' % pal
        + num + "</p>"
        '<section>'
        '<p style="margin:0;font-size:18px;font-weight:900;color:%(heading)s;'
        'line-height:1.25;">' % pal + title + "</p>"
        '<p style="margin:4px 0 0 0;font-family:Menlo,Consolas,monospace;font-size:9px;'
        'font-weight:700;color:%(caption)s;line-height:1;letter-spacing:1.5px;">' % pal
        + label + "</p>"
        "</section></section></section>"
    )


def crop_frame(src, caption, fig, pal):
    # 渲染管线会给属性值里的中西文边界插空格，中英混排文件名会被改坏；
    # 对路径里的非 ASCII 字符做百分号编码后就没有中西边界了，浏览器会自动解码
    src = urllib.parse.quote(src, safe=":/?&=%#")
    edge = "2px solid %(text)s" % pal
    def bar(border):
        return ('<span style="display:block;width:28px;height:18px;%s;font-size:0;'
                'line-height:0;"><br/></span>' % border)
    tl = "top:%s;border-left:%s" % (edge, edge)
    tr = "top:%s;border-right:%s" % (edge, edge)
    bl = "bottom:%s;border-left:%s" % (edge, edge)
    br = "bottom:%s;border-right:%s" % (edge, edge)
    cap = dict(pal, fig=fig, caption=caption)
    return (
        '<section style="margin:24px 0;background:#ffffff;padding:0 8px;">'
        '<section style="display:flex;justify-content:space-between;margin-bottom:-9px;">'
        + bar(tl) + bar(tr) + "</section>"
        '<section style="margin:0 8px;border-radius:4px;overflow:hidden;line-height:0;">'
        '<img src="%(src)s" style="max-width:100%%;"/></section>' % dict(cap, src=src)
        + '<section style="display:flex;justify-content:space-between;margin-top:-9px;">'
        + bar(bl) + bar(br) + "</section>"
        '<section style="display:flex;justify-content:space-between;margin:7px 8px 0;">'
        '<span style="font-family:Menlo,Consolas,monospace;font-size:10px;font-weight:800;'
        'color:%(text)s;letter-spacing:1px;">FIG.%(fig)s</span>'
        '<span style="font-size:11px;font-weight:700;color:%(caption)s;text-align:right;'
        'line-height:1.4;">%(caption)s</span>'
        "</section></section>" % cap
    )


def numbered_h2(num, title, pal):
    return ('<h2><span style="font-family:Menlo,Consolas,monospace;font-weight:900;'
            'color:%(secondary)s;margin-right:10px;font-size:14px;">' % pal
            + num + " /</span>" + title + "</h2>")


def _frontmatter_iter(lines):
    """产出 (i, line)，自动跳过 YAML frontmatter 区域的 ---。"""
    in_fm = lines and lines[0].strip() == "---"
    for i, line in enumerate(lines):
        yield i, line, in_fm
        if in_fm and i > 0 and line.strip() == "---":
            in_fm = False


def transform_kazk(md, labels, pal):
    """h2→幽灵数字小节；---→圆点线；独立成段的图→裁切框。"""
    lines = md.split("\n")
    out, section_no, fig_no = [], 0, 0
    was_blank = False
    for i, line, in_fm in _frontmatter_iter(lines):
        stripped = line.strip()
        if in_fm:
            out.append(line); was_blank = stripped == ""; continue
        h2 = re.match(r"^##\s+(?!#)(.+?)\s*#*\s*$", line)
        img = re.match(r"^!\[([^\]]*)\]\(([^)]+)\)\s*$", stripped)
        if h2:
            section_no += 1
            title = h2.group(1).strip()
            label = labels.get(title, "SECTION %02d" % section_no)
            out.append(ghost_section("%02d" % section_no, title, label, pal))
        elif img:
            fig_no += 1
            out.append(crop_frame(img.group(2), img.group(1) or " ", "%02d" % fig_no, pal))
        elif stripped in ("---", "***", "___") and i > 0 and was_blank:
            out.append(dots_divider(pal))
        else:
            out.append(line)
        was_blank = stripped == ""
    return "\n".join(out), section_no, fig_no


def transform_bold(md, labels, pal):
    """h2→编号前缀；其余靠 CSS（黑底金句卡、短黑线 hr）。"""
    lines = md.split("\n")
    out, section_no = [], 0
    for i, line, in_fm in _frontmatter_iter(lines):
        if in_fm:
            out.append(line); continue
        h2 = re.match(r"^##\s+(?!#)(.+?)\s*#*\s*$", line)
        if h2:
            section_no += 1
            out.append(numbered_h2("%02d" % section_no, h2.group(1).strip(), pal))
        else:
            out.append(line)
    return "\n".join(out), section_no, 0


CN_NUM = ["零", "一", "二", "三", "四", "五", "六", "七", "八", "九", "十",
          "十一", "十二", "十三", "十四", "十五", "十六", "十七", "十八", "十九", "二十"]


def transform_qa(md, labels, pal):
    """h2→「问」徽章 + 聊天气泡；适合一问一答结构。"""
    lines = md.split("\n")
    out, section_no = [], 0
    for i, line, in_fm in _frontmatter_iter(lines):
        if in_fm:
            out.append(line); continue
        h2 = re.match(r"^##\s+(?!#)(.+?)\s*#*\s*$", line)
        if h2:
            section_no += 1
            out.append(
                '<section style="display:flex;align-items:flex-start;gap:10px;margin:32px 0 14px;">'
                '<span style="flex-shrink:0;display:inline-block;width:24px;height:24px;'
                'border-radius:50%%;background:%(primary)s;color:#ffffff;font-size:13px;'
                'font-weight:700;line-height:24px;text-align:center;">问</span>' % pal
                + '<section style="flex:1;background:%(fm)s;border-radius:2px 10px 10px 10px;'
                'padding:10px 14px;">' % pal
                + '<p style="margin:0;font-size:15px;font-weight:800;color:%(heading)s;'
                'line-height:1.6;">' % pal + h2.group(1).strip() + "</p></section></section>"
            )
        else:
            out.append(line)
    return "\n".join(out), section_no, 0


def transform_timeline(md, labels, pal):
    """h2→时间轴节点（圆点+下垂轴线）；适合按时间推进的记录。"""
    lines = md.split("\n")
    out, section_no = [], 0
    for i, line, in_fm in _frontmatter_iter(lines):
        if in_fm:
            out.append(line); continue
        h2 = re.match(r"^##\s+(?!#)(.+?)\s*#*\s*$", line)
        if h2:
            section_no += 1
            out.append(
                '<section style="display:flex;align-items:center;gap:10px;margin:36px 0 0;">'
                '<span style="flex-shrink:0;display:inline-block;width:12px;height:12px;'
                'border-radius:50%%;background:%(primary)s;line-height:0;font-size:0;">&nbsp;</span>' % pal
                + '<p style="margin:0;font-size:16px;font-weight:800;color:%(heading)s;'
                'line-height:1.5;">' % pal + h2.group(1).strip() + "</p></section>"
                + '<section style="margin:8px 0 0 5px;width:0;height:20px;'
                'border-left:2px solid %(rail)s;line-height:0;font-size:0;">&nbsp;</section>' % pal
            )
        else:
            out.append(line)
    return "\n".join(out), section_no, 0


def transform_knowledge(md, labels, pal):
    """h2→编号知识卡（浅底圆角条 + 数字章）；适合知识点密集的干货。"""
    lines = md.split("\n")
    out, section_no = [], 0
    for i, line, in_fm in _frontmatter_iter(lines):
        if in_fm:
            out.append(line); continue
        h2 = re.match(r"^##\s+(?!#)(.+?)\s*#*\s*$", line)
        if h2:
            section_no += 1
            out.append(
                '<section style="background:%(fm)s;border-radius:8px;padding:10px 14px;'
                'margin:30px 0 14px;display:flex;align-items:center;gap:10px;">' % pal
                + '<span style="flex-shrink:0;font-family:Menlo,Consolas,monospace;font-size:12px;'
                'font-weight:800;color:#ffffff;background:%(primary)s;border-radius:4px;'
                'padding:2px 7px;">' % pal + "%02d" % section_no + "</span>"
                + '<p style="margin:0;font-size:15px;font-weight:800;color:%(heading)s;'
                'line-height:1.5;">' % pal + h2.group(1).strip() + "</p></section>"
            )
        else:
            out.append(line)
    return "\n".join(out), section_no, 0


def transform_press(md, labels, pal):
    """h2→「一、二、三」中文编号（衬线版式靠主题 CSS）。"""
    lines = md.split("\n")
    out, section_no = [], 0
    for i, line, in_fm in _frontmatter_iter(lines):
        if in_fm:
            out.append(line); continue
        h2 = re.match(r"^##\s+(?!#)(.+?)\s*#*\s*$", line)
        if h2:
            section_no += 1
            num = CN_NUM[section_no] if section_no < len(CN_NUM) else str(section_no)
            out.append("<h2>" + num + "、" + h2.group(1).strip() + "</h2>")
        else:
            out.append(line)
    return "\n".join(out), section_no, 0


TEMPLATES = {
    "kazk-editorial": (transform_kazk, "kazk-editorial"),
    "bold-contrast": (transform_bold, "bold-contrast"),
    "qa-bubble": (transform_qa, "qa-bubble"),
    "timeline-log": (transform_timeline, "timeline-log"),
    "knowledge-card": (transform_knowledge, "knowledge-card"),
    "press": (transform_press, "press"),
}


def main():
    ap = argparse.ArgumentParser(description="把 markdown 重写成模板版式结构（渲染前跑）")
    ap.add_argument("input")
    ap.add_argument("--template", required=True, choices=sorted(TEMPLATES))
    ap.add_argument("--theme", help="配色来源主题名（默认=模板原生主题）")
    ap.add_argument("--labels", help="h2 标题→英文小标签的 JSON（内联或文件路径）；缺省 SECTION 0N")
    ap.add_argument("-o", "--output", required=True)
    args = ap.parse_args()

    labels = {}
    if args.labels:
        raw = args.labels.strip()
        if raw.startswith("{"):
            labels = json.loads(raw)
        else:
            with open(args.labels, encoding="utf-8") as f:
                labels = json.load(f)

    default_theme = TEMPLATES[args.template][1]
    pal = load_palette(args.theme or default_theme)
    if _luminance(pal["text"]) > 0.55:
        print("警告: 该主题是暗色皮肤（浅色文字），微信正文默认白底，结构装饰会看不清；"
              "建议改配浅色主题。", file=sys.stderr)

    with open(args.input, encoding="utf-8") as f:
        md = f.read()

    transform = TEMPLATES[args.template][0]
    result, sections, figs = transform(md, labels, pal)

    with open(args.output, "w", encoding="utf-8") as f:
        f.write(result)
    print("%s × %s: %d 个小节, %d 张图 → %s"
          % (args.template, args.theme or default_theme, sections, figs, args.output))


if __name__ == "__main__":
    sys.exit(main())
