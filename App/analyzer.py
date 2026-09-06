import dataclasses
import json
import logging
from pathlib import Path

import instructor
from anthropic import Anthropic
from pydantic import ValidationError

from App.models import AnalysisResult, DocumentContent, SlideContent, LayoutInfo
from App.client import MiniMaxClient
from Utils.logger import setup_logger
from pydantic import BaseModel, Field
from langchain.messages import SystemMessage, HumanMessage
from typing import List, Optional

# 打开 instructor 内部日志，校验失败时可看到完整堆栈
logging.getLogger("instructor").setLevel(logging.DEBUG)

# 用 instructor 包装底层的 anthropic SDK（绕开 ChatAnthropic，
# 因为部分兼容协议在嵌套 Pydantic 时会让 LangChain 解析失败）
_instructor_client = instructor.from_anthropic(
    Anthropic(
        api_key=MiniMaxClient().config.api_key,
        base_url=MiniMaxClient().config.base_url,
    )
)

# 从 config.json 读取 logging 节
_config_path = Path(__file__).resolve().parent.parent / "Config" / "config.json"
with _config_path.open(encoding="utf-8") as _f:
    _log_cfg = json.load(_f)["logging"]

logger = setup_logger(
    __name__,
    _log_cfg["file"],
    _log_cfg["level"],
)


class AIAnalyzer:
    """AI 分析器"""
    client: MiniMaxClient = MiniMaxClient()

    @staticmethod
    def analyze(content: DocumentContent) -> AnalysisResult:
        """分析文档内容并返回 PPT 结构

        使用 instructor + Anthropic 协议，返回强类型 Pydantic 对象。
        校验失败会自动重试，并把错误信息反馈给模型。
        """
        try:
            return _instructor_client.messages.create(
                model=MiniMaxClient().config.model,
                max_tokens=MiniMaxClient().config.max_tokens,
                temperature=0,
                response_model=AnalysisResult,
                max_retries=0,
                messages=[
                    {
                        "role": "user",
                        "content": (
                            "你是一个专业的 PPT 内容规划助手。"
                            "任务:根据用户提供的文档内容,生成结构化的 PPT 大纲。\n"
                            "注意:必须通过工具调用输出结构化结果,不要输出 markdown 代码块或纯文本。\n"
                            "要求:\n"
                            "1. 提取文档的核心主题和关键信息\n"
                            "2. 合理分页,确保每页内容聚焦\n"
                            "3. 每页内容简洁明了,适合演讲展示\n"
                            "4. 所有内容必须来源于用户提供的文档,不要自行发挥\n\n"
                            f"文档内容:\n{content.raw_text}"
                        ),
                    }
                ],
            )
        except (ValidationError, Exception) as e:
            last = getattr(e, "last_completion", None) or getattr(e, "last_attempt", None)
            # DEBUG:把模型的最后一次返回完整 dump 出来,方便看 stop_reason / content / tool_calls
            logger.error("[DEBUG] AI 大纲校验失败")
            logger.error("[DEBUG] 异常类型: %s", type(e).__name__)
            logger.error("[DEBUG] 异常: %s", e)
            logger.error("[DEBUG] last_completion 类型: %s", type(last).__name__ if last else "None")
            logger.error("[DEBUG] last_completion 内容:\n%s", last)
            raise RuntimeError(f"AI 大纲解析失败: {e}")



    @staticmethod
    def layout(outline: AnalysisResult) -> LayoutInfo:
        """根据大纲,AI生成 PPT 布局

        使用 instructor + Anthropic 协议，确保嵌套 Pydantic 校验通过。
        """
        try:
            return _instructor_client.messages.create(
                model=MiniMaxClient().config.model,
                max_tokens=MiniMaxClient().config.max_tokens,
                temperature=0,
                response_model=LayoutInfo,
                max_retries=0,
                messages=[
                    {
                        "role": "user",
                        "content": (
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
                            "要求:\n"
                            "1. outline 逐页对应输入大纲,首页 TITLE,末页 SUMMARY 或 TITLE\n"
                            "2. 不要凭空新增文字、图片或要点\n"
                            "3. 颜色用 #RRGGBB,字体用 Microsoft YaHei\n"
                            "4. BULLETS/TWO_COL/SUMMARY 至少 2 个 points;PARAGRAPH 至少 1 个;"
                            "QUOTE 必填 quote;IMAGE 必填 image_prompt 或 image_url\n\n"
                            f"PPT 大纲:\n{outline.model_dump_json(indent=2)}"
                        ),
                    }
                ],
            )
        except (ValidationError, Exception) as e:
            last = getattr(e, "last_completion", None) or getattr(e, "last_attempt", None)
            # DEBUG:把模型的最后一次返回完整 dump 出来,方便看 stop_reason / content / tool_calls
            logger.error("[DEBUG] AI 布局校验失败")
            logger.error("[DEBUG] 异常类型: %s", type(e).__name__)
            logger.error("[DEBUG] 异常: %s", e)
            logger.error("[DEBUG] last_completion 类型: %s", type(last).__name__ if last else "None")
            logger.error("[DEBUG] last_completion 内容:\n%s", last)
            raise RuntimeError(f"AI 布局解析失败: {e}")