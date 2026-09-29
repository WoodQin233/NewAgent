import logging
from typing import Optional

from App.client import LLMClient, StructuredOutputError, get_llm
from App.models import AnalysisResult, DocumentContent, LayoutInfo
from App.prompts import PromptID, render_prompt
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
                prompt=render_prompt(PromptID.ANALYZE_OUTLINE, document=content.raw_text),
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
                prompt=render_prompt(
                    PromptID.LAYOUT,
                    outline_json=outline.model_dump_json(indent=2),
                ),
            )
            logger.info("AI 布局生成成功:\n%s", result.model_dump_json(indent=2))
            return result
        except StructuredOutputError as e:
            _log_structured_failure("AI 布局", e)
            raise RuntimeError(f"AI 布局解析失败: {e}") from e
