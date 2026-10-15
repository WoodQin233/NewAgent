"""版式原型库

每个 PageType 的第一个注册原型是 classic 系列(自旧硬编码 handler 迁移,
槽位 box 与旧坐标逐一对应),由 golden 测试锁定行为;
后续新增原型追加注册,选型默认取该类型的第一个原型。
"""
from typing import Dict, List, Optional

from App.models import Box, CompositionSchema, PageType, SlotDef

_SCHEMAS: Dict[str, CompositionSchema] = {}


def _register(schema: CompositionSchema) -> CompositionSchema:
    if schema.schema_id in _SCHEMAS:
        raise ValueError(f"原型 schema_id 重复注册: {schema.schema_id}")
    _SCHEMAS[schema.schema_id] = schema
    return schema


def _slot(name: str, role: str, x: float, y: float, w: float, h: float,
          z: int = 2, font_key: Optional[str] = None, bold: bool = False) -> SlotDef:
    return SlotDef(name=name, role=role, box=Box(x=x, y=y, w=w, h=h),
                   z=z, font_key=font_key, bold=bold)


# ── classic 系列:与旧 PageRenderer handler 坐标逐一对应 ──────────────

_register(CompositionSchema(
    schema_id="title_classic",
    page_types=[PageType.TITLE],
    slots=[
        _slot("title", "title", 0.10, 0.30, 0.80, 0.30, font_key="title_main", bold=True),
        _slot("subtitle", "subtitle", 0.15, 0.62, 0.70, 0.10, font_key="title_sub"),
        _slot("underline", "accent", 0.35, 0.78, 0.30, 0.0, z=1),
    ],
))

_register(CompositionSchema(
    schema_id="section_classic",
    page_types=[PageType.SECTION],
    slots=[
        _slot("bar", "accent", 0.08, 0.31, 0.01, 0.29, z=0),
        _slot("kicker", "kicker", 0.11, 0.30, 0.80, 0.08, font_key="section_kicker"),
        _slot("name", "title", 0.11, 0.38, 0.80, 0.22, font_key="section_name", bold=True),
        _slot("subtitle", "subtitle", 0.11, 0.62, 0.80, 0.08, font_key="title_sub"),
    ],
))

_register(CompositionSchema(
    schema_id="paragraph_classic",
    page_types=[PageType.PARAGRAPH],
    slots=[
        _slot("title", "title", 0.06, 0.08, 0.88, 0.12, font_key="bullet", bold=True),
        _slot("subtitle", "subtitle", 0.06, 0.20, 0.88, 0.06, font_key="title_sub"),
        # 旧 handler 在有/无 subtitle 时 body 的 y/h 不同,拆成两个槽位由 builder 择一
        _slot("body", "body", 0.06, 0.26, 0.88, 0.66, font_key="para"),
        _slot("body_sub", "body", 0.06, 0.28, 0.88, 0.64, font_key="para"),
    ],
))

_register(CompositionSchema(
    schema_id="bullets_classic",
    page_types=[PageType.BULLETS],
    slots=[
        _slot("title", "title", 0.06, 0.08, 0.88, 0.12, font_key="bullet", bold=True),
        _slot("subtitle", "subtitle", 0.06, 0.20, 0.88, 0.06, font_key="title_sub"),
        _slot("bullets", "bullets", 0.10, 0.30, 0.80, 0.62, font_key="bullet"),
    ],
))

_register(CompositionSchema(
    schema_id="two_col_classic",
    page_types=[PageType.TWO_COL],
    slots=[
        _slot("title", "title", 0.06, 0.08, 0.88, 0.12, font_key="bullet", bold=True),
        _slot("subtitle", "subtitle", 0.06, 0.20, 0.88, 0.06, font_key="title_sub"),
        _slot("card_left", "accent", 0.04, 0.26, 0.44, 0.68, z=0),
        _slot("card_right", "accent", 0.52, 0.26, 0.44, 0.68, z=0),
        _slot("divider", "accent", 0.50, 0.30, 0.0, 0.60, z=1),
        _slot("text_left", "bullets", 0.07, 0.30, 0.38, 0.60, font_key="two_col"),
        _slot("text_right", "bullets", 0.55, 0.30, 0.38, 0.60, font_key="two_col"),
    ],
))

