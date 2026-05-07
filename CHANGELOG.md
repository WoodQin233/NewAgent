# 更新日志

## dev 0.0.1 - 2025-05-07

### 新增
+ langchain-anthropic插件开发
+ uv包管理

## main 0.0.1 - 2025-05-07

### 新增
+ MiniMax API封装模块
+ MiniMaxClient客户端类
+ Config配置管理类
+ 自定义异常类（MiniMaxAPIError、AuthenticationError、APIResponseError）

### 功能
+ 支持从环境变量`MINIMAX_API_KEY`读取API密钥
+ 支持自定义对话参数
+ chat()方法返回结构化响应（主要包含thinking和text）
