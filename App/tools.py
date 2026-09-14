from langchain.tools import tool
from pydantic import BaseModel, Field
from typing import Literal
from langchain.messages import SystemMessage, HumanMessage, AIMessage, ToolMessage

@tool
def TestTool(location: str) -> ToolMessage:
    '''给ai的注释，必须写.'''
    # 这里是工具的实现逻辑，可以根据输入参数执行相应的操作并返回结果返回任意，推荐字符串，或者使用 ToolMessage 来返回更复杂的消息结构
    return ToolMessage(content=f"工具执行结果: {location}")


#使用 Pydantic 模型 或 JSON 架构 定义复杂的输入
class WeatherInput(BaseModel):
    """Input for weather queries."""
    location: str = Field(description="City name or coordinates")
    units: Literal["celsius", "fahrenheit"] = Field(
        default="celsius",
        description="Temperature unit preference"
    )
    include_forecast: bool = Field(
        default=False,
        description="Include 5-day forecast"
    )

@tool(args_schema=WeatherInput)
def get_weather(location: str, units: str = "celsius", include_forecast: bool = False) -> str:
    """Get current weather and optional forecast."""
    temp = 22 if units == "celsius" else 72
    result = f"Current weather in {location}: {temp} degrees {units[0].upper()}"
    if include_forecast:
        result += "\nNext 5 days: Sunny"
    return result


