# 提示词管理集成文档

所有 LLM 提示词集中存放在 `Prompts/` 目录，业务代码通过 `App.prompts` 模块按 ID 取用，禁止在业务代码中内联提示词文本。

## 目录结构

```
Prompts/                     # 提示词模板（数据文件，改提示词不动代码）
  analyze_outline.yaml       # PPT 大纲生成（AIAnalyzer.analyze）
  layout.yaml                # PPT 布局生成（AIAnalyzer.layout）
App/prompts.py               # 管理模块：PromptID / PromptManager / render_prompt
tests/test_prompts.py        # 单元测试
```

## 快速使用

```python
from App.prompts import PromptID, render_prompt

# 常规调用：使用默认版本
prompt = render_prompt(PromptID.ANALYZE_OUTLINE, document=raw_text)

# 显式指定版本（A/B 实验、快速回滚）
prompt = render_prompt(PromptID.LAYOUT, outline_json=outline_json, version=2)
```

参数名由 `@overload` 静态约束：IDE 会自动补全，传错参数名 mypy/IDE 直接标红；
运行时再经严格双向校验兜底（缺变量、多变量均抛 `PromptRenderError`）。

## YAML 文件格式

```yaml
id: analyze_outline          # 必须 = 文件名 = PromptID 成员值
description: 用途说明
default_version: 1           # 未指定 version 时使用
versions:
  1:
    template: |-             # 必须用 |-（strip 块标量），防止尾部多余换行
      模板文本，占位符写作 {{document}}
```

占位符规则：`{{variable}}`（双花括号，允许内部空白）。模板里写 JSON 示例的
单花括号 `{"page":3}` 不会被误识别，无需转义。

## 新增提示词（三步）

1. `Prompts/` 下新建 `<name>.yaml`，按上面格式填写
2. `App/prompts.py` 的 `PromptID` 中登记成员：`NAME = "<name>"`
3. 在 `render_prompt` 上补一个 `@overload`，声明该提示词的关键字参数

## 版本管理

- 同一份提示词的多个版本共存于 `versions:` 下，键为整数版本号
- `default_version` 指向生产生效版本；发新版本只需追加 `versions.2` 并改 `default_version`
- 回滚：把 `default_version` 改回旧版本号，或调用处显式 `version=1`
- 迭代中的实验版本可只追加不进 `default_version`，通过 `version=` 参数试用

## 异常

| 异常 | 触发场景 |
|---|---|
| `PromptNotFoundError` | YAML 文件不存在；指定的 version 不存在 |
| `PromptRenderError` | 缺少模板声明的变量；传入了模板未使用的变量 |
| `PromptError` | YAML schema 不合法（id 与文件名不一致、versions 为空、default_version 未指向已有版本等） |

## 性能

YAML 进程内只解析一次（`PromptManager` 实例级缓存 + 模块级单例），渲染仅为
一次正则替换；热路径上 `render_prompt()` 无磁盘 IO。

## 测试

```powershell
python -m unittest discover tests -v
```

其中 `RealPromptsTest` 是防回归用例：它持有当前生产模板的期望渲染结果，
直接渲染 `Prompts/` 下的真实模板并逐字节比对。修改提示词后需同步更新该
用例的期望值，保证改动是显式的、可审查的。
