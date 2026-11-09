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
  kazk-editorial     h2→幽灵数字小节  ---→三色圆点线  独立成段的图→四角裁切框+FIG编号
  bold-contrast      h2→编号前缀「01 /」(等宽强调色)
  qa-bubble          h2→「问」徽章+聊天气泡          适合 FAQ/测评
  timeline-log       h2→时间轴节点+下垂轴线          适合踩坑记录/过程日志
  knowledge-card     h2→编号知识卡（浅底圆角+数字章）  适合干货科普
  press              h2→「一、二、三」中文编号        适合深度分析（衬线版式靠 CSS）
  tutorial-dashboard Hero 教程仪表盘 + 横向路线图 + PART/STEP 标记 + 提示卡
  muppet-editorial   刊头细线 + 炭黑信息条 + PART 编号小节 + pill 小标题 + Step 徽章
                     + 虚线图框 + 卡片表格（适合福利/简报/清单）
  chengzi-benefit    渐变标题条 + 圆点徽章小节头（01/02…）+ 珊瑚橙重点下划线
                     + 胶囊引导条 + 引用提示卡（适合福利/活动/清单汇总）
"""

import argparse
import html
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
    background = colors.get("background", "#ffffff")
    background_light = colors.get("background_light") or _mix(primary, background, 0.94)
    return {
        "text": text,
        "heading": colors.get("text_heading", text),
        "caption": caption,
        "primary": primary,
        "secondary": _darken_for_text(secondary),
        "background": background,
        "background_light": background_light,
        "ghost": _mix(primary, "#ffffff", 0.82),
        "dots_mid": _mix(primary, "#ffffff", 0.5),
        "rail": _mix(primary, "#ffffff", 0.72),
        "fm": colors.get("background_light") or _mix(primary, background, 0.94),
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
        '<section style="display:flex;align-items:flex-start;gap:10px;">'
        '<p style="margin:0;flex:0 0 auto;font-size:56px;font-weight:900;font-style:italic;'
        'color:%(ghost)s;line-height:0.9;letter-spacing:-3px;">' % pal
        + num + "</p>"
        '<section style="flex:1 1 auto;min-width:0;">'
        '<p style="margin:0;font-size:18px;font-weight:900;color:%(heading)s;'
        'line-height:1.25;word-break:break-word;">' % pal + title + "</p>"
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
    cap = dict(pal, fig=fig, caption=caption, background=pal.get("background", "#ffffff"))
    return (
        '<section style="margin:24px 0;background:%(background)s;padding:0 8px;">'
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


# ---------------------------------------------------------------- chengzi-benefit

def gradient_lead(pal, kicker, headline):
    """渐变标题条：小标签 + 大标题，天蓝→珊瑚橙对角渐变。"""
    return (
        '<section style="border-radius:12px;padding:18px 20px 16px;margin:0 0 18px;'
        'background-image:linear-gradient(135deg,%(primary)s 0%%,%(secondary)s 100%%);'
        'box-sizing:border-box;">' % pal
        + '<p style="margin:0 0 6px;font-size:11px;font-weight:800;letter-spacing:2px;'
        'color:rgba(255,255,255,.82);">' + (kicker or "LEAD / 导语") + "</p>"
        + '<p style="margin:0;font-size:21px;font-weight:900;line-height:1.35;'
        'color:#ffffff;">' + headline + "</p></section>"
    )


def pill_lead(text, pal):
    """胶囊引导条：圆点 + 强调色文字，用于「为自己而坚持 / 超强安利！」这类短引导。

    圆点用 inline-block + vertical-align 对齐，不依赖 flex——微信编辑器粘贴时会
    丢掉 flex 容器布局。
    """
    return (
        '<section style="margin:0 0 14px;line-height:1.6;">'
        '<span style="display:inline-block;width:8px;height:8px;border-radius:50%%;'
        'background:%(secondary)s;vertical-align:2px;margin-right:8px;'
        'line-height:0;font-size:0;">&nbsp;</span>' % pal
        + '<span style="font-size:15px;font-weight:700;color:%(primary)s;">' % pal
        + text + "</span></section>"
    )


def badge_section(num, title, label, pal):
    """圆点徽章小节头：蓝色圆点（编号）+ 天蓝大标题 + 灰色英文小标签。

    圆点与文字用 inline-block + vertical-align:top 并排，不依赖 flex；文字包一层
    inline-block 限制宽度，标签才能在自己的行上换行。
    """
    return (
        '<section style="margin:34px 0 14px;">'
        '<span style="display:inline-block;width:26px;height:26px;border-radius:50%%;'
        'background:%(primary)s;color:#ffffff;font-size:13px;font-weight:800;'
        'line-height:26px;text-align:center;vertical-align:top;margin-right:10px;">' % pal
        + num + "</span>"
        + '<span style="display:inline-block;vertical-align:top;max-width:calc(100% - 40px);">'
        + '<span style="display:block;font-size:17px;font-weight:800;color:%(heading)s;'
        'line-height:1.5;">' % pal + title + "</span>"
        + '<span style="display:block;margin-top:4px;font-size:10px;font-weight:700;'
        'letter-spacing:1.6px;color:%(caption)s;">' % pal + label + "</span>"
        + "</span></section>"
    )


def coral_underline(text, pal):
    """珊瑚橙重点下划线：用于一句话总结、金句。"""
    return (
        '<span style="font-weight:800;color:%(heading)s;border-bottom:3px solid %(secondary)s;'
        'padding-bottom:1px;">' % pal + text + "</span>"
    )


def transform_chengzi(md, labels, pal):
    """h2→圆点徽章小节头；独立成段的 **短句**→胶囊引导条；引用→提示卡。

    源文章特征（考研英语外刊阅读 / 大橙子）：天蓝 #89CEEA + 珊瑚橙 #F86B4A 双色，
    渐变标题条、圆点字徽章（不负青春）、珊瑚橙下划线重点。
    """
    lines = md.split("\n")
    out, section_no = [], 0
    kicker = None
    headline = None
    for i, line, in_fm in _frontmatter_iter(lines):
        stripped = line.strip()
        if in_fm:
            # 从 frontmatter 取 chengzi.kicker / chengzi.headline
            m_k = re.match(r"^\s*kicker:\s*(.+?)\s*$", line)
            m_h = re.match(r"^\s*headline:\s*(.+?)\s*$", line)
            if m_k:
                kicker = m_k.group(1).strip().strip("\"'")
            elif m_h:
                headline = m_h.group(1).strip().strip("\"'")
            out.append(line)
            continue
        h2 = re.match(r"^##\s+(?!#)(.+?)\s*#*\s*$", line)
        # 独立成段的加粗短句 → 胶囊引导条
        pill = re.match(r"^\*\*(.{1,20}?)\*\*[!！。.~]?$", stripped)
        if h2:
            section_no += 1
            title = h2.group(1).strip()
            label = labels.get(title, "SECTION %02d" % section_no)
            out.append(badge_section("%02d" % section_no, title, label, pal))
        elif pill:
            out.append(pill_lead(pill.group(1).strip(), pal))
        else:
            out.append(line)
    # 有 headline 时，在 frontmatter 之后插入渐变标题条（不能插到 frontmatter 前，否则失效）
    if headline:
        insert_at = 0
        if out and out[0].strip() == "---":
            for k in range(1, len(out)):
                if out[k].strip() == "---":
                    insert_at = k + 1
                    break
        out.insert(insert_at, gradient_lead(pal, kicker, headline))
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


# ----------------------------------------------------------- 教程仪表盘模板

def _split_frontmatter(md):
    """保留原 frontmatter，同时读取 tutorial_dashboard 的结构配置。"""
    lines = md.split("\n")
    if not lines or lines[0].strip() != "---":
        return "", lines, {}

    for index in range(1, len(lines)):
        if lines[index].strip() != "---":
            continue
        data = yaml.safe_load("\n".join(lines[1:index])) or {}
        if not isinstance(data, dict):
            raise SystemExit("YAML frontmatter 必须是对象")
        return "\n".join(lines[:index + 1]), lines[index + 1:], data

    return "", lines, {}


def _dashboard_plain_text(value):
    """去掉 markdown 标记并折叠空白，不做 HTML 转义（供估宽等内部计算用）。"""
    if value is None:
        return ""
    text = str(value).strip()
    text = re.sub(r"!\[([^\]]*)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"[`*_]+", "", text)
    return re.sub(r"\s+", " ", text).strip()


def _dashboard_text(value):
    """将模板配置和标题转成安全的纯文本，避免模板注入原始 HTML。"""
    return html.escape(_dashboard_plain_text(value), quote=True)


def _dashboard_on_color(color):
    return "#111827" if _luminance(color) > 0.58 else "#ffffff"


def _dashboard_palette(pal):
    """只从传入主题取色，让结构模板可跨主题复用。"""
    primary = pal["primary"]
    secondary = pal["secondary"]
    surface = pal.get("background", "#ffffff")
    surface_alt = pal.get("background_light") or _mix(primary, surface, 0.94)
    return dict(
        pal,
        surface=surface,
        surface_alt=surface_alt,
        primary_deep=_mix(primary, "#111827", 0.24),
        primary_fresh=_mix(primary, surface, 0.12),
        primary_soft=_mix(primary, surface, 0.93),
        primary_mid=_mix(primary, surface, 0.76),
        secondary_soft=_mix(secondary, surface, 0.87),
        secondary_panel=_mix(secondary, surface, 0.90),
        secondary_border=_mix(secondary, surface, 0.68),
        secondary_text=_darken_for_text(secondary),
        danger=_mix(secondary, "#991b1b", 0.50),
        border=_mix(primary, surface, 0.68),
        panel=surface_alt,
        on_primary=_dashboard_on_color(primary),
        on_primary_muted=_mix(_dashboard_on_color(primary), primary, 0.28),
    )


def _tutorial_dashboard_settings(frontmatter):
    settings = frontmatter.get("tutorial_dashboard") or {}
    if not isinstance(settings, dict):
        raise SystemExit("tutorial_dashboard frontmatter 必须是对象")
    return settings


def _dashboard_section_label(title, section_no, labels, settings):
    configured = settings.get("section_labels") or {}
    if not isinstance(configured, dict):
        raise SystemExit("tutorial_dashboard.section_labels 必须是对象")
    label = configured.get(title) or labels.get(title) or "SECTION %02d" % section_no
    return _dashboard_text(label)


def _dashboard_is_closing(title, label=""):
    return bool(re.search(r"(?:最后|结语|总结|写在最后|结尾)", str(title))) or bool(
        re.search(r"(?:SUMMARY|CONCLUSION|LAST)", str(label), re.I)
    )


def _dashboard_roadmap_items(section_entries, labels, settings):
    configured = settings.get("roadmap")
    if configured is not None:
        if not isinstance(configured, list):
            raise SystemExit("tutorial_dashboard.roadmap 必须是列表")
        items = []
        for index, item in enumerate(configured, start=1):
            if isinstance(item, dict):
                title = item.get("title")
                label = item.get("label") or item.get("meta")
                is_last = bool(item.get("last") or item.get("conclusion"))
            else:
                title = item
                label = None
                is_last = False
            if not title:
                continue
            title_text = str(title)
            closing = is_last or _dashboard_is_closing(title_text, label or "")
            items.append((title_text, _dashboard_text(label or ("SUMMARY" if closing else "PART %02d" % index)), closing))
        if items:
            return items

    items = []
    for index, entry in enumerate(section_entries, start=1):
        if isinstance(entry, (tuple, list)):
            values = list(entry) + [None, False]
            title, source_label, source_closing = values[:3]
        else:
            title, source_label, source_closing = entry, None, False
        closing = bool(source_closing) or _dashboard_is_closing(title, source_label or "")
        label = _dashboard_text(source_label) if source_label else _dashboard_section_label(title, index, labels, settings)
        items.append((title, label, closing))

    # summary/closing 是可选配置，但一旦存在，路线图也应明确告诉读者还有收尾段。
    if items and not any(item[2] for item in items):
        summary = _dashboard_block(settings, "summary")
        closing_config = settings.get("closing")
        if summary is not None or closing_config:
            route_title = "写在最后"
            route_label = "SUMMARY"
            source = summary if isinstance(summary, dict) else closing_config
            if isinstance(source, dict):
                route_title = source.get("roadmap_title") or source.get("route_title") or source.get("title") or route_title
                route_label = source.get("roadmap_label") or source.get("route_label") or source.get("label") or route_label
            items.append((str(route_title), _dashboard_text(route_label), True))
    return items


def tutorial_dashboard_hero(title, settings, pal):
    """首屏信息卡：教程分类、承诺、标题、色带与标签。"""
    eyebrow = _dashboard_text(settings.get("eyebrow") or "TUTORIAL / GUIDE")
    issue = _dashboard_text(settings.get("issue") or "PRACTICAL")
    question = _dashboard_text(settings.get("question"))
    subtitle = _dashboard_text(settings.get("subtitle"))
    ribbon = _dashboard_text(settings.get("ribbon") or "实操教程")
    accent = _dashboard_text(settings.get("accent"))
    title_lines = settings.get("title_lines")
    if title_lines is not None:
        if isinstance(title_lines, str):
            title_lines = [title_lines]
        if not isinstance(title_lines, list):
            raise SystemExit("tutorial_dashboard.title_lines 必须是列表或字符串")
        title_parts = [_dashboard_text(line) for line in title_lines if _dashboard_text(line)]
    else:
        title_parts = [_dashboard_text(title)]
    title_html = "<br/>".join(title_parts)
    if accent and title_html:
        title_html = title_html.replace(
            accent,
            '<span style="color:%s;">%s</span>' % (pal["primary"], accent),
        )

    question_html = (
        '<p style="font-size:14px;color:%s;margin:0 0 6px;text-decoration:line-through;'
        'letter-spacing:.4px;">%s</p>' % (pal["caption"], question)
        if question else ""
    )
    subtitle_html = (
        '<p style="font-size:13px;color:%s;margin:12px 0 0;line-height:1.7;letter-spacing:.4px;">%s</p>'
        % (pal["caption"], subtitle)
        if subtitle else ""
    )
    tags = settings.get("tags") or []
    if isinstance(tags, str):
        tags = [tags]
    if not isinstance(tags, list):
        raise SystemExit("tutorial_dashboard.tags 必须是列表或字符串")
    tag_html = "".join(
        '<span style="display:inline-block;background:rgba(255,255,255,.20);padding:2px 6px;'
        'border-radius:3px;font-size:9px;color:%s;font-weight:700;">%s</span>'
        % (pal["on_primary"], _dashboard_text(tag))
        for tag in tags if _dashboard_text(tag)
    )
    tags_row = (
        '<section style="display:flex;gap:4px;align-items:center;flex-wrap:wrap;justify-content:flex-end;">%s</section>' % tag_html
        if tag_html else ""
    )

    return (
        '<section data-template="tutorial-dashboard" style="margin:8px 0 24px;border:1.5px solid %s;'
        'border-radius:18px;overflow:hidden;background:%s;box-shadow:0 4px 20px rgba(0,0,0,.06);">'
        % (pal["border"], pal["surface"])
        + '<section style="padding:28px 24px 24px;">'
        + '<section style="display:flex;align-items:center;gap:8px;margin-bottom:24px;">'
        + '<span style="font-size:10px;font-weight:800;letter-spacing:2.4px;color:%s;">%s</span>'
        % (pal["primary"], eyebrow)
        + '<span style="flex:1;height:1px;background:%s;line-height:0;font-size:0;">&nbsp;</span>'
        % pal["primary_mid"]
        + '<span style="font-size:10px;color:%s;font-weight:700;">%s</span>' % (pal["caption"], issue)
        + '</section>'
        + question_html
        + '<p style="font-size:24px;font-weight:900;color:%s;margin:0;line-height:1.14;letter-spacing:.2px;word-break:break-word;">%s</p>'
        % (pal["heading"], title_html)
        + '<section style="width:48px;height:3px;background:%s;border-radius:2px;margin:14px 0 0;line-height:0;font-size:0;">&nbsp;</section>'
        % pal["primary"]
        + subtitle_html
        + '</section>'
        + '<section style="background:linear-gradient(135deg,%s,%s);padding:11px 24px;display:flex;'
        'align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap;">' % (pal["primary_deep"], pal["primary"])
        + '<p style="font-size:12px;color:%s;margin:0;font-weight:700;letter-spacing:.4px;">%s</p>'
        % (pal["on_primary"], ribbon)
        + tags_row
        + '</section></section>'
    )


def tutorial_dashboard_roadmap(items, pal):
    """以横向可滚动的 PART 卡片预告教程路径。"""
    if not items:
        return ""

    cards = []
    for index, item in enumerate(items, start=1):
        if len(item) == 3:
            title, label, closing = item
        else:
            title, label = item
            closing = False
        active = index == 1
        if active:
            card_style = (
                'background:linear-gradient(135deg,%s,%s);border:1px solid %s;' %
                (pal["primary_deep"], pal["primary"], pal["primary"])
            )
            top_color = pal["on_primary_muted"]
            title_color = pal["on_primary"]
            meta_color = pal["on_primary_muted"]
        else:
            card_style = 'background:%s;border:1px solid %s;box-shadow:0 2px 6px rgba(0,0,0,.04);' % (pal["surface"], pal["border"])

            top_color = pal["caption"]
            title_color = pal["heading"]
            meta_color = pal["caption"]
        marker = "PART ///" if closing else "PART %02d" % index
        cards.append(
            '<section style="flex:0 0 122px;width:122px;white-space:normal;border-radius:10px;padding:11px;%s">' % card_style
            + '<p style="font-size:9px;font-weight:800;color:%s;letter-spacing:1px;margin:0 0 5px;">%s</p>'
            % (top_color, marker)
            + '<p style="font-size:13px;font-weight:800;color:%s;margin:0 0 3px;line-height:1.35;word-break:break-word;">%s</p>'
            % (title_color, _dashboard_text(title))
            + '<p style="font-size:9px;color:%s;margin:0;line-height:1.45;word-break:break-word;">%s</p>' % (meta_color, label)
            + '</section>'
        )

    part_count = sum(not (len(item) == 3 and item[2]) for item in items)
    conclusion_count = len(items) - part_count
    route_label = "ROUTE / %d PARTS" % part_count
    if conclusion_count:
        route_label += " + CONCLUSION"
    return (
        '<section data-template="tutorial-dashboard-roadmap" style="margin:0 0 20px;">'
        '<section style="display:flex;align-items:center;justify-content:space-between;margin:0 0 9px;">'
        '<p style="font-size:10px;color:%s;margin:0;text-transform:uppercase;letter-spacing:1.8px;font-weight:700;">%s</p>'
        % (pal["caption"], route_label)
        + '<p style="font-size:10px;color:%s;margin:0;">SCROLL</p></section>' % pal["caption"]
        + '<section style="display:flex;align-items:stretch;gap:8px;overflow-x:auto;padding:0 0 8px;">%s</section></section>' % "".join(cards)
    )


def _dashboard_blocks(settings):
    blocks = settings.get("blocks") or {}
    if not isinstance(blocks, dict):
        raise SystemExit("tutorial_dashboard.blocks 必须是对象")
    return blocks


def _dashboard_block(settings, name):
    """读取 block，兼容 kebab-case、snake_case 和顶层简写。"""
    blocks = _dashboard_blocks(settings)
    aliases = (name, name.replace("-", "_"))
    for key in aliases:
        if key in blocks:
            return blocks[key]
    for key in aliases:
        if key in settings:
            return settings[key]
    return None


def _dashboard_item(item, title_key="title"):
    if isinstance(item, dict):
        title = item.get(title_key) or item.get("text") or item.get("label")
        body = item.get("text") if title_key != "text" else item.get("body")
        meta = item.get("meta") or item.get("label")
        return title, body, meta, item.get("tone")
    return item, None, None, None


def _dashboard_items(block, keys=("items",)):
    if not isinstance(block, dict):
        return []
    for key in keys:
        value = block.get(key)
        if value is None:
            continue
        if isinstance(value, str):
            return [value]
        if not isinstance(value, list):
            raise SystemExit("tutorial_dashboard.%s 必须是列表或字符串" % key)
        return value
    return []


def tutorial_dashboard_problem(block, pal):
    """问题对比卡：复原参考文中的浅黄虚线「先说人话」面板。"""
    if not block:
        return ""
    if isinstance(block, str):
        block = {"emphasis": block}
    if not isinstance(block, dict):
        raise SystemExit("tutorial_dashboard.blocks.problem 必须是对象或字符串")
    title = _dashboard_text(block.get("title") or "先说人话")
    items = _dashboard_items(block)
    emphasis = _dashboard_text(block.get("emphasis") or block.get("highlight"))
    item_html = "".join(
        '<p style="font-size:13px;color:%s;margin:0;line-height:1.9;">%s</p>'
        % (pal["text"], _dashboard_text(item.get("text") if isinstance(item, dict) else item))
        for item in items if _dashboard_text(item.get("text") if isinstance(item, dict) else item)
    )
    emphasis_html = (
        '<p style="font-size:13px;color:%s;margin:0;line-height:1.9;font-weight:800;">%s</p>'
        % (pal["danger"], emphasis)
        if emphasis else ""
    )
    if not item_html and not emphasis_html:
        return ""
    return (
        '<section data-template="tutorial-dashboard-problem" style="margin:0 0 18px;background:%s;'
        'border:1px dashed %s;border-radius:8px;padding:12px 16px;text-align:left;">'
        % (pal["secondary_panel"], pal["secondary_border"])
        + '<p style="font-size:10px;font-family:Menlo,Consolas,monospace;font-weight:800;'
        'letter-spacing:1.2px;color:%s;margin:0 0 6px;">%s</p>' % (pal["secondary_text"], title)
        + item_html + emphasis_html
        + '</section>'
    )


def tutorial_dashboard_tag_cloud(block, pal):
    """厂商/工具标签云：暖色首组、白底次组、实色收尾标签。"""
    if not block:
        return ""
    if isinstance(block, list):
        block = {"items": block}
    if not isinstance(block, dict):
        raise SystemExit("tutorial_dashboard.blocks.tag_cloud 必须是对象或列表")
    title = _dashboard_text(block.get("title") or "已接入的工具 · 部分名单")
    note = _dashboard_text(block.get("note") or block.get("caption"))
    items = _dashboard_items(block, ("items", "tags"))
    tags = []
    for index, item in enumerate(items):
        text, _, _, tone = _dashboard_item(item, "text")
        text = _dashboard_text(text)
        if not text:
            continue
        tone = (tone or ("warm" if index < 4 else "default")).lower()
        if tone in ("primary", "active", "accent"):
            style = 'background:%s;border:1px solid %s;color:%s;font-weight:800;' % (
                pal["primary"], pal["primary"], pal["on_primary"])
        elif tone in ("warm", "secondary", "hot"):
            style = 'background:%s;border:1px solid %s;color:%s;font-weight:800;' % (
                pal["secondary_panel"], pal["secondary_border"], pal["secondary_text"])
        else:
            style = 'background:%s;border:1px solid %s;color:%s;font-weight:700;' % (
                pal["surface"], pal["border"], pal["primary_deep"])

        tags.append(
            '<span style="display:inline-block;margin:3px;padding:3px 10px;border-radius:6px;'
            'font-size:12px;line-height:1.4;%s">%s</span>' % (style, text)
        )
    if not tags:
        return ""
    note_html = (
        '<p style="font-size:11px;color:%s;text-align:center;margin:8px 0 0;line-height:1.6;">%s</p>'
        % (pal["caption"], note)
        if note else ""
    )
    return (
        '<section data-template="tutorial-dashboard-tag-cloud" style="margin:0 0 8px;padding:14px 6px 10px;'
        'background:%s;border:1px solid %s;border-radius:12px;text-align:center;">'
        % (pal["panel"], pal["border"])
        + '<p style="font-size:11px;font-weight:800;color:%s;letter-spacing:1.8px;margin:0 0 7px;">%s</p>'
        % (pal["primary_deep"], title)
        + '<section style="text-align:center;line-height:2.35;">%s</section>' % "".join(tags)
        + note_html
        + '</section>'
    )


def tutorial_dashboard_stats(block, pal):
    """统计签名行，保持参考文中标签云下方的轻量数据注脚。"""
    if not block:
        return ""
    if isinstance(block, str):
        text = block
    elif isinstance(block, dict):
        text = block.get("text") or block.get("value") or block.get("note")
    else:
        raise SystemExit("tutorial_dashboard.blocks.stats 必须是对象或字符串")
    text = _dashboard_text(text)
    if not text:
        return ""
    return (
        '<p data-template="tutorial-dashboard-stats" style="font-size:12px;color:%s;text-align:center;'
        'margin:0 0 20px;line-height:1.6;">— %s —</p>' % (pal["caption"], text)
    )


def tutorial_dashboard_flow(block, pal):
    """三段流程条：卡片、箭头、卡片，适合放在首屏之后。"""
    if not block:
        return ""
    if isinstance(block, list):
        block = {"items": block}
    if not isinstance(block, dict):
        raise SystemExit("tutorial_dashboard.blocks.flow 必须是对象或列表")
    items = _dashboard_items(block)
    cards = []
    for index, item in enumerate(items):
        title, body, meta, _ = _dashboard_item(item)
        title = _dashboard_text(title)
        body = _dashboard_text(body or meta)
        if not title:
            continue
        active = index == 0
        if active:
            card = (
                'background:linear-gradient(135deg,%s,%s);border:1px solid %s;'
                % (pal["primary_deep"], pal["primary"], pal["primary"])
            )
            title_color = pal["on_primary"]
            body_color = pal["on_primary_muted"]
        else:
            card = 'background:%s;border:1px solid %s;' % (pal["surface"], pal["border"])

            title_color = pal["heading"]
            body_color = pal["caption"]
        if cards:
            cards.append(
                '<span style="display:flex;align-items:center;color:%s;font-size:14px;padding:0 2px;">→</span>'
                % pal["caption"]
            )
        cards.append(
            '<section style="flex:0 0 96px;min-width:96px;text-align:center;padding:10px 7px;border-radius:8px;%s">'
            % card
            + '<p style="font-size:13px;font-weight:800;color:%s;margin:0 0 3px;line-height:1.35;">%s</p>'
            % (title_color, title)
            + '<p style="font-size:10px;color:%s;margin:0;line-height:1.5;word-break:break-word;">%s</p>'
            % (body_color, body)
            + '</section>'
        )
    if not cards:
        return ""
    note = _dashboard_text(block.get("note") or block.get("caption"))
    note_html = (
        '<p style="font-size:12px;color:%s;text-align:center;margin:12px 0 0;letter-spacing:.4px;">%s</p>'
        % (pal["caption"], note)
        if note else ""
    )
    return (
        '<section data-template="tutorial-dashboard-flow" style="margin:0 0 22px;background:%s;'
        'padding:16px;border-radius:12px;border:1px solid %s;">'
        % (pal["panel"], pal["border"])
        + '<section style="display:flex;align-items:stretch;justify-content:center;gap:6px;overflow-x:auto;padding-bottom:4px;">'
        + "".join(cards) + '</section>' + note_html + '</section>'
    )


def tutorial_dashboard_connection(block, pal):
    """地址 / Key / 模型三联卡，复原教程中的「万能钥匙」信息块。"""
    if not block:
        return ""
    if isinstance(block, list):
        block = {"items": block}
    if not isinstance(block, dict):
        raise SystemExit("tutorial_dashboard.blocks.connection 必须是对象或列表")
    title = _dashboard_text(block.get("title") or "以后任何工具来问你「AI 怎么接」，答案都是这三样")
    note = _dashboard_text(block.get("note") or block.get("caption"))
    items = _dashboard_items(block)
    cards = []
    for index, item in enumerate(items):
        name, value, meta, _ = _dashboard_item(item)
        name = _dashboard_text(name)
        value = _dashboard_text(value or meta)
        if not name and not value:
            continue
        if index == 0:
            card_style = 'background:linear-gradient(135deg,%s,%s);border:1px solid %s;' % (
                pal["primary_deep"], pal["primary"], pal["primary"])
            name_color, value_color = pal["on_primary"], pal["on_primary_muted"]
        else:
            card_style = 'background:%s;border:1px solid %s;' % (pal["surface"], pal["border"])

            name_color, value_color = pal["heading"], pal["text"]
        cards.append(
            '<section style="flex:0 0 112px;min-width:112px;text-align:center;padding:10px 8px;border-radius:8px;%s">'
            % card_style
            + '<p style="font-size:11px;font-weight:800;color:%s;margin:0 0 4px;line-height:1.4;">%s</p>'
            % (name_color, name)
            + '<p style="font-family:Menlo,Consolas,monospace;font-size:10px;color:%s;margin:0;line-height:1.45;word-break:break-all;">%s</p>'
            % (value_color, value)
            + '</section>'
        )
    if not cards:
        return ""
    note_html = (
        '<p style="font-size:11px;color:%s;text-align:center;margin:11px 0 0;line-height:1.6;">%s</p>'
        % (pal["caption"], note)
        if note else ""
    )
    return (
        '<section data-template="tutorial-dashboard-connection" style="margin:0 0 22px;background:%s;'
        'padding:14px 10px;border-radius:12px;border:1px solid %s;">'
        % (pal["panel"], pal["border"])
        + '<p style="font-size:12px;color:%s;font-weight:800;text-align:center;margin:0 0 10px;line-height:1.6;">%s</p>'
        % (pal["primary_deep"], title)
        + '<section style="display:flex;align-items:stretch;justify-content:center;gap:6px;overflow-x:auto;padding-bottom:4px;">%s</section>' % "".join(cards)

        + note_html + '</section>'
    )


def tutorial_dashboard_truths(block, pal):
    """编号真相清单：圆形数字章 + 可选粗体小标题。"""
    if not block:
        return ""
    if isinstance(block, list):
        block = {"items": block}
    if not isinstance(block, dict):
        raise SystemExit("tutorial_dashboard.blocks.truths 必须是对象或列表")
    title = _dashboard_text(block.get("title") or "开始前的几个提醒")
    items = _dashboard_items(block)
    rows = []
    for index, item in enumerate(items, start=1):
        item_title, body, _, _ = _dashboard_item(item)
        if isinstance(item, dict):
            item_title = _dashboard_text(item_title)
            body = _dashboard_text(body)
            if body and item_title and body != item_title:
                content = '<strong style="color:%s;font-weight:800;">%s</strong>：%s' % (
                    pal["primary_deep"], item_title, body)
            else:
                content = item_title or body
        else:
            raw = _dashboard_text(item_title)
            match = re.match(r"^([^：:]{1,18})[：:](.+)$", raw)
            if match:
                content = '<strong style="color:%s;font-weight:800;">%s</strong>：%s' % (
                    pal["primary_deep"], match.group(1), match.group(2))
            else:
                content = raw
        if not content:
            continue
        rows.append(
            '<section style="display:flex;align-items:flex-start;gap:10px;margin:0 0 12px;">'
            '<span style="display:inline-flex;align-items:center;justify-content:center;width:22px;height:22px;'
            'background:%s;color:%s;font-size:11px;font-weight:800;border-radius:50%%;flex-shrink:0;margin-top:2px;">%02d</span>'
            % (pal["primary"], pal["on_primary"], index)
            + '<p style="font-size:14px;color:%s;margin:0;line-height:1.9;flex:1;text-align:justify;">%s</p>'
            % (pal["text"], content)
            + '</section>'
        )
    if not rows:
        return ""
    return (
        '<section data-template="tutorial-dashboard-truths" style="margin:22px 0 24px;">'
        '<p style="font-size:15px;font-weight:900;color:%s;margin:0 0 14px;line-height:1.6;">'
        '<span style="background:linear-gradient(transparent 65%%,%s 65%%);padding:0 4px;">%s</span></p>'
        % (pal["heading"], pal["highlight"], title)
        + '<section>' + "".join(rows) + '</section></section>'
    )


def tutorial_dashboard_summary(block, pal):
    """末章摘要卡：标签、荧光笔式主句、来源/补充注脚。"""
    if not block:
        return ""
    if isinstance(block, str):
        block = {"text": block}
    if not isinstance(block, dict):
        raise SystemExit("tutorial_dashboard.blocks.summary 必须是对象或字符串")
    label = _dashboard_text(block.get("label") or "—— 写在最后 ——")
    text = _dashboard_text(block.get("text") or block.get("highlight"))
    note = _dashboard_text(block.get("note") or block.get("source"))
    if not text:
        return ""
    note_html = (
        '<p style="font-size:13px;color:%s;margin:8px 0 0;line-height:1.7;">%s</p>'
        % (pal["caption"], note)
        if note else ""
    )
    return (
        '<section data-template="tutorial-dashboard-summary" style="margin:0 0 22px;background:%s;'
        'border:1px dashed %s;border-radius:8px;padding:14px 16px;text-align:center;">' % (pal["surface"], pal["border"])

        + '<p style="font-size:12px;color:%s;margin:0 0 6px;line-height:1.5;">%s</p>' % (pal["caption"], label)
        + '<p style="margin:0;line-height:1.65;">'
        '<span style="font-size:15px;color:%s;font-weight:800;border-bottom:3px solid %s;padding-bottom:2px;">%s</span>'
        '</p>' % (pal["primary"], pal["highlight"], text)
        + note_html + '</section>'
    )


def tutorial_dashboard_cta(block, pal):
    """结尾行动区：复原参考文末的互动提示，但用静态 span 保证微信兼容。"""
    if not block:
        return ""
    if isinstance(block, str):
        block = {"text": block}
    if not isinstance(block, dict):
        raise SystemExit("tutorial_dashboard.blocks.cta 必须是对象或字符串")
    text = _dashboard_text(block.get("text") or block.get("message"))
    button = _dashboard_text(block.get("button") or block.get("action"))
    actions = _dashboard_items(block, ("actions", "items"))
    action_html = []
    for index, action in enumerate(actions):
        icon, label, meta, _ = _dashboard_item(action, "label")
        icon = _dashboard_text((action.get("icon") if isinstance(action, dict) else None) or icon or "·")
        label = _dashboard_text(label or meta or action)
        if not label:
            continue
        action_html.append(
            '<span style="display:inline-flex;align-items:center;gap:4px;margin:0 3px;padding:5px 9px;'
            'border:1px solid %s;border-radius:999px;background:%s;color:%s;font-size:11px;font-weight:700;">'
            '<span style="display:inline-flex;align-items:center;justify-content:center;width:16px;height:16px;'
            'border-radius:50%%;background:%s;color:%s;font-size:9px;">%s</span>%s</span>'
            % (pal["border"], pal["surface"], pal["primary_deep"], pal["primary"], pal["on_primary"], icon, label)

        )
    button_html = (
        '<span style="display:inline-block;margin:12px 0 0;padding:6px 16px;border-radius:4px;'
        'background:%s;color:%s;font-size:11px;font-weight:800;">%s</span>'
        % (pal["primary"], pal["on_primary"], button)
        if button else ""
    )
    if not text and not action_html and not button_html:
        return ""
    return (
        '<section data-template="tutorial-dashboard-cta" style="margin:0 0 24px;background:%s;'
        'border:1px solid %s;border-radius:14px;padding:22px 16px;text-align:center;">'
        % (pal["panel"], pal["border"])
        + ('<p style="font-size:14px;font-weight:800;color:%s;margin:0 0 12px;line-height:1.7;">%s</p>'
           % (pal["heading"], text) if text else "")
        + ('<section style="text-align:center;">%s</section>' % "".join(action_html) if action_html else "")
        + button_html
        + '<p style="font-family:Menlo,Consolas,monospace;font-size:9px;font-weight:800;color:%s;'
        'letter-spacing:1.2px;margin:12px 0 0;">THANKS FOR READING</p>' % pal["caption"]
        + '</section>'
    )


DASHBOARD_BLOCK_RENDERERS = {
    "problem": tutorial_dashboard_problem,
    "tag-cloud": tutorial_dashboard_tag_cloud,
    "stats": tutorial_dashboard_stats,
    "flow": tutorial_dashboard_flow,
    "connection": tutorial_dashboard_connection,
    "truths": tutorial_dashboard_truths,
    "summary": tutorial_dashboard_summary,
    "cta": tutorial_dashboard_cta,
}


def _dashboard_configured_blocks(settings):
    raw_blocks = _dashboard_blocks(settings)
    canonical_keys = {}
    unknown = []
    for raw_name in raw_blocks:
        name = str(raw_name).replace("_", "-")
        if name not in DASHBOARD_BLOCK_RENDERERS:
            unknown.append(name)
            continue
        previous = canonical_keys.get(name)
        if previous is not None and previous != raw_name:
            raise SystemExit("tutorial_dashboard.blocks 别名重复: %s" % name)
        canonical_keys[name] = raw_name

    if unknown:
        raise SystemExit("tutorial_dashboard.blocks 不支持: %s" % ", ".join(sorted(set(unknown))))

    for name in DASHBOARD_BLOCK_RENDERERS:
        aliases = (name, name.replace("-", "_"))
        configured_in_blocks = [key for key in aliases if key in raw_blocks]
        configured_at_top = [key for key in aliases if key in settings]
        if configured_in_blocks and configured_at_top:
            raise SystemExit("tutorial_dashboard block 配置重复: %s" % name)

    return {
        name for name in DASHBOARD_BLOCK_RENDERERS
        if _dashboard_block(settings, name) is not None
    }


def _dashboard_render_block(name, settings, pal):
    renderer = DASHBOARD_BLOCK_RENDERERS.get(name)
    return renderer(_dashboard_block(settings, name), pal) if renderer else ""


def _dashboard_slot_name(line):
    match = re.match(r"^\s*<!--\s*tutorial-dashboard:([a-zA-Z0-9_-]+)\s*-->\s*$", line)
    return match.group(1).replace("_", "-") if match else None


def _dashboard_caption_line(line):
    stripped = line.strip()
    match = re.match(r"^\*([^*]+)\*\s*$", stripped)
    if match:
        return match.group(1).strip()
    match = re.match(r"^—\s*(.+?)\s*—\s*$", stripped)
    return match.group(1).strip() if match else None


def _dashboard_marker_title(line):
    stripped = line.strip()
    if not stripped or len(stripped) > 80:
        return None
    if re.match(r"^(?:[✦✧★💡⚠！!]\s*|提示(?:[:：]|$)|小贴士(?:[:：]|$)|踩坑(?:提示)?(?:[:：]|$)|注意(?:[:：]|$)|警告(?:[:：]|$))", stripped, re.I):
        return stripped
    return None


def _dashboard_plain_callout(lines, start):
    """读取 marker 行后的第一段正文，返回 (正文行, 下一行索引)。"""
    index = start
    while index < len(lines) and not lines[index].strip():
        index += 1
    body = []
    while index < len(lines) and lines[index].strip():
        if (re.match(r"^#{1,4}\s+", lines[index]) or
                _dashboard_marker_title(lines[index]) or
                _dashboard_slot_name(lines[index])):
            break
        body.append(lines[index].strip())
        index += 1
    return body, index


def _dashboard_raw_route_item(lines, start):
    """识别展平来源 Hero 下的 ``PART 01 / 标题 / 标签`` 路线概览项。"""
    if start >= len(lines):
        return None
    marker = lines[start].strip()
    compact = re.match(r"^PART\s+(\d{1,2}|///)\s*$", marker, re.I)
    if not compact:
        return None
    index = start + 1
    values = []
    while index < len(lines) and len(values) < 2:
        value = lines[index].strip()
        if value:
            values.append(value)
        index += 1
    if len(values) != 2:
        return None
    title, label = values
    if re.match(r"^(?:PART|LAST|STEP)\b", title, re.I):
        return None
    return marker, title, label, index


def _dashboard_route_summary_end(lines, section_start=None):
    """返回展平来源的 Hero 路线摘要末尾，无法确认则不丢弃任何正文。"""
    index = 0
    saw_item = False
    last_end = None
    while index < len(lines):
        item = _dashboard_raw_route_item(lines, index)
        if item:
            saw_item = True
            last_end = item[3]
            index = item[3]
            continue
        if saw_item:
            if not lines[index].strip():
                index += 1
                continue
            return last_end if last_end is not None and (section_start is None or last_end <= section_start) else None
        index += 1
    return last_end if last_end is not None and (section_start is None or last_end <= section_start) else None


def _dashboard_inline_markup(text):
    """表格单元格内的最小行内标记：先转义，再还原粗体与行内代码。"""
    escaped = html.escape(str(text or ""), quote=False)
    escaped = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", escaped)
    return re.sub(r"`([^`]+)`", r"<code>\1</code>", escaped)


def _dashboard_cell_weight(text):
    """粗略计算列宽权重：CJK 记 2，其余记 1。"""
    return sum(2 if ord(char) > 0x2e80 else 1 for char in str(text or ""))


def _dashboard_table_widths(rows):
    """按内容宽度分配列宽，避免等分导致窄列浪费、宽列挤压。"""
    column_count = len(rows[0])
    weights = []
    for column in range(column_count):
        values = [_dashboard_cell_weight(row[column]) for row in rows if column < len(row)]
        weights.append(max(6, max(values) if values else 6))
    total = float(sum(weights))
    percentages = [max(12.0, min(52.0, weight / total * 100.0)) for weight in weights]
    scale = 100.0 / sum(percentages)
    percentages = [round(value * scale, 1) for value in percentages]
    percentages[-1] = round(100.0 - sum(percentages[:-1]), 1)
    return percentages


def _dashboard_split_row(line):
    stripped = line.strip()
    if stripped.startswith("|"):
        stripped = stripped[1:]
    if stripped.endswith("|"):
        stripped = stripped[:-1]
    return [cell.strip() for cell in re.split(r"(?<!\\)\|", stripped)]


def _dashboard_table_rows(lines, start):
    """识别标准 markdown 表格，返回 (rows, aligns, next_index)；不是表格则 None。"""
    if start + 1 >= len(lines) or "|" not in lines[start]:
        return None
    header = _dashboard_split_row(lines[start])
    if len(header) < 2:
        return None
    separator = _dashboard_split_row(lines[start + 1])
    if len(separator) != len(header) or not all(
            re.fullmatch(r":?-{2,}:?", cell) for cell in separator):
        return None
    aligns = []
    for cell in separator:
        left, right = cell.startswith(":"), cell.endswith(":")
        aligns.append("center" if left and right else "right" if right else "left")
    rows = [header]
    index = start + 2
    while index < len(lines) and lines[index].strip() and "|" in lines[index]:
        cells = _dashboard_split_row(lines[index])
        if len(cells) < 2:
            break
        rows.append(cells)
        index += 1
    return rows, aligns, index


def tutorial_dashboard_table(rows, aligns, pal):
    """把 markdown 表格渲染成带列宽的内联样式表格（微信粘贴不丢样式）。"""
    column_count = len(rows[0])
    normalised = []
    for row in rows:
        cells = list(row[:column_count])
        cells.extend([""] * (column_count - len(cells)))
        normalised.append(cells)
    widths = _dashboard_table_widths(normalised)
    colgroup = "".join('<col style="width:%s%%"/>' % width for width in widths)
    head_cells = [
        '<th style="padding:8px 10px;border:1px solid %s;background:%s;color:%s;font-size:12px;'
        'font-weight:800;text-align:%s;line-height:1.6;word-break:break-word;">%s</th>'
        % (pal["primary"], pal["primary"], pal["on_primary"], aligns[index],
           _dashboard_inline_markup(cell))
        for index, cell in enumerate(normalised[0])
    ]
    body_rows = []
    for row_index, row in enumerate(normalised[1:]):
        background = pal["surface_alt"] if row_index % 2 else pal["surface"]
        cells = [
            '<td style="padding:8px 10px;border:1px solid %s;background:%s;color:%s;font-size:12px;'
            'text-align:%s;line-height:1.7;word-break:break-word;overflow-wrap:anywhere;'
            'vertical-align:top;">%s</td>'
            % (pal["border"], background, pal["text"], aligns[index], _dashboard_inline_markup(cell))
            for index, cell in enumerate(row)
        ]
        body_rows.append("<tr>" + "".join(cells) + "</tr>")
    return (
        '<table data-template="tutorial-dashboard-table" style="width:100%;table-layout:fixed;'
        'border-collapse:collapse;margin:16px 0;font-size:12px;"><colgroup>' + colgroup
        + '</colgroup><thead><tr>' + "".join(head_cells) + '</tr></thead><tbody>'
        + "".join(body_rows) + '</tbody></table>'
    )


def _dashboard_raw_section(lines, start):
    """识别展平来源中的分行或一行式 PART/LAST 章节头。"""
    if start >= len(lines):
        return None
    marker = lines[start].strip()

    # 抓取器有时把「01 / PART / 标题 / 英文标签」压成一行。
    compact = re.match(r"^(?:(\d{1,2})\s+|///\s+)(PART|LAST)\s+(.+)$", marker, re.I)
    if compact:
        number, kind, content = compact.groups()
        label_match = re.search(
            r"\s+((?:[A-Z][A-Z0-9_-]*)(?:\s+[A-Z][A-Z0-9_-]*)*(?:\s*[·/&+]\s*.*)?)$",
            content,
        )
        if label_match:
            title = content[:label_match.start()].strip()
            label = label_match.group(1).strip()
            if title:
                return number or ("///" if kind.upper() == "LAST" else ""), kind.upper(), title, label, start + 1

    if not (re.fullmatch(r"\d{1,2}", marker) or marker == "///"):
        return None
    index = start + 1
    while index < len(lines) and not lines[index].strip():
        index += 1
    if index >= len(lines) or lines[index].strip().upper() not in ("PART", "LAST"):
        return None
    kind = lines[index].strip().upper()
    index += 1
    while index < len(lines) and not lines[index].strip():
        index += 1
    if index >= len(lines):
        return None
    title = lines[index].strip()
    index += 1
    while index < len(lines) and not lines[index].strip():
        index += 1
    if index >= len(lines):
        return None
    label = lines[index].strip()
    if not label or re.match(r"^(?:STEP|PART)\b", label, re.I):
        return None
    return marker, kind, title, label, index + 1


def _dashboard_raw_step(lines, start):
    """识别教程原文被展平后的 STEP 标签，并消费紧随其后的重复 Markdown 标题。"""
    if start >= len(lines):
        return None
    match = re.match(r"^\s*STEP\s*(\d{1,2})?\s*(?:[·:：\-]\s*)?(.*?)\s*$", lines[start], re.I)
    if not match:
        return None
    step_no = int(match.group(1) or 0)
    title = match.group(2).strip()
    index = start + 1
    while index < len(lines) and not lines[index].strip():
        index += 1
    if not title:
        if index >= len(lines):
            return None
        candidate = lines[index].strip()
        heading = re.match(r"^#{3,4}\s+(.+?)\s*#*\s*$", candidate)
        if heading:
            title = heading.group(1).strip()
            index += 1
        else:
            if (re.match(r"^#{1,2}\s+", candidate) or _dashboard_raw_section(lines, index)
                    or _dashboard_slot_name(candidate)):
                return None
            title = candidate
            index += 1
    else:
        # 只有当下一行 Markdown 标题与 inline 标题重复时才消费它；否则它是下一个步骤。
        if index < len(lines):
            heading = re.match(r"^#{3,4}\s+(.+?)\s*#*\s*$", lines[index].strip())
            if heading and _dashboard_compact_text(heading.group(1)) == _dashboard_compact_text(title):
                index += 1
    return step_no, title, index


def _dashboard_plain_caption(text, pal):
    return (
        '<p data-template="tutorial-dashboard-caption" style="font-size:11px;color:%s;text-align:center;'
        'margin:6px 0 18px;line-height:1.55;">%s</p>'
        % (pal["caption"], _dashboard_text(text))
    )


def _dashboard_plain_marker_callout(title, body_lines, pal):
    quote_lines = [title] + body_lines
    return tutorial_dashboard_callout(quote_lines, pal)


def _dashboard_compact_text(value):
    return re.sub(r"\s+", "", re.sub(r"[`*_]+", "", str(value or ""))).lower()


def _dashboard_section_descriptors(lines):
    descriptors = []
    fenced = False
    index = 0
    while index < len(lines):
        line = lines[index]
        if re.match(r"^\s*(```|~~~)", line):
            fenced = not fenced
            index += 1
            continue
        if fenced:
            index += 1
            continue
        heading = re.match(r"^##\s+(?!#)(.+?)\s*#*\s*$", line)
        if heading:
            title = heading.group(1).strip()
            descriptors.append((title, None, _dashboard_is_closing(title)))
            index += 1
            continue
        raw = _dashboard_raw_section(lines, index)
        if raw:
            descriptors.append((raw[2], raw[3], raw[1] == "LAST" or raw[0] == "///"))
            index = raw[4]
            continue
        index += 1
    return descriptors


def _dashboard_section_candidates(lines):
    return [descriptor[0] for descriptor in _dashboard_section_descriptors(lines)]


def tutorial_dashboard_outcome(settings, pal):
    outcome = settings.get("outcome")
    if not outcome:
        return ""
    if isinstance(outcome, str):
        label, text = "完成后", outcome
    elif isinstance(outcome, dict):
        label, text = outcome.get("label") or "完成后", outcome.get("text")
    else:
        raise SystemExit("tutorial_dashboard.outcome 必须是对象或字符串")
    if not text:
        return ""
    return (
        '<section data-template="tutorial-dashboard-outcome" style="margin:0 0 24px;background:%s;'
        'border:1px dashed %s;border-radius:8px;padding:14px 16px;text-align:center;">'
        % (pal["panel"], pal["primary_mid"])
        + '<p style="font-size:12px;color:%s;margin:0 0 5px;line-height:1.5;">%s</p>' % (pal["caption"], _dashboard_text(label))
        + '<p style="font-size:15px;color:%s;font-weight:800;margin:0;line-height:1.65;">%s</p>'
        % (pal["primary"], _dashboard_text(text))
        + '</section>'
    )


def tutorial_dashboard_section(section_no, title, label, pal, is_last=False):
    closing = is_last or bool(re.search(r"(?:最后|结语|总结|写在最后|结尾)", title))
    marker = "///" if closing else "%02d" % section_no
    kind = "LAST" if closing else "PART"
    return (
        '<section data-template="tutorial-dashboard-section" style="margin:42px 0 20px;padding:0 2px;">'
        '<section style="display:flex;align-items:center;gap:14px;">'
        '<section style="text-align:center;flex-shrink:0;min-width:42px;">'
        '<p style="font-family:Menlo,Consolas,monospace;font-size:28px;font-weight:900;color:%s;line-height:1;margin:0;">%s</p>'
        % (pal["primary"], marker)
        + '<p style="font-size:8px;font-weight:800;color:%s;letter-spacing:1.2px;margin:4px 0 0;">%s</p>'
        % (pal["caption"], kind)
        + '</section>'
        + '<section style="min-width:0;">'
        + '<p style="font-size:19px;font-weight:900;color:%s;margin:0;line-height:1.3;word-break:break-word;">%s</p>'
        % (pal["heading"], _dashboard_text(title))
        + '<p style="font-family:Menlo,Consolas,monospace;font-size:9px;font-weight:700;color:%s;letter-spacing:1.2px;margin:4px 0 0;line-height:1.3;">%s</p>'
        % (pal["caption"], label)
        + '</section></section></section>'
    )


def tutorial_dashboard_step(step_no, title, pal):
    return (
        '<section data-template="tutorial-dashboard-step" style="display:flex;align-items:center;gap:8px;'
        'margin:24px 0 10px;">'
        '<span style="flex-shrink:0;background:%s;color:%s;border-radius:3px;padding:2px 6px;'
        'font-family:Menlo,Consolas,monospace;font-size:9px;font-weight:800;letter-spacing:.5px;">STEP %02d</span>'
        % (pal["primary"], pal["on_primary"], step_no)
        + '<p style="margin:0;font-size:16px;font-weight:800;color:%s;line-height:1.45;">%s</p>'
        % (pal["heading"], _dashboard_text(title))
        + '</section>'
    )


def tutorial_dashboard_figure(src, caption, fig_no, pal):
    src = urllib.parse.quote(src, safe=":/?&=%#")
    return (
        '<section data-template="tutorial-dashboard-figure" style="margin:18px 0 22px;background:%s;'
        'border:1px solid %s;border-radius:8px;padding:6px;box-shadow:0 2px 8px rgba(0,0,0,.04);">' % (pal["surface"], pal["border"])

        + '<img src="%s" style="max-width:100%%;height:auto;display:block;margin:0;border-radius:5px;"/>' % src
        + '<p style="font-size:10px;color:%s;text-align:center;margin:8px 4px 1px;line-height:1.45;">FIG.%02d · %s</p>'
        % (pal["caption"], fig_no, _dashboard_text(caption or "界面截图"))
        + '</section>'
    )


def _dashboard_quote_group(lines, start):
    """读取连续引用块，同时把结尾的普通空行留给主循环。"""
    quote_lines = []
    index = start
    while index < len(lines):
        line = lines[index]
        if line.lstrip().startswith(">"):
            quote_lines.append(re.sub(r"^\s*>\s?", "", line))
            index += 1
            continue
        if line.strip() == "" and index + 1 < len(lines) and lines[index + 1].lstrip().startswith(">"):
            quote_lines.append("")
            index += 1
            continue
        break
    return quote_lines, index


def tutorial_dashboard_callout(quote_lines, pal):
    nonempty = [line for line in quote_lines if line.strip()]
    if not nonempty:
        return ""
    first = _dashboard_text(nonempty[0])
    source = " ".join(nonempty)
    is_callout = re.match(r"^(?:[✦✧★💡⚠!！]+|(?:提示|注意|踩坑|避坑|警告|tip|note|warning))", first, re.I)
    if not is_callout:
        return ""

    warning = bool(re.search(r"(?:⚠|注意|踩坑|避坑|警告|warning|风险|错误)", source, re.I))
    accent = pal["secondary"] if warning else pal["primary"]
    background = pal["secondary_soft"] if warning else pal["panel"]
    label = "WARNING" if warning else "TIP"
    title = re.sub(r"^[✦✧★💡⚠!！\s]+", "", first) or ("注意事项" if warning else "小贴士")
    body = " ".join(_dashboard_text(line) for line in nonempty[1:])
    body_html = (
        '<p style="font-size:13px;color:%s;margin:5px 0 0;line-height:1.8;">%s</p>' % (pal["text"], body)
        if body else ""
    )
    return (
        '<section data-template="tutorial-dashboard-callout" style="background:%s;border-left:3px solid %s;'
        'border-radius:0 8px 8px 0;padding:10px 14px;margin:18px 0;">' % (background, accent)
        + '<p style="font-family:Menlo,Consolas,monospace;font-size:9px;font-weight:800;color:%s;'
        'letter-spacing:1px;margin:0;">%s · %s</p>' % (accent, label, title)
        + body_html
        + '</section>'
    )


def tutorial_dashboard_divider(pal):
    return (
        '<section data-template="tutorial-dashboard-divider" style="display:flex;align-items:center;'
        'justify-content:center;gap:6px;margin:30px 0;">'
        '<span style="width:20px;height:1px;background:%s;line-height:0;font-size:0;">&nbsp;</span>' % pal["primary_mid"]
        + '<span style="width:6px;height:6px;border-radius:50%%;background:%s;line-height:0;font-size:0;">&nbsp;</span>' % pal["primary"]
        + '<span style="width:20px;height:1px;background:%s;line-height:0;font-size:0;">&nbsp;</span></section>' % pal["primary_mid"]
    )


def tutorial_dashboard_closing(settings, pal):
    closing = settings.get("closing")
    if not closing:
        return ""
    if isinstance(closing, str):
        label, text = "THANKS FOR READING", closing
    elif isinstance(closing, dict):
        label = closing.get("label") or "THANKS FOR READING"
        text = closing.get("text")
    else:
        raise SystemExit("tutorial_dashboard.closing 必须是对象或字符串")
    if not text:
        return ""
    return (
        '<section data-template="tutorial-dashboard-closing" style="margin:32px 0 0;background:%s;'
        'border:1px solid %s;border-radius:14px;padding:24px 18px;text-align:center;">' % (pal["panel"], pal["border"])
        + '<p style="font-size:14px;font-weight:800;color:%s;margin:0 0 8px;line-height:1.7;">%s</p>'
        % (pal["heading"], _dashboard_text(text))
        + '<p style="font-family:Menlo,Consolas,monospace;font-size:9px;font-weight:800;color:%s;letter-spacing:1.2px;margin:0;">%s</p>'
        % (pal["caption"], _dashboard_text(label))
        + '</section>'
    )


def transform_tutorial_dashboard(md, labels, pal):
    """把教程 Markdown 改造成参考文章同类的信息仪表盘结构。

    HTML 组件均由 frontmatter 的 ``tutorial_dashboard.blocks`` 提供数据；正文用
    ``<!-- tutorial-dashboard:<block> -->`` 放置组件。没有 frontmatter 时仍按普通
    Markdown 的 h1/h2/h3、图片、引用和分隔线退化工作。
    """
    _, lines, parsed_frontmatter = _split_frontmatter(md)
    settings = _tutorial_dashboard_settings(parsed_frontmatter)
    configured_blocks = _dashboard_configured_blocks(settings)
    palette = _dashboard_palette(pal)
    title = settings.get("title")
    title_lines = settings.get("title_lines")
    if title_lines is not None:
        if isinstance(title_lines, str):
            title_lines = [title_lines]
        if not isinstance(title_lines, list):
            raise SystemExit("tutorial_dashboard.title_lines 必须是列表或字符串")
        title = " ".join(str(line).strip() for line in title_lines if str(line).strip())
    for line in lines:
        if title:
            break
        h1 = re.match(r"^#\s+(.+?)\s*#*\s*$", line)
        if h1:
            title = h1.group(1).strip()
    title = title or "实操教程"
    section_entries = _dashboard_section_descriptors(lines)
    roadmap = _dashboard_roadmap_items(section_entries, labels, settings)
    first_raw_section = next((index for index in range(len(lines)) if _dashboard_raw_section(lines, index)), None)
    route_summary_end = _dashboard_route_summary_end(lines, first_raw_section) if section_entries else None

    title_line = _dashboard_text(title)
    out = ["# " + title_line, "", tutorial_dashboard_hero(title, settings, palette)]
    roadmap_html = tutorial_dashboard_roadmap(roadmap, palette)
    if roadmap_html:
        out.append(roadmap_html)
    outcome_html = tutorial_dashboard_outcome(settings, palette)
    if outcome_html:
        out.append(outcome_html)

    section_no = 0
    step_no = 0
    fig_no = 0
    first_h1_removed = False
    used_slots = set()
    fenced = False
    index = 0
    while index < len(lines):
        line = lines[index]
        stripped = line.strip()
        if re.match(r"^\s*(```|~~~)", line):
            fenced = not fenced
            out.append(line)
            index += 1
            continue
        if fenced:
            out.append(line)
            index += 1
            continue

        if route_summary_end is not None and index < route_summary_end:
            index += 1
            continue

        slot = _dashboard_slot_name(line)
        if slot:
            if slot in used_slots:
                raise SystemExit("tutorial_dashboard 插槽重复: %s" % slot)
            component = _dashboard_render_block(slot, settings, palette)
            if not component:
                raise SystemExit("tutorial_dashboard 插槽未配置或不支持: %s" % slot)
            out.append(component)
            used_slots.add(slot)
            index += 1
            continue

        table = _dashboard_table_rows(lines, index)
        if table:
            rows, aligns, next_index = table
            out.append(tutorial_dashboard_table(rows, aligns, palette))
            index = next_index
            continue

        h1 = re.match(r"^#\s+(.+?)\s*#*\s*$", line)
        h2 = re.match(r"^##\s+(?!#)(.+?)\s*#*\s*$", line)
        subheading = re.match(r"^#{3,4}\s+(.+?)\s*#*\s*$", line)
        image = re.match(r"^!\[([^\]]*)\]\(([^)]+)\)\s*$", stripped)
        raw_section = _dashboard_raw_section(lines, index)
        raw_step = _dashboard_raw_step(lines, index)
        marker_title = _dashboard_marker_title(line)
        caption = _dashboard_caption_line(line)

        if h1 and not first_h1_removed:
            first_h1_removed = True
        elif raw_section:
            marker, kind, heading, label, next_index = raw_section
            section_no += 1
            step_no = 0
            out.append(tutorial_dashboard_section(
                section_no,
                heading,
                _dashboard_text(label),
                palette,
                is_last=(kind == "LAST" or marker == "///"),
            ))
            index = next_index
            continue
        elif h2:
            section_no += 1
            step_no = 0
            heading = h2.group(1).strip()
            label = _dashboard_section_label(heading, section_no, labels, settings)
            out.append(tutorial_dashboard_section(section_no, heading, label, palette))
        elif subheading:
            step_no += 1
            out.append(tutorial_dashboard_step(step_no, subheading.group(1).strip(), palette))
        elif raw_step:
            source_step_no, step_title, next_index = raw_step
            step_no = source_step_no or step_no + 1
            out.append(tutorial_dashboard_step(step_no, step_title, palette))
            index = next_index
            continue
        elif image:
            fig_no += 1
            image_caption = image.group(1)
            caption_index = index + 1
            while caption_index < len(lines) and not lines[caption_index].strip():
                caption_index += 1
            following_caption = (
                _dashboard_caption_line(lines[caption_index])
                if caption_index < len(lines) else None
            )
            if following_caption:
                image_caption = following_caption
                index = caption_index
            out.append(tutorial_dashboard_figure(image.group(2), image_caption, fig_no, palette))
        elif stripped.startswith(">"):
            quote_lines, next_index = _dashboard_quote_group(lines, index)
            callout = tutorial_dashboard_callout(quote_lines, palette)
            if callout:
                out.append(callout)
            else:
                out.extend(lines[index:next_index])
            index = next_index
            continue
        elif marker_title:
            body_lines, next_index = _dashboard_plain_callout(lines, index + 1)
            callout = _dashboard_plain_marker_callout(marker_title, body_lines, palette)
            if callout:
                out.append(callout)
                index = next_index
                continue
            out.append(line)
        elif caption:
            out.append(_dashboard_plain_caption(caption, palette))
        elif stripped in ("---", "***", "___"):
            out.append(tutorial_dashboard_divider(palette))
        else:
            out.append(line)
        index += 1

    missing_slots = sorted(configured_blocks - used_slots)
    if missing_slots:
        raise SystemExit("tutorial_dashboard block 未找到插槽: %s" % ", ".join(missing_slots))

    closing_html = tutorial_dashboard_closing(settings, palette)
    if closing_html:
        out.extend(["", closing_html])
    return "\n".join(out), section_no, fig_no

# ---------------------------------------------------------------- muppet-editorial

MUPPET_DEFAULT_MASTHEAD = "FIELD NOTES"
MUPPET_DEFAULT_NOTE_LABEL = "EDITOR'S NOTE"
MUPPET_PILL_MAX_WEIGHT = 30
MUPPET_TABLE_CELL_MIN = 56.0
MUPPET_TABLE_CELL_PADDING = 30.0
MUPPET_TABLE_MAX_WIDTH = 640.0
MUPPET_TABLE_HEAD_SIZE = 12.0
MUPPET_TABLE_BODY_SIZE = 13.0
MUPPET_CLOSING_PATTERN = r"(?:最后|结语|总结|写在最后|结尾)"
MUPPET_STEP_PATTERN = r"^(?:Step|STEP|步骤)\s*(\d+)\s*[\.·、:：\-]?\s*(.*)$"


def _muppet_palette(pal):
    """主题取色 → 简报版式需要的中间色（深色信息条、浅底卡、细线）。"""
    surface = pal.get("background", "#f7f4f0")
    panel = pal.get("background_light") or _mix(pal["primary"], surface, 0.94)
    ink = pal.get("heading", pal["text"])
    body = pal["text"]
    dark = pal["primary"]
    on_dark = _dashboard_on_color(dark)
    return dict(
        pal,
        surface=surface,
        panel=panel,
        chip=pal.get("highlight") or panel,
        ink=ink,
        body=body,
        muted=_mix(body, surface, 0.35),
        faint=pal.get("caption") or _mix(body, surface, 0.60),
        line=_mix(surface, ink, 0.08),
        dash=_mix(surface, ink, 0.16),
        dark=dark,
        on_dark=on_dark,
        dark_soft=_mix(on_dark, dark, 0.12),
        dark_muted=_mix(on_dark, dark, 0.38),
        accent=pal["secondary"],
    )


def _muppet_settings(frontmatter):
    settings = frontmatter.get("muppet") or {}
    if not isinstance(settings, dict):
        raise SystemExit("muppet frontmatter 必须是对象")
    return settings


def _muppet_tags(value):
    if value is None:
        return []
    if isinstance(value, str):
        return [value] if value.strip() else []
    if not isinstance(value, list):
        raise SystemExit("muppet.tags 必须是列表或字符串")
    return [tag for tag in value if str(tag).strip()]


def _muppet_block(html_text):
    """组件前后补空行，避免相邻 Markdown 被当成 HTML 块吞掉。"""
    return ["", html_text, ""] if html_text else []


def muppet_masthead(settings, frontmatter, heading, pal):
    """刊头细线 + 大标题：左侧字距拉开的刊名，右侧日期；线下是正文大标题。"""
    masthead = _dashboard_text(settings.get("masthead") or frontmatter.get("author"))
    masthead = masthead or MUPPET_DEFAULT_MASTHEAD
    date = _dashboard_text(settings.get("date"))
    right = ""
    if date:
        right = ('<span style="font-size:10px;font-weight:500;color:%(faint)s;'
                 'font-variant-numeric:tabular-nums;">' % pal + date + "</span>")
    line = (
        '<section data-template="muppet-masthead" style="display:flex;align-items:center;'
        'justify-content:space-between;gap:10px;border-bottom:1px solid %(line)s;'
        'padding-bottom:10px;margin-bottom:16px;">'
        '<span style="font-size:10px;font-weight:700;letter-spacing:3px;color:%(muted)s;">'
        % pal + masthead + "</span>" + right + "</section>"
    )
    title = ("<p style=\"margin:0 0 12px;font-size:24px;font-weight:800;color:%(ink)s;"
             "line-height:1.22;letter-spacing:-0.3px;\">" % pal + heading + "</p>") if heading else ""
    return line + title


def muppet_kicker(text, pal):
    return ("<p style=\"margin:0 0 18px;font-size:13px;color:%(muted)s;line-height:1.75;"
            "text-align:justify;\">" % pal + text + "</p>")


def muppet_leadbar(lead, tags, pal):
    """炭黑信息条：左侧一句话结论，右侧浅底小标签。"""
    chips = "".join(
        '<span style="display:inline-block;background:%(chip)s;color:%(ink)s;padding:3px 8px;'
        'border-radius:4px;font-size:8px;font-weight:700;border:1px solid %(line)s;">' % pal
        + _dashboard_text(tag) + "</span>"
        for tag in tags
    )
    if not lead and not chips:
        return ""
    left = ""
    if lead:
        left = ('<p style="margin:0;font-size:12px;font-weight:600;color:%(dark_soft)s;'
                'line-height:1.6;">' % pal + lead + "</p>")
    right = ('<section style="display:flex;gap:6px;flex-wrap:wrap;">' + chips + "</section>") if chips else ""
    return (
        '<section data-template="muppet-leadbar" style="background:%(dark)s;border-radius:6px;'
        'padding:11px 16px;display:flex;align-items:center;justify-content:space-between;'
        'gap:10px;flex-wrap:wrap;margin:0 0 24px;">' % pal + left + right + "</section>"
    )


def muppet_note(note, pal):
    """EDITOR'S NOTE 卡：炭黑头条 + 浅底引言。"""
    if not isinstance(note, dict):
        return ""
    text = _dashboard_text(note.get("text"))
    if not text:
        return ""
    label = _dashboard_text(note.get("label")) or MUPPET_DEFAULT_NOTE_LABEL
    caption = _dashboard_text(note.get("caption"))
    right = ""
    if caption:
        right = ('<span style="font-size:10px;color:%(dark_muted)s;">' % pal + caption + "</span>")
    return (
        ('<section data-template="muppet-note" style="border:1px solid %(line)s;border-radius:6px;'
         'overflow:hidden;background:%(surface)s;margin:0 0 24px;">'
         '<section style="padding:10px 16px;background:%(dark)s;display:flex;align-items:center;'
         'justify-content:space-between;gap:10px;">'
         '<p style="margin:0;font-size:10px;font-weight:800;letter-spacing:2px;'
         'color:%(on_dark)s;">' % pal)
        + label + "</p>" + right + "</section>"
        + '<section style="padding:16px 18px 18px;background:%(panel)s;">'
          '<p style="margin:0;font-size:14px;line-height:1.9;color:%(body)s;text-align:justify;">'
          % pal + text + "</p></section></section>"
    )


