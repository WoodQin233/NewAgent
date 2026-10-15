"""字号与颜色助手(自 generator.py 迁入,逻辑不变)

FontScale 仍按 Mood 缩放,服务于经典(classic)原型;
M2 起新原型叠加 text_metrics 容量算法做自适应收缩。
"""
from typing import Optional

from pptx.dml.color import RGBColor

from App.models import Mood


def hex_to_rgb(hex_color: str) -> RGBColor:
    """将 #RRGGBB 字符串转换为 python-pptx 的 RGBColor"""
    hex_color = hex_color.lstrip("#")
    return RGBColor(int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16))


def lighten(hex_color: str, t: float = 0.88) -> str:
    """把 #RRGGBB 向白色混合 t 比例,返回浅色版(用于卡片底色)"""
    r, g, b = (int(hex_color[i:i + 2], 16) for i in (1, 3, 5))
    mix = lambda c: int(c + (255 - c) * t)
    return f"#{mix(r):02X}{mix(g):02X}{mix(b):02X}"


_CN_DIGITS = "零一二三四五六七八九"


def cn_section_num(n: int) -> str:
    """章节序号转中文数字:1→'一'…10→'十'…11→'十一';超过 19 回退阿拉伯数字"""
    if 1 <= n <= 10:
        return "十" if n == 10 else _CN_DIGITS[n]
    if 11 <= n <= 19:
        return "十" + _CN_DIGITS[n - 10]
    return str(n)


class FontScale:
    """按 Mood 调整后的字号表。所有数字单位:pt"""

    _BASE = {
        "title_main":   44,
        "title_sub":    20,
        "section_kicker": 16,
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

    @classmethod
    def base(cls, key: str) -> int:
        """未缩放的基准字号(M2 容量算法的收缩起点)。"""
        return cls._BASE[key]
