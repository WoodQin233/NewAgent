"""原型 Builder:把 (内容, 主题, 状态, 原型) 编译成 PageLayout

classic 系列 builder 是旧 PageRenderer handler 的逐行迁移,几何取自
schema 槽位(数值与旧硬编码一致),行为由 golden 测试锁定。
M3 起新原型在此追加 builder 并注册到 BUILDERS。
"""
from __future__ import annotations

import math
import re
from typing import Callable, Dict, Optional

from App.models import (
    Box,
    CompositionSchema,
    Mood,
    PageLayout,
    ShapeBox,
    SlideContent,
    ThemeConfig,
)
from App.layout_engine.fonts import FontScale, cn_section_num, lighten
from App.layout_engine.grid import DEFAULT_GRID
from App.layout_engine.state import RenderState
from App.layout_engine.text_metrics import fit_font

Builder = Callable[[SlideContent, ThemeConfig, RenderState, CompositionSchema], PageLayout]


def _slot(schema: CompositionSchema, name: str):
    for slot in schema.slots:
        if slot.name == name:
            return slot
    raise ValueError(f"原型 {schema.schema_id} 缺少槽位 '{name}'")


def _textbox(schema: CompositionSchema, name: str, content: str, mood: Optional[Mood],
             *, font_key: Optional[str] = None, bold: Optional[bool] = None,
             color: Optional[str] = None) -> ShapeBox:
    """按槽位构造文本框;字号键/加粗/颜色可被调用方覆盖,字号按 mood 缩放。"""
    slot = _slot(schema, name)
    key = font_key or slot.font_key
    return ShapeBox(
        kind="textbox",
        box=slot.box,
        z=slot.z,
        content=content,
        font_size=FontScale.get(key, mood) if key else None,
        bold=slot.bold if bold is None else bold,
        color=color,
    )


# ── 扩展原型共用助手(M3) ─────────────────────────────────────────

def _gtb(col: int, row: int, col_span: int, row_span: int, content: str, *,
         font_size: Optional[int] = None, bold: bool = False, color: Optional[str] = None,
         z: int = 2, align: Optional[str] = None) -> ShapeBox:
    """按网格区构造文本框。"""
    return ShapeBox(kind="textbox", box=DEFAULT_GRID.region(col, row, col_span, row_span),
                    z=z, content=content, font_size=font_size, bold=bold,
                    color=color, align=align)


def _fit_size(state: RenderState, text: str, box: Box, base_pt: int,
              min_pt: int = 12) -> int:
    """按画布实际尺寸做容量收缩。"""
    w_in, h_in = state.canvas_size()
    return fit_font(text, box.w * w_in, box.h * h_in, base_pt, min_pt=min_pt)


def _strip_section_prefix(title: str, subtitle: Optional[str]):
    """剥离 LLM 写进 title 的'第X部分/章'序号前缀,序号由渲染器统一派生。"""
    title = (title or "").strip()
    m = _SECTION_PREFIX_RE.match(title)
    if m:
        stripped = (m.group(1) or "").strip()
        if stripped:
            return stripped, subtitle
        if subtitle:
            # title 只剩序号(如"第三部分"),章节名落在 subtitle,对调
            return subtitle, None
    # 剥完为空且无 subtitle:保留原 title 兜底,避免空标题页
    return title, subtitle


# ── classic 系列 ──────────────────────────────────────────────────

def build_title(s: SlideContent, theme: ThemeConfig, state: RenderState,
                schema: CompositionSchema) -> PageLayout:
    shapes = [
        _textbox(schema, "title", s.title, s.mood, bold=True, color=theme.primary_color),
    ]
    if s.subtitle:
        shapes.append(_textbox(schema, "subtitle", s.subtitle, s.mood,
                               color=theme.secondary_color))
    slot = _slot(schema, "underline")
    shapes.append(ShapeBox(kind="line", box=slot.box, z=slot.z, color=theme.accent_color))
    return PageLayout(background=theme.background_color, shapes=shapes)


_SECTION_PREFIX_RE = re.compile(
    r"^第[一二三四五六七八九十百\d]+\s*(?:部分|章|讲|节)\s*[：:、.．\-—]*\s*(.*)$"
)


