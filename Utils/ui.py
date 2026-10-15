"""CLI 视觉与交互工具

统一的终端美化层：ANSI 颜色、状态图标、分隔线、进度动画。

设计目标
--------
1. 跨终端兼容：自动检测 TTY，非交互环境（管道 / 重定向）下去除颜色与动画，
   保证日志 / 输出文件干净，遵循 https://no-color.org/ 约定。
2. Windows：启用控制台 VT 处理，使 ANSI 转义在 PowerShell / Windows Terminal 生效。
3. 不阻塞主流程：进度动画基于守护线程，start/stop 即可，异常安全。

功能完全不变——仅优化视觉呈现与交互体验。
"""
import os
import sys
import time
import shutil
import threading
from functools import lru_cache


# ── ANSI 转义码 ───────────────────────────────────────────────
_RESET = "\033[0m"
_BOLD = "\033[1m"
_DIM = "\033[2m"

_FG = {
    "black":   "\033[30m",
    "red":     "\033[31m",
    "green":   "\033[32m",
    "yellow":  "\033[33m",
    "blue":    "\033[34m",
    "magenta": "\033[35m",
    "cyan":    "\033[36m",
    "white":   "\033[37m",
    "bright_red":    "\033[91m",
    "bright_green":  "\033[92m",
    "bright_yellow": "\033[93m",
    "bright_blue":   "\033[94m",
    "bright_magenta":"\033[95m",
    "bright_cyan":   "\033[96m",
}

# 语义化样式表：一处定义，全局复用
_STYLES = {
    "title":     [_BOLD, _FG["bright_cyan"]],
    "subtitle":  [_BOLD, _FG["cyan"]],
    "step":      [_BOLD, _FG["cyan"]],
    "success":   [_FG["bright_green"]],
    "warn":      [_FG["bright_yellow"]],
    "warn_bold": [_BOLD, _FG["bright_yellow"]],
    "error":     [_BOLD, _FG["bright_red"]],
    "error_bold":[_BOLD, _FG["bright_red"]],
    "info":      [_FG["cyan"]],
    "muted":     [_DIM],
    "label":     [_BOLD, _FG["bright_blue"]],
    "accent":    [_FG["bright_magenta"]],
    "num":       [_FG["bright_yellow"]],
    "rule":      [_DIM, _FG["cyan"]],
}


# ── 终端能力检测 ──────────────────────────────────────────────
def _enable_windows_ansi() -> None:
    """在 Windows 上启用控制台虚拟终端处理，使 ANSI 转义生效。"""
    if os.name != "nt":
        return
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
        ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004
        STD_OUTPUT_HANDLE = -11
        handle = kernel32.GetStdHandle(STD_OUTPUT_HANDLE)
        mode = ctypes.c_ulong()
        if kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
            kernel32.SetConsoleMode(handle, mode.value | ENABLE_VIRTUAL_TERMINAL_PROCESSING)
    except Exception:
        # 极旧环境无法启用也无妨：颜色码会被当作普通字符，
        # 由 _color_enabled() 进一步通过 NO_COLOR / isatty 判断兜底
        pass


@lru_cache(maxsize=1)
def color_enabled() -> bool:
    """是否启用颜色 / 动画。

    - 显式设置 ``NO_COLOR`` 环境变量 → 关闭（no-color.org 约定）
    - stdout 不是 TTY（被管道 / 重定向）→ 关闭，避免日志混入控制字符
    - 否则：尝试启用 Windows VT，返回 True
    """
    if "NO_COLOR" in os.environ:
        return False
    if not sys.stdout.isatty():
        return False
    _enable_windows_ansi()
    return True


# ── 着色核心 ──────────────────────────────────────────────────
def c(text: str, kind: str = "info") -> str:
    """按语义样式给文本上色；颜色禁用时原样返回。

    颜色码为零显示宽度，不影响终端列对齐。
    """
    if not color_enabled():
        return text
    codes = _STYLES.get(kind) or _STYLES["info"]
    return "".join(codes) + text + _RESET


def strip(text: str) -> str:
    """去除字符串中的 ANSI 转义码（用于按显示宽度计算等场景）。"""
    out = []
    i = 0
    n = len(text)
    while i < n:
        ch = text[i]
        if ch == "\033" and i + 1 < n and text[i + 1] == "[":
            j = i + 2
            while j < n and text[j] not in "ABCDEFGHJKSTfimnsulh":
                j += 1
            i = j + 1
            continue
        out.append(ch)
        i += 1
    return "".join(out)


# ── 显示宽度（处理 CJK 全角字符）──────────────────────────────
def _disp_len(text: str) -> int:
    """计算字符串的显示宽度（CJK / 全角符号记 2，其余记 1）。"""
    s = strip(text)
    width = 0
    for ch in s:
        o = ord(ch)
        if (
            o in range(0x1100, 0x115F + 1)
            or o in range(0x2E80, 0x303E + 1)
            or o in range(0x3041, 0x33FF + 1)
            or o in range(0x3400, 0x4DBF + 1)
            or o in range(0x4E00, 0x9FFF + 1)
            or o in range(0xA000, 0xA4CF + 1)
            or o in range(0xAC00, 0xD7A3 + 1)
            or o in range(0xF900, 0xFAFF + 1)
            or o in range(0xFE30, 0xFE4F + 1)
            or o in range(0xFF00, 0xFF60 + 1)
            or o in range(0xFFE0, 0xFFE6 + 1)
        ):
            width += 2
        else:
            width += 1
    return width