def muppet_section_head(mark, title, label, pal, tag="PART"):
    """PART 小节头与 /// END 收尾头共用：左侧大号编号，右侧标题 + 英文小标签。"""
    label_line = ""
    if label:
        label_line = ('<p style="margin:0;font-size:11px;font-weight:600;color:%(muted)s;'
                      'letter-spacing:1.2px;line-height:1.5;">' % pal + label + "</p>")
    return (
        ('<section data-template="muppet-section" style="display:flex;align-items:center;'
         'gap:14px;margin:34px 0 16px;">'
         '<section style="text-align:center;flex-shrink:0;">'
         '<p style="margin:0;font-size:24px;font-weight:800;color:%(ink)s;line-height:1;'
         'letter-spacing:-2px;">' % pal)
        + mark + "</p>"
        + '<p style="margin:0;font-size:8px;font-weight:700;color:%(faint)s;letter-spacing:2px;">'
          % pal + tag + "</p></section>"
        + '<section style="min-width:0;">'
          '<p style="margin:0 0 2px;font-size:17px;font-weight:800;color:%(ink)s;'
          'letter-spacing:0.2px;line-height:1.45;">' % pal + title + "</p>"
        + label_line + "</section></section>"
    )


def muppet_step(number, title, pal):
    badge = "Step %s" % number
    return (
        ('<section data-template="muppet-step" style="display:flex;align-items:center;gap:10px;'
         'margin:26px 0 0;">'
         '<span style="display:inline-block;background:%(dark)s;color:%(on_dark)s;'
         'padding:4px 10px;border-radius:4px;font-size:11px;font-weight:700;line-height:1.5;'
         'white-space:nowrap;">' % pal)
        + badge + "</span>"
        + '<span style="font-size:14px;font-weight:600;color:%(ink)s;line-height:1.5;">'
          % pal + title + "</span></section>"
    )


