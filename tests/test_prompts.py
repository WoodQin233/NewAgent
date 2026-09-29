"""提示词管理模块单元测试

运行方式（项目根目录）：
    python -m unittest discover tests -v

两类用例：
- RealPromptsTest 直接渲染生产 Prompts/ 下的模板，断言与迁移前内联字符串逐字节等价
- ManagerTest 用临时目录构造独立 PromptManager，覆盖校验、版本、缓存行为
"""
import tempfile
import unittest
from pathlib import Path

from App.prompts import (
    PromptError,
    PromptID,
    PromptManager,
    PromptNotFoundError,
    PromptRenderError,
    render_prompt,
)


# ─────────────────────── 迁移等价性（生产模板） ───────────────────────

class RealPromptsTest(unittest.TestCase):
    """迁移前后渲染结果必须逐字节一致（业务逻辑不变）。"""

    def test_analyze_outline_byte_identical(self):
        doc = "示例文档内容"
        expected = (
            "你是一个专业的 PPT 内容规划助手。"
            "任务:根据用户提供的文档内容,生成结构化的 PPT 大纲。\n"
            "注意:只输出符合要求结构的 JSON 结果,不要输出 markdown 代码块或多余解释。\n"
            "要求:\n"
            "1. 提取文档的核心主题和关键信息\n"
            "2. 合理分页,确保每页内容聚焦\n"
            "3. 每页内容简洁明了,适合演讲展示\n"
            "4. 所有内容必须来源于用户提供的文档,不要自行发挥\n"
            "5. 每个 slide 的 title 必须是该页内容的语义化概括，禁止页码式标题（如 \"第N页\"、\"第N部分\"、\"01\"）\n\n"
            "文档内容:\n"
            f"{doc}"
        )
        self.assertEqual(
            render_prompt(PromptID.ANALYZE_OUTLINE, document=doc), expected
        )

    def test_layout_byte_identical(self):
        outline = '{"title": "示例"}'
        expected = (
            "你是一个专业的 PPT 内容细化助手。"
            "任务:根据提供的大纲,输出结构化布局 LayoutInfo(只做语义决策,不生成坐标/字号/对齐)。\n"
            "注意:只输出符合 LayoutInfo 结构的 JSON 结果,不要输出 markdown 代码块或多余解释。\n"
            "注意:items 与 slides 字段都是数组,直接输出 JSON 数组 [...],不要用 item 键包裹。\n"
            "输出结构 LayoutInfo 包含:\n"
            "- outline: 对象,包含 title(标题) 与 items(页面条目数组,逐页对应,page 从 1 连续)\n"
            "- detail: 可选,每页可补充 subtitle/quote/image_prompt/image_url/mood/颜色覆盖\n"
            "- theme: 全局主题色\n"
            "- canvas: 画布尺寸(默认 13.33x7.5 英寸)\n"
            "页面类型 PageType 取值: TITLE / SECTION / PARAGRAPH / BULLETS / TWO_COL / IMAGE / QUOTE / SUMMARY\n"
            "title 硬性规则:必须是该页内容的语义化概括,禁止 '第N页/第N章/N./01/Part N' 等页码式标题\n"
            "反例: {\"page\":3,\"type\":\"SECTION\",\"title\":\"03\"}\n"
            "正例: {\"page\":3,\"type\":\"SECTION\",\"title\":\"市场竞争格局\"}\n"
            "SECTION 页字段约定:title 只写章节名本身,禁止携带'第X部分/第X章'序号前缀,\n"
            "序号由渲染器按章节出现顺序自动生成;subtitle 可选,用一句话概括本章看点\n"
            "outline.items 的 points 必须逐字沿用输入大纲对应页的内容,不得改写、增删或丢字;\n"
            "title 优先沿用输入大纲,但若输入大纲的 title 是页码式标题(如 '3'、'第3页'),\n"
            "必须根据该页内容改写为语义化标题\n"
            "要求:\n"
            "1. outline 逐页对应输入大纲,首页 TITLE,末页 SUMMARY 或 TITLE\n"
            "2. 不要凭空新增文字、图片或要点\n"
            "3. 颜色用 #RRGGBB,字体用 Microsoft YaHei\n"
            "4. BULLETS/TWO_COL/SUMMARY 至少 2 个 points;PARAGRAPH 至少 1 个;"
            "QUOTE 必填 quote;IMAGE 必填 image_prompt 或 image_url\n\n"
            "PPT 大纲:\n"
            f"{outline}"
        )
        self.assertEqual(
            render_prompt(PromptID.LAYOUT, outline_json=outline), expected
        )

    def test_template_no_trailing_newline(self):
        """|- 块标量不应带入尾部换行。"""
        from App.prompts import _manager

        for pid in PromptID:
            self.assertFalse(_manager().template(pid).endswith("\n"), pid.value)


