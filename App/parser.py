from ctypes.util import test
from tkinter.ttk import Separator
from typing import List, Optional
from App.models import DocumentContent, DocumentMetadata, TableData
from pathlib import Path
import os
from dataclasses import dataclass
from langchain_text_splitters import CharacterTextSplitter

class UnsupportedFormatError(Exception):
    """不支持的文件格式异常"""
    pass

@dataclass
class BaseParser:
    """解析器基类"""
    def parse(self, file_path: str, Delimiter: str) -> List[DocumentContent]:
        """解析文档并返回内容"""
        pass

    def validate(self, file_path: str) -> bool:
        """验证文件格式是否支持"""
        pass

class ParserFactory:
    """解析器工厂"""
    @staticmethod
    def get_parser(file_path: str) -> BaseParser:
        """根据文件类型返回对应的解析器"""
        extension = Path(file_path).suffix.lower()
        if extension == ".pdf":
            return PdfParser()
        elif extension in [".docx", ".doc"]:
            return WordParser()
        elif extension == ".txt":
            return TXTParser()
        else:
            raise UnsupportedFormatError(f"不支持的文件格式: {extension}")

class TXTParser(BaseParser):
    """文本解析器"""
    def parse(self, file_path: str, Delimiter: str) -> List[DocumentContent]:
        """解析文本文件"""
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
         
        text_splitter = CharacterTextSplitter(
            separator=Delimiter,#文本块之间的分隔符，默认"\n\n"
            chunk_size=50, #每个文本块的最大长度
            chunk_overlap=20, #文本块之间的重叠长度
            length_function=len, #计算文本长度的函数
            is_separator_regex=False #分隔符是否是正则表达式，这里使用默认
            
        )

        chunks = text_splitter.create_documents([content])
        return chunks



