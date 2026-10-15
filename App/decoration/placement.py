"""装饰放置:留白感知 + 差异化策略

1. 从内容盒计算占用,过滤与内容相交的候选装饰区;
2. 按 token 家族优先序选母题,放入第一个可用区;
3. 相邻页家族去重(motif_history),保证差异化。
"""
from __future__ import annotations

from typing import List, Optional, Tuple

from App.models import Box, PageLayout, ThemeConfig
from App.layout_engine.state import RenderState
from App.decoration import motifs
from App.decoration.tokens import StyleTokens

# 候选装饰区(相对画布):角落/边缘条带,面积足够放母题
CANDIDATE_ZONES: List[Tuple[str, Box]] = [
    ("top_right", Box(x=0.64, y=0.07, w=0.30, h=0.15)),
    ("bottom_left", Box(x=0.07, y=0.80, w=0.26, h=0.14)),
    ("top_left", Box(x=0.07, y=0.07, w=0.22, h=0.12)),
    ("bottom_right", Box(x=0.68, y=0.79, w=0.26, h=0.15)),
    ("right_mid", Box(x=0.82, y=0.40, w=0.12, h=0.22)),
]

# 装饰与内容盒允许的最大交叠比例(装饰区被内容占据超过该比例即弃用)
_MAX_OVERLAP_RATIO = 0.08


def _overlap_ratio(a: Box, b: Box) -> float:
    ix = min(a.x + a.w, b.x + b.w) - max(a.x, b.x)
    iy = min(a.y + a.h, b.y + b.h) - max(a.y, b.y)
    if ix <= 0 or iy <= 0:
        return 0.0
    area_a = a.w * a.h
    if area_a <= 0:
        return 0.0
    return (ix * iy) / area_a


def free_zones(layout: PageLayout) -> List[Tuple[str, Box]]:
    """未被内容占据的候选装饰区,按候选顺序返回。"""
    content_boxes = [s.box for s in layout.shapes]
    result = []
    for name, zone in CANDIDATE_ZONES:
        if all(_overlap_ratio(zone, cb) <= _MAX_OVERLAP_RATIO for cb in content_boxes):
            result.append((name, zone))
    return result


def decorate_page(layout: PageLayout, theme: ThemeConfig, state: RenderState,
                  tokens: StyleTokens, page_no: int) -> None:
    """就地往 PageLayout 追加装饰。legacy 模式不调用(golden 基线不受影响)。"""
    zones = free_zones(layout)
    if not zones:
        return

    budget = min(tokens.max_per_page, len(zones))
    placed = 0
    for family in tokens.motif_families:
        if placed >= budget:
            break
        # 相邻页差异化:该家族若与前 2 页签名同族则跳过
        recent = state.motif_history[-2:]
        if any(sig.startswith(family + "@") for sig in recent):
            continue
        # 优先选与上页不同方位的区(错位放置)
        zone_name, zone = zones[placed % len(zones)]
        shapes = motifs.generate(family, zone, theme, tokens)
        if not shapes:
            continue
        layout.shapes.extend(shapes)
        state.motif_history.append(f"{family}@{zone_name}")
        placed += 1
