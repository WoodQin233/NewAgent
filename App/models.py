import dataclasses
from typing import List, Optional, Annotated, Literal
from dataclasses import dataclass
from enum import Enum
from pydantic import BaseModel, Field, AfterValidator, model_validator, field_validator



"""
文档解析器模型
"""
class FileType(str,Enum):
    """文件类型"""
    OTHER = "other"
    PDF = "pdf"
    DOCX = "docx"
    DOC = "doc"
    TXT = "txt"
    PPTX = "pptx"
    PPT = "ppt"


@dataclass
class TableData:
    """表格数据"""
    headers: List[str]                     # 表头
    rows: List[List[str]]                   # 数据行

@dataclass
class DocumentMetadata:
    """文档元数据"""
    file_name: str                          # 文件名
    file_path: str                          # 文件路径
    file_type: str                          # 文件类型
    file_size: int                          # 文件大小（字节）

    def __str__(self):
        result = f"文件名: {self.file_name}\n"
        result += f"文件路径: {self.file_path}\n"
        result += f"文件类型: {self.file_type}\n"
        result += f"文件大小: {self.file_size} 字节\n"
        return result

@dataclass
class DocumentContent:
    """解析后的文档内容"""
    raw_text: str                          # 原始文本
    tables: List[TableData]                # 表格列表
    metadata: DocumentMetadata              # 元数据

    def __str__(self):
        result = f"原始文本: {self.raw_text}\n"
        result += f"表格数量: {len(self.tables)}\n"
        result += f"元数据:[\n {self.metadata}]\n"
        return result

"""
AI分析模型-大纲
"""

class PageType(str, Enum):
    """页面类型。大纲 / 布局都会引用"""
    TITLE    = "TITLE"
    SECTION  = "SECTION"
    PARAGRAPH = "PARAGRAPH"
    BULLETS  = "BULLETS"
    TWO_COL  = "TWO_COL"
    IMAGE    = "IMAGE"
    QUOTE    = "QUOTE"
    SUMMARY  = "SUMMARY"

class OutlineSlide(BaseModel):
    """大纲阶段的单页幻灯片。仅包含大纲所需字段，不含布局信息"""
    type: PageType = Field(description="页面类型")
    title: str = Field(description="页面主标题")
    bullet_points: List[str] = Field(default_factory=list, description="内容列表")

    @field_validator("bullet_points", mode="before")
    @classmethod
    def _v_bullets_coerce(cls, v):
        # 兜底:大模型对"无要点"页面可能输出空字符串而非数组,统一转成空列表
        if v is None or v == "":
            return []
        return v

    @field_validator("bullet_points")
    @classmethod
    def _v_bullets(cls, v: List[str], info) -> List[str]:
        t = info.data.get("type")
        if t == PageType.BULLETS and len(v) < 2:
            raise ValueError(f"{t.value} 至少需要 2 个 bullet_points")
        if t == PageType.PARAGRAPH and len(v) < 1:
            raise ValueError("PARAGRAPH 至少需要 1 个 bullet_points")
        return v


class AnalysisResult(BaseModel):
    """AI 分析结果"""
    title: str = Field(description="PPT 标题")
    slides: List[OutlineSlide] = Field(description="幻灯片内容列表")
    summary: str = Field(description="总结")
    notes: Optional[str] = Field(default=None, description="演讲者备注")



"""
AI分析模型-布局
"""
# ───────────────────────── 16进制颜色格式校验 ────────────────────────

def _validate_hex(v: str) -> str:
    if not v.startswith("#") or len(v) != 7:
        raise ValueError(f"颜色必须是 #RRGGBB 格式,收到 {v}")
    return v.upper()

HexColor = Annotated[str, AfterValidator(_validate_hex)]


# ─────────────────────────── 枚举 ───────────────────────────

