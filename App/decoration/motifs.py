"""装饰母题库

每个母题是参数化生成器:输入(区域盒, 风格 token, 主题) → 一组 ShapeBox。
装饰统一约定:z=0(压在内容之下)、低透明度、不出画布、不与内容盒相交
(相交过滤由 placement 负责,母题本身只负责在给定区域内生成)。
"""
from __future__ import annotations

from typing import Callable, Dict, List

from App.models import Box, ShapeBox, ThemeConfig
from App.decoration.tokens import StyleTokens

MotifFn = Callable[[Box, ThemeConfig, StyleTokens], List[ShapeBox]]

# 母题签名 = 家族 + 量化参数(M5 相似度/去重用)
MOTIFS: Dict[str, MotifFn] = {}


def _register(family: str):
    def deco(fn: MotifFn) -> MotifFn:
        MOTIFS[family] = fn
        return fn
    return deco


def _round(v: float) -> float:
    return round(v, 4)


@_register("dots")
def motif_dots(zone: Box, theme: ThemeConfig, tokens: StyleTokens) -> List[ShapeBox]:
    """点阵:3×2 小圆点。"""
    cols, rows = 3, 2
    r = min(zone.w / (cols * 4), zone.h / (rows * 4))
    gap_x = r * 4
    gap_y = r * 4
    shapes = []
    for i in range(cols):
        for j in range(rows):
            cx = zone.x + r + i * gap_x
            cy = zone.y + r + j * gap_y
            d = 2 * r / 2  # 直径
            shapes.append(ShapeBox(
                kind="circle",
                box=Box(x=_round(cx - d / 2), y=_round(cy - d / 2), w=_round(d), h=_round(d)),
                z=0, fill=theme.accent_color, opacity=tokens.opacity,
            ))
    return shapes


@_register("ring")
def motif_ring(zone: Box, theme: ThemeConfig, tokens: StyleTokens) -> List[ShapeBox]:
    """同心圆环:外描边圆 + 内小圆。"""
    d_out = min(zone.w, zone.h) * 0.9
    d_in = d_out * 0.45
    cx = zone.x + zone.w / 2
    cy = zone.y + zone.h / 2
    return [
        ShapeBox(kind="circle",
                 box=Box(x=_round(cx - d_out / 2), y=_round(cy - d_out / 2),
                         w=_round(d_out), h=_round(d_out)),
                 z=0, stroke=theme.accent_color),
        ShapeBox(kind="circle",
                 box=Box(x=_round(cx - d_in / 2), y=_round(cy - d_in / 2),
                         w=_round(d_in), h=_round(d_in)),
                 z=0, fill=theme.primary_color, opacity=tokens.opacity),
    ]


@_register("block")
def motif_block(zone: Box, theme: ThemeConfig, tokens: StyleTokens) -> List[ShapeBox]:
    """渐变色块:大圆角矩形。"""
    w = zone.w * 0.9
    h = zone.h * 0.85
    return [ShapeBox(
        kind="round_rect",
        box=Box(x=_round(zone.x + (zone.w - w) / 2), y=_round(zone.y + (zone.h - h) / 2),
                w=_round(w), h=_round(h)),
        z=0, radius=tokens.radius,
        gradient={"start": theme.primary_color, "end": theme.accent_color,
                  "angle": tokens.gradient_angle},
        opacity=tokens.opacity,
    )]


@_register("line")
def motif_lines(zone: Box, theme: ThemeConfig, tokens: StyleTokens) -> List[ShapeBox]:
    """斜线组:3 条平行细线。"""
    thick = 0.008
    step = min(zone.h / 4, 0.05)
    shapes = []
    for i in range(3):
        shapes.append(ShapeBox(
            kind="rect",
            box=Box(x=_round(zone.x), y=_round(zone.y + i * step + step),
                    w=_round(min(zone.w * 0.8, 0.25)), h=_round(thick)),
            z=0, rotation=-30.0,
            fill=theme.accent_color, opacity=tokens.opacity,
        ))
    return shapes


@_register("corner_dots")
def motif_corner_dots(zone: Box, theme: ThemeConfig, tokens: StyleTokens) -> List[ShapeBox]:
    """角点组合:一大一小两圆。"""
    d_big = min(zone.w, zone.h) * 0.7
    d_small = d_big * 0.35
    return [
        ShapeBox(kind="circle",
                 box=Box(x=_round(zone.x), y=_round(zone.y + zone.h - d_big),
                         w=_round(d_big), h=_round(d_big)),
                 z=0, fill=theme.primary_color, opacity=tokens.opacity),
        ShapeBox(kind="circle",
                 box=Box(x=_round(zone.x + d_big + 0.01), y=_round(zone.y),
                         w=_round(d_small), h=_round(d_small)),
                 z=0, fill=theme.accent_color, opacity=min(1.0, tokens.opacity * 1.6)),
    ]


def generate(family: str, zone: Box, theme: ThemeConfig,
             tokens: StyleTokens) -> List[ShapeBox]:
    fn = MOTIFS.get(family)
    if fn is None:
        return []
    return fn(zone, theme, tokens)
