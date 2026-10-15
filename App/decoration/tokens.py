"""装饰风格 token

从 (theme, mood, deck_seed) 派生整册共享的装饰参数,保证页间一致、册间差异化。
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import List

from App.models import Mood, ThemeConfig


@dataclass
class StyleTokens:
    """一份 PPT 的全局装饰参数。"""

    motif_families: List[str] = field(default_factory=list)  # 允许的母题家族及优先序
    opacity: float = 0.18        # 装饰填充透明度(低存在感)
    radius: float = 0.5          # 圆角比例
    gradient_angle: float = 90.0
    max_per_page: int = 2        # 每页装饰数上限

    @property
    def signature(self) -> str:
        """token 指纹(M5 风格漂移校验用)。"""
        return (f"{','.join(self.motif_families)}|{self.opacity:.2f}|"
                f"{self.radius:.2f}|{self.gradient_angle:.0f}|{self.max_per_page}")


# mood → 母题家族白名单(风格约束:越克制的 mood 允许的家族越少)
_FAMILIES_BY_MOOD = {
    Mood.MINIMAL: ["dots", "line"],
    Mood.PROFESSIONAL: ["dots", "ring", "line"],
    Mood.TECH: ["dots", "block", "ring"],
    Mood.PLAYFUL: ["dots", "ring", "corner_dots"],
    Mood.BOLD: ["block", "corner_dots", "ring", "dots"],
}

_OPACITY_BY_MOOD = {
    Mood.MINIMAL: 0.12,
    Mood.PROFESSIONAL: 0.15,
    Mood.TECH: 0.22,
    Mood.PLAYFUL: 0.28,
    Mood.BOLD: 0.35,
}

_MAX_PER_PAGE_BY_MOOD = {
    Mood.MINIMAL: 1,
    Mood.PROFESSIONAL: 1,
    Mood.TECH: 2,
    Mood.PLAYFUL: 2,
    Mood.BOLD: 2,
}


def derive_tokens(theme: ThemeConfig, mood, deck_seed: int) -> StyleTokens:
    """按 mood 收窄家族集合,再用种子旋转优先序(册间差异化,页间一致)。"""
    mood = mood or Mood.PROFESSIONAL
    families = list(_FAMILIES_BY_MOOD.get(mood, _FAMILIES_BY_MOOD[Mood.PROFESSIONAL]))
    rng = random.Random(deck_seed)
    shift = rng.randrange(len(families))
    families = families[shift:] + families[:shift]
    return StyleTokens(
        motif_families=families,
        opacity=_OPACITY_BY_MOOD.get(mood, 0.15),
        radius=rng.choice([0.25, 0.5]),
        gradient_angle=rng.choice([90.0, 115.0, 135.0]),
        max_per_page=_MAX_PER_PAGE_BY_MOOD.get(mood, 2),
    )
