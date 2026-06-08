from typing import List
from pptx import Presentation
from App.models import AnalysisResult, SlideContent
import os

"""
幻灯片总页数: 11
幻灯片标题: 前言：从“对话者”到“行动者”的范式跃迁
幻灯片内容: ['从被动回答到主动理解目标、制定计划、调用工具、与真实世界交互', '核心比喻：LLM是被动的"对话者"，AI Agent是主动的"行动者"', '代表AI应用范式的根本性转变']
幻灯片标题: 1.1 什么是AI Agent？
幻灯片内容: ['以LLM为核心"大脑"的智能系统', '具备自主理解、感知、规划、记忆和使用工具能力', 'OpenAI定义 ：自动化执行复杂任务的系统', '吴恩达定义：Agent = LLM + 规划能力 + 工具调用能力 + 记忆能力']
幻灯片标题: 1.2 AI Agent的核心特征
幻灯片内容: ['自主性(Autonomy)：无需实时干预，自主完成任务', '闭环性(Closed-loop)：目标→规划→行动→观察→ 反思→调整', '工具扩展性(Tool-use Extension)：通过调用外部工具无限拓展能力', '记忆持续性(Memory Persistence)：分层记忆系统实现持续学习']
幻灯片标题: 1.3 AI Agent与传统AI/LLM的区别
幻灯片内容: ['工作模式：主动决策 vs 被动响应', '核心能力：规划、记忆、工具调用 vs 特定任务执行或文本生成', '交互方式：自然语言目标设定 vs 结构化指令或问答', '任务复杂度：复杂、长链路任务 vs 简单、单步任务', '与环境交互：强交互 vs 有限或无交互']
幻灯片标题: 2.1 AI Agent的通用架构
幻灯片内容: ['感知模块：Agent的"五官"，接收多样化输入', '记忆模块：Agent的"大脑硬盘"，存储短期和长期信息', '规划模块：Agent的"大脑前额叶"，分解目标为子任务', '行动/工具调用模块：Agent的"手脚"，执行计划并调用 工具', '反思模块：Agent的"复盘能力"，评估结果并调整策略']
幻灯片标题: 2.2 经典工作范式
幻灯片内容: ['ReAct："思考-行动-观察"循环，灵活适应动态任务', 'Plan-and-Execute："先规划，后执行"，结构 清晰，适合目标明确的复杂任务', 'Reflexion：在基础范式上增加"反思"步骤，具备自我修正和学习能力']
幻灯片标题: 3.1 规划(Planning)
幻灯片内容: ['思维链(CoT)：将复杂问题分解为中间推理步骤', '树状思考(ToT)：探索多种可能性，进行前瞻性思考和回溯']
幻灯片标题: 3.2 记忆(Memory)
幻灯片内容: ['短期记忆：利用LLM上下文窗口', '长期记忆：通过向量数据库进行语义检索']
幻灯片标题: 3.3 工具调用(Tool Use)
幻灯片内容: ['函数调用(Function Calling)：LLM生成符合规范的函数调用请求', '工具选择与调度：LLM自主决定调用工具及参数', '常见工具类型：信息获取、数据处理、服务交互、物理世界交互']
幻灯片标题: 核心价值回顾
幻灯片内容: ['开启全新的AI应用时代', '成为"数字员工"和"全能助理"']
幻灯片标题: 未来趋势
幻灯片内容: ['多智能体协作(Multi-Agent Systems)：多个Agent协同工作', '更强的自主性与通用性：处理更复杂、模糊的开放式任务', '与物理世界深度融合：广泛控制机器人和智能设备']
"""

"""
class SlideContent(BaseModel):
    title: str = Field(description="本页幻灯片标题")
    bullet_points: List[str] = Field(description="具体文本内容列表")

class AnalysisResult(BaseModel):
    title: str = Field(description="PPT 标题")
    slides: List[SlideContent] = Field(description="幻灯片内容列表")
    summary: str = Field(description="总结")
    notes: Optional[str] = Field(description="演讲者署名", default=None)
"""

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
        prs.save("output/output.pptx")
        return "output/output.pptx"



    def list_templates(self) -> List[str]:
        """列出所有可用模板"""
        pass




