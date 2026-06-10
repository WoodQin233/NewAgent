from ctypes.util import test
from tkinter.ttk import Separator
from typing import List, Optional

from models import DocumentContent, DocumentMetadata, TableData
from pathlib import Path
import os
from dataclasses import dataclass

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from langchain_community.document_loaders import UnstructuredImageLoader, UnstructuredWordDocumentLoader, UnstructuredPDFLoader, UnstructuredPowerPointLoader


class UnsupportedFormatError(Exception):
    """不支持的文件格式异常"""
    pass

@dataclass
class BaseParser:
    """解析器基类"""
    
    chunk_size: int = 100
    chunk_overlap: int = 4

    def parse(self, file_path: str, Delimiter: str) -> DocumentContent:
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

    def txtlen(self, file_path: str) -> int:
        """计算chunk_size and chunk_overlap"""
        pass

    def parse(self, file_path: str) -> DocumentContent:
        """解析文本文件"""
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size = self.chunk_size, #每个文本块的最大长度
            chunk_overlap = self.chunk_overlap, #文本块之间的重叠长度
            length_function = len, #计算文本长度的函数，影响上面的两个参数(未实现)
            is_separator_regex = False #分隔符是否是正则表达式，这里使用默认
        )

        chunks = text_splitter.create_documents([content])

        #转为DocumentContent
        testTable = TableData(
            headers = ["分割数据"],
            rows = []
        )
        for chunk in chunks:
            testTable.rows.append([chunk.page_content])

        TXTDocumentContent = DocumentContent(
            raw_text=content,
            tables = [testTable],
            metadata = DocumentMetadata(
                file_name = Path(file_path).name,
                file_path = file_path,
                file_type = ".txt",
                file_size=os.path.getsize(file_path)
            )
        )
        return TXTDocumentContent

        pass
      

class PdfParser(BaseParser):
    """PDF解析器，不支持图片"""

    def parse(self, file_path: str) -> DocumentContent:
        """解析PDF文件"""
        loader = UnstructuredPDFLoader(file_path)
        chunks = loader.load_and_split(text_splitter=RecursiveCharacterTextSplitter(
            chunk_size = self.chunk_size,
            chunk_overlap = self.chunk_overlap,
            )
        )

        #转为DocumentContent
        PdfTxtTable = TableData(
            headers = ["分割数据"],
            rows = []
        )

        pdftext = ""

        for chunk in chunks:
            PdfTxtTable.rows.append([chunk.page_content])
            pdftext = pdftext + chunk.page_content

        PdfDocumentContent = DocumentContent(
            raw_text = pdftext,
            tables = [PdfTxtTable],
            metadata = DocumentMetadata(
                file_name = Path(file_path).name,
                file_path = file_path,
                file_type = ".pdf",
                file_size = os.path.getsize(file_path)
            )
        )
        return PdfDocumentContent

        pass


class WordParser(BaseParser):
    """Word解析器，不支持图片"""

    def parse(self, file_path: str) -> DocumentContent:
        """解析Word文件"""

        loader = UnstructuredWordDocumentLoader(file_path)
        chunks = loader.load()

        #转为DocumentContent
        WordTxtTable = TableData(
            headers = ["分割数据"],
            rows = []
        )

        pdftext = ""

        WordImageTable = TableData(
            headers = ["图片数据"],
            rows = []
        )

        for chunk in chunks:
            WordTxtTable.rows.append([chunk.page_content])
            pdftext = pdftext + chunk.page_content
            #WordImageTable.rows.append([chunk.metadata.get("source", "")])

        WordDocumentContent = DocumentContent(
            raw_text = pdftext,
            tables = [WordTxtTable],
            metadata = DocumentMetadata(
                file_name = Path(file_path).name,
                file_path = file_path,
                file_type = ".docx",
                file_size = os.path.getsize(file_path)
            )
        )
        return WordDocumentContent

        pass

if __name__ == "__main__":
    """test"""
    file_path = "data/test.pdf"
    print(ParserFactory().get_parser(file_path).parse(file_path))