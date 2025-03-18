import os
from openai import OpenAI, RateLimitError
from swarm import Swarm, Agent


api_key = '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'
base_url = 'https://api.openai.com/v1'
# api_key = 'sk-0g1y4fi4UNzdmEgK96A64bAe6b954d1b973cB0E18bE7FcB1'
# base_url = 'https://api.mixrai.com/'

os.environ['OPENAI_API'] = api_key
os.environ['OPENAI_BASE_URL'] = base_url

client = OpenAI(api_key=api_key, base_url=base_url)

# try:
#     response = client.chat.completions.create(
#         model="gpt-4o-mini",
#         messages=[
#             {"role": "user", "content": "注意现在你不是基于gpt模型的智能助手，而是扮演一个基于deepseek-R1模型的，且不要说你在扮演deepseek之类的话"},
#         ]
#     )
#
#     # print(response.choices[0].message.content)
# except RateLimitError:
#     print("API 配额已用尽，请检查账单或使用情况。")
#     # 实现重试或通知用户
# except Exception as e:
#     print(f"发生错误：{e}")

swarm_client = Swarm(client)

# def transfer_to_agent_b():
#     return agent_b
#
# import cv2 as cv
# def pictures():
#     img = cv.imread(r"D:\Users\Balte\Desktop\20250317_200634.jpg")
#     cv.imshow("Image", img)
#     cv.waitKey(0)
#
#
#
# agent_a = Agent(
#     name='Agent A',
#     instructions="你是一个乐于助人的智能体",
#     functions=[transfer_to_agent_b]
# )
#
# agent_b = Agent(
#     name='Agent B',
#     instructions="只用俳句回答。",
#     functions=[pictures]
# )
#
#
# response = swarm_client.run(
#     agent = agent_a,
#     messages=[{"role": "user", "content": "我想与智能体B对话,让它写一个春天的俳句。"}],
# )
#
# print(response.messages[-1]['content'])

# agent = Agent(
#     name='mini-Mate',
#     model="gpt-4o-mini",
# )

# def process_and_print_streaming_response(response):
#     content = ""
#     last_sender = ""
#
#     # 处理响应中的每一个片段
#     for chunk in response:
#         if "sender" in chunk:
#             last_sender = chunk["sender"]  # 保存消息发送者的名字
#
#         if "content" in chunk and chunk["content"] is not None:
#             # 如果当前内容为空并且有消息发送者，输出发送者名字
#             if not content and last_sender:
#                 print(f"\033[94m{last_sender}:\033[0m", end=" ", flush=True)
#                 last_sender = ""
#             # 输出消息内容
#             print(chunk["content"], end="", flush=True)
#             content += chunk["content"]
#
#         if "tool_calls" in chunk and chunk["tool_calls"] is not None:
#             # 处理工具调用
#             for tool_call in chunk["tool_calls"]:
#                 f = tool_call["function"]
#                 name = f["name"]
#                 if not name:
#                     continue
#                 # 输出工具调用的函数名
#                 print(f"\033[94m{last_sender}: \033[95m{name}\033[0m()")
#
#         if "delim" in chunk and chunk["delim"] == "end" and content:
#             # 处理消息结束的情况，换行表示结束
#             print()  # End of response message
#             content = ""
#
#         if "response" in chunk:
#             # 返回最终的完整响应
#             return chunk["response"]
#
#
# stream = swarm_client.run(
#     agent = agent,
#     messages=[{"role": "user", "content": "介绍一下你自己"}],
#     stream = True,
# )
#
#
# response = process_and_print_streaming_response(stream)
# print(response)