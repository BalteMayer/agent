import json
from swarm import Swarm


def run_api_loop(
        openai_client,
        starting_agent,
        user_input,
        messages=None,
        context_variables=None,
        stream=False,
        debug=False):
    """
    API版本的Swarm循环，接收用户输入并返回响应

    Args:
        openai_client: OpenAI客户端实例
        starting_agent: 起始智能体
        user_input: 用户输入的消息
        messages: 历史消息列表，如果为None则创建新的
        context_variables: 上下文变量
        stream: 是否使用流式响应
        debug: 是否开启调试模式

    Returns:
        dict: 包含响应消息和更新后的消息历史
    """
    client = Swarm(openai_client)

    if messages is None:
        messages = []

    # 添加用户输入到消息列表
    messages.append({"role": "user", "content": user_input})

    # 运行Swarm客户端，与智能体交互
    response = client.run(
        agent=starting_agent,
        messages=messages,
        context_variables=context_variables or {},
        stream=stream,
        debug=debug,
    )

    if stream:
        # 如果启用了流式处理，调用流处理函数
        stream_response = process_stream_response(response)
        return {
            "messages": messages + stream_response["messages"],
            "agent": stream_response["agent"],
            "stream_chunks": stream_response["chunks"]
        }
    else:
        # 非流式处理
        response_messages = response.messages
        updated_messages = messages + response_messages

        return {
            "messages": updated_messages,
            "agent": response.agent,
            "response_content": extract_response_content(response_messages)
        }


def extract_response_content(messages):
    """从响应消息中提取内容"""
    result = []
    for message in messages:
        if message["role"] != "assistant":
            continue

        response_item = {
            "sender": message["sender"],
            "content": message.get("content", ""),
        }

        # 如果有工具调用，添加到结果中
        tool_calls = message.get("tool_calls", [])
        if tool_calls:
            response_item["tool_calls"] = []
            for tool_call in tool_calls:
                f = tool_call["function"]
                response_item["tool_calls"].append({
                    "name": f["name"],
                    "arguments": json.loads(f["arguments"]) if f["arguments"] else {}
                })

        result.append(response_item)
    return result


def process_stream_response(response):
    """处理流式响应并返回格式化的结果"""
    chunks = []
    messages = []
    current_message = {"role": "assistant", "content": "", "sender": ""}
    agent = None

    for chunk in response:
        chunk_copy = chunk.copy()  # 创建副本以便安全修改

        # 收集所有数据块以便发送到客户端
        chunks.append(chunk_copy)

        if "sender" in chunk and chunk["sender"]:
            current_message["sender"] = chunk["sender"]

        if "content" in chunk and chunk["content"] is not None:
            current_message["content"] += chunk["content"]

        if "tool_calls" in chunk and chunk["tool_calls"] is not None:
            if "tool_calls" not in current_message:
                current_message["tool_calls"] = []

            for tool_call in chunk["tool_calls"]:
                # 添加工具调用到当前消息
                current_message["tool_calls"].append(tool_call)

        if "delim" in chunk and chunk["delim"] == "end" and current_message["content"]:
            # 消息结束，添加到消息列表中
            messages.append(current_message)
            current_message = {"role": "assistant", "content": "", "sender": ""}

        if "response" in chunk:
            agent = chunk["response"].agent

    return {
        "chunks": chunks,
        "messages": messages,
        "agent": agent
    }