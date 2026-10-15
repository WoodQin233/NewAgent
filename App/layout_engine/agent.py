"""LLM LayoutAgent:批量原型选型(仅语义决策,不生成坐标)

调用一次 LLM 为整册每页选择 schema_id;缺页/非法 schema_id 逐页回退规则选型,
保证任何情况下都能产出完整决策集。
"""
from __future__ import annotations

import json
import logging
from typing import List

from App.models import LayoutDecision, LayoutDecisionSet, SlideContent
from App.layout_engine import selector
from App.layout_engine.content import profile_page
from App.layout_engine.schemas import catalog_json, get as get_schema
from App.prompts import PromptID, render_prompt

logger = logging.getLogger(__name__)


def decide_with_llm(client, merged_list: List[SlideContent]) -> List[LayoutDecision]:
    """client 需提供 extract(response_model, prompt) 接口(见 App.client.LLMClient)。"""
    pages_payload = []
    for m in merged_list:
        p = profile_page(m)
        pages_payload.append({
            "page": m.page,
            "type": m.type.value,
            "title": m.title,
            "subtitle": m.subtitle,
            "n_points": p.n_points,
            "total_chars": p.total_chars,
            "max_point_chars": p.max_point_chars,
            "has_numbers": p.has_numbers,
            "has_image": p.has_image,
        })

    prompt = render_prompt(
        PromptID.LAYOUT_DECISION,
        schema_catalog=catalog_json(),
        pages_json=json.dumps(pages_payload, ensure_ascii=False, indent=1),
    )
    result: LayoutDecisionSet = client.extract(LayoutDecisionSet, prompt=prompt, temperature=0.0)

    by_page = {d.page: d for d in result.decisions}
    decisions: List[LayoutDecision] = []
    for m in merged_list:
        d = by_page.get(m.page)
        schema = get_schema(d.schema_id) if d else None
        if schema is None or m.type not in schema.page_types:
            logger.warning("页 %d LLM 决策缺失或原型非法(%s),回退规则选型",
                           m.page, getattr(d, "schema_id", None))
            decisions.append(selector.select_schema(m))
        else:
            decisions.append(d)
    return decisions
