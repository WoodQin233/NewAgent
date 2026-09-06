"""
PPT 生成器

用法（接口调用）：
    from App.models import LayoutInfo
    from App.generator import PPTGenerator

    layout = LayoutInfo(...)                  # 由 analyzer 或其他来源构造
    output_path = PPTGenerator.generate(layout)   # 返回 output/<标题>.pptx 路径
"""
from __future__ import annotations

import os
from typing import Dict, List, Optional, Tuple

from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE

from App.models import (
    LayoutInfo,
    SlideContent,
    OutlineItem,
    Box,
    ShapeBox,
    PageLayout,
    ThemeConfig,
    PageType,
    Mood,
)


# ─────────────────────────────── 工具函数 ───────────────────────────────

def _hex_to_rgb(hex_color: str) -> RGBColor:
    """将 #RRGGBB 字符串转换为 python-pptx 的 RGBColor"""
    hex_color = hex_color.lstrip("#")
    return RGBColor(int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16))


def _box(box: Box, cw: float, ch: float) -> Tuple[float, float, float, float]:
    """把相对 Box 换算成英寸 (left, top, width, height)"""
    return box.x * cw, box.y * ch, box.w * cw, box.h * ch


# ─────────────────────────────── 字号策略 ───────────────────────────────

class FontScale:
    """按 Mood 调整后的字号表。所有数字单位:pt"""

    _BASE = {
        "title_main":   44,
        "title_sub":    20,
        "section_no":   96,
        "section_name": 32,
        "para":         22,
        "bullet":       24,
        "two_col":      22,
        "quote":        36,
        "summary":      24,
        "image_cap":    14,
    }

    _SCALE = {
        Mood.PROFESSIONAL: 1.0,
        Mood.TECH:         1.1,
        Mood.PLAYFUL:      0.9,
        Mood.MINIMAL:      0.85,
        Mood.BOLD:         1.15,
    }

    @classmethod
    def get(cls, key: str, mood: Optional[Mood]) -> int:
        base = cls._BASE[key]
        scale = cls._SCALE.get(mood, 1.0) if mood else 1.0
        return max(8, int(round(base * scale)))


# ─────────────────────────────── 渲染策略 ───────────────────────────────