def muppet_pill(text, pal):
    return (
        '<p style="margin:16px 0 6px;">'
        '<span style="display:inline-block;font-size:13px;font-weight:700;color:%(ink)s;'
        'background:%(chip)s;padding:3px 10px;border-radius:999px;border:1px solid %(line)s;">'
        % pal + "&nbsp;" + text + "&nbsp;</span></p>"
    )


def muppet_figure(src, caption, pal):
    """虚线框图片卡：中英混排路径做百分号编码，避免渲染器插空格裂图。"""
    src = urllib.parse.quote(src, safe=":/?&=%#")
    cap = ""
    if caption:
        cap = ('<p style="margin:12px 0 0;font-size:11px;color:%(faint)s;line-height:1.6;">'
               % pal + _dashboard_text(caption) + "</p>")
    return (
        ('<section data-template="muppet-figure" style="margin:24px 0;padding:22px 20px;'
         'border:1.5px dashed %(dash)s;border-radius:14px;background:%(surface)s;'
         'text-align:center;">' % pal)
        + '<img src="' + src + '" style="max-width:100%;border-radius:6px;display:block;'
          'margin:0 auto;" />' + cap + "</section>"
    )


def _muppet_table_row(row, widths, aligns, pal, header=False):
    cells = []
    for index, text in enumerate(row):
        if header:
            style = ("padding:10px 12px;background:%s;font-size:12px;font-weight:800;color:%s;"
                     % (pal["panel"], pal["ink"]))
        else:
            style = ("padding:10px 12px;background:%s;font-size:13px;color:%s;"
                     % (pal["surface"], pal["body"] if index == 0 else pal["ink"]))
        if index:
            style += "border-left:1px solid %s;" % pal["line"]
        # min-width + flex-grow：宽屏时各列等比撑满容器，窄屏时也不被压到内容宽以下
        cells.append(
            '<section style="width:%s;min-width:%s;flex:1 1 auto;box-sizing:border-box;%s'
            'text-align:%s;line-height:1.6;word-break:normal;overflow-wrap:break-word;">%s</section>'
            % (widths[index], widths[index], style, aligns[index], _dashboard_inline_markup(text))
        )
    return "".join(cells)


