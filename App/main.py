from ctypes.wintypes import PUINT

import client as Client

def main():
    #获取客户端
    client = Client.MiniMaxClient()

    #生成对话结果
    response = client.chat("你好！")

    print(response)


if __name__ == "__main__":
    main()
