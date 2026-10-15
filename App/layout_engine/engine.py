"""布局引擎主入口

流水线:内容合并 → 原型决策(规则/LLM) → Builder 编译 → 装饰(M4) → 校验修复(M5)。
M1 阶段仅实现 决策=类型默认原型 + Builder 编译,后续里程碑逐段接入。
"""
from __future__ import annotations

import logging
import zlib
from typing import Dict, List, Optional

from App.models import (
    CanvasConfig,
    LayoutDecision,
    OutlineItem,
    PageLayout,
    SlideContent,
    ThemeConfig,
)
from App.layout_engine.builders import BUILDERS
from App.layout_engine.content import merge_outline_detail
from App.layout_engine.schemas import default_for, get as get_schema
from App.layout_engine.state import RenderState
from App.decoration import decorate_page, derive_tokens
from App.validator import (
    DeckReport,
    PageReport,
    repair_issues,
    validate_geometry,
    validate_style,
)

logger = logging.getLogger(__name__)


class LayoutEngine:
    """把整册内容编译成逐页 PageLayout。

    decision_mode:
        "legacy" — 每类页面固定用 classic 原型(与旧渲染器行为一致,golden 基线);
        "rules"  — 内容画像规则选型(默认,确定性);
        "llm"    — LayoutAgent 批量选型,失败/缺页/非法逐页回退规则。
    """

    def __init__(
        self,
        theme: ThemeConfig,
        canvas: Optional[CanvasConfig] = None,
        decision_mode: str = "rules",
        client: Optional[object] = None,
    ):
        if decision_mode not in ("legacy", "rules", "llm"):
            raise ValueError(f"未知 decision_mode: {decision_mode}")
        self.theme = theme
        self.canvas = canvas
        self.decision_mode = decision_mode
        self.client = client
        self.last_report: Optional[DeckReport] = None

    # ── 整册渲染 ──────────────────────────────────────────────────

    def render_deck(
        self,
        items: List[OutlineItem],
        detail_index: Optional[Dict[int, SlideContent]] = None,
    ) -> List[PageLayout]:
        detail_index = detail_index or {}
        merged_list = [
            merge_outline_detail(item, detail_index.get(item.page)) for item in items
        ]
        decisions = self._decide(merged_list)

        state = RenderState(theme=self.theme, canvas=self.canvas)
        # 稳定种子:同主题同册 → 同种子(zlib.crc32 跨进程一致,不用内建 hash)
        state.deck_seed = zlib.crc32(self.theme.model_dump_json().encode("utf-8")) % (2 ** 31)
        # 装饰 token 整册一份(legacy 基线模式不装饰,保 golden)
        tokens = None
        if self.decision_mode != "legacy":
            tokens = derive_tokens(self.theme,
                                   next((m.mood for m in merged_list if m.mood), None),
                                   state.deck_seed)
        layouts: List[PageLayout] = []
        report = DeckReport()
        for merged, decision in zip(merged_list, decisions):
            schema = get_schema(decision.schema_id)
            if schema is None or merged.type not in schema.page_types:
                fallback = default_for(merged.type)
                logger.warning(
                    "页 %d 决策原型 '%s' 不可用,回退 '%s'",
                    merged.page, decision.schema_id, fallback.schema_id,
                )
                schema = fallback
            builder = BUILDERS[schema.schema_id]
            page_layout = builder(merged, self.theme, state, schema)
            if tokens is not None:
                decorate_page(page_layout, self.theme, state, tokens, merged.page)
                # 校验 → 参数级修复 → 复检(legacy 基线模式不校验,保持行为冻结)
                canvas_size = state.canvas_size()
                issues = (validate_geometry(page_layout, canvas_size)
                          + validate_style(page_layout, self.theme, canvas_size,
                                           family=schema.family))
                actions = repair_issues(page_layout, issues, canvas_size)
                issues_after = (validate_geometry(page_layout, canvas_size)
                                + validate_style(page_layout, self.theme, canvas_size,
                                                 family=schema.family))
                # 修复后仍溢出 → 按方案降级为最保守原型重编译一次
                if any(i["code"] == "TEXT_OVERFLOW" for i in issues_after):
                    conservative = default_for(merged.type)
                    if conservative.schema_id != schema.schema_id:
                        logger.warning(
                            "页 %d 原型 '%s' 修复后仍溢出,降级为 '%s'",
                            merged.page, schema.schema_id, conservative.schema_id,
                        )
                        schema = conservative
                        page_layout = BUILDERS[schema.schema_id](
                            merged, self.theme, state, schema)
                        decorate_page(page_layout, self.theme, state, tokens, merged.page)
                        issues = (validate_geometry(page_layout, canvas_size)
                                  + validate_style(page_layout, self.theme, canvas_size,
                                                   family=schema.family))
                        actions += repair_issues(page_layout, issues, canvas_size)
                        issues_after = (validate_geometry(page_layout, canvas_size)
                                        + validate_style(page_layout, self.theme,
                                                         canvas_size,
                                                         family=schema.family))
                report.pages.append(PageReport(
                    page=merged.page, schema_id=schema.schema_id,
                    issues_before=issues, issues_after=issues_after, repairs=actions,
                ))
            layouts.append(page_layout)
        self.last_report = report
        return layouts

    # ── 原型决策 ──────────────────────────────────────────────────

    def _decide(self, merged_list: List[SlideContent]) -> List[LayoutDecision]:
        if self.decision_mode == "legacy":
            return [
                LayoutDecision(page=m.page, schema_id=default_for(m.type).schema_id)
                for m in merged_list
            ]
        if self.decision_mode == "llm":
            try:
                from App.layout_engine.agent import decide_with_llm

                client = self.client
                if client is None:
                    from App.client import get_llm

                    client = get_llm()
                return decide_with_llm(client, merged_list)
            except Exception as e:  # LLM 决策失败回退规则,不阻塞出片
                logger.warning("LLM 布局决策失败,回退规则选型: %s", e)
        return self._decide_by_rules(merged_list)

    def _decide_by_rules(self, merged_list: List[SlideContent]) -> List[LayoutDecision]:
        from App.layout_engine.selector import select_schema

        return [select_schema(m) for m in merged_list]
