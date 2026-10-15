"""规则选型器:内容画像 → 版式原型(确定性,不调 LLM)

这是 LayoutAgent 的基线决策层:LLM 失败/缺页/非法时逐页回退到这里。
"""
from __future__ import annotations

from App.models import LayoutDecision, PageType, SlideContent
from App.layout_engine.content import profile_page


def select_schema(merged: SlideContent) -> LayoutDecision:
    """按内容画像规则选择原型,附带一句选择理由(便于追溯)。"""
    p = profile_page(merged)
    schema_id, reason = _rule(merged.type, p)
    return LayoutDecision(page=merged.page, schema_id=schema_id, reason=reason)


def _rule(t: PageType, p) -> tuple:
    if t == PageType.TITLE:
        if p.total_chars <= 25:
            return "title_center", "封面文字少,居中式更聚焦"
        return "title_classic", "封面信息较多,左对齐分层更稳"

    if t == PageType.SECTION:
        if p.has_subtitle:
            return "section_number", "带看点副标题,编号侧栏式突出章节感"
        return "section_classic", "纯章节名,经典竖线式"

    if t == PageType.PARAGRAPH:
        if p.total_chars >= 60:
            return "paragraph_split", "正文较长,右侧渐变强调块平衡留白"
        return "paragraph_classic", "正文短,通栏排版"

    if t == PageType.BULLETS:
        if 3 <= p.n_points <= 5 and p.max_point_chars <= 18:
            return "bullets_steps", "3-5 条短要点,步骤式呈现递进感"
        if p.n_points >= 4 or p.is_dense:
            return "bullets_grid", "要点多或单条长,卡片网格压缩排版"
        return "bullets_classic", "要点少,通栏列表"

    if t == PageType.TWO_COL:
        return "two_col_asymmetric", "对比页非对称分栏突出重点"

    if t == PageType.IMAGE:
        if p.total_chars >= 40:
            return "image_left_text", "图文并重,左图右文"
        return "image_top", "大图为主,上图下注"

    if t == PageType.QUOTE:
        return "quote_center", "引言居中更庄重"

    if t == PageType.SUMMARY:
        if p.has_numbers and 2 <= p.n_points <= 4:
            return "summary_kpi", "要点含数字,KPI 大数呈现"
        return "summary_classic", "无数字要点,清单式收束"

    return "paragraph_classic", "未知类型兜底"
