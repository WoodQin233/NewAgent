"""装饰生成器包

风格 token(整册一致) → 母题参数化生成 → 留白感知放置 + 相邻页差异化。
入口:decorate_page(layout, theme, state, tokens, page_no)
"""
from App.decoration.placement import decorate_page, free_zones
from App.decoration.tokens import StyleTokens, derive_tokens

__all__ = ["decorate_page", "free_zones", "StyleTokens", "derive_tokens"]