def _muppet_text_width(text, font_size):
    """估算一行文本宽度（px）：CJK 按全宽计，其余按 0.55 全宽。"""
    return sum(font_size if ord(char) > 0x2e80 else font_size * 0.55 for char in text)


def _muppet_table_widths(rows):
    """按内容估算每列 px 宽度：保证最长单元格一行放得下，小屏不出现竖排单字。"""
    widths = []
    for column in range(len(rows[0])):
        needed = 0.0
        for row_index, row in enumerate(rows):
            if column >= len(row):
                continue
            size = MUPPET_TABLE_HEAD_SIZE if row_index == 0 else MUPPET_TABLE_BODY_SIZE
            needed = max(needed, _muppet_text_width(_dashboard_plain_text(row[column]), size))
        widths.append(max(MUPPET_TABLE_CELL_MIN, needed + MUPPET_TABLE_CELL_PADDING))
    total = sum(widths)
    if total > MUPPET_TABLE_MAX_WIDTH:
        widths = [width * MUPPET_TABLE_MAX_WIDTH / total for width in widths]
    return ["%.0fpx" % width for width in widths]


def muppet_table(rows, aligns, pal):
    """卡片式表格：浅底表头 + 细分隔行，列宽按内容分配。"""
    column_count = len(rows[0])
    normalised = []
    for row in rows:
        cells = list(row[:column_count])
        cells.extend([""] * (column_count - len(cells)))
        normalised.append(cells)
    widths = _muppet_table_widths(normalised)
    head = ('<section style="display:flex;background:%(panel)s;border-bottom:1px solid %(line)s;'
            'border-radius:6px 6px 0 0;">' % pal
            + _muppet_table_row(normalised[0], widths, aligns, pal, header=True) + "</section>")
    body = normalised[1:]
    body_rows = []
    for index, row in enumerate(body):
        last = index == len(body) - 1
        border = "border-radius:0 0 6px 6px;" if last else "border-bottom:1px solid %s;" % pal["line"]
        body_rows.append('<section style="display:flex;%s">' % border
                         + _muppet_table_row(row, widths, aligns, pal) + "</section>")
    # 列宽按内容定宽：窄屏时表格保持单行、由外层横向滑动，不把文字压成竖排
    return (
        '<section style="overflow-x:auto;-webkit-overflow-scrolling:touch;margin:22px 0;">'
        '<section data-template="muppet-table" style="display:inline-block;vertical-align:top;'
        'min-width:100%%;border:1px solid %(line)s;border-radius:6px;background:%(surface)s;">' % pal
        + head + "".join(body_rows) + "</section></section>"
    )