def build_section(s: SlideContent, theme: ThemeConfig, state: RenderState,
                  schema: CompositionSchema) -> PageLayout:
    state.section_seq += 1
    title, subtitle = _strip_section_prefix(s.title, s.subtitle)

    shapes = [
        ShapeBox(kind="rect", box=_slot(schema, "bar").box, z=0,
                 fill=theme.accent_color),
        _textbox(schema, "kicker", f"第{cn_section_num(state.section_seq)}部分",
                 s.mood, color=theme.accent_color),
        _textbox(schema, "name", title, s.mood, bold=True, color=theme.primary_color),
    ]
    if subtitle:
        shapes.append(_textbox(schema, "subtitle", subtitle, s.mood,
                               color=theme.secondary_color))
    return PageLayout(background=theme.background_color, shapes=shapes)


def build_paragraph(s: SlideContent, theme: ThemeConfig, state: RenderState,
                    schema: CompositionSchema) -> PageLayout:
    shapes = [_textbox(schema, "title", s.title, s.mood, bold=True,
                       color=theme.primary_color)]
    if s.subtitle:
        shapes.append(_textbox(schema, "subtitle", s.subtitle, s.mood,
                               color=theme.secondary_color))
        body_name = "body_sub"
    else:
        body_name = "body"
    text = "    ".join(s.point_list())
    shapes.append(_textbox(schema, body_name, text, s.mood, color=theme.primary_color))
    return PageLayout(background=theme.background_color, shapes=shapes)


def build_bullets(s: SlideContent, theme: ThemeConfig, state: RenderState,
                  schema: CompositionSchema) -> PageLayout:
    shapes = [_textbox(schema, "title", s.title, s.mood, bold=True,
                       color=theme.primary_color)]
    if s.subtitle:
        shapes.append(_textbox(schema, "subtitle", s.subtitle, s.mood,
                               color=theme.secondary_color))
    bullet_text = "\n".join(f"• {b}" for b in s.point_list())
    shapes.append(_textbox(schema, "bullets", bullet_text, s.mood,
                           color=theme.primary_color))
    return PageLayout(background=theme.background_color, shapes=shapes)


def build_two_col(s: SlideContent, theme: ThemeConfig, state: RenderState,
                  schema: CompositionSchema) -> PageLayout:
    shapes = [_textbox(schema, "title", s.title, s.mood, bold=True,
                       color=theme.primary_color)]
    if s.subtitle:
        shapes.append(_textbox(schema, "subtitle", s.subtitle, s.mood,
                               color=theme.secondary_color))

    bullets = s.point_list()
    mid = (len(bullets) + 1) // 2
    left_text = "\n".join(f"• {b}" for b in bullets[:mid])
    right_text = "\n".join(f"• {b}" for b in bullets[mid:])

    # 左右卡片底色(z=0 置于文字之下)
    shapes.append(ShapeBox(kind="rect", box=_slot(schema, "card_left").box, z=0,
                           fill=lighten(theme.primary_color)))
    shapes.append(ShapeBox(kind="rect", box=_slot(schema, "card_right").box, z=0,
                           fill=lighten(theme.accent_color)))
    # 中缝竖分隔线
    divider = _slot(schema, "divider")
    shapes.append(ShapeBox(kind="line", box=divider.box, z=divider.z,
                           color=theme.secondary_color))
    # 左右栏文字(z=2 置于卡片之上)
    shapes.append(_textbox(schema, "text_left", left_text, s.mood,
                           color=theme.primary_color))
    shapes.append(_textbox(schema, "text_right", right_text, s.mood,
                           color=theme.primary_color))
    return PageLayout(background=theme.background_color, shapes=shapes)


def build_quote(s: SlideContent, theme: ThemeConfig, state: RenderState,
                schema: CompositionSchema) -> PageLayout:
    mark = _slot(schema, "mark")
    shapes = [
        ShapeBox(kind="textbox", box=mark.box, z=mark.z, content="\u201C",
                 font_size=120, bold=True, color=theme.accent_color),
        _textbox(schema, "text", s.quote or s.title, s.mood, bold=True,
                 color=theme.primary_color),
    ]
    if s.subtitle:
        shapes.append(_textbox(schema, "subtitle", s.subtitle, s.mood,
                               color=theme.secondary_color))
    return PageLayout(background=theme.background_color, shapes=shapes)


