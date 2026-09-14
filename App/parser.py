from typing import List, Optional
from App.models import DocumentContent, DocumentMetadata, TableData, FileType
from pathlib import Path
import os
from dataclasses import dataclass



class UnsupportedFormatError(Exception):
    """不支持的文件格式异常"""
    pass

@dataclass
class BaseParser:
    """解析器基类"""
    def parse(self, file_path: str, file_type: FileType) -> DocumentContent:
        """解析文档并返回内容"""
        pass


class TXTParser(BaseParser):
    """文本解析器"""
    def parse(self, file_path: str, file_type: FileType) -> DocumentContent:
        """解析文本文件"""
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        return DocumentContent(
            raw_text=content,
            tables=[],
            metadata=DocumentMetadata(
                file_name=Path(file_path).name,
                file_path=file_path,
                file_type=file_type.value,
                file_size=os.path.getsize(file_path)
            )
        )

class PDFParser(BaseParser):
    """PDF解析器"""
    def parse(self, file_path: str, file_type: FileType) -> DocumentContent:
        """解析PDF文件"""
        pass

class WordParser(BaseParser):
    """Word解析器"""
    def parse(self, file_path: str, file_type: FileType) -> DocumentContent:
        """解析Word文件"""
        pass





"""
Parser.parse
作用：解析用户输入的文件，提取文本
输入：用户输入的文件路径->str；文件类型->FileType
输出：提取的内容->DocumentContent
失败行为：文件读取失败
所在文件：parser.py
"""
class Parser:
    @staticmethod
    def parse(file_path: str, file_type: FileType) -> DocumentContent:
        """解析文档并返回内容"""
        parser = Parser.get_parser(file_type)
        return parser.parse(file_path, file_type)



    @staticmethod
    def get_parser(file_type: FileType) -> BaseParser:
        """根据文件类型返回对应的解析器"""
        if file_type == FileType.PDF:
            return PDFParser()
        elif file_type in [FileType.DOCX, FileType.DOC]:
            return WordParser()
        elif file_type == FileType.TXT:
            return TXTParser()
        else:
            raise UnsupportedFormatError(f"不支持的文件格式: {file_type.value}")

