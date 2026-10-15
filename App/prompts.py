"""提示词管理中心

所有 LLM 提示词集中存放在项目根目录 Prompts/ 下的 YAML 文件中，
业务代码只通过 PromptID + render_prompt() 取用，不再内联提示词文本。

YAML 文件约定（一个文件对应一个提示词，支持多版本共存）：
    id: analyze_outline            # 必须与文件名、PromptID 成员值一致
    description: 用途说明
    default_version: 1             # 未显式指定 version 时使用的版本
    versions:
      1:
        template: |-               # 必须 |-（strip 块标量），避免尾部换行
          你是一个专业的 PPT 内容规划助手。
          文档内容:
          {{document}}

模板占位符写作 {{variable}}（双花括号，允许空白），与模板中可能出现的
JSON 单花括号不冲突；渲染时严格校验：缺变量、多变量都会抛出 PromptRenderError。

使用示例:
    >>> from App.prompts import PromptID, render_prompt
    >>> prompt = render_prompt(PromptID.ANALYZE_OUTLINE, document=raw_text)

新增提示词三步：
    1. 在 Prompts/ 下新建 <name>.yaml
    2. 在 PromptID 中登记同名枚举值
    3. 在 render_prompt 的 @overload 里补上参数签名（类型安全）
"""
import re
from enum import Enum
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Literal, Optional, overload

import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROMPTS_DIR = PROJECT_ROOT / "Prompts"

# 占位符：{{name}}，花括号间允许空白；与 JSON 的单花括号不冲突
_VAR_RE = re.compile(r"\{\{\s*(\w+)\s*\}\}")


class PromptError(RuntimeError):
    """提示词加载/渲染失败，附带可执行的修复建议。"""


class PromptNotFoundError(PromptError):
    """提示词文件或指定版本不存在。"""


class PromptRenderError(PromptError):
    """模板渲染失败：变量缺失或多余。"""


class PromptID(str, Enum):
    """提示词唯一标识。成员值 = Prompts/ 下的 YAML 文件名（不含扩展名）。"""

    ANALYZE_OUTLINE = "analyze_outline"
    LAYOUT = "layout"
    LAYOUT_DECISION = "layout_decision"


class PromptManager:
    """加载并缓存 Prompts/*.yaml，按版本渲染模板。

    prompts_dir 可注入，测试时指向临时目录；生产代码一般用模块级
    render_prompt()，进程内共享一个实例，每个 YAML 只解析一次。
    """

    def __init__(self, prompts_dir: Path = PROMPTS_DIR):
        self._dir = Path(prompts_dir)
        self._cache: Dict[PromptID, Dict[str, Any]] = {}

    # ── 加载与 schema 校验 ──────────────────────────────────────

    def _load(self, pid: PromptID) -> Dict[str, Any]:
        if pid in self._cache:
            return self._cache[pid]

        path = self._dir / f"{pid.value}.yaml"
        if not path.is_file():
            raise PromptNotFoundError(
                f"提示词文件不存在：{path}\n"
                f"请在 Prompts/ 下创建 {pid.value}.yaml，或检查 PromptID 登记是否正确"
            )
        with path.open(encoding="utf-8") as f:
            raw = yaml.safe_load(f)

        data = self._validate(pid, path, raw)
        self._cache[pid] = data
        return data

    @staticmethod
    def _validate(pid: PromptID, path: Path, raw: Any) -> Dict[str, Any]:
        if not isinstance(raw, dict):
            raise PromptError(f"{path} 内容为空或不是合法的 YAML 映射")
        if raw.get("id") != pid.value:
            raise PromptError(
                f"{path} 的 id 字段（{raw.get('id')!r}）必须与文件名一致（{pid.value!r}）"
            )
        versions_raw = raw.get("versions")
        if not isinstance(versions_raw, dict) or not versions_raw:
            raise PromptError(f"{path} 缺少非空的 versions 映射")

        versions: Dict[int, str] = {}
        for k, v in versions_raw.items():
            template = (v or {}).get("template") if isinstance(v, dict) else None
            if not isinstance(template, str) or not template:
                raise PromptError(f"{path} 的 versions.{k}.template 缺失或为空")
            versions[int(k)] = template

        default_version = raw.get("default_version")
        if default_version is None or int(default_version) not in versions:
            raise PromptError(
                f"{path} 的 default_version（{default_version!r}）必须指向已存在的版本："
                f"{sorted(versions)}"
            )
        return {
            "description": raw.get("description", ""),
            "default_version": int(default_version),
            "versions": versions,
        }

    # ── 查询与渲染 ──────────────────────────────────────────────

    def template(self, pid: PromptID, version: Optional[int] = None) -> str:
        """取原始模板文本（不渲染）。version 为 None 时用 default_version。"""
        data = self._load(pid)
        v = data["default_version"] if version is None else int(version)
        try:
            return data["versions"][v]
        except KeyError:
            raise PromptNotFoundError(
                f"提示词 '{pid.value}' 没有版本 {v}，可选：{sorted(data['versions'])}"
            ) from None

    def render(
        self,
        pid: PromptID,
        *,
        version: Optional[int] = None,
        **params: Any,
    ) -> str:
        """渲染模板：替换 {{变量}}，并对变量做严格双向校验。"""
        template = self.template(pid, version)
        declared = set(_VAR_RE.findall(template))
        provided = set(params)

        missing = declared - provided
        if missing:
            raise PromptRenderError(
                f"渲染 '{pid.value}' 缺少变量：{sorted(missing)}，"
                f"模板声明：{sorted(declared)}"
            )
        extra = provided - declared
        if extra:
            raise PromptRenderError(
                f"渲染 '{pid.value}' 传入了模板未使用的变量：{sorted(extra)}，"
                f"模板声明：{sorted(declared)}（检查是否拼写错误）"
            )
        return _VAR_RE.sub(lambda m: str(params[m.group(1)]), template)


@lru_cache(maxsize=1)
def _manager() -> PromptManager:
    """进程内共享的默认实例，YAML 只解析一次。"""
    return PromptManager()


@overload
def render_prompt(
    pid: Literal[PromptID.ANALYZE_OUTLINE],
    *,
    document: str,
    version: Optional[int] = None,
) -> str: ...


@overload
def render_prompt(
    pid: Literal[PromptID.LAYOUT],
    *,
    outline_json: str,
    version: Optional[int] = None,
) -> str: ...


@overload
def render_prompt(
    pid: Literal[PromptID.LAYOUT_DECISION],
    *,
    schema_catalog: str,
    pages_json: str,
    version: Optional[int] = None,
) -> str: ...


def render_prompt(
    pid: PromptID,
    *,
    version: Optional[int] = None,
    **params: Any,
) -> str:
    """按 PromptID 渲染提示词（进程内缓存，重复调用无 IO 开销）。

    version 不传时使用该提示词的 default_version；
    显式传版本号可用于 A/B 实验或快速回滚。
    """
    return _manager().render(pid, version=version, **params)
