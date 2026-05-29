import dataclasses
from typing import List, Optional
from dataclasses import dataclass

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

@dataclass
class SlideContent:
    """单页幻灯片内容"""
    title: str                              # 页面标题
    bullet_points: List[str]                # 要点列表

@dataclass
class AnalysisResult:
    """AI 分析结果"""
    title: str                              # PPT 标题
    slides: List[SlideContent]              # 幻灯片内容列表
    summary: str                            # 总结
    notes: Optional[str] = None             # 演讲者备注



