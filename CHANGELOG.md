# 更新日志

## dev 0.0.2 - 2025-05-08

### 新增
+ langchain_community
+ 用langchain-anthropic接管了原有的char接口
- key参数改为api_key，且不再支持直接传入key参数，必须通过环境变量或配置文件设置
+ Tools接口的初步设计和实现

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
