"""L3 视觉评审(可降级链)

出片后对 pptx 做抽样视觉复核,三级降级,任何环节缺失都不阻塞出片:
1. VLM:client 提供 extract_vision(prompt, image_path) 时按抽样页评审
2. PIL 代理指标:墨量占比 + 左右/上下平衡(确定性计算,零模型依赖)
3. skipped:LibreOffice / PDF 转换器 / Pillow 任一缺失 → 返回 skipped 条目

约定:judge_deck 永不抛异常,调用方拿到结果直接用,失败自动折叠为 skipped。
"""
from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import List, Optional

# soffice 不在 PATH 时的常见安装位置(Windows/macOS/Linux)
_SOFFICE_CANDIDATES = (
    r"C:\Program Files\LibreOffice\program\soffice.exe",
    r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
    "/Applications/LibreOffice.app/Contents/MacOS/soffice",
    "/usr/bin/soffice",
    "/opt/libreoffice/program/soffice",
)
_CONVERT_TIMEOUT = 120  # 单次外部转换的秒数上限
_THUMB_W = 256          # 统一缩放宽度,兼顾指标稳定性与速度
_INK_THRESHOLD = 40     # 与背景亮度差超过该值视为"墨迹"(内容/装饰)


def _find_soffice() -> Optional[str]:
    """定位 LibreOffice 可执行文件,找不到返回 None(触发降级)。"""
    found = shutil.which("soffice")
    if found:
        return found
    for cand in _SOFFICE_CANDIDATES:
        if Path(cand).is_file():
            return cand
    return None


