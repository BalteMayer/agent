from utils.api_loop import run_api_loop
from agent import agent_main, client, init_agent

# 创建一个字典用于存储会话
sessions = {}

# 存储当前全局agent配置
current_agent_config = {
    "model_name": "gpt-4o-mini",
}


def update_global_agent(model_name=None):
    """更新全局智能体"""
    global agent_main, current_agent_config

    # 更新配置
    if model_name:
        current_agent_config["model_name"] = model_name

    # 重新初始化智能体
    agent_main = init_agent(
        model_name=current_agent_config["model_name"],
    )

    return agent_main


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
        stream=stream,
    )

    # 更新会话
    session["messages"] = response["messages"]
    session["agent"] = response["agent"]

    return response


def get_current_agent_config():
    """获取当前智能体配置"""
    return current_agent_config