class PageRenderer:
    """把单页内容(OutlineItem + 可选 SlideContent 覆盖)转成 PageLayout。"""

    def __init__(self, theme: ThemeConfig):
        self.theme = theme

    def render(
        self,
        outline_item: OutlineItem,
        detail_slide: Optional[SlideContent] = None,
    ) -> PageLayout:
        """渲染单页。detail_slide 可选,字段会覆盖 outline_item。"""
        merged = self._merge(outline_item, detail_slide)
        handler = self._DISPATCH.get(merged.type)
        if handler is None:
            return self._render_paragraph(merged)
        return handler(self, merged)

    def _merge(
        self,
        item: OutlineItem,
        detail: Optional[SlideContent],
    ) -> SlideContent:
        """把 outline_item 与可选 detail 合并成最终 SlideContent。

        用 model_construct 而不是 SlideContent(**kwargs),因为 SlideContent 的
        model_validator 会强制 QUOTE 有 quote、IMAGE 有 image_url 等,而 outline
        阶段 AI 不会写这些字段;缺失由对应 _render_xxx 自己兜底。
        """
        merged: dict = dict(
            page=item.page,
            type=item.type,
            title=item.title,
            subtitle=item.subtitle,
            points=item.points,
            mood=item.mood,
        )
        if detail is not None:
            for f in ("subtitle", "points", "quote", "image_prompt",
                      "image_url", "primary_color", "accent_color", "mood"):
                v = getattr(detail, f)
                if v is not None:
                    merged[f] = v
        return SlideContent.model_construct(**merged)

    _DISPATCH: Dict[PageType, object] = {}

    # ── 各类型模板 ───────────────────────────────────────────────

    def _render_title(self, s: SlideContent) -> PageLayout:
        shapes: List[ShapeBox] = []
        shapes.append(ShapeBox(
            kind="textbox",
            box=Box(x=0.1, y=0.30, w=0.8, h=0.30),
            z=2, content=s.title,
            font_size=FontScale.get("title_main", s.mood),
            bold=True, color=self.theme.primary_color,
        ))
        if s.subtitle:
            shapes.append(ShapeBox(
                kind="textbox",
                box=Box(x=0.15, y=0.62, w=0.7, h=0.10),
                z=2, content=s.subtitle,
                font_size=FontScale.get("title_sub", s.mood),
                color=self.theme.secondary_color,
            ))
        shapes.append(ShapeBox(
            kind="line",
            box=Box(x=0.35, y=0.78, w=0.30, h=0.0),
            z=1, color=self.theme.accent_color,
        ))
        return PageLayout(background=self.theme.background_color, shapes=shapes)

    def _render_section(self, s: SlideContent) -> PageLayout:
        shapes: List[ShapeBox] = []
        shapes.append(ShapeBox(
            kind="textbox",
            box=Box(x=0.05, y=0.20, w=0.30, h=0.60),
            z=2, content=f"{s.page:02d}",
            font_size=FontScale.get("section_no", s.mood),
            bold=True, color=self.theme.accent_color,
        ))
        shapes.append(ShapeBox(
            kind="textbox",
            box=Box(x=0.40, y=0.35, w=0.55, h=0.30),
            z=2, content=s.title,
            font_size=FontScale.get("section_name", s.mood),
            bold=True, color=self.theme.primary_color,
        ))
        if s.subtitle:
            shapes.append(ShapeBox(
                kind="textbox",
                box=Box(x=0.40, y=0.62, w=0.55, h=0.10),
                z=2, content=s.subtitle,
                font_size=FontScale.get("title_sub", s.mood),
                color=self.theme.secondary_color,
            ))
        return PageLayout(background=self.theme.background_color, shapes=shapes)

    def _render_paragraph(self, s: SlideContent) -> PageLayout:
        shapes: List[ShapeBox] = []
        shapes.append(ShapeBox(
            kind="textbox",
            box=Box(x=0.06, y=0.08, w=0.88, h=0.12),
            z=2, content=s.title,
            font_size=FontScale.get("bullet", s.mood),
            bold=True, color=self.theme.primary_color,
        ))
        body_top = 0.26
        body_h = 0.66
        if s.subtitle:
            shapes.append(ShapeBox(
                kind="textbox",
                box=Box(x=0.06, y=0.20, w=0.88, h=0.06),
                z=2, content=s.subtitle,
                font_size=FontScale.get("title_sub", s.mood),
                color=self.theme.secondary_color,
            ))
            body_top = 0.28
            body_h = 0.64
        text = "    ".join(s.point_list())
        shapes.append(ShapeBox(
            kind="textbox",
            box=Box(x=0.06, y=body_top, w=0.88, h=body_h),
            z=2, content=text,
            font_size=FontScale.get("para", s.mood),
            color=self.theme.primary_color,
        ))
        return PageLayout(background=self.theme.background_color, shapes=shapes)

    def _render_bullets(self, s: SlideContent) -> PageLayout:
        shapes: List[ShapeBox] = []
        shapes.append(ShapeBox(
            kind="textbox",
            box=Box(x=0.06, y=0.08, w=0.88, h=0.12),
            z=2, content=s.title,
            font_size=FontScale.get("bullet", s.mood),
            bold=True, color=self.theme.primary_color,
        ))
        if s.subtitle:
            shapes.append(ShapeBox(
                kind="textbox",
                box=Box(x=0.06, y=0.20, w=0.88, h=0.06),
                z=2, content=s.subtitle,
                font_size=FontScale.get("title_sub", s.mood),
                color=self.theme.secondary_color,
            ))
        bullets = s.point_list()
        bullet_text = "\n".join(f"• {b}" for b in bullets)
        shapes.append(ShapeBox(
            kind="textbox",
            box=Box(x=0.10, y=0.30, w=0.80, h=0.62),
            z=2, content=bullet_text,
            font_size=FontScale.get("bullet", s.mood),
            color=self.theme.primary_color,
        ))
        return PageLayout(background=self.theme.background_color, shapes=shapes)

    def _render_two_col(self, s: SlideContent) -> PageLayout:
        shapes: List[ShapeBox] = []
        shapes.append(ShapeBox(
            kind="textbox",
            box=Box(x=0.06, y=0.08, w=0.88, h=0.12),
            z=2, content=s.title,
            font_size=FontScale.get("bullet", s.mood),
            bold=True, color=self.theme.primary_color,
        ))
        bullets = s.point_list()
        mid = (len(bullets) + 1) // 2
        left_text = "\n".join(f"• {b}" for b in bullets[:mid])
        right_text = "\n".join(f"• {b}" for b in bullets[mid:])
        shapes.append(ShapeBox(
            kind="textbox",
            box=Box(x=0.05, y=0.26, w=0.43, h=0.66),
            z=2, content=left_text,
            font_size=FontScale.get("two_col", s.mood),
            color=self.theme.primary_color,
        ))
        shapes.append(ShapeBox(
            kind="textbox",
            box=Box(x=0.52, y=0.26, w=0.43, h=0.66),
            z=2, content=right_text,
            font_size=FontScale.get("two_col", s.mood),
            color=self.theme.primary_color,
        ))
        return PageLayout(background=self.theme.background_color, shapes=shapes)

    def _render_quote(self, s: SlideContent) -> PageLayout:
        shapes: List[ShapeBox] = []
        shapes.append(ShapeBox(
            kind="textbox",
            box=Box(x=0.05, y=0.10, w=0.20, h=0.25),
            z=1, content="\u201C", font_size=120, bold=True,
            color=self.theme.accent_color,
        ))
        shapes.append(ShapeBox(
            kind="textbox",
            box=Box(x=0.10, y=0.30, w=0.80, h=0.35),
            z=2, content=s.quote or s.title,
            font_size=FontScale.get("quote", s.mood),
            bold=True, color=self.theme.primary_color,
        ))
        if s.subtitle:
            shapes.append(ShapeBox(
                kind="textbox",
                box=Box(x=0.10, y=0.70, w=0.80, h=0.10),
                z=2, content=s.subtitle,
                font_size=FontScale.get("title_sub", s.mood),
                color=self.theme.secondary_color,
            ))
        return PageLayout(background=self.theme.background_color, shapes=shapes)

    def _render_image(self, s: SlideContent) -> PageLayout:
        shapes: List[ShapeBox] = []
        shapes.append(ShapeBox(
            kind="textbox",
            box=Box(x=0.06, y=0.08, w=0.88, h=0.12),
            z=2, content=s.title,
            font_size=FontScale.get("bullet", s.mood),
            bold=True, color=self.theme.primary_color,
        ))
        if s.image_url:
            shapes.append(ShapeBox(
                kind="image",
                box=Box(x=0.20, y=0.24, w=0.60, h=0.55),
                z=1, image_path=s.image_url,
            ))
        else:
            shapes.append(ShapeBox(
                kind="rect",
                box=Box(x=0.20, y=0.24, w=0.60, h=0.55),
                z=1, fill=self.theme.secondary_color,
            ))
        if s.image_prompt:
            shapes.append(ShapeBox(
                kind="textbox",
                box=Box(x=0.10, y=0.82, w=0.80, h=0.10),
                z=2, content=f"[图片提示] {s.image_prompt}",
                font_size=FontScale.get("image_cap", s.mood),
                color=self.theme.secondary_color,
            ))
        return PageLayout(background=self.theme.background_color, shapes=shapes)

    def _render_summary(self, s: SlideContent) -> PageLayout:
        shapes: List[ShapeBox] = []
        shapes.append(ShapeBox(
            kind="textbox",
            box=Box(x=0.06, y=0.08, w=0.88, h=0.12),
            z=2, content=s.title,
            font_size=FontScale.get("bullet", s.mood),
            bold=True, color=self.theme.primary_color,
        ))
        bullets = s.point_list()
        bullet_text = "\n".join(f"✓ {b}" for b in bullets)
        shapes.append(ShapeBox(
            kind="textbox",
            box=Box(x=0.10, y=0.26, w=0.80, h=0.66),
            z=2, content=bullet_text,
            font_size=FontScale.get("summary", s.mood),
            bold=True, color=self.theme.primary_color,
        ))
        return PageLayout(background=self.theme.background_color, shapes=shapes)


