import dataclasses

from langchain.tools import tool
from App.models import AnalysisResult, DocumentContent, SlideContent
from App.client import MiniMaxClient
from pydantic import BaseModel, Field
from langchain.messages import SystemMessage, HumanMessage
from typing import List, Optional

"""
json格式化分析结果
"""
class SlideContent(BaseModel):
    title: str = Field(description="本页幻灯片标题")
    bullet_points: List[str] = Field(description="具体文本内容列表")

class AnalysisResult(BaseModel):
    title: str = Field(description="PPT 标题")
    slides: List[SlideContent] = Field(description="幻灯片内容列表")
    summary: str = Field(description="总结")
    notes: Optional[str] = Field(description="演讲者署名", default=None)

class AIAnalyzer:
    """AI 分析器"""
    client: MiniMaxClient

    def __init__(self, client: MiniMaxClient):
        self.client = client

    def analyze(self, content: List[DocumentContent]) -> AnalysisResult:
        """分析文档内容并返回 PPT 结构"""
        messages = [
            SystemMessage(content="""
            你是一个专业的 PPT 内容规划助手。
            你的任务是根据用户提供的文档内容，生成结构化的 PPT 大纲。
            要求：
            1. 提取文档的核心主题和关键信息
            2. 合理分页，确保每页内容聚焦
            3. 每页内容简洁明了，适合演讲展示
            4. 所有内容必须来源于用户提供的文档，不要自行发挥
            严格按 JSON 格式输出，不要添加任何其他内容。
            5. 输出结构必须包含 PPT 标题、每页幻灯片的标题和要点列表，以及整体总结和演讲者备注（如果有）。
            6. AnalysisResult的结构为：
            {
                "title": "PPT 标题",
                "slides": [
                    {
                        "title": "幻灯片标题",
                        "bullet_points": ["要点1", "要点2", ...]
                    },
                    ...
            }
            """),
            HumanMessage(content = f"请分析以下文档内容并生成 PPT 结构：{[doc.raw_text for doc in content]}请严格按照 JSON 格式输出。")
        ]
        structured_result = self.client.llm.with_structured_output(AnalysisResult)
        return structured_result.invoke(messages)
    
    def confirm_result(self, result: AnalysisResult) -> bool:
        """等待用户确认分析结果"""
        pass

