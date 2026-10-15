"""网格系统

所有新版式原型的槽位几何都从网格推导:12 列 × 8 行 + 边距 + gutter,
保证对齐与比例有统一基准,也为校验器提供"网格吸附率"的判定线。
坐标全部是相对画布的 [0,1] 值(与 Box 一致)。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple

from App.models import Box


@dataclass(frozen=True)
class Grid:
    """版面网格。margin/gutter 均为相对画布比例。"""

    cols: int = 12
    rows: int = 8
    margin_x: float = 0.06
    margin_y: float = 0.08
    gutter: float = 0.015

    # ── 轴向计算 ──────────────────────────────────────────────────

    def _span(self, i: int, span: int, n: int, margin: float,
              gutter: float) -> Tuple[float, float]:
        """第 i 格起跨 span 格 → (start, size)。i/span 越界由调用方约束。"""
        total = 1.0 - 2.0 * margin
        cell = (total - (n - 1) * gutter) / n
        start = margin + i * (cell + gutter)
        size = span * cell + (span - 1) * gutter
        return start, size

    def region(self, col: int, row: int, col_span: int, row_span: int) -> Box:
        """grid 区 → 相对坐标盒。"""
        if not (0 <= col and col + col_span <= self.cols):
            raise ValueError(f"列区间 [{col},{col + col_span}) 越界(共 {self.cols} 列)")
        if not (0 <= row and row + row_span <= self.rows):
            raise ValueError(f"行区间 [{row},{row + row_span}) 越界(共 {self.rows} 行)")
        x, w = self._span(col, col_span, self.cols, self.margin_x, self.gutter)
        y, h = self._span(row, row_span, self.rows, self.margin_y, self.gutter)
        return Box(x=round(x, 6), y=round(y, 6), w=round(w, 6), h=round(h, 6))

    # ── 网格线(校验器吸附率判定用) ────────────────────────────────

    def col_lines(self) -> List[float]:
        """全部列边界 x 值(含左右安全边距线)。"""
        total = 1.0 - 2.0 * self.margin_x
        cell = (total - (self.cols - 1) * self.gutter) / self.cols
        lines = [self.margin_x]
        for i in range(self.cols):
            lines.append(self.margin_x + i * (cell + self.gutter))
            lines.append(self.margin_x + i * (cell + self.gutter) + cell)
        lines.append(1.0 - self.margin_x)
        return sorted({round(v, 6) for v in lines})

    def row_lines(self) -> List[float]:
        total = 1.0 - 2.0 * self.margin_y
        cell = (total - (self.rows - 1) * self.gutter) / self.rows
        lines = [self.margin_y]
        for i in range(self.rows):
            lines.append(self.margin_y + i * (cell + self.gutter))
            lines.append(self.margin_y + i * (cell + self.gutter) + cell)
        lines.append(1.0 - self.margin_y)
        return sorted({round(v, 6) for v in lines})

    def snap_ok(self, box: Box, tol: float = 0.004) -> bool:
        """盒四边是否都吸附到某条网格线(容差 tol,约 0.4% 画布)。"""
        for v, lines in ((box.x, self.col_lines()), (box.x + box.w, self.col_lines()),
                         (box.y, self.row_lines()), (box.y + box.h, self.row_lines())):
            if not any(abs(v - line) <= tol for line in lines):
                return False
        return True


DEFAULT_GRID = Grid()