PageRenderer._DISPATCH = {
    PageType.TITLE:     PageRenderer._render_title,
    PageType.SECTION:   PageRenderer._render_section,
    PageType.PARAGRAPH: PageRenderer._render_paragraph,
    PageType.BULLETS:   PageRenderer._render_bullets,
    PageType.TWO_COL:   PageRenderer._render_two_col,
    PageType.IMAGE:     PageRenderer._render_image,
    PageType.QUOTE:     PageRenderer._render_quote,
    PageType.SUMMARY:   PageRenderer._render_summary,
}


# ─────────────────────────────── 落盘 ───────────────────────────────

class LayoutApplier:
    """把 PageLayout 写到一张空的 python-pptx 幻灯片上。"""

    @staticmethod
    def apply(slide, layout: PageLayout, canvas_w: float, canvas_h: float) -> None:
        LayoutApplier._apply_background(slide, layout)
        shapes = sorted(layout.shapes, key=lambda s: s.z)
        for sb in shapes:
            LayoutApplier._apply_shape(slide, sb, canvas_w, canvas_h)

    @staticmethod
    def _apply_background(slide, layout: PageLayout) -> None:
        bg = layout.background or "#FFFFFF"
        fill = slide.background.fill
        fill.solid()
        fill.fore_color.rgb = _hex_to_rgb(bg)

    @staticmethod
    def _apply_shape(slide, sb: ShapeBox, cw: float, ch: float) -> None:
        left, top, width, height = _box(sb.box, cw, ch)
        if sb.kind == "textbox":
            tb = slide.shapes.add_textbox(Inches(left), Inches(top), Inches(width), Inches(height))
            tf = tb.text_frame
            tf.word_wrap = True
            tf.vertical_anchor = MSO_ANCHOR.MIDDLE
            text = sb.content or ""
            for i, line in enumerate(text.split("\n")):
                p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
                p.alignment = PP_ALIGN.LEFT
                run = p.add_run()
                run.text = line
                run.font.name = "Microsoft YaHei"
                if sb.font_size:
                    run.font.size = Pt(sb.font_size)
                run.font.bold = sb.bold
                if sb.color:
                    run.font.color.rgb = _hex_to_rgb(sb.color)
        elif sb.kind == "rect":
            rect = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE,
                                           Inches(left), Inches(top),
                                           Inches(width), Inches(height))
            if sb.fill:
                rect.fill.solid()
                rect.fill.fore_color.rgb = _hex_to_rgb(sb.fill)
            else:
                rect.fill.background()
        elif sb.kind == "line":
            slide.shapes.add_connector(
                1,
                Inches(left), Inches(top),
                Inches(left + width), Inches(top + height),
            )
        elif sb.kind == "image":
            if sb.image_path:
                try:
                    slide.shapes.add_picture(
                        sb.image_path,
                        Inches(left), Inches(top),
                        Inches(width), Inches(height),
                    )
                except Exception:
                    rect = slide.shapes.add_shape(
                        MSO_SHAPE.RECTANGLE,
                        Inches(left), Inches(top),
                        Inches(width), Inches(height),
                    )
                    rect.fill.solid()
                    rect.fill.fore_color.rgb = RGBColor(0xE5, 0xE7, 0xEB)