class Mood(str, Enum):
    """情绪/风格关键字。Level 2 可选填,Renderer 据此调整字号与强调色"""
    PROFESSIONAL = "professional"   # 商务,字号偏中,深色
    TECH    = "tech"           # 科技,字号偏大,冷色调
    PLAYFUL = "playful"        # 活泼,字号偏小,亮色
    MINIMAL = "minimal"        # 极简,字号偏小,大量留白
    BOLD    = "bold"           # 大胆,字号偏大,强烈强调色


# ────────────────────── Level 1: 大纲 ──────────────────────

class OutlineItem(BaseModel):
    """Level 1 Planner 输出。item 内部全部是扁平字段,严禁再嵌 list/dict。"""
    page: int = Field(ge=1, description="页码,从 1 开始")
    type: PageType = Field(description="页面类型")
    title: str = Field(description="页面主标题")
    subtitle: Optional[str] = Field(default=None, description="副标题,封面/章节页可用")
    points: str = Field(
        default="",
        description="要点文本,用 \\n 分隔多行。"
                    "BULLETS/TWO_COL/SUMMARY ≥2 行,"
                    "PARAGRAPH ≥1 行,SECTION/TITLE 可空",
    )
    mood: Optional[Mood] = Field(default=None, description="可选:本页情绪关键字")

    @field_validator("type", mode="before")
    @classmethod
    def _coerce_type(cls, v):
        # 兜底:模型输出的是字符串,显式转成 PageType 枚举
        if isinstance(v, str):
            try:
                return PageType(v)
            except ValueError:
                raise ValueError(f"页面类型 {v} 无效")
                return None
        return v

    @field_validator("mood", mode="before")
    @classmethod
    def _coerce_mood(cls, v):
        # 兜底:模型输出的是字符串,显式转成 Mood 枚举
        if isinstance(v, str):
            return Mood(v)
        return v

    def point_list(self) -> List[str]:
        """把 points 字符串拆回 list,渲染器内部使用"""
        # 兜底:模型可能把换行输出成字面的 \n(反斜杠+n),先转成真正换行再拆
        return [p for p in self.points.replace("\\n", "\n").split("\n") if p.strip()]


class PresentationOutline(BaseModel):
    """Level 1 Planner 整体输出。"""
    title: str = Field(description="演示文稿标题")
    author: Optional[str] = Field(default=None, description="作者")
    items: List[OutlineItem] = Field(min_length=1, description="页面大纲条目列表")

    @field_validator("items", mode="before")
    @classmethod
    def _coerce_items(cls, v):
        # 兜底:模型可能把数组包装成 {"item": [...]},展开成数组
        if isinstance(v, dict) and "item" in v:
            return v["item"]
        return v

# ────────────────────── Level 2: 单页内容（可选） ──────────────────────

class SlideContent(BaseModel):
    """Level 2 Executor 输出。单页所有字段扁平。"""
    page: int = Field(ge=1, description="对应 OutlineItem.page")
    type: PageType = Field(description="页面类型,通常与对应大纲项一致")
    title: str = Field(description="页面主标题")
    subtitle: Optional[str] = Field(default=None, description="副标题")
    points: str = Field(default="", description="正文要点,用 \\n 分隔多行")
    quote: Optional[str] = Field(default=None, description="引言页用到的引言文本")
    image_prompt: Optional[str] = Field(default=None, description="图片生成 prompt(IMAGE 类型)")
    image_url: Optional[str] = Field(default=None, description="已生成的图片 URL/路径")
    primary_color: Optional[HexColor] = Field(default=None, description="本页主色覆盖")
    accent_color: Optional[HexColor] = Field(default=None, description="本页强调色覆盖")
    mood: Optional[Mood] = Field(default=None, description="情绪关键字")

    @field_validator("type", mode="before")
    @classmethod
    def _coerce_type(cls, v):
        # 兜底:模型输出的是字符串,显式转成 PageType 枚举
        if isinstance(v, str):
            return PageType(v)
        return v

    @field_validator("mood", mode="before")
    @classmethod
    def _coerce_mood(cls, v):
        # 兜底:模型输出的是字符串,显式转成 Mood 枚举
        if isinstance(v, str):
            try:
                return Mood(v)
            except ValueError:
                raise ValueError(f"情绪关键字 {v} 无效")
        return v

    def point_list(self) -> List[str]:
        # 兜底:模型可能把换行输出成字面的 \n(反斜杠+n),先转成真正换行再拆
        return [p for p in self.points.replace("\\n", "\n").split("\n") if p.strip()]

    @model_validator(mode="after")
    def _check_required(self):
        pl = self.point_list()
        if self.type in (PageType.BULLETS, PageType.TWO_COL) and len(pl) < 2:
            raise ValueError(f"{self.type.value} 至少需要 2 个 points")
        if self.type in (PageType.PARAGRAPH, PageType.SUMMARY) and len(pl) < 1:
            raise ValueError("PARAGRAPH 至少需要 1 个 points")
        if self.type == PageType.QUOTE and not self.quote:
            raise ValueError("QUOTE 必须提供 quote 字段")
        if self.type == PageType.IMAGE and not (self.image_url or self.image_prompt):
            raise ValueError("IMAGE 必须提供 image_url 或 image_prompt")
        return self