def _pdf_to_pngs(pdf_path: Path, out_dir: Path) -> List[Path]:
    """PDF → 逐页 PNG。优先 PyMuPDF,退回 pdftoppm,都不可用返回空列表。"""
    try:
        import fitz  # PyMuPDF
        pngs: List[Path] = []
        with fitz.open(pdf_path) as doc:
            for i, page in enumerate(doc):
                pix = page.get_pixmap(dpi=96)
                out = out_dir / f"page_{i + 1:03d}.png"
                pix.save(out)
                pngs.append(out)
        return pngs
    except ImportError:
        pass
    pdftoppm = shutil.which("pdftoppm")
    if pdftoppm:
        subprocess.run(
            [pdftoppm, "-png", "-r", "96", str(pdf_path), str(out_dir / "page")],
            check=True, timeout=_CONVERT_TIMEOUT,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        return sorted(out_dir.glob("page*.png"))
    return []


def render_pages(pptx_path, out_dir=None) -> List[Path]:
    """pptx → 逐页 PNG(soffice 转 PDF,再逐页转图)。

    任一环节不可用或失败都返回空列表——这是"视觉评审不可用"的统一信号。
    """
    try:
        soffice = _find_soffice()
        if soffice is None:
            return []
        out = Path(out_dir) if out_dir else Path(tempfile.mkdtemp(prefix="visual_judge_"))
        out.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            [soffice, "--headless", "--convert-to", "pdf",
             "--outdir", str(out), str(pptx_path)],
            check=True, timeout=_CONVERT_TIMEOUT,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        pdfs = list(out.glob("*.pdf"))
        if not pdfs:
            return []
        return _pdf_to_pngs(pdfs[0], out)
    except Exception:
        return []


def _sample_indices(n: int, ratio: float) -> List[int]:
    """确定性等距抽样:始终覆盖首页,页数少时只看首页,结果升序去重。"""
    if n <= 0:
        return []
    k = max(1, round(n * ratio))
    if k == 1:
        return [0]
    step = (n - 1) / (k - 1)
    return sorted({min(n - 1, round(i * step)) for i in range(k)})


def _load_gray(path) -> Optional["object"]:
    """读图转灰度;Pillow 缺失或文件损坏返回 None。"""
    try:
        from PIL import Image
    except ImportError:
        return None
    try:
        im = Image.open(path)
        try:
            gray = im.convert("L")
            gray.load()  # 物化像素,关闭源文件后仍可用
        finally:
            im.close()
        return gray
    except Exception:
        return None


def _image_metrics(path) -> Optional[dict]:
    """PIL 代理指标:墨量占比 + 左右/上下墨量平衡。

    背景取直方图最高峰亮度,与背景差超过 _INK_THRESHOLD 记为墨迹。
    balance 为 (右-左)/墨量:负值=左重,正值=右重,取值 [-1, 1]。
    """
    gray = _load_gray(path)
    if gray is None:
        return None
    w = _THUMB_W
    h = max(1, round(gray.height * w / gray.width))
    px = list(gray.resize((w, h)).getdata())

    hist = [0] * 256
    for v in px:
        hist[v] += 1
    bg = max(range(256), key=hist.__getitem__)

    ink_count = left = right = top = bottom = 0
    for i, v in enumerate(px):
        if abs(v - bg) <= _INK_THRESHOLD:
            continue
        ink_count += 1
        x, y = i % w, i // w
        if x < w // 2:
            left += 1
        else:
            right += 1
        if y < h // 2:
            top += 1
        else:
            bottom += 1

    if ink_count == 0:
        return {"ink_ratio": 0.0, "balance_lr": 0.0, "balance_tb": 0.0, "flags": []}

    balance_lr = (right - left) / ink_count
    balance_tb = (bottom - top) / ink_count
    flags: List[str] = []
    if abs(balance_lr) > 0.5:
        flags.append("lr_imbalance")
    if abs(balance_tb) > 0.6:
        flags.append("tb_imbalance")
    return {
        "ink_ratio": round(ink_count / len(px), 4),
        "balance_lr": round(balance_lr, 4),
        "balance_tb": round(balance_tb, 4),
        "flags": flags,
    }


_VLM_PROMPT = (
    "你是幻灯片视觉评审员。请评审这张幻灯片截图的版面质量:"
    "是否存在元素重叠、文字截断、明显失衡或拥挤。\n"
    '只输出 JSON: {"score": 0到10的整数, "issues": ["问题简述", ...]}'
)


def _judge_vlm(extract_vision, image_path) -> Optional[dict]:
    """调用 VLM 评审单页;client 缺失/调用失败/输出非法都返回 None。"""
    try:
        verdict = extract_vision(_VLM_PROMPT, str(image_path))
        score = int(verdict.get("score", -1))
        issues = [str(i) for i in (verdict.get("issues") or [])]
        if 0 <= score <= 10:
            return {"score": score, "issues": issues}
    except Exception:
        pass
    return None


def judge_deck(pptx_path, client=None, sample_ratio: float = 0.2,
               out_dir=None) -> List[dict]:
    """出片后视觉抽检入口,永不抛异常。

    - client.extract_vision(prompt, image_path) → {"score": int, "issues": [str]}
      未提供该钩子或调用失败时,逐页回退 PIL 代理指标
    - 渲染链不可用(soffice/转换器缺失)时返回单条 skipped
    返回条目形如 {"page": 页码(1起)|None, "status": "ok"|"skipped", "mode": "vlm"|"pil", ...}
    """
    try:
        pngs = render_pages(pptx_path, out_dir)
    except Exception:
        pngs = []
    if not pngs:
        return [{"page": None, "status": "skipped",
                 "reason": "renderer_unavailable(需 LibreOffice + PyMuPDF/poppler)"}]

    sample = _sample_indices(len(pngs), sample_ratio)
    extract_vision = getattr(client, "extract_vision", None)

    reviews: List[dict] = []
    for idx in sample:
        page = {"page": idx + 1}
        if extract_vision is not None:
            verdict = _judge_vlm(extract_vision, pngs[idx])
            if verdict is not None:
                reviews.append({**page, "status": "ok", "mode": "vlm", **verdict})
                continue
        metrics = _image_metrics(pngs[idx])
        if metrics is None:
            reviews.append({**page, "status": "skipped", "reason": "pillow_unavailable"})
            continue
        reviews.append({**page, "status": "ok", "mode": "pil", **metrics})
    return reviews