def muppet_divider(pal):
    bar = ('<span style="flex:1 1 auto;height:1px;background:%(line)s;font-size:0;'
           'line-height:0;">&nbsp;</span>')
    dot = ('<span style="width:6px;height:6px;border-radius:50%%;background:%(accent)s;'
           'font-size:0;line-height:0;">&nbsp;</span>')
    return ('<section data-template="muppet-divider" style="display:flex;align-items:center;'
            'gap:8px;margin:26px 0;">' + bar + dot + bar + "</section>") % pal


def muppet_callout(quote_lines, pal):
    """引用块 → 浅底提示卡（橙色左线）。"""
    nonempty = [_dashboard_text(line) for line in quote_lines if line.strip()]
    if not nonempty:
        return ""
    paragraphs = "".join(
        '<p style="margin:%s;font-size:14px;line-height:1.9;color:%s;text-align:justify;">%s</p>'
        % ("0" if index == 0 else "10px 0 0", pal["body"], text)
        for index, text in enumerate(nonempty)
    )
    return (
        '<section data-template="muppet-callout" style="background:%(panel)s;'
        'border-left:3px solid %(accent)s;border-radius:0 6px 6px 0;padding:14px 16px;'
        'margin:18px 0;">' % pal + paragraphs + "</section>"
    )