# ─────────────────────────────── 渲染器主体 ───────────────────────────────

class PPTGenerator:
    """根据 LayoutInfo 渲染 PPT"""

    # 使用空白模板作为底板，避免依赖模板中的占位符。
    DEFAULT_TEMPLATE = "Templates/blank.pptx"

    @staticmethod
    def generate(layout: LayoutInfo) -> str:
        """
        主入口：渲染整个演示文稿并保存为 .pptx 文件，返回输出路径。

        流程：
        1. 加载空白模板；
        2. 根据 layout.canvas 设置幻灯片尺寸；
        3. 遍历 layout.outline.items，逐页渲染；
        4. 保存到 output/<title>.pptx。
        """
        # ── 1. 加载模板 ───────────────────────────────────────────────
        prs = Presentation(PPTGenerator.DEFAULT_TEMPLATE)

        # ── 2. 设置画布尺寸（按 layout.canvas 的英寸数） ──────────────
        prs.slide_width = Inches(layout.canvas.width)
        prs.slide_height = Inches(layout.canvas.height)

        # ── 3. 建立 detail 索引（按 page 快速查） ──────────────────────
        detail_index: Dict[int, SlideContent] = {}
        if layout.detail is not None:
            for ds in layout.detail.slides:
                detail_index[ds.page] = ds

        # ── 4. 逐页渲染 ───────────────────────────────────────────────
        renderer = PageRenderer(theme=layout.theme)
        blank_layout = prs.slide_layouts[6]
        cw, ch = layout.canvas.width, layout.canvas.height
        for item in layout.outline.items:
            page_layout = renderer.render(item, detail_index.get(item.page))
            slide = prs.slides.add_slide(blank_layout)
            LayoutApplier.apply(slide, page_layout, cw, ch)

        # ── 5. 保存 ───────────────────────────────────────────────────
        output_dir = "output"
        os.makedirs(output_dir, exist_ok=True)
        safe_title = (layout.outline.title or "presentation").strip() or "presentation"
        output_path = os.path.join(output_dir, f"{safe_title}.pptx")
        prs.save(output_path)
        return output_path
