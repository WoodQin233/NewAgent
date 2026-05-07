import MiniMaxAPI

#获取客户端
client = MiniMaxAPI.MiniMaxClient()

#生成对话结果
response = client.chat("你好！")

#解析响应
for item in response["content"]:
    if item["type"] == "thinking":              #输出思考过程
        print(f"思考:\n{item['text']}\n")
    elif item["type"] == "text":                #输出回复内容
        print(f"回复:\n{item['text']}\n")

