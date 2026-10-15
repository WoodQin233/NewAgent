"""L1 几何校验(纯计算)

- OUT_OF_BOUNDS: 形状出画布(含安全容差)
- TEXT_OVERFLOW: 文本估算高度超过盒高
- MIN_FONT: 字号低于 12pt 下限
- CONTENT_OVERLAP: 同层内容盒交叠(跨层为有意叠放,不判)
- DECOR_OVERLAP: 装饰被内容覆盖过半(留白感知失效信号)
"""
from __future__ import annotations

from typing import Dict, List, Tuple

from App.models import Box, PageLayout, ShapeBox
from App.layout_engine.text_metrics import estimate_height_in

SAFE = 0.005          # 画布出界容差(相对值)
MIN_FONT_PT = 12
_SAME_Z_OVERLAP = 0.02    # 同层交叠面积/较小盒面积 阈值
_DECOR_COVERED = 0.5      # 装饰被内容覆盖比例阈值


def is_decoration(shape: ShapeBox) -> bool:
    """装饰形状 = z=0 且带透明度/描边(母题产物)。"""
    return shape.z == 0 and (shape.opacity is not None or shape.stroke is not None)


def _overlap_ratio(a: Box, b: Box) -> float:
    ix = min(a.x + a.w, b.x + b.w) - max(a.x, b.x)
    iy = min(a.y + a.h, b.y + b.h) - max(a.y, b.y)
    if ix <= 0 or iy <= 0:
        return 0.0
    inter = ix * iy
    smaller = min(a.w * a.h, b.w * b.h)
    return inter / smaller if smaller > 0 else 0.0


def validate(layout: PageLayout, canvas_size: Tuple[float, float]) -> List[Dict]:
    """返回 issue 列表:{"index": 形状序号或 None, "code": ..., "msg": ...}"""
    w_in, h_in = canvas_size
    issues: List[Dict] = []

    for i, s in enumerate(layout.shapes):
        b = s.box
        if (b.x < -SAFE or b.y < -SAFE
                or b.x + b.w > 1 + SAFE or b.y + b.h > 1 + SAFE):
            issues.append({"index": i, "code": "OUT_OF_BOUNDS",
                           "msg": f"{s.kind}@({b.x:.3f},{b.y:.3f},{b.w:.3f},{b.h:.3f}) 越界"})
        if s.kind == "textbox":
            content = s.content or ""
            if s.font_size and len(content) > 2:
                est = estimate_height_in(content, s.font_size, b.w * w_in)
                if est > b.h * h_in * 1.05:
                    issues.append({"index": i, "code": "TEXT_OVERFLOW",
                                   "msg": f"估算高 {est:.2f}in > 盒高 {b.h * h_in:.2f}in"})
                if s.font_size < MIN_FONT_PT:
                    issues.append({"index": i, "code": "MIN_FONT",
                                   "msg": f"字号 {s.font_size}pt < {MIN_FONT_PT}pt 下限"})

    content = [(i, s) for i, s in enumerate(layout.shapes) if not is_decoration(s)]
    for a in range(len(content)):
        for b in range(a + 1, len(content)):
            ia, sa = content[a]
            ib, sb = content[b]
            if sa.z != sb.z or sa.kind == "line" or sb.kind == "line":
                continue  # 跨层是有意叠放;线条不参与重叠判定
            if _overlap_ratio(sa.box, sb.box) > _SAME_Z_OVERLAP:
                issues.append({"index": ib, "code": "CONTENT_OVERLAP",
                               "msg": f"与形状 #{ia}({sa.kind}) 同层交叠"})

    for i, s in enumerate(layout.shapes):
        if not is_decoration(s):
            continue
        covered = max(
            (_overlap_ratio(s.box, c.box) for _, c in content if c is not s),
            default=0.0,
        )
        if covered > _DECOR_COVERED:
            issues.append({"index": i, "code": "DECOR_OVERLAP",
                           "msg": f"装饰被内容覆盖 {covered:.0%},应移除"})
    return issues
