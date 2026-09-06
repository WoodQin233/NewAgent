import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from App.models import FileType
from App.parser import Parser
from App.analyzer import AIAnalyzer
from App.generator import PPTGenerator



#假装获取用户输入
file_path="data/test.txt"

document_content = Parser.parse(file_path,FileType.TXT)

# print(document_content)
print("用户上传文件已解析完成")

outline = AIAnalyzer.analyze(document_content)
# print(outline)
print("AI已生成大纲")

layout_info = AIAnalyzer.layout(outline)
# print(layout_info)
print("AI已生成布局")

output_path = PPTGenerator.generate(layout_info)
print(f"PPT已成功渲染到 {output_path}")
