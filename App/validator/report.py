"""质量报告与门禁

DeckReport 聚合逐页校验结果,提供 gate_pass 判定与序列化,
供 CI 断言与执行日志使用。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class PageReport:
    page: int
    schema_id: str
    issues_before: List[Dict] = field(default_factory=list)
    issues_after: List[Dict] = field(default_factory=list)
    repairs: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "page": self.page,
            "schema_id": self.schema_id,
            "issues_before": self.issues_before,
            "issues_after": self.issues_after,
            "repairs": self.repairs,
        }


@dataclass
class DeckReport:
    pages: List[PageReport] = field(default_factory=list)

    @property
    def total_before(self) -> int:
        return sum(len(p.issues_before) for p in self.pages)

    @property
    def total_after(self) -> int:
        return sum(len(p.issues_after) for p in self.pages)

    @property
    def unfixable(self) -> List[Dict]:
        """修复后仍存在的形状级问题(页级风格问题单独看 style_open)。"""
        return [i for p in self.pages for i in p.issues_after if i.get("index") is not None]

    @property
    def style_open(self) -> List[Dict]:
        return [i for p in self.pages for i in p.issues_after if i.get("index") is None]

    @property
    def gate_pass(self) -> bool:
        """门禁:修复后无形状级问题,页级风格问题数 ≤ 每页 1 条(留白边缘容差)。"""
        return not self.unfixable and len(self.style_open) <= len(self.pages)

    def to_dict(self) -> Dict:
        return {
            "gate_pass": self.gate_pass,
            "total_issues_before": self.total_before,
            "total_issues_after": self.total_after,
            "pages": [p.to_dict() for p in self.pages],
        }
