from typing import List, Optional
from App.models import DocumentContent, DocumentMetadata, TableData
from pathlib import Path
import os
from dataclasses import dataclass

class UnsupportedFormatError(Exception):
    """不支持的文件格式异常"""
    pass

@dataclass
class BaseParser:
    """解析器基类"""
    def parse(self, file_path: str) -> DocumentContent:
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
    def parse(self, file_path: str) -> DocumentContent:
        """解析文本文件"""
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        return DocumentContent(
            raw_text=content,
            tables=[],
            metadata=DocumentMetadata(
                file_name=Path(file_path).name,
                file_path=file_path,
                file_type="txt",
                file_size=os.path.getsize(file_path)
            )
        )



