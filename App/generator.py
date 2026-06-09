from typing import List
from pptx import Presentation
from App.models import AnalysisResult, SlideContent
import os

class PPTGenerator:
    """PPT 生成器"""
    def __init__(self, template_dir: str = "Templates"):
        self.template_dir = template_dir

    def generate(self, result: AnalysisResult, template: str = "blank") -> str:
        """生成 PPT 文件并返回保存路径"""
        
        prs = Presentation(f"{self.template_dir}/{template}.pptx")

        title_slide = prs.slides.add_slide(prs.slide_layouts[0])
        title_slide.shapes.title.text = result.title

        for content in result.slides:
            slide = prs.slides.add_slide(prs.slide_layouts[1])
            slide.shapes.title.text = content.title
            text_frame = slide.shapes.placeholders[1].text_frame
            for point in content.bullet_points:
                # print("INFO:",point)
                text_frame.add_paragraph().text = point
        os.makedirs("output", exist_ok=True)
        prs.save(f"output/{result.title}.pptx")
        return f"output/{result.title}.pptx"



    def list_templates(self) -> List[str]:
        """列出所有可用模板"""
        pass




