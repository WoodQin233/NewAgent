"""配置中心

项目读取配置的唯一入口：合并 Config/config.json（用户选择）与 .env（密钥），
产出强类型对象，供 App/providers.py 和 App/client.py 使用。

配置文件里的 providers 是"预设表"，api.active 指向当前生效的那一条。
切换厂商/模型只需要改 Config/config.json，不需要动代码：
    "api": { "active": "deepseek" }
"""
import json
import os
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = PROJECT_ROOT / "Config" / "config.json"
ENV_PATH = PROJECT_ROOT / ".env"

# 目前只实现了 Anthropic Messages 协议，等出现第二种协议再提升为配置项
DEFAULT_PROTOCOL = "anthropic"


class ConfigError(RuntimeError):
    """配置缺失或不合法，附带可执行的修复建议。"""


@dataclass(frozen=True)
class ProviderSpec:
    """一个模型厂商的预设：从哪里连、用哪个模型、密钥从哪个环境变量取。

    api_key 是 property 而不是字段——每次读取都重新查环境变量，
    这样 CLI 在 import 之后才填 key 也能生效，且不会把密钥存进缓存。
    """

    name: str
    base_url: str
    model: str
    api_key_env: str
    protocol: str = DEFAULT_PROTOCOL
    # 结构化输出模式：None/"tools" 走工具调用（默认），"json" 让模型直接输出
    # JSON 文本。部分 Anthropic 兼容厂商（如 GLM）在 tool_use 里会把嵌套
    # 对象序列化成字符串，导致嵌套 Pydantic 校验失败，需要退回 json 模式。
    structured_mode: Optional[str] = None
    # 结构化输出时透传给 messages.create 的厂商级参数。
    # 例如推理模型默认开启 thinking 时，不允许强制 tool_choice，
    # 厂商预设里可以写 {"tool_choice": {"type": "auto"}} 来规避；
    # 也可以传智谱扩展的 {"thinking": {"type": "enabled", "level": "low"}} 降速。
    structured_kwargs: dict[str, Any] = field(default_factory=dict)

    @property
    def api_key(self) -> str:
        """从 api_key_env 指定的环境变量取密钥，取不到则报错。"""
        key = os.getenv(self.api_key_env, "").strip()
        if not key:
            raise ConfigError(
                f"厂商 '{self.name}' 缺少 API Key：环境变量 {self.api_key_env} 为空。"
                f"请在 {ENV_PATH} 或系统环境变量中设置后重试。"
            )
        return key

    def __repr__(self) -> str:
        # 不要用默认 repr：它会把 api_key_env 之外的信息全打出来，
        # 排查时容易顺手把密钥贴进日志
        return (
            f"ProviderSpec(name={self.name!r}, model={self.model!r}, "
            f"base_url={self.base_url!r}, api_key_env={self.api_key_env!r})"
        )


@dataclass(frozen=True)
class ApiSettings:
    """api 节里与厂商无关的通用参数，外加当前生效的厂商。"""

    provider: ProviderSpec
    max_tokens: int
    timeout: float
    temperature: float


@dataclass(frozen=True)
class Settings:
    """已解析的配置。只保留当前有消费方的部分。"""

    api: ApiSettings
    logging: dict[str, Any]


def _load_json() -> dict[str, Any]:
    if not CONFIG_PATH.is_file():
        raise ConfigError(f"配置文件不存在：{CONFIG_PATH}")
    with CONFIG_PATH.open(encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError as e:
            raise ConfigError(f"配置文件不是合法 JSON：{CONFIG_PATH}（{e}）") from e


def _build_provider(name: str, raw: dict[str, Any]) -> ProviderSpec:
    missing = [k for k in ("base_url", "model", "api_key_env") if not raw.get(k)]
    if missing:
        raise ConfigError(
            f"providers.{name} 缺少必填项：{', '.join(missing)}"
        )
    structured_raw = dict(raw.get("structured") or {})
    mode = structured_raw.pop("mode", None)
    if mode is not None and mode not in ("tools", "json"):
        raise ConfigError(
            f"providers.{name}.structured.mode 只能是 'tools' 或 'json'，收到 {mode!r}"
        )
    return ProviderSpec(
        name=name,
        base_url=raw["base_url"],
        model=raw["model"],
        api_key_env=raw["api_key_env"],
        protocol=raw.get("protocol", DEFAULT_PROTOCOL),
        structured_mode=mode,
        structured_kwargs=structured_raw,
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """读取并校验配置。结果缓存，进程内只解析一次。

    只做结构性校验（文件可读、active 指向存在的预设、预设字段齐全）。
    密钥是否存在延迟到真正调用模型时再检查，因为 CLI 是先 import、
    后交互式索要 key 的。
    """
    load_dotenv(ENV_PATH)  # 文件不存在时是 no-op
    raw = _load_json()

    api_raw = raw.get("api") or {}
    providers_raw = raw.get("providers") or {}
    if not providers_raw:
        raise ConfigError(
            f"{CONFIG_PATH} 里没有配置任何厂商，请在 providers 节至少添加一条"
        )

    active = api_raw.get("active")
    if not active:
        raise ConfigError(
            f"配置项 api.active 为空，请从 {list(providers_raw)} 中选择一个厂商"
        )
    if active not in providers_raw:
        raise ConfigError(
            f"api.active 指向的厂商 '{active}' 不存在，"
            f"可选：{list(providers_raw)}"
        )

    api = ApiSettings(
        provider=_build_provider(active, providers_raw[active]),
        max_tokens=int(api_raw.get("max_tokens", 4096)),
        timeout=float(api_raw.get("timeout", 60)),
        temperature=float(api_raw.get("temperature", 0.7)),
    )

    return Settings(
        api=api,
        logging=raw.get("logging") or {},
    )