class PresentationDetail(BaseModel):
    """Level 2 Executor 整体输出。"""
    slides: List[SlideContent] = Field(min_length=1, description="细化后的页面内容")

    @field_validator("slides", mode="before")
    @classmethod
    def _coerce_slides(cls, v):
        # 兜底:模型可能把数组包装成 {"item": [...]},展开成数组
        if isinstance(v, dict) and "item" in v:
            return v["item"]
        return v


# ────────────────────── Level 3: 渲染器内部模型 ──────────────────────

class ThemeConfig(BaseModel):
    """全局主题,Renderer 内部使用"""
    primary_color:    HexColor = Field(default="#1F2937")
    secondary_color:  HexColor = Field(default="#6B7280")
    accent_color:     HexColor = Field(default="#3B82F6")
    background_color: HexColor = Field(default="#FFFFFF")
    title_font: str = Field(default="Microsoft YaHei")
    body_font:  str = Field(default="Microsoft YaHei")


class CanvasConfig(BaseModel):
    """画布,Renderer 内部使用"""
    width: float  = Field(default=13.33, description="英寸")
    height: float = Field(default=7.5,   description="英寸")

    @field_validator("width", "height", mode="before")
    @classmethod
    def _coerce_float(cls, v):
        # 兜底:模型可能把数字输出成字符串,统一转 float
        if isinstance(v, str):
            return float(v)
        return v


class Box(BaseModel):
    """相对坐标盒,Renderer 内部使用。AI 不直接输出"""
    x: float = Field(ge=0.0, le=1.0)
    y: float = Field(ge=0.0, le=1.0)
    w: float = Field(ge=0.0, le=1.0)
    h: float = Field(ge=0.0, le=1.0)


class ShapeBox(BaseModel):
    """Renderer 内部:一个形状 + 相对坐标 + z"""
    kind: Literal["textbox", "rect", "line", "image"]
    box: Box
    z: int = 1
    content: Optional[str] = None
    font_size: Optional[int] = None
    bold: bool = False
    color: Optional[HexColor] = None
    fill: Optional[HexColor] = None
    image_path: Optional[str] = None


class PageLayout(BaseModel):
    """Renderer 内部:一页最终的所有形状 + 背景"""
    background: Optional[HexColor] = None
    shapes: List[ShapeBox] = Field(default_factory=list)


# ─────────────────────── 顶层入口 ───────────────────────

class LayoutInfo(BaseModel):
    """整个演示文稿。AI 输出的顶层对象。

    outline 是 Level 1 大纲,detail 是可选的 Level 2 细化;
    为 None 时 Renderer 用 outline 直出。
    """
    outline: PresentationOutline
    detail: Optional[PresentationDetail] = Field(
        default=None,
        description="可选的 Executor 细页内容;为 None 时 Renderer 用 outline 直出",
    )
    theme: ThemeConfig = Field(default_factory=ThemeConfig)
    canvas: CanvasConfig = Field(default_factory=CanvasConfig)