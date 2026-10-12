# NewAgent

文档驱动的 AI PPT 生成 Agent：输入一份文档，AI 自动完成大纲规划与版式设计，最终渲染输出 `.pptx` 演示文稿。

## 功能特性

- **文档解析**：读取文本并构造结构化文档对象（当前支持 `.txt`，更多格式开发中）
- **多厂商接入**：MiniMax / DeepSeek / GLM 三选一（推荐DeepSeek），均走 Anthropic 兼容协议，改一行配置即可切换
- **两阶段生成**：先由 AI 生成结构化大纲（JSON），再生成逐页版式布局
- **PPT 渲染**：基于 python-pptx 原生渲染
- **运行统计**：打印各阶段耗时与 Token 消耗
- **提示词集中管理**：全部提示词抽离为 YAML 模板，支持参数化渲染与版本管理（详见 [docs/prompts.md](docs/prompts.md)）

## 工作流程

```
文档 → [1/4] 解析 → [2/4] AI 生成大纲 → [3/4] AI 生成布局 → [4/4] 渲染 PPTX
```

## 快速开始

### 环境要求

- Python 3.10+
- [uv](https://docs.astral.sh/uv/)（推荐）或 pip

### 安装依赖

```bash
uv sync
# 或
pip install -e .
```

### 配置 API Key

1. 复制环境变量模板并填入你的 Key：
   ```bash
   cp .env.example .env
   ```
2. 在 `Config/config.json` 中通过 `api.active` 选择厂商（`minimax` / `deepseek` / `glm`），只需配置对应厂商的环境变量。

### 运行

```bash
python App/cli.py
```

按提示输入文档路径（回车使用示例文档 `data/test.txt`），流水线完成后在 `output/` 目录找到生成的 PPT。

## 项目结构

```
NewAgent/
├── App/                  # 核心业务：解析、分析、生成、渲染
│   ├── cli.py            # 交互式命令行入口
│   ├── parser.py         # 文档解析
│   ├── analyzer.py       # AI 大纲与布局生成
│   ├── generator.py      # PPT 渲染
│   ├── providers.py      # 多厂商客户端适配
│   └── prompts.py        # 提示词管理模块
├── Prompts/              # 提示词 YAML 模板
├── Config/config.json    # 运行配置（厂商切换、模型参数）
├── Utils/                # 配置加载、日志、统计
├── data/                 # 示例文档
├── tests/                # 单元测试
└── output/               # 生成结果（自动创建）
```

## 运行测试

```bash
python -m unittest discover tests -v
```

## 许可证

[MIT](LICENSE)
