from typing import List, Optional
from App.models import DocumentContent, DocumentMetadata, TableData, FileType
from pathlib import Path
import os
from dataclasses import dataclass

from docx import Document as DocxDocument
from docx.oxml.table import CT_Tbl
from docx.oxml.text.paragraph import CT_P
from docx.table import Table
from docx.text.paragraph import Paragraph



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
        """解析Word文件（.docx）。旧版二进制 .doc 不支持，需先另存为 .docx"""
        if file_type == FileType.DOC:
            raise UnsupportedFormatError("暂不支持旧版 .doc 格式，请先将文件另存为 .docx")

        doc = DocxDocument(file_path)
        lines: List[str] = []
        tables: List[TableData] = []

        # 按文档顺序遍历正文元素，保持段落与表格的原始先后关系
        for child in doc.element.body.iterchildren():
            if isinstance(child, CT_P):
                text = Paragraph(child, doc).text.strip()
                if text:
                    lines.append(text)
            elif isinstance(child, CT_Tbl):
                table = Table(child, doc)
                rows = [[cell.text.strip() for cell in row.cells] for row in table.rows]
                if not rows:
                    continue
                # 首行作为表头，其余为数据行
                tables.append(TableData(headers=rows[0], rows=rows[1:]))
                # 表格内容同时写入 raw_text，保证下游分析能看到完整信息
                for row in rows:
                    lines.append("\t".join(row))

        return DocumentContent(
            raw_text="\n".join(lines),
            tables=tables,
            metadata=DocumentMetadata(
                file_name=Path(file_path).name,
                file_path=file_path,
                file_type=file_type.value,
                file_size=os.path.getsize(file_path)
            )
        )





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

