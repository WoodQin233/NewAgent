"""自动修复(参数级优先,不做激进改动)

- TEXT_OVERFLOW → 容量算法收缩字号(触底仍放不下则保留 issue 由报告呈现)
- OUT_OF_BOUNDS → 收敛回安全区
- DECOR_OVERLAP → 直接移除该装饰
- 其余(对比度/色彩/留白/网格)只报告不自动改,避免静默扭曲设计意图
"""
from __future__ import annotations

from typing import Dict, List, Tuple

from App.models import PageLayout
from App.layout_engine.text_metrics import fit_font
from App.validator.geometry import SAFE, is_decoration


def repair(layout: PageLayout, issues: List[Dict],
           canvas_size: Tuple[float, float]) -> List[str]:
    """就地修复,返回动作记录(供报告追溯)。"""
    w_in, h_in = canvas_size
    actions: List[str] = []
    for issue in issues:
        code = issue["code"]
        i = issue.get("index")
        if i is None or i >= len(layout.shapes):
            continue
        shape = layout.shapes[i]
        if code == "TEXT_OVERFLOW" and shape.kind == "textbox" and shape.font_size:
            base = shape.font_size
            shrunk = fit_font(shape.content or "", shape.box.w * w_in,
                              shape.box.h * h_in, base_pt=base, min_pt=12)
            if shrunk < base:
                shape.font_size = shrunk
                actions.append(f"#{i} 字号 {base}→{shrunk}pt(溢出修复)")
        elif code == "OUT_OF_BOUNDS":
            b = shape.box
            shape.box = b.model_copy(update={
                "x": min(max(b.x, SAFE), 1 - SAFE - b.w),
                "y": min(max(b.y, SAFE), 1 - SAFE - b.h),
            })
            actions.append(f"#{i} {shape.kind} 收敛回安全区")
        elif code == "DECOR_OVERLAP" and is_decoration(shape):
            layout.shapes = [s for s in layout.shapes if s is not shape]
            actions.append(f"#{i} 移除被覆盖装饰({shape.kind})")
    return actions
