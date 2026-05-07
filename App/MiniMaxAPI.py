import os
from dataclasses import dataclass
from typing import Optional, Literal, Dict, Any, List
import anthropic





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

    def __post_init__(self):
        if not self.api_key:
            self.api_key = os.getenv("MINIMAX_API_KEY")
        if not self.api_key:
            raise AuthenticationError(
                "未找到API密钥，请设置 MINIMAX_API_KEY 环境变量 "
                "或传入 api_key 参数"
            )


class MiniMaxClient:
    """MiniMax API交互客户端

    参数说明:
        api_key: MiniMax API密钥，若未传入则从 MINIMAX_API_KEY 环境变量读取
        base_url: API端点URL
        model: 使用的模型（默认: MiniMax-M2.7）
        max_tokens: 响应中的最大token数
        timeout: 请求超时时间（秒）

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

    def chat(
        self,
        message: str,
        system: str = "你是高级硅基生物，使命是辅助我完成任务，你需要回答我问你的问题",
        **kwargs
    ) -> Dict[str, Any]:
        """发送聊天消息并获取响应

        参数说明:
            message: 用户消息
            system: 系统提示词
            **kwargs: 额外参数（max_tokens, temperature等）

        返回值:
            包含响应内容和元数据的字典

        抛出异常:
            APIResponseError: API返回错误时
        """
        try:
            response = self._client.messages.create(
                model=self.config.model,
                max_tokens=kwargs.get("max_tokens", self.config.max_tokens),
                system=system,
                messages=[{
                    "role": "user",
                    "content": [{"type": "text", "text": message}]
                }],
                temperature=kwargs.get("temperature"),
                top_p=kwargs.get("top_p")
            )

            result = {"content": [], "usage": response.usage}
            for block in response.content:
                if block.type == "thinking":
                    result["content"].append({"type": "thinking", "text": block.thinking})
                elif block.type == "text":
                    result["content"].append({"type": "text", "text": block.text})

            return result

        except Exception as e:
            raise APIResponseError(f"API请求失败: {str(e)}") from e

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

    for item in result["content"]:
        if item["type"] == "thinking":
            print(f"思考:\n{item['text']}\n")
        elif item["type"] == "text":
            print(f"回复:\n{item['text']}\n")














