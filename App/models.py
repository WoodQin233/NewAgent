import dataclasses
from typing import List, Optional
from dataclasses import dataclass
from enum import Enum
from pydantic import BaseModel, Field



"""
文档解析器模型
"""
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

@dataclass
class DocumentContent:
    """解析后的文档内容"""
    raw_text: str                          # 原始文本
    tables: List[TableData]                # 表格列表
    metadata: DocumentMetadata              # 元数据

"""
AI分析模型
"""
class SlideType(str,Enum):
    """幻灯片类型"""
    TITLE = "title"        # 总标题页
    SECTION = "section"    # 小标题页
    PARAGRAPH = "paragraph"  # 大段文字页
    LIST = "list"          # 平行列举页
    BULLETS = "bullets"      # 要点列表页

class SlideContent(BaseModel):
    """单页幻灯片内容"""
    type: SlideType = Field(description="页面类型。决定内容结构和渲染方式")
    title: str = Field(description="页面主标题。所有页面类型均必填")
    number: List[str] = Field(default_factory=list, description="序号。LIST 类型不填，SECTION 类型有且仅有一个，具体意义为本章节的序号。BULLETS类需要多个，数量与bullet_points字段一致，具体意义为每个要点的序号。")
    bullet_points: List[str] = Field(default_factory=list, description="内容列表。TITLE、SECTION 0-1个内容。PARAGRAPH，至少一个内容。BULLETS、LIST 至少2个内容")


class AnalysisResult(BaseModel):
    """AI 分析结果"""
    title: str = Field(description="PPT 标题")
    slides: List[SlideContent] = Field(description="幻灯片内容列表")
    summary: str = Field(description="总结")
    notes: Optional[str] = Field(default=None, description="演讲者备注")



