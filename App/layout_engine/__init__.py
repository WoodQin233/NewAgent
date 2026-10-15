"""布局引擎包

把"AI 语义决策 → 确定性几何编译"串成流水线:
    content(内容合并/画像) → selector(原型选型) → schemas(原型库)
    → builders(原型→ShapeBox) → decoration(装饰,M4) → validator(校验修复,M5)

对外主入口是 LayoutEngine.render_deck。
"""
from App.layout_engine.engine import LayoutEngine
from App.layout_engine.state import RenderState

__all__ = ["LayoutEngine", "RenderState"]
