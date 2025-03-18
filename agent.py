import os
from openai import OpenAI
from swarm import Swarm, Agent

# 导入我们修改过的模块
from utils.api_loop import run_api_loop

# API密钥和基础URL设置
api_key = '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'
base_url = 'https://api.openai.com/v1'

os.environ['OPENAI_API'] = api_key
os.environ['OPENAI_BASE_URL'] = base_url

client = OpenAI(api_key=api_key, base_url=base_url)
swarm_client = Swarm(client)

# 全局配置
model_name = 'gpt-4o-mini'
language = 'zh'
data = 'data'
chart = 'chart'

# 智能体定义
agent_main = Agent(
    name='Agent Main',
    model=model_name,
    instructions="你是一个乐于助人的智能体",
    functions=[],
)

# 创建一个字典用于存储会话
sessions = {}


def get_or_create_session(session_id):
    """获取或创建会话"""
    if session_id not in sessions:
        sessions[session_id] = {
            "messages": [],
            "agent": agent_main
        }
    return sessions[session_id]


def process_message(session_id, user_message, stream=True):
    """处理用户消息，返回智能体响应"""
    session = get_or_create_session(session_id)

    response = run_api_loop(
        openai_client=client,
        starting_agent=session["agent"],
        user_input=user_message,
        messages=session["messages"],
        stream=stream
    )

    # 更新会话
    session["messages"] = response["messages"]
    session["agent"] = response["agent"]

    return response