def build_image(s: SlideContent, theme: ThemeConfig, state: RenderState,
                schema: CompositionSchema) -> PageLayout:
    shapes = [_textbox(schema, "title", s.title, s.mood, bold=True,
                       color=theme.primary_color)]
    image_slot = _slot(schema, "image")
    if s.image_url:
        shapes.append(ShapeBox(kind="image", box=image_slot.box, z=image_slot.z,
                               image_path=s.image_url))
    else:
        shapes.append(ShapeBox(kind="rect", box=image_slot.box, z=image_slot.z,
                               fill=theme.secondary_color))
    if s.image_prompt:
        shapes.append(_textbox(schema, "caption", f"[图片提示] {s.image_prompt}",
                               s.mood, color=theme.secondary_color))
    return PageLayout(background=theme.background_color, shapes=shapes)


def build_summary(s: SlideContent, theme: ThemeConfig, state: RenderState,
                  schema: CompositionSchema) -> PageLayout:
    shapes = [_textbox(schema, "title", s.title, s.mood, bold=True,
                       color=theme.primary_color)]
    bullet_text = "\n".join(f"✓ {b}" for b in s.point_list())
    shapes.append(_textbox(schema, "list", bullet_text, s.mood,
                           color=theme.primary_color))
    return PageLayout(background=theme.background_color, shapes=shapes)


# ── 扩展原型(M3):几何按网格现算,字号按容量收缩 ───────────────────

def build_title_center(s: SlideContent, theme: ThemeConfig, state: RenderState,
                       schema: CompositionSchema) -> PageLayout:
    title_box = DEFAULT_GRID.region(0, 2, 12, 2)
    shapes = [_gtb(0, 2, 12, 2, s.title,
                   font_size=_fit_size(state, s.title, title_box, FontScale.base("title_main")),
                   bold=True, color=theme.primary_color, align="center")]
    if s.subtitle:
        sub_box = DEFAULT_GRID.region(1, 4, 10, 1)
        shapes.append(_gtb(1, 4, 10, 1, s.subtitle,
                           font_size=_fit_size(state, s.subtitle, sub_box,
                                               FontScale.base("title_sub"), min_pt=14),
                           color=theme.secondary_color, align="center"))
    # 居中下划线(h=0 直线)
    underline_y = DEFAULT_GRID.region(4, 5, 4, 1).y
    shapes.append(ShapeBox(kind="line",
                           box=Box(x=0.35, y=underline_y, w=0.30, h=0.0),
                           z=1, color=theme.accent_color))
    return PageLayout(background=theme.background_color, shapes=shapes)


def build_section_number(s: SlideContent, theme: ThemeConfig, state: RenderState,
                         schema: CompositionSchema) -> PageLayout:
    state.section_seq += 1
    title, subtitle = _strip_section_prefix(s.title, s.subtitle)
    num_box = DEFAULT_GRID.region(0, 1, 4, 6)
    name_box = DEFAULT_GRID.region(4, 3, 8, 3)
    shapes = [
        _gtb(0, 1, 4, 6, f"{state.section_seq:02d}", font_size=80,
             bold=True, color=lighten(theme.accent_color, t=0.45), z=1),
        _gtb(4, 2, 8, 1, f"第{cn_section_num(state.section_seq)}部分",
             font_size=FontScale.get("section_kicker", s.mood),
             color=theme.primary_color),  # 小字号用主色保证对比度;点缀感交给左侧大编号
        _gtb(4, 3, 8, 3, title,
             font_size=_fit_size(state, title, name_box, FontScale.base("section_name")),
             bold=True, color=theme.primary_color),
    ]
    if subtitle:
        shapes.append(_gtb(4, 6, 8, 1, subtitle,
                           font_size=FontScale.get("title_sub", s.mood),
                           color=theme.secondary_color))
    return PageLayout(background=theme.background_color, shapes=shapes)


