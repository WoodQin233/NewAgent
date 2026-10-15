"""页面内容处理:大纲与细化内容的合并、内容画像"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from App.models import OutlineItem, SlideContent


def merge_outline_detail(
    item: OutlineItem,
    detail: Optional[SlideContent],
) -> SlideContent:
    """把 outline_item 与可选 detail 合并成最终 SlideContent。

    用 model_construct 而不是 SlideContent(**kwargs),因为 SlideContent 的
    model_validator 会强制 QUOTE 有 quote、IMAGE 有 image_url 等,而 outline
    阶段 AI 不会写这些字段;缺失由对应 builder 自己兜底。
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


@dataclass
class ContentProfile:
    """单页内容的可量化画像,作为原型选型的依据(M3)。"""

    page: int
    page_type: str
    title: str
    n_points: int                    # 要点条数
    total_chars: int                 # 全部正文(含标题)字符数
    max_point_chars: int             # 最长单条要点字符数
    has_numbers: bool                # 是否含数字(数据感)
    has_image: bool                  # 是否带图片
    has_subtitle: bool

    @property
    def is_dense(self) -> bool:
        """文字量大,需要压缩排版(多栏/卡片)。"""
        return self.total_chars >= 120 or self.n_points >= 5


def profile_page(merged: SlideContent) -> ContentProfile:
    """从合并后的 SlideContent 提取内容画像。"""
    points = merged.point_list()
    texts = [merged.title or ""] + points
    if merged.subtitle:
        texts.append(merged.subtitle)
    if merged.quote:
        texts.append(merged.quote)
    total = sum(len(t) for t in texts)
    has_numbers = any(any(c.isdigit() for c in p) for p in points)
    return ContentProfile(
        page=merged.page,
        page_type=merged.type.value,
        title=merged.title or "",
        n_points=len(points),
        total_chars=total,
        max_point_chars=max((len(p) for p in points), default=0),
        has_numbers=has_numbers,
        has_image=bool(merged.image_url or merged.image_prompt),
        has_subtitle=bool(merged.subtitle),
    )
