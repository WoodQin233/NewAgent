"""文本容量估算

CJK≈1em、Latin≈0.5-0.7em 的贪心换行模拟,用于:
- 行数/高度估算(校验器判溢出)
- 字号自适应收缩(新原型 builder 的 fit_font)
单位约定:em 是相对字号的宽度系数,1pt = 1/72 英寸。
"""
from __future__ import annotations

from typing import List

LINE_SPACING = 1.35  # 行高倍数(经验值,微软雅黑偏松)


def char_em(ch: str) -> float:
    """单字符宽度(em)。"""
    o = ord(ch)
    if 0x2E80 <= o <= 0x9FFF or 0x3000 <= o <= 0x303F or 0xFF00 <= o <= 0xFFEF:
        return 1.0   # CJK / 全角标点
    if ch.isdigit():
        return 0.6
    if ch.isupper():
        return 0.7
    if ch.islower():
        return 0.55
    if ch == " ":
        return 0.3
    return 0.45      # 半角标点等


def _tokenize(text: str) -> List[str]:
    """切分换行单元:连续 Latin/数字为一个词,CJK 单字成词,空格独立。"""
    tokens: List[str] = []
    buf = ""
    for ch in text:
        if ch == " ":
            if buf:
                tokens.append(buf)
                buf = ""
            tokens.append(" ")
        elif ord(ch) >= 0x2E80:
            if buf:
                tokens.append(buf)
                buf = ""
            tokens.append(ch)
        else:
            buf += ch
    if buf:
        tokens.append(buf)
    return tokens


def text_em(text: str) -> float:
    """单行总宽(em),忽略换行符。"""
    return sum(char_em(c) for c in text if c != "\n")


def estimate_lines(text: str, font_pt: float, width_in: float) -> int:
    """估算换行后的行数。width_in <= 0 视为完全放不下,返回极大值。"""
    if width_in <= 0:
        return 9999
    width_em = width_in * 72.0 / font_pt
    lines = 0
    for hard_line in text.split("\n"):
        if not hard_line:
            lines += 1
            continue
        count = 1
        cur = 0.0
        for token in _tokenize(hard_line):
            w = text_em(token)
            if cur + w > width_em and cur > 0:
                count += 1
                cur = w if token != " " else 0.0
            else:
                cur += w
        lines += count
    return lines


def estimate_height_in(text: str, font_pt: float, width_in: float,
                       line_spacing: float = LINE_SPACING) -> float:
    """估算文本渲染高度(英寸)。"""
    return estimate_lines(text, font_pt, width_in) * font_pt / 72.0 * line_spacing


def fit_font(text: str, width_in: float, height_in: float, base_pt: int,
             min_pt: int = 12, line_spacing: float = LINE_SPACING) -> int:
    """从基准字号向下收缩,直到文本高度装进盒内;触底返回 min_pt。"""
    size = base_pt
    while size > min_pt and estimate_height_in(text, size, width_in, line_spacing) > height_in:
        size -= 1
    return size