def pad_right(text: str, width: int) -> str:
    """按显示宽度右补空格至 width（保留已有颜色码，不影响对齐）。"""
    diff = width - _disp_len(text)
    return text + (" " * diff if diff > 0 else "")


# ── 终端宽度 ──────────────────────────────────────────────────
@lru_cache(maxsize=1)
def _term_width() -> int:
    try:
        w = shutil.get_terminal_size((80, 20)).columns
        return w if w > 0 else 80
    except Exception:
        return 80


# ── 分隔线 / 横幅 ─────────────────────────────────────────────
def divider(width: int | None = None, char: str = "─", kind: str = "rule") -> None:
    """打印一条分隔线，宽度自适应终端。"""
    w = width or _term_width()
    # 避免窄终端时超长
    w = min(w, 72)
    print(c(char * w, kind))


def banner(title_text: str, subtitle: str | None = None) -> None:
    """打印居中标题横幅（上下双横线，避免 CJK 右边框对齐问题）。"""
    w = min(_term_width(), 72)
    print(c("═" * w, "title"))
    inner = title_text
    pad = max((w - _disp_len(inner)) // 2, 0)
    print(" " * pad + c(inner, "title"))
    if subtitle:
        spad = max((w - _disp_len(subtitle)) // 2, 0)
        print(" " * spad + c(subtitle, "muted"))
    print(c("═" * w, "title"))


def kv(label: str, value: str, label_width: int = 10) -> None:
    """打印 ``  标签   值``，标签按显示宽度对齐。"""
    print("  " + c(pad_right(label, label_width), "label") + " " + value)


# ── 标准化状态输出 ────────────────────────────────────────────
# 纯 ASCII 标记，避免 emoji；颜色禁用时标记仍可传达状态
_SUCCESS_ICON = "[+]"
_ERROR_ICON = "[x]"
_WARN_ICON = "[!]"
_INFO_ICON = "[i]"
_DONE_ICON = "[*]"


def success(msg: str) -> None:
    print(f"{c(_SUCCESS_ICON, 'success')} {c(msg, 'success')}")


def error(msg: str) -> None:
    print(f"{c(_ERROR_ICON, 'error')} {c(msg, 'error')}")


def warning(msg: str) -> None:
    print(f"{c(_WARN_ICON, 'warn')} {c(msg, 'warn')}")


def info(msg: str) -> None:
    print(f"{c(_INFO_ICON, 'info')} {msg}")


def done(msg: str) -> None:
    print(f"{c(_DONE_ICON, 'success')} {c(msg, 'success')}")


def step_header(index: int, total: int, msg: str) -> None:
    """打印带步骤序号的标题：``[1/4] 正在解析文档``。"""
    tag = f"[{index}/{total}]"
    print(c(f"{tag} {msg}", "step"))


def section(title_text: str) -> None:
    """打印小节标题。"""
    print(c(f"■ {title_text}", "subtitle"))


# ── 非阻塞进度动画 ────────────────────────────────────────────
class Spinner:
    """守护线程驱动的旋转动画，不阻塞主流程。

    用法::

        with ui.Spinner("[1/4] 正在解析文档..."):
            document = Parser.parse(...)
        ui.success("解析完成")

    非 TTY 环境（日志 / 管道）下，仅打印一次提示，不做动画，避免控制字符污染输出。
    """

    _FRAMES = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"

    def __init__(self, message: str):
        self._message = message
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._max_len = 0

    def __enter__(self) -> "Spinner":
        self.start()
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        self.stop()
        return False

    def start(self) -> None:
        if not color_enabled():
            # 非交互环境：只打印一次提示
            print(self._message)
            return
        self._thread = threading.Thread(target=self._spin, daemon=True)
        self._thread.start()

    def _spin(self) -> None:
        i = 0
        interval = 0.08
        while not self._stop.is_set():
            frame = self._FRAMES[i % len(self._FRAMES)]
            line = f"\r{c(frame, 'info')} {self._message}"
            # 记录已写过最长行，用于退出时清屏
            self._max_len = max(self._max_len, len(strip(line)))
            sys.stdout.write(line)
            sys.stdout.flush()
            time.sleep(interval)
            i += 1

    def stop(self) -> None:
        if self._thread is None:
            return
        self._stop.set()
        self._thread.join()
        # 清除本行残留动画
        sys.stdout.write("\r" + " " * self._max_len + "\r")
        sys.stdout.flush()
        self._thread = None


def spinner(message: str) -> Spinner:
    """便捷工厂，等价于 ``Spinner(message)``。"""
    return Spinner(message)


def blank() -> None:
    """打印空行（仅排版用途）。"""
    print()