def build_paragraph_split(s: SlideContent, theme: ThemeConfig, state: RenderState,
                          schema: CompositionSchema) -> PageLayout:
    title_box = DEFAULT_GRID.region(0, 0, 12, 1)
    body_text = "    ".join(s.point_list())
    body_box = DEFAULT_GRID.region(0, 2, 7, 6)
    shapes = [
        _gtb(0, 0, 12, 1, s.title,
             font_size=_fit_size(state, s.title, title_box, FontScale.base("bullet"), min_pt=16),
             bold=True, color=theme.primary_color),
        _gtb(0, 2, 7, 6, body_text,
             font_size=_fit_size(state, body_text, body_box, FontScale.base("para"), min_pt=14),
             color=theme.primary_color),
        ShapeBox(kind="round_rect", box=DEFAULT_GRID.region(8, 2, 4, 6), z=0,
                 gradient={"start": theme.primary_color, "end": theme.accent_color,
                           "angle": 90.0}, radius=0.08),
    ]
    if s.subtitle:
        shapes.append(_gtb(0, 1, 12, 1, s.subtitle,
                           font_size=FontScale.get("title_sub", s.mood),
                           color=theme.secondary_color))
    return PageLayout(background=theme.background_color, shapes=shapes)


def _card_grid_layout(n: int):
    """n 张卡片 → (列数, 每卡列跨度, 行跨度, 起始行)。1-3 条单行,4-6 条两行,最多 4 列。"""
    cols = n if n <= 3 else (4 if n in (7, 8) else 3)
    rows = math.ceil(n / cols)
    col_span = 12 // cols
    row_span = max(1, 7 // rows)
    return cols, col_span, row_span, 1


def build_bullets_grid(s: SlideContent, theme: ThemeConfig, state: RenderState,
                       schema: CompositionSchema) -> PageLayout:
    bullets = s.point_list()
    title_box = DEFAULT_GRID.region(0, 0, 12, 1)
    shapes = [_gtb(0, 0, 12, 1, s.title,
                   font_size=_fit_size(state, s.title, title_box, FontScale.base("bullet"), min_pt=16),
                   bold=True, color=theme.primary_color)]
    cols, col_span, row_span, start_row = _card_grid_layout(len(bullets))
    for i, b in enumerate(bullets):
        col0 = (i % cols) * col_span
        row0 = start_row + (i // cols) * row_span
        card_box = DEFAULT_GRID.region(col0, row0, col_span, row_span)
        inner = Box(x=card_box.x + 0.012, y=card_box.y + 0.03,
                    w=card_box.w - 0.024, h=card_box.h - 0.06)
        shapes.append(ShapeBox(kind="round_rect", box=card_box, z=0,
                               fill=lighten(theme.primary_color if i % 2 == 0 else theme.accent_color),
                               radius=0.06))
        shapes.append(ShapeBox(kind="textbox", box=inner, z=2, content=f"• {b}",
                               font_size=_fit_size(state, f"• {b}", inner,
                                                   FontScale.base("two_col")),
                               color=theme.primary_color))
    return PageLayout(background=theme.background_color, shapes=shapes)


def build_bullets_steps(s: SlideContent, theme: ThemeConfig, state: RenderState,
                        schema: CompositionSchema) -> PageLayout:
    bullets = s.point_list()
    if not 2 <= len(bullets) <= 5:
        return build_bullets_grid(s, theme, state, schema)  # 超出步骤适用范围回退网格
    col_span = 12 // len(bullets)
    title_box = DEFAULT_GRID.region(0, 0, 12, 1)
    shapes = [_gtb(0, 0, 12, 1, s.title,
                   font_size=_fit_size(state, s.title, title_box, FontScale.base("bullet"), min_pt=16),
                   bold=True, color=theme.primary_color)]
    for i, b in enumerate(bullets):
        col0 = i * col_span
        shapes.append(_gtb(col0, 1, col_span, 1, f"{i + 1:02d}",
                           font_size=28, bold=True, color=theme.accent_color,
                           align="center"))
        text_box = DEFAULT_GRID.region(col0, 2, col_span, 5)
        shapes.append(_gtb(col0, 2, col_span, 5, b,
                           font_size=_fit_size(state, b, text_box,
                                               FontScale.base("two_col")),
                           color=theme.primary_color, align="center"))
        if i > 0:  # 步骤间连接横线(h=0)
            line_y = DEFAULT_GRID.region(col0, 1, col_span, 1)
            prev_right = DEFAULT_GRID.region(col0 - col_span, 1, col_span, 1)
            shapes.append(ShapeBox(kind="line",
                                   box=Box(x=prev_right.x + prev_right.w, y=line_y.y + 0.04,
                                           w=DEFAULT_GRID.gutter, h=0.0),
                                   z=1, color=theme.secondary_color))
    return PageLayout(background=theme.background_color, shapes=shapes)


def build_two_col_asymmetric(s: SlideContent, theme: ThemeConfig, state: RenderState,
                             schema: CompositionSchema) -> PageLayout:
    bullets = s.point_list()
    left_text = "\n".join(f"• {b}" for b in bullets)
    title_box = DEFAULT_GRID.region(0, 0, 12, 1)
    left_box = DEFAULT_GRID.region(0, 1, 7, 6)
    panel = DEFAULT_GRID.region(7, 1, 5, 6)
    inner = Box(x=panel.x + 0.015, y=panel.y + 0.05, w=panel.w - 0.03, h=panel.h - 0.1)
    highlight = s.subtitle or bullets[0]
    shapes = [
        _gtb(0, 0, 12, 1, s.title,
             font_size=_fit_size(state, s.title, title_box, FontScale.base("bullet"), min_pt=16),
             bold=True, color=theme.primary_color),
        _gtb(0, 1, 7, 6, left_text,
             font_size=_fit_size(state, left_text, left_box, FontScale.base("two_col")),
             color=theme.primary_color),
        ShapeBox(kind="round_rect", box=panel, z=0,
                 gradient={"start": theme.accent_color, "end": theme.primary_color,
                           "angle": 115.0}, radius=0.06),
        ShapeBox(kind="textbox", box=inner, z=2, content=highlight,
                 font_size=_fit_size(state, highlight, inner,
                                     FontScale.base("section_name"), min_pt=14),
                 bold=True, color=theme.background_color),  # 深色渐变面板上用底色文字保证对比
    ]
    return PageLayout(background=theme.background_color, shapes=shapes)


def build_image_left_text(s: SlideContent, theme: ThemeConfig, state: RenderState,
                          schema: CompositionSchema) -> PageLayout:
    image_box = DEFAULT_GRID.region(0, 0, 6, 8)
    title_box = DEFAULT_GRID.region(6, 0, 6, 2)
    shapes = [
        ShapeBox(kind="image" if s.image_url else "rect", box=image_box, z=1,
                 image_path=s.image_url,
                 fill=None if s.image_url else lighten(theme.secondary_color)),
        _gtb(6, 0, 6, 2, s.title,
             font_size=_fit_size(state, s.title, title_box, FontScale.base("bullet"), min_pt=16),
             bold=True, color=theme.primary_color),
    ]
    if s.image_prompt:
        shapes.append(_gtb(6, 6, 6, 1, f"[图片提示] {s.image_prompt}",
                           font_size=FontScale.get("image_cap", s.mood),
                           color=theme.secondary_color))
    return PageLayout(background=theme.background_color, shapes=shapes)


def build_image_top(s: SlideContent, theme: ThemeConfig, state: RenderState,
                    schema: CompositionSchema) -> PageLayout:
    title_box = DEFAULT_GRID.region(0, 0, 12, 1)
    image_box = DEFAULT_GRID.region(1, 1, 10, 5)
    shapes = [
        _gtb(0, 0, 12, 1, s.title,
             font_size=_fit_size(state, s.title, title_box, FontScale.base("bullet"), min_pt=16),
             bold=True, color=theme.primary_color),
        ShapeBox(kind="image" if s.image_url else "rect", box=image_box, z=1,
                 image_path=s.image_url,
                 fill=None if s.image_url else lighten(theme.secondary_color)),
    ]
    if s.image_prompt:
        shapes.append(_gtb(0, 6, 12, 1, f"[图片提示] {s.image_prompt}",
                           font_size=FontScale.get("image_cap", s.mood),
                           color=theme.secondary_color, align="center"))
    return PageLayout(background=theme.background_color, shapes=shapes)


def build_quote_center(s: SlideContent, theme: ThemeConfig, state: RenderState,
                       schema: CompositionSchema) -> PageLayout:
    text = s.quote or s.title
    text_box = DEFAULT_GRID.region(0, 2, 12, 4)
    shapes = [
        _gtb(5, 1, 2, 1, "\u201C", font_size=60, bold=True,
             color=theme.accent_color, align="center"),
        _gtb(0, 2, 12, 4, text,
             font_size=_fit_size(state, text, text_box, FontScale.base("quote"), min_pt=18),
             bold=True, color=theme.primary_color, align="center"),
    ]
    if s.subtitle:
        shapes.append(_gtb(2, 6, 8, 1, s.subtitle,
                           font_size=FontScale.get("title_sub", s.mood),
                           color=theme.secondary_color, align="center"))
    return PageLayout(background=theme.background_color, shapes=shapes)


def build_summary_kpi(s: SlideContent, theme: ThemeConfig, state: RenderState,
                      schema: CompositionSchema) -> PageLayout:
    points = s.point_list()
    pairs = []
    for p in points:
        if ":" in p or "：" in p:
            num, _, label = re.split(r"[:：]", p, maxsplit=1)
        else:
            num, label = p, ""
        pairs.append((num.strip(), label.strip()))
    title_box = DEFAULT_GRID.region(0, 0, 12, 1)
    shapes = [_gtb(0, 0, 12, 1, s.title,
                   font_size=_fit_size(state, s.title, title_box, FontScale.base("bullet"), min_pt=16),
                   bold=True, color=theme.primary_color)]
    n = len(pairs)
    col_span = 12 // n
    for i, (num, label) in enumerate(pairs):
        col0 = i * col_span
        num_box = DEFAULT_GRID.region(col0, 2, col_span, 3)
        shapes.append(_gtb(col0, 2, col_span, 3, num,
                           font_size=_fit_size(state, num, num_box, 48, min_pt=24),
                           bold=True, color=theme.accent_color, align="center"))
        if label:
            shapes.append(_gtb(col0, 5, col_span, 1, label,
                               font_size=FontScale.get("title_sub", s.mood),
                               color=theme.secondary_color, align="center"))
        if i > 0:  # KPI 间分隔竖线(w=0)
            sep_x = DEFAULT_GRID.region(col0, 2, col_span, 4).x
            mid_y = DEFAULT_GRID.region(col0, 2, col_span, 4).y
            shapes.append(ShapeBox(kind="line",
                                   box=Box(x=sep_x - DEFAULT_GRID.gutter / 2, y=mid_y + 0.05,
                                           w=0.0, h=0.25),
                                   z=1, color=lighten(theme.secondary_color)))
    return PageLayout(background=theme.background_color, shapes=shapes)


BUILDERS: Dict[str, Builder] = {
    "title_classic": build_title,
    "section_classic": build_section,
    "paragraph_classic": build_paragraph,
    "bullets_classic": build_bullets,
    "two_col_classic": build_two_col,
    "quote_classic": build_quote,
    "image_classic": build_image,
    "summary_classic": build_summary,
    "title_center": build_title_center,
    "section_number": build_section_number,
    "paragraph_split": build_paragraph_split,
    "bullets_grid": build_bullets_grid,
    "bullets_steps": build_bullets_steps,
    "two_col_asymmetric": build_two_col_asymmetric,
    "image_left_text": build_image_left_text,
    "image_top": build_image_top,
    "quote_center": build_quote_center,
    "summary_kpi": build_summary_kpi,
}


def register_builder(schema_id: str, builder: Builder) -> None:
    """M3 起新原型的 builder 注册入口。"""
    BUILDERS[schema_id] = builder
