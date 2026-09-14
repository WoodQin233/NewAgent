import os
import sys
import getpass
import traceback
from pathlib import Path

# 保证从任意目录启动都能正确导入 App 包，且 output/ 落在项目根目录
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
os.chdir(PROJECT_ROOT)

from App.models import FileType
from App.parser import Parser
from App.analyzer import AIAnalyzer
from App.generator import PPTGenerator


EXT_TO_TYPE = {
    ".txt": FileType.TXT,
}


def ask_file_path() -> str:
    """提示用户输入文件路径，回车使用默认值。"""
    default = "data/test.txt"
    while True:
        raw = input(f"请输入文档路径（回车默认 {default}）: ").strip().strip('"')
        path = raw or default
        if not Path(path).is_file():
            print(f"❌ 找不到文件：{path}，请重新输入\n")
            continue
        ext = Path(path).suffix.lower()
        if ext not in EXT_TO_TYPE:
            print(f"❌ 暂不支持 {ext or '无扩展名'} 格式，目前仅支持：{', '.join(EXT_TO_TYPE)}\n")
            continue
        return path


def ensure_api_key() -> None:
    """环境变量里没有 key 时，提示用户输入（输入内容不显示）。"""
    if os.getenv("MINIMAX_API_KEY"):
        return
    print("未检测到环境变量 MINIMAX_API_KEY")
    key = getpass.getpass("请输入 MiniMax API Key（输入时不显示，留空退出）: ").strip()
    if not key:
        print("未提供 API Key，退出。")
        sys.exit(0)
    os.environ["MINIMAX_API_KEY"] = key


def ask_yes_no(prompt: str, default: bool = False) -> bool:
    hint = "Y/n" if default else "y/N"
    answer = input(f"{prompt} [{hint}]: ").strip().lower()
    if not answer:
        return default
    return answer in ("y", "yes")


def run_once(file_path: str):
    """执行一次完整流水线。"""
    file_type = EXT_TO_TYPE[Path(file_path).suffix.lower()]

    print("\n[1/4] 正在解析文档...")
    document_content = Parser.parse(file_path, file_type)
    print(f"✅ 解析完成：{document_content.metadata.file_name}，"
          f"{document_content.metadata.file_size} 字节")

    print("\n[2/4] AI 正在生成大纲，请稍候...")
    outline = AIAnalyzer.analyze(document_content)
    print(f"✅ 大纲完成：{len(outline.slides)} 页，标题《{outline.title}》")

    print("\n[3/4] AI 正在生成布局，请稍候...")
    layout_info = AIAnalyzer.layout(outline)
    print("✅ 布局完成")

    print("\n[4/4] 正在渲染 PPT...")
    output_path = PPTGenerator.generate(layout_info)
    print(f"🎉 PPT 已生成：{output_path}")


def main():
    ensure_api_key()

    while True:
        try:
            file_path = ask_file_path()
            run_once(file_path)
        except KeyboardInterrupt:
            print("\n已取消。")
            break
        except Exception as e:
            print(f"\n❌ 生成失败：{e}")
            if ask_yes_no("是否打印完整错误信息（调试用）", default=False):
                traceback.print_exc()

        if not ask_yes_no("\n是否继续生成另一个文档", default=True):
            print("再见！")
            break


if __name__ == "__main__":
    main()
