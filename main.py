from ctypes.wintypes import PUINT

import App.MiniMaxAPI

def main():
    #获取客户端
    client = App.MiniMaxAPI.MiniMaxClient()

    #生成对话结果
    response = client.chat("你好！")

    print(response)


if __name__ == "__main__":
    main()
