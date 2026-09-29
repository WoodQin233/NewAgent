"""LLM 客户端门面

对外只暴露两条路径，厂商与协议由 Config/config.json 决定：
    llm     —— LangChain 模型，用于自由文本 / tool calling / agent
    extract —— instructor 客户端，用于强类型结构化输出

上层代码不感知厂商：切换厂商只改配置，这里和调用方都不用动。
"""
from functools import lru_cache
from typing import Any, Optional, Protocol, TypeVar

from langchain_core.language_models import BaseChatModel
from pydantic import BaseModel

from App.providers import get_adapter
from Utils.settings import ApiSettings, ProviderSpec, get_settings

T = TypeVar("T", bound=BaseModel)


class StructuredOutputError(RuntimeError):
    """结构化输出失败：模型未给出可通过校验的结果，或重试次数耗尽。"""

    def __init__(self, response_model: type[BaseModel], cause: Exception):
        self.response_model = response_model
        self.cause = cause
        # instructor 会把模型的最后一次返回挂在异常上，留作排查用
        self.last_completion = (
            getattr(cause, "last_completion", None)
            or getattr(cause, "last_attempt", None)
        )
        super().__init__(
            f"{response_model.__name__} 解析失败: {type(cause).__name__}: {cause}"
        )


class StructuredLLM(Protocol):
    """结构化输出契约：给一个 Pydantic 类型和提示词，返回该类型的实例。"""

    def extract(
        self,
        response_model: type[T],
        prompt: str,
        *,
        system: Optional[str] = None,
        **overrides: Any,
    ) -> T: ...


class LLMClient:
    """LLM 客户端门面

    厂商、模型、base_url 全部来自 Config/config.json 的 api.active 与
    providers 预设表，这里不再持有任何硬编码的端点信息。

    使用示例:
        >>> client = get_llm()
        >>> client.extract(AnalysisResult, "把下面的文档整理成 PPT 大纲：...")
    """

    def __init__(self) -> None:
        # 懒加载：不调用就不建连接，避免 import 期副作用
        self._llm: Optional[BaseChatModel] = None
        self._structured: Optional[Any] = None

    @property
    def spec(self) -> ProviderSpec:
        """当前生效的厂商预设（base_url / model / api_key_env）。"""
        return get_settings().api.provider

    @property
    def api(self) -> ApiSettings:
        """与厂商无关的通用参数（max_tokens / timeout / temperature）。"""
        return get_settings().api

    @property
    def llm(self) -> BaseChatModel:
        """LangChain 侧的模型，用于自由文本 / tool calling 场景。"""
        if self._llm is None:
            self._llm = get_adapter(self.spec.protocol).build_llm(self.spec, self.api)
        return self._llm

    @property
    def _instructor(self) -> Any:
        """instructor 包装后的 SDK 客户端，用于结构化输出。"""
        if self._structured is None:
            self._structured = get_adapter(self.spec.protocol).build_structured(
                self.spec, self.api
            )
        return self._structured

    def extract(
        self,
        response_model: type[T],
        prompt: str,
        *,
        system: Optional[str] = None,
        temperature: float = 0.0,
        max_retries: int = 2,
        **overrides: Any,
    ) -> T:
        """按 response_model 约束模型输出，返回已校验的 Pydantic 对象

        model / max_tokens 等默认值取自配置，调用方通常只需要提供
        response_model 和 prompt。校验失败时 instructor 会带着错误信息重试，
        次数由 max_retries 控制；重试耗尽后统一抛出 StructuredOutputError。
        """
        kwargs: dict[str, Any] = {}
        if system:
            kwargs["system"] = system
        try:
            return self._instructor.messages.create(
                model=self.spec.model,
                max_tokens=self.api.max_tokens,
                temperature=temperature,
                max_retries=max_retries,
                response_model=response_model,
                messages=[{"role": "user", "content": prompt}],
                # 厂商预设里的参数（如 tool_choice=auto），调用方 overrides 可覆盖
                **self.spec.structured_kwargs,
                **kwargs,
                **overrides,
            )
        except Exception as cause:
            raise StructuredOutputError(response_model, cause) from cause


@lru_cache(maxsize=1)
def get_llm() -> LLMClient:
    """全进程复用一个客户端实例，避免重复创建底层连接池。"""
    return LLMClient()
