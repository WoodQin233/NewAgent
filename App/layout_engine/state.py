"""渲染会话状态

整册 PPT 渲染过程中跨页共享的状态:
- section_seq:章节页计数,用于自动派生"第X部分"序号
- deck_seed / motif_history:M4 装饰差异化使用(种子与母题签名历史)
"""
from dataclasses import dataclass, field
from typing import List, Optional

from App.models import CanvasConfig, ThemeConfig


@dataclass
class RenderState:
    """一次 render_deck 调用的会话状态。"""

    theme: ThemeConfig
    canvas: Optional[CanvasConfig] = None
    section_seq: int = 0
    deck_seed: int = 0
    motif_history: List[str] = field(default_factory=list)

    def canvas_size(self) -> tuple:
        """(宽, 高) 英寸;未提供 canvas 时用 16:9 默认值。"""
        if self.canvas is None:
            return 13.33, 7.5
        return self.canvas.width, self.canvas.height