_register(CompositionSchema(
    schema_id="quote_classic",
    page_types=[PageType.QUOTE],
    slots=[
        _slot("mark", "accent", 0.05, 0.10, 0.20, 0.25, z=1),
        _slot("text", "quote", 0.10, 0.30, 0.80, 0.35, font_key="quote", bold=True),
        _slot("subtitle", "subtitle", 0.10, 0.70, 0.80, 0.10, font_key="title_sub"),
    ],
))

_register(CompositionSchema(
    schema_id="image_classic",
    page_types=[PageType.IMAGE],
    slots=[
        _slot("title", "title", 0.06, 0.08, 0.88, 0.12, font_key="bullet", bold=True),
        _slot("image", "image", 0.20, 0.24, 0.60, 0.55, z=1),
        _slot("caption", "caption", 0.10, 0.82, 0.80, 0.10, font_key="image_cap"),
    ],
))

_register(CompositionSchema(
    schema_id="summary_classic",
    page_types=[PageType.SUMMARY],
    slots=[
        _slot("title", "title", 0.06, 0.08, 0.88, 0.12, font_key="bullet", bold=True),
        _slot("list", "bullets", 0.10, 0.26, 0.80, 0.66, font_key="summary", bold=True),
    ],
))


# ── 扩展原型(M3):几何由 builder 按网格现算,槽位仅作声明 ────────────

_register(CompositionSchema(
    schema_id="title_center", page_types=[PageType.TITLE], family="center",
    hint="封面文字少时用,标题副题居中聚焦",
    slots=[],
))

_register(CompositionSchema(
    schema_id="section_number", page_types=[PageType.SECTION], family="number",
    hint="章节页,左侧大编号+右侧章名,带看点副标题时效果最佳",
    slots=[],
))

_register(CompositionSchema(
    schema_id="paragraph_split", page_types=[PageType.PARAGRAPH], family="split",
    hint="正文较长时用,右侧渐变强调块平衡留白",
    slots=[],
))

_register(CompositionSchema(
    schema_id="bullets_grid", page_types=[PageType.BULLETS], family="grid",
    hint="要点≥4 或单条较长时用,卡片网格压缩排版",
    slots=[],
))

_register(CompositionSchema(
    schema_id="bullets_steps", page_types=[PageType.BULLETS], family="steps",
    hint="3-5 条短要点且呈递进/流程关系时用,编号步骤式",
    slots=[],
))

_register(CompositionSchema(
    schema_id="two_col_asymmetric", page_types=[PageType.TWO_COL], family="split",
    hint="对比页非对称分栏:左侧全要点,右侧渐变面板突出重点",
    slots=[],
))

_register(CompositionSchema(
    schema_id="image_left_text", page_types=[PageType.IMAGE], family="split",
    hint="图文并重:左半图右半文字",
    slots=[],
))

_register(CompositionSchema(
    schema_id="image_top", page_types=[PageType.IMAGE], family="stack",
    hint="大图为主:上图下注",
    slots=[],
))

_register(CompositionSchema(
    schema_id="quote_center", page_types=[PageType.QUOTE], family="center",
    hint="引言居中排版,庄重聚焦",
    slots=[],
))

_register(CompositionSchema(
    schema_id="summary_kpi", page_types=[PageType.SUMMARY], family="kpi",
    hint="要点含数字且 2-4 条时用,KPI 大数呈现",
    slots=[],
))


# ── 查询接口 ──────────────────────────────────────────────────────

def get(schema_id: str) -> Optional[CompositionSchema]:
    return _SCHEMAS.get(schema_id)


def schemas_for(page_type: PageType) -> List[CompositionSchema]:
    """该页面类型的全部可选原型,按注册顺序(第一个是 classic)。"""
    return [s for s in _SCHEMAS.values() if page_type in s.page_types]


def default_for(page_type: PageType) -> CompositionSchema:
    """类型默认原型;未知类型回退 paragraph_classic(与旧渲染兜底一致)。"""
    candidates = schemas_for(page_type)
    if not candidates:
        return _SCHEMAS["paragraph_classic"]
    return candidates[0]


def all_schemas() -> List[CompositionSchema]:
    return list(_SCHEMAS.values())


def catalog_json() -> str:
    """原型目录 JSON(供 LayoutAgent 提示词使用)。"""
    import json

    items = [
        {
            "schema_id": s.schema_id,
            "page_types": [t.value for t in s.page_types],
            "family": s.family,
            "hint": s.hint or "",
        }
        for s in _SCHEMAS.values()
    ]
    return json.dumps(items, ensure_ascii=False, indent=1)
