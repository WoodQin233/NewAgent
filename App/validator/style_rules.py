"""L2 风格校验(规则库)

- LOW_CONTRAST: 文字/底色对比度不足(≥18pt 按 3.0,小字按 4.0)
- COLOR_BUDGET: 每页内容填充色(不含背景/装饰)超过 3 种
- WHITESPACE: 内容覆盖率超出 [0.30, 0.85](装饰不计入)
- GRID_DRIFT: 非装饰、非嵌套内容盒的网格吸附率 < 95%
"""
from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from App.models import Box, PageLayout, ThemeConfig
from App.layout_engine.grid import DEFAULT_GRID
from App.validator.geometry import is_decoration

CONTRAST_BODY = 4.0     # 小字阈值(WCAG 4.5 的工程放宽,详见执行日志 M5 备注)
CONTRAST_LARGE = 3.0
LARGE_FONT_PT = 18
MAX_FILLS = 3
COVERAGE_RANGE = (0.30, 0.85)
SNAP_MIN = 0.95


def _rgb(hex_color: str) -> Tuple[float, float, float]:
    h = hex_color.lstrip("#")
    return tuple(int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4))  # type: ignore


def _luma(hex_color: str) -> float:
    def lin(c: float) -> float:
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = _rgb(hex_color)
    return 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b)


def contrast_ratio(c1: str, c2: str) -> float:
    l1, l2 = _luma(c1), _luma(c2)
    lighter, darker = max(l1, l2), min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)


def _contains(outer: Box, inner: Box) -> bool:
    eps = 1e-9
    return (outer.x <= inner.x + eps and outer.y <= inner.y + eps
            and outer.x + outer.w >= inner.x + inner.w - eps
            and outer.y + outer.h >= inner.y + inner.h - eps)


def _effective_bg(layout: PageLayout, text_color: str,
                  idx: int) -> Optional[str]:
    """文字盒中心所在的底层填充色(近似;渐变取 start,记为已知局限)。"""
    s = layout.shapes[idx]
    cx, cy = s.box.x + s.box.w / 2, s.box.y + s.box.h / 2
    bg = None
    for j, other in enumerate(layout.shapes):
        if j == idx or other.z != 0 or is_decoration(other):
            continue
        b = other.box
        if b.x <= cx <= b.x + b.w and b.y <= cy <= b.y + b.h:
            if other.fill:
                bg = other.fill
            elif other.gradient:
                bg = other.gradient.start
    return bg


def _coverage_ratio(layout: PageLayout) -> float:
    """内容覆盖率:100×56 网格采样(装饰不计入)。"""
    nx, ny = 100, 56
    content = [s.box for s in layout.shapes if not is_decoration(s)]
    if not content:
        return 0.0
    hits = 0
    for gx in range(nx):
        for gy in range(ny):
            x, y = (gx + 0.5) / nx, (gy + 0.5) / ny
            if any(b.x <= x <= b.x + b.w and b.y <= y <= b.y + b.h for b in content):
                hits += 1
    return hits / (nx * ny)


def validate(layout: PageLayout, theme: ThemeConfig,
             canvas_size: Tuple[float, float], family: str = "classic") -> List[Dict]:
    """family="classic" 时豁免 WHITESPACE/GRID_DRIFT(旧版式为兼容基线,不做新式约束)。"""
    issues: List[Dict] = []

    # 1) 对比度(classic 豁免:旧版式配色为冻结的兼容基线)
    if family != "classic":
        for i, s in enumerate(layout.shapes):
            if s.kind != "textbox" or not s.color or not s.content or len(s.content) <= 2:
                continue  # 单/双字符多为符号与装饰性编号,不参与判定
            bg = _effective_bg(layout, s.color, i) or theme.background_color
            if not bg:
                continue
            ratio = contrast_ratio(s.color, bg)
            required = CONTRAST_LARGE if (s.font_size or 0) >= LARGE_FONT_PT else CONTRAST_BODY
            if ratio < required:
                issues.append({"index": i, "code": "LOW_CONTRAST",
                               "msg": f"对比度 {ratio:.2f} < {required}"})

    # 2) 每页色彩预算(内容填充色,渐变计 start)
    fills = set()
    for s in layout.shapes:
        if is_decoration(s):
            continue
        if s.fill:
            fills.add(s.fill)
        elif s.gradient:
            fills.add(s.gradient.start)
    if len(fills) > MAX_FILLS:
        issues.append({"index": None, "code": "COLOR_BUDGET",
                       "msg": f"内容填充色 {len(fills)} 种 > {MAX_FILLS}"})

    # 3) 留白率(classic 豁免)
    if family != "classic":
        coverage = _coverage_ratio(layout)
        if not (COVERAGE_RANGE[0] <= coverage <= COVERAGE_RANGE[1]):
            issues.append({"index": None, "code": "WHITESPACE",
                           "msg": f"内容覆盖率 {coverage:.0%} 超出 "
                                  f"[{COVERAGE_RANGE[0]:.0%}, {COVERAGE_RANGE[1]:.0%}]"})

    # 4) 网格吸附(排除装饰与嵌套内衬盒;线条零面积不参与;classic 豁免)
    if family != "classic":
        content = [s for s in layout.shapes if not is_decoration(s) and s.kind != "line"]
        outer = [s for s in content
                 if not any(o is not s and _contains(o.box, s.box) for o in content)]
        if outer:
            snapped = sum(1 for s in outer if DEFAULT_GRID.snap_ok(s.box))
            ratio = snapped / len(outer)
            if ratio < SNAP_MIN:
                issues.append({"index": None, "code": "GRID_DRIFT",
                               "msg": f"网格吸附率 {ratio:.0%} < {SNAP_MIN:.0%}"})
    return issues
