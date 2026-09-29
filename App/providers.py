"""协议适配层

要抽象的是"协议"，不是"厂商"：厂商（base_url / model / api_key_env）是配置数据，
协议才是代码分支。因此——

    新增厂商 → 只改 Config/config.json 的 providers 表
    新增协议 → 才需要在这里加一个 Adapter

目前只实现 Anthropic Messages 协议。MiniMax 的 /anthropic 端点、
Claude 官方端点、以及任何自称 Anthropic 兼容的服务都走同一个 Adapter。
"""
from typing import Any, Protocol

import instructor
from anthropic import Anthropic
from langchain_anthropic import chat_models
from langchain_core.language_models import BaseChatModel

from Utils.settings import ApiSettings, ConfigError, ProviderSpec


class ProtocolAdapter(Protocol):
    """一种模型协议需要提供的两个构造入口。

    返回值刻意不做类型约束：build_llm 是 LangChain 模型，
    build_structured 是 instructor 包装后的 SDK 客户端，两者没有公共基类。
    """

    def build_llm(self, spec: ProviderSpec, api: ApiSettings) -> BaseChatModel:
        """构造 LangChain 侧模型，用于自由文本 / tool calling。"""
        ...

    def build_structured(self, spec: ProviderSpec, api: ApiSettings) -> Any:
        """构造 instructor 侧客户端，用于结构化输出。"""
        ...


class AnthropicAdapter:
    """Anthropic Messages 协议。"""

    def build_llm(self, spec: ProviderSpec, api: ApiSettings) -> BaseChatModel:
        return chat_models.ChatAnthropic(
            model=spec.model,
            api_key=spec.api_key,
            base_url=spec.base_url,
            max_tokens=api.max_tokens,
            timeout=api.timeout,
            temperature=api.temperature,
        )

    def build_structured(self, spec: ProviderSpec, api: ApiSettings) -> Any:
        # 绕开 ChatAnthropic 直连 SDK：部分兼容协议在嵌套 Pydantic 时
        # 会让 LangChain 的解析链路失败
        return instructor.from_anthropic(
            Anthropic(
                api_key=spec.api_key,
                base_url=spec.base_url,
            )
        )


"""协议映射字典，新增厂商时需要在这里注册。"""
_ADAPTERS: dict[str, ProtocolAdapter] = {
    "anthropic": AnthropicAdapter(),
}


def get_adapter(protocol: str) -> ProtocolAdapter:
    """按协议名取适配器，未实现的协议给出可执行的提示。"""
    try:
        return _ADAPTERS[protocol]
    except KeyError:
        raise ConfigError(
            f"未实现的协议 '{protocol}'，已实现：{list(_ADAPTERS)}。"
            f"如需接入请参考 App/providers.py 添加对应的 Adapter"
        ) from None