# ─────────────────────── PromptManager 行为（临时目录） ───────────────────────

_BASE = """\
id: analyze_outline
description: 测试用
default_version: {default}
versions:
{versions}
"""

_V1 = """\
  1:
    template: |-
      v1 正文 {{document}}"""

_V2 = """\
  2:
    template: |-
      v2 正文 {{document}}"""


class ManagerTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name)
        self.manager = PromptManager(self.dir)

    def tearDown(self):
        self._tmp.cleanup()

    def _write(self, name: str, content: str) -> None:
        (self.dir / name).write_text(content, encoding="utf-8")

    def _write_analyze(self, body: str) -> None:
        self._write("analyze_outline.yaml", body)

    # ── 渲染与校验 ──

    def test_render_substitutes_variable(self):
        self._write_analyze(_BASE.format(default=1, versions=_V1))
        self.assertEqual(
            self.manager.render(PromptID.ANALYZE_OUTLINE, document="文档"),
            "v1 正文 文档",
        )

    def test_render_missing_variable_raises(self):
        self._write_analyze(_BASE.format(default=1, versions=_V1))
        with self.assertRaises(PromptRenderError) as ctx:
            self.manager.render(PromptID.ANALYZE_OUTLINE)
        self.assertIn("document", str(ctx.exception))

    def test_render_extra_variable_raises(self):
        self._write_analyze(_BASE.format(default=1, versions=_V1))
        with self.assertRaises(PromptRenderError) as ctx:
            self.manager.render(PromptID.ANALYZE_OUTLINE, document="x", typo_var="y")
        self.assertIn("typo_var", str(ctx.exception))

    def test_single_brace_json_not_treated_as_placeholder(self):
        body = _BASE.format(default=1, versions="""\
  1:
    template: |-
      反例: {"page":3,"type":"SECTION"} 变量 {{document}}""")
        self._write_analyze(body)
        result = self.manager.render(PromptID.ANALYZE_OUTLINE, document="X")
        self.assertIn('{"page":3,"type":"SECTION"}', result)
        self.assertTrue(result.endswith("X"))

    # ── 版本管理 ──

    def test_default_version_fallback(self):
        self._write_analyze(_BASE.format(default=2, versions=_V1 + "\n" + _V2))
        self.assertEqual(
            self.manager.render(PromptID.ANALYZE_OUTLINE, document="d"),
            "v2 正文 d",
        )

    def test_explicit_version_selection(self):
        self._write_analyze(_BASE.format(default=2, versions=_V1 + "\n" + _V2))
        self.assertEqual(
            self.manager.render(PromptID.ANALYZE_OUTLINE, document="d", version=1),
            "v1 正文 d",
        )

    def test_unknown_version_raises(self):
        self._write_analyze(_BASE.format(default=1, versions=_V1))
        with self.assertRaises(PromptNotFoundError) as ctx:
            self.manager.render(PromptID.ANALYZE_OUTLINE, document="d", version=99)
        self.assertIn("99", str(ctx.exception))

    # ── 加载与 schema 校验 ──

    def test_missing_file_raises(self):
        with self.assertRaises(PromptNotFoundError):
            self.manager.render(PromptID.LAYOUT, outline_json="{}")

    def test_id_mismatch_raises(self):
        self._write_analyze(_BASE.format(default=1, versions=_V1).replace(
            "id: analyze_outline", "id: wrong_name"
        ))
        with self.assertRaises(PromptError):
            self.manager.render(PromptID.ANALYZE_OUTLINE, document="d")

    def test_missing_versions_raises(self):
        self._write_analyze("id: analyze_outline\ndescription: 无版本\n")
        with self.assertRaises(PromptError):
            self.manager.render(PromptID.ANALYZE_OUTLINE, document="d")

    def test_default_version_not_in_versions_raises(self):
        self._write_analyze(_BASE.format(default=9, versions=_V1))
        with self.assertRaises(PromptError):
            self.manager.render(PromptID.ANALYZE_OUTLINE, document="d")

    # ── 缓存 ──

    def test_yaml_parsed_only_once(self):
        self._write_analyze(_BASE.format(default=1, versions=_V1))
        first = self.manager.render(PromptID.ANALYZE_OUTLINE, document="a")
        # 改写文件后再渲染，结果不变 → 第二次命中缓存，未重新读盘
        self._write_analyze(_BASE.format(default=1, versions=_V1).replace("v1", "vX"))
        second = self.manager.render(PromptID.ANALYZE_OUTLINE, document="a")
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
