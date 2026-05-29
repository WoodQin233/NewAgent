from langchain_core.language_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder, SystemMessagePromptTemplate, HumanMessagePromptTemplate, AIMessagePromptTemplate,StringPromptTemplate
from langchain.messages import SystemMessage, HumanMessage, AIMessage, ToolMessage
from pydantic import BaseModel, Field, validator
from langchain_core.prompts.prompt import PromptTemplate
from langchain_core.prompts.loading import load_prompt


'''CustmClass'''

'''自定义输出'''
class Joke(BaseModel):
    setup: str = Field(description="笑话的设定")
    punchline: str = Field(description="笑话的笑点")


'''提示词Prompt'''
class NamePrompt(StringPromptTemplate):
    def format(self, **kwargs)->str:

        return "114525"


temp_char = ChatPromptTemplate.format_messages( [
            SystemMessage("你是我的人工智能助手，协助我完成制做PPT任务。"),
            SystemMessage("")
        ]
    )

if __name__ == "__main__":
    po=load_prompt("prompts/name_prompt.yaml")
    print(po.format(name="张三"))