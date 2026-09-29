import logging
from typing import Optional

from App.client import LLMClient, StructuredOutputError, get_llm
from App.models import AnalysisResult, DocumentContent, LayoutInfo
from Utils.logger import setup_logger
from Utils.settings import get_settings

# 打开 instructor 内部日志，校验失败时可看到完整堆栈
logging.getLogger("instructor").setLevel(logging.DEBUG)

_log_cfg = get_settings().logging
logger = setup_logger(
    __name__,
    _log_cfg.get("file"),
    _log_cfg.get("level", "INFO"),
)


def _log_structured_failure(stage: str, error: StructuredOutputError) -> None:
    """把模型最后一次返回完整 dump 出来，方便排查。

    能看到 stop_reason / content / tool_calls，比只看异常文本有用得多。
    """
    last = error.last_completion
    logger.error("[DEBUG] %s校验失败", stage)
    logger.error("[DEBUG] 异常类型: %s", type(error.cause).__name__)
    logger.error("[DEBUG] 异常: %s", error.cause)
    logger.error("[DEBUG] last_completion 类型: %s", type(last).__name__ if last else "None")
    logger.error("[DEBUG] last_completion 内容:\n%s", last)


class AIAnalyzer:
    """AI 分析器

    client 由构造参数注入，默认取进程内单例；测试时可传入替身。
    具体厂商/模型来自 Config/config.json，本类不需要感知。
    """

    def __init__(self, client: Optional[LLMClient] = None):
        self.client = client or get_llm()

    def analyze(self, content: DocumentContent) -> AnalysisResult:
        """分析文档内容并返回 PPT 结构

        结构化输出由 LLMClient.extract 负责，校验失败会自动重试，
        并把错误信息反馈给模型。
        """
        try:
            result = self.client.extract(
                AnalysisResult,
                prompt=(
                    "你是一个专业的 PPT 内容规划助手。"
                    "任务:根据用户提供的文档内容,生成结构化的 PPT 大纲。\n"
                    "注意:必须通过工具调用输出结构化结果,不要输出 markdown 代码块或纯文本。\n"
                    "要求:\n"
                    "1. 提取文档的核心主题和关键信息\n"
                    "2. 合理分页,确保每页内容聚焦\n"
                    "3. 每页内容简洁明了,适合演讲展示\n"
                    "4. 所有内容必须来源于用户提供的文档,不要自行发挥\n"
                    "5. 每个 slide 的 title 必须是该页内容的语义化概括，禁止页码式标题（如 \"第N页\"、\"第N部分\"、\"01\"）\n\n"
                    f"文档内容:\n{content.raw_text}"
                ),
            )
            logger.info("AI 大纲生成成功:\n%s", result.model_dump_json(indent=2))
            return result
        except StructuredOutputError as e:
            _log_structured_failure("AI 大纲", e)
            raise RuntimeError(f"AI 大纲解析失败: {e}") from e

    def layout(self, outline: AnalysisResult) -> LayoutInfo:
        """根据大纲,AI生成 PPT 布局"""
        try:
            result = self.client.extract(
                LayoutInfo,
                prompt=(
                    "你是一个专业的 PPT 内容细化助手。"
                    "任务:根据提供的大纲,输出结构化布局 LayoutInfo(只做语义决策,不生成坐标/字号/对齐)。\n"
                    "注意:必须通过工具调用输出结构化结果,不要输出 markdown 代码块或纯文本。\n"
                    "注意:items 与 slides 字段都是数组,直接输出 JSON 数组 [...],不要用 item 键包裹。\n"
                    "输出结构 LayoutInfo 包含:\n"
                    "- outline: 对象,包含 title(标题) 与 items(页面条目数组,逐页对应,page 从 1 连续)\n"
                    "- detail: 可选,每页可补充 subtitle/quote/image_prompt/image_url/mood/颜色覆盖\n"
                    "- theme: 全局主题色\n"
                    "- canvas: 画布尺寸(默认 13.33x7.5 英寸)\n"
                    "页面类型 PageType 取值: TITLE / SECTION / PARAGRAPH / BULLETS / TWO_COL / IMAGE / QUOTE / SUMMARY\n"
                    "title 硬性规则:必须是该页内容的语义化概括,禁止 '第N页/第N章/N./01/Part N' 等页码式标题\n"
                    "反例: {\"page\":3,\"type\":\"SECTION\",\"title\":\"03\"}\n"
                    "正例: {\"page\":3,\"type\":\"SECTION\",\"title\":\"市场竞争格局\"}\n"
                    "SECTION 页字段约定:title 只写章节名本身,禁止携带'第X部分/第X章'序号前缀,\n"
                    "序号由渲染器按章节出现顺序自动生成;subtitle 可选,用一句话概括本章看点\n"
                    "outline.items 的 points 必须逐字沿用输入大纲对应页的内容,不得改写、增删或丢字;\n"
                    "title 优先沿用输入大纲,但若输入大纲的 title 是页码式标题(如 '3'、'第3页'),\n"
                    "必须根据该页内容改写为语义化标题\n"
                    "要求:\n"
                    "1. outline 逐页对应输入大纲,首页 TITLE,末页 SUMMARY 或 TITLE\n"
                    "2. 不要凭空新增文字、图片或要点\n"
                    "3. 颜色用 #RRGGBB,字体用 Microsoft YaHei\n"
                    "4. BULLETS/TWO_COL/SUMMARY 至少 2 个 points;PARAGRAPH 至少 1 个;"
                    "QUOTE 必填 quote;IMAGE 必填 image_prompt 或 image_url\n\n"
                    f"PPT 大纲:\n{outline.model_dump_json(indent=2)}"
                ),
            )
            logger.info("AI 布局生成成功:\n%s", result.model_dump_json(indent=2))
            return result
        except StructuredOutputError as e:
            _log_structured_failure("AI 布局", e)
            raise RuntimeError(f"AI 布局解析失败: {e}") from e
