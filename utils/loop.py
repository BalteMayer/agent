import json
from swarm import Swarm


def run_demo_loop(
        openai_client,
        starting_agent,
        context_variables=None,
        stream=False,
        debug=False) -> None:
    client = Swarm(openai_client)
    print("Starting Swarm CLI 🐝")
    print('Type "exit" or "quit" to leave the chat.')

    messages = []
    agent = starting_agent

    # 主循环，用户可以持续与智能体对话
    while True:
        user_input = input("\033[90mUser\033[0m: ").strip()  # 读取用户输入并去除首尾空格

        # 检查用户是否输入了退出关键词
        if user_input.lower() in {"exit", "quit"}:
            print("Exiting chat. Goodbye!")
            break  # 退出循环，结束聊天

        messages.append({"role": "user", "content": user_input})  # 将用户输入添加到消息列表

        # 运行 Swarm 客户端，与智能体交互
        response = client.run(
            agent=agent,
            messages=messages,
            context_variables=context_variables or {},
            stream=stream,
            debug=debug,
        )

        if stream:
            # 如果启用了流式处理，调用流处理函数
            response = process_and_print_streaming_response(response)
        else:
            # 否则直接打印消息
            pretty_print_messages(response.messages)

        # 更新消息和当前智能体
        messages.extend(response.messages)
        agent = response.agent



def process_and_print_streaming_response(response):
    content = ""
    last_sender = ""

    # 处理响应中的每一个片段
    for chunk in response:
        if "sender" in chunk:
            last_sender = chunk["sender"]  # 保存消息发送者的名字

        if "content" in chunk and chunk["content"] is not None:
            # 如果当前内容为空并且有消息发送者，输出发送者名字
            if not content and last_sender:
                print(f"\033[94m{last_sender}:\033[0m", end=" ", flush=True)
                last_sender = ""
            # 输出消息内容
            print(chunk["content"], end="", flush=True)
            content += chunk["content"]

        if "tool_calls" in chunk and chunk["tool_calls"] is not None:
            # 处理工具调用
            for tool_call in chunk["tool_calls"]:
                f = tool_call["function"]
                name = f["name"]
                if not name:
                    continue
                # 输出工具调用的函数名
                print(f"\033[94m{last_sender}: \033[95m{name}\033[0m()")

        if "delim" in chunk and chunk["delim"] == "end" and content:
            # 处理消息结束的情况，换行表示结束
            print()  # End of response message
            content = ""

        if "response" in chunk:
            # 返回最终的完整响应
            return chunk["response"]


def pretty_print_messages(messages) -> None:
    for message in messages:
        if message["role"] != "assistant":
            continue

        # 输出智能体名称，蓝色显示
        print(f"\033[94m{message['sender']}\033[0m:", end=" ")

        # 输出智能体的回复
        if message["content"]:
            print(message["content"])

        # 如果有工具调用，输出工具调用信息
        tool_calls = message.get("tool_calls") or []
        if len(tool_calls) > 1:
            print()
        for tool_call in tool_calls:
            f = tool_call["function"]
            name, args = f["name"], f["arguments"]
            arg_str = json.dumps(json.loads(args)).replace(":", "=")
            print(f"\033[95m{name}\033[0m({arg_str[1:-1]})")