def muppet_closing(settings, pal):
    """收尾卡：浅底圆角 + 橙下划线金句 + 字距拉开的小字标签。"""
    closing = settings.get("closing")
    if not closing:
        return ""
    if isinstance(closing, dict):
        text = _dashboard_text(closing.get("text"))
        label = _dashboard_text(closing.get("label"))
    else:
        text, label = _dashboard_text(closing), ""
    if not text:
        return ""
    label_line = ""
    if label:
        label_line = ('<p style="margin:0;font-size:10px;font-weight:500;color:%(faint)s;'
                      'letter-spacing:2px;">' % pal + label + "</p>")
    return (
        '<section data-template="muppet-closing" style="margin:30px 0 0;background:%(panel)s;'
        'border:1px solid %(line)s;border-radius:6px;padding:22px 18px;text-align:center;">'
        '<p style="margin:0 0 12px;font-size:15px;font-weight:800;color:%(ink)s;line-height:1.7;">'
        '<strong style="border-bottom:3px solid %(accent)s;">' % pal + text + "</strong></p>"
        + label_line + "</section>"
    )


def transform_muppet(md, labels, pal):
    """编辑部简报版式：刊头线 / PART 编号小节 / pill 小标题 / Step 徽章 / 虚线图框 / 卡片表格。

    刊名、副标题、信息条、按语卡等由 frontmatter 的 ``muppet`` 段提供；不写也能跑，
    只按 Markdown 的 h1/h2/h3、引用、图片、表格生成结构。
    """
    _, lines, frontmatter = _split_frontmatter(md)
    settings = _muppet_settings(frontmatter)
    palette = _muppet_palette(pal)
    tags = _muppet_tags(settings.get("tags"))

    heading = ""
    for line in lines:
        match = re.match(r"^#\s+(?!#)(.+?)\s*#*\s*$", line)
        if match:
            heading = _dashboard_text(match.group(1))
            break
    if not heading:
        heading = _dashboard_text(frontmatter.get("title"))

    kicker = _dashboard_text(settings.get("kicker"))
    out = ["", muppet_masthead(settings, frontmatter, heading, palette), ""]
    out.extend(html_text for html_text in (
        muppet_kicker(kicker, palette) if kicker else "",
        muppet_leadbar(_dashboard_text(settings.get("lead")), tags, palette),
        muppet_note(settings.get("note"), palette),
    ) if html_text)

    section_no = 0
    step_no = 0
    fig_no = 0
    fenced = False
    index = 0
    while index < len(lines):
        line = lines[index]
        stripped = line.strip()
        if re.match(r"^\s*(```|~~~)", line):
            fenced = not fenced
            out.append(line)
            index += 1
            continue
        if fenced:
            out.append(line)
            index += 1
            continue

        table = _dashboard_table_rows(lines, index)
        if table:
            rows, aligns, next_index = table
            out.extend(_muppet_block(muppet_table(rows, aligns, palette)))
            index = next_index
            continue

        h1 = re.match(r"^#\s+(.+?)\s*#*\s*$", line)
        h2 = re.match(r"^##\s+(?!#)(.+?)\s*#*\s*$", line)
        h3 = re.match(r"^###\s+(?!#)(.+?)\s*#*\s*$", line)
        image = re.match(r"^!\[([^\]]*)\]\(([^)]+)\)\s*$", stripped)
        pill = re.match(r"^\*\*([^*]+)\*\*\s*$", stripped)

        if image:
            fig_no += 1
            caption = image.group(1).strip()
            follow = index + 1
            while follow < len(lines) and not lines[follow].strip():
                follow += 1
            italic = re.match(r"^\*([^*]+)\*\s*$", lines[follow].strip()) if follow < len(lines) else None
            if italic:
                caption = italic.group(1).strip()
                index = follow
            out.extend(_muppet_block(muppet_figure(image.group(2), caption, palette)))
        elif h1:
            out.append(line)
        elif h2:
            title = h2.group(1).strip()
            if re.search(MUPPET_CLOSING_PATTERN, title):
                label = labels.get(title) or "TO WRAP UP"
                out.extend(_muppet_block(muppet_section_head(
                    "///", title, _dashboard_text(label), palette, tag="END")))
            else:
                section_no += 1
                step_no = 0
                label = labels.get(title) or "SECTION %02d" % section_no
                out.extend(_muppet_block(muppet_section_head(
                    "%02d" % section_no, title, _dashboard_text(label), palette)))
        elif h3:
            step = re.match(MUPPET_STEP_PATTERN, h3.group(1).strip())
            if step:
                step_no = int(step.group(1))
                out.extend(_muppet_block(muppet_step(step_no, _dashboard_text(step.group(2)), palette)))
            else:
                out.append(line)
        elif pill and _dashboard_cell_weight(pill.group(1)) <= MUPPET_PILL_MAX_WEIGHT:
            out.extend(_muppet_block(muppet_pill(_dashboard_text(pill.group(1)), palette)))
        elif stripped.startswith(">"):
            quote_lines, next_index = _dashboard_quote_group(lines, index)
            out.extend(_muppet_block(muppet_callout(quote_lines, palette)))
            index = next_index
            continue
        elif stripped in ("---", "***", "___"):
            out.extend(_muppet_block(muppet_divider(palette)))
        else:
            out.append(line)
        index += 1

    closing = muppet_closing(settings, palette)
    if closing:
        out.extend(_muppet_block(closing))
    return "\n".join(out), section_no, fig_no


TEMPLATES = {
    "kazk-editorial": (transform_kazk, "kazk-editorial"),
    "muppet-editorial": (transform_muppet, "muppet-editorial"),
    "bold-contrast": (transform_bold, "bold-contrast"),
    "qa-bubble": (transform_qa, "qa-bubble"),
    "timeline-log": (transform_timeline, "timeline-log"),
    "knowledge-card": (transform_knowledge, "knowledge-card"),
    "press": (transform_press, "press"),
    "tutorial-dashboard": (transform_tutorial_dashboard, "emerald-tutorial"),
    "chengzi-benefit": (transform_chengzi, "chengzi-orange"),
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
