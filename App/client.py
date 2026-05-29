import os
from dataclasses import dataclass
from typing import Optional, Literal, Dict, Any, List
import anthropic

from langchain_anthropic import chat_models
from langchain.messages import SystemMessage, HumanMessage, AIMessage, ToolMessage
from langchain.tools import tool



import test_tools as TestTools

#这是用于多轮对话的，目前这个功能还没实现
@dataclass
class Message:
    """表示对话中的单条消息"""
    role: Literal["user", "assistant"]
    content: str



@dataclass
class Config:
    """MiniMax API客户端配置"""
    api_key: Optional[str] = None
    base_url: str = "https://api.minimaxi.com/anthropic"
    model: str = "MiniMax-M2.7"
    max_tokens: int = 1024
    timeout: Optional[float] = None
    temperature: float = 0.7

    def __post_init__(self):
        if not self.api_key:
            self.api_key = os.getenv("MINIMAX_API_KEY")
        if not self.api_key:
            self.api_key = "114514"

            

class MiniMaxClient:
    """MiniMax API交互客户端

    参数说明:
        api_key: MiniMax API密钥，若未传入则从 MINIMAX_API_KEY 环境变量读取
        base_url: API端点URL
        model: 使用的模型（默认: MiniMax-M2.7）
        max_tokens: 响应中的最大token数
        timeout: 请求超时时间（秒）
        temperature: 生成文本的随机程度（0-1）

    使用示例:
        >>> client = MiniMaxClient()
        >>> response = client.chat("你好！")
        >>> print(response)
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "https://api.minimaxi.com/anthropic",
        model: str = "MiniMax-M2.7",
        max_tokens: int = 1024,
        timeout: Optional[float] = None
    ):
        self.config = Config(
            api_key=api_key,
            base_url=base_url,
            model=model,
            max_tokens=max_tokens,
            timeout=timeout
        )
        self._client = anthropic.Anthropic(
            api_key=self.config.api_key,
            base_url=self.config.base_url
        )
        self.langmodel = chat_models.ChatAnthropic(
                model=self.config.model,
                api_key=self.config.api_key,
                base_url=self.config.base_url,
                max_tokens=self.config.max_tokens,
                timeout=self.config.timeout,
                temperature=self.config.temperature
        ) 
        
    

    def chat(
        self,
        user: str,
        system: str = "你是高级硅基生物，使命是辅助我完成任务，你需要回答我问你的问题",
        **kwargs
    ) -> Dict[str, Any]:
        """发送聊天消息并获取响应

        参数说明:
            user: 用户消息
            system: 系统提示词
            **kwargs: 额外参数（max_tokens, temperature等）

        返回值:
            包含响应内容和元数据的字典

        抛出异常:
            APIResponseError: API返回错误时
        """
        try:
            # 绑定工具到语言模型
            self.langmodel.bind_tools([TestTools.TestTool])
                #消息列表，包含系统提示,用户消息,AI回复和工具信息(AI回复和工具信息一般由AI生成)
            messages = [
                SystemMessage(system),
                HumanMessage(user),
                AIMessage(""),
            ]

            response = self.langmodel.invoke(messages)
            for tool_call in response.tool_calls:
                # 使用生成的参数执行工具
                tool_result = TestTools.TestTool.invoke(tool_call)
                messages.append(tool_result)

            # 将结果传递回模型以获取最终响应
            final_response = self.langmodel.invoke(messages)
            
            return final_response.text

        except Exception as e:
            print(f"API请求失败{str(e)}")
            


    @property
    def text(self) -> str:
        """用于访问上次响应文本的属性（需要时使用）"""
        return ""


_client_instance: Optional[MiniMaxClient] = None


def get_client() -> MiniMaxClient:
    """获取或创建单例客户端实例"""
    global _client_instance
    if _client_instance is None:
        _client_instance = MiniMaxClient()
    return _client_instance


if __name__ == "__main__":
    client = get_client()
    result = client.chat("你好，近况如何？")
    print(result)
