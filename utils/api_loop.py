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


    client = Swarm(openai_client)

    if messages is None:
        messages = []


    response = client.run(
        agent=starting_agent,
        messages=messages,
        context_variables=context_variables or {},
        stream=stream,
        debug=debug,
    )

    if stream:
        stream_response = process_stream_response(response)
        return {
            "messages": messages + stream_response["messages"],
            "agent": stream_response["agent"],
            "stream_chunks": stream_response["chunks"]
        }
    else:
        response_messages = response.messages
        updated_messages = messages + response_messages

        return {
            "messages": updated_messages,
            "agent": response.agent,
            "response_content": extract_response_content(response_messages)
        }


def extract_response_content(messages):

    result = []
    for message in messages:
        if message["role"] != "assistant":
            continue

        response_item = {
            "sender": message["sender"],
            "content": message.get("content", ""),
        }


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

    chunks = []
    messages = []
    current_message = {"role": "assistant", "content": "", "sender": ""}
    agent = None

    for chunk in response:
        chunk_copy = chunk.copy()


        chunks.append(chunk_copy)

        if "sender" in chunk and chunk["sender"]:
            current_message["sender"] = chunk["sender"]

        if "content" in chunk and chunk["content"] is not None:
            current_message["content"] += chunk["content"]

        if "tool_calls" in chunk and chunk["tool_calls"] is not None:
            if "tool_calls" not in current_message:
                current_message["tool_calls"] = []

            for tool_call in chunk["tool_calls"]:

                current_message["tool_calls"].append(tool_call)

        if "delim" in chunk and chunk["delim"] == "end" and current_message["content"]:

            messages.append(current_message)
            current_message = {"role": "assistant", "content": "", "sender": ""}

        if "response" in chunk:
            agent = chunk["response"].agent

    return {
        "chunks": chunks,
        "messages": messages,
        "agent": agent
    }