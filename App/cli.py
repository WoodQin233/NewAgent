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
from Utils.settings import get_settings
from Utils import ui


EXT_TO_TYPE = {
    ".txt": FileType.TXT,
    ".docx": FileType.DOCX,
    ".doc": FileType.DOC,
    ".pdf": FileType.PDF,
}


def show_welcome(spec) -> None:
    """打印启动横幅、当前配置、流程说明与使用提示。"""
    ui.banner("文档 → PPT 智能生成器")
    ui.blank()

    ui.section("当前配置")
    ui.kv("当前模型", f"{spec.name} / {spec.model}")
    ui.kv("配置文件", "Config/config.json")
    ui.kv("支持格式", "  ".join(sorted(EXT_TO_TYPE)))
    ui.kv("密钥变量", spec.api_key_env)
    ui.blank()

    ui.section("处理流程")
    print(f"  {ui.c('1.', 'num')} 解析文档     提取文本与元数据")
    print(f"  {ui.c('2.', 'num')} AI 生成大纲   调用模型规划幻灯片结构")
    print(f"  {ui.c('3.', 'num')} AI 生成布局   为每页确定版式与配色")
    print(f"  {ui.c('4.', 'num')} 渲染 PPT     生成 .pptx 文件")
    ui.blank()

    ui.section("使用提示")
    print(f"  · 回车使用默认文档路径 {ui.c('data/test.txt', 'accent')}")
    print(f"  · 切换模型：修改 {ui.c('Config/config.json', 'accent')} 的 api.active")
    print(f"  · 设置 API Key：写入 {ui.c('.env', 'accent')} 或系统环境变量")
    print(f"  · 中断操作：{ui.c('Ctrl + C', 'warn')}")
    ui.divider()


def ask_file_path() -> str:
    """提示用户输入文件路径，回车使用默认值。"""
    default = "data/test.txt"
    while True:
        raw = input(
            f"{ui.c('文档路径', 'label')} "
            f"{ui.c(f'(回车默认 {default})', 'muted')}: "
        ).strip().strip('"')
        path = raw or default
        if not Path(path).is_file():
            ui.error(f"找不到文件：{path}，请重新输入")
            ui.blank()
            continue
        ext = Path(path).suffix.lower()
        if ext not in EXT_TO_TYPE:
            ui.error(
                f"暂不支持 {ext or '无扩展名'} 格式，"
                f"目前仅支持：{', '.join(EXT_TO_TYPE)}"
            )
            ui.blank()
            continue
        return path


def ensure_api_key() -> None:
    """环境变量里没有 key 时，提示用户输入（输入内容不显示）。

    需要哪个环境变量由当前厂商的 api_key_env 决定，换厂商不用改这里。
    """
    spec = get_settings().api.provider
    if os.getenv(spec.api_key_env):
        return
    ui.warning(f"未检测到环境变量 {spec.api_key_env}（厂商：{spec.name}）")
    key = getpass.getpass(
        f"请输入 {spec.name} 的 API Key（输入时不显示，留空退出）: "
    ).strip()
    if not key:
        ui.error("未提供 API Key，退出。")
        sys.exit(0)
    os.environ[spec.api_key_env] = key


def ask_yes_no(prompt: str, default: bool = False) -> bool:
    hint = "Y/n" if default else "y/N"
    answer = input(f"{prompt} {ui.c(f'[{hint}]', 'muted')}: ").strip().lower()
    if not answer:
        return default
    return answer in ("y", "yes")


def run_once(file_path: str):
    """执行一次完整流水线：解析 → 大纲 → 布局 → 渲染。

    每步只打印简洁的完成状态，不再输出文件大小 / 页数 / 标题等日志数据，
    也不再打印运行统计表，保持终端输出干净。
    """
    file_type = EXT_TO_TYPE[Path(file_path).suffix.lower()]
    analyzer = AIAnalyzer()

    # [1/4] 解析文档
    ui.blank()
    with ui.spinner("[1/4] 正在解析文档，请稍候..."):
        document_content = Parser.parse(file_path, file_type)
    ui.success("解析完成")

    # [2/4] AI 生成大纲
    ui.blank()
    with ui.spinner("[2/4] AI 正在生成大纲，请稍候..."):
        outline = analyzer.analyze(document_content)
    ui.success("大纲完成")

    # [3/4] AI 生成布局
    ui.blank()
    with ui.spinner("[3/4] AI 正在生成布局，请稍候..."):
        layout_info = analyzer.layout(outline)
    ui.success("布局完成")

    # [4/4] 渲染 PPT
    ui.blank()
    with ui.spinner("[4/4] 正在渲染 PPT..."):
        output_path = PPTGenerator.generate(layout_info)
    ui.done(f"PPT 已生成：{output_path}")
    return output_path


def main():
    ensure_api_key()

    spec = get_settings().api.provider
    show_welcome(spec)

    while True:
        try:
            file_path = ask_file_path()
            run_once(file_path)
        except KeyboardInterrupt:
            ui.warning("已取消。")
            break
        except Exception as e:
            ui.error(f"生成失败：{e}")
            if ask_yes_no("是否打印完整错误信息（调试用）", default=False):
                traceback.print_exc()

        if not ask_yes_no("是否继续生成另一个文档", default=True):
            ui.success("再见！")
            break


if __name__ == "__main__":
    main()
