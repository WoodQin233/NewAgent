import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from typing import List, Optional

from App.models import DocumentContent, DocumentMetadata, TableData
from App.parser import ParserFactory
from App.analyzer import AIAnalyzer
from App.client import MiniMaxClient
from App.generator import PPTGenerator

#假装获取用户输入
file_path="data/test.txt"

#读取文件并初步解析
parser = ParserFactory().get_parser(file_path)
document_content = parser.parse(file_path)

client = MiniMaxClient()

#AI分析PPT结构
ppt_structure = AIAnalyzer(client).analyze(document_content)

# 展示分析结果在控制台
print("内容总结：",ppt_structure.summary)
print("类型:",type(ppt_structure),type(ppt_structure.slides))
print("幻灯片总页数:",len(ppt_structure.slides)+1)
for slide in ppt_structure.slides:
    print("幻灯片标题:",slide.title)
    print("幻灯片内容:",slide.bullet_points)

#这里是我测试用的代码，不用管
# class SlideContent():
#     title: str
#     bullet_points: List[str]
#     def __init__(self, title: str, bullet_points: List[str]):
#         self.title = title
#         self.bullet_points = bullet_points

# class AnalysisResult():
#     title: str
#     slides: List[SlideContent]
#     summary: str
#     notes: Optional[str] = None

# ppt_structure = AnalysisResult()
# ppt_structure.title = "测试PPT"
# ppt_structure.slides = [SlideContent(title="测试幻灯片1", bullet_points=["测试内容1"])]

# 生成PPT文件，并获取保存路径

path = PPTGenerator().generate(ppt_structure)

print("ppt已生成：",path)

# print("演讲人署名：",ppt_structure.notes)




