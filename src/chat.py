from utils.api_loop import run_api_loop
from agent import agent_main, client
from utils.memory import ConversationMemory
import time

memory = {
    'sessions': {}  # 格式: { 'session_id': [message1, message2, ...] }
}


def get_or_create_session(session_id):
    """获取或创建会话"""
    if session_id not in memory['sessions']:
        memory['sessions'][session_id] = []

    return {
        "agent": agent_main,
        "last_active": time.time()
    }


def process_message(session_id, user_message, stream=True):
    """处理用户消息，返回智能体响应"""
    session = get_or_create_session(session_id)

    # 获取当前会话的消息历史
    if session_id not in memory['sessions']:
        memory['sessions'][session_id] = []

    # 添加用户消息到历史
    memory['sessions'][session_id].append({
        "role": "user",
        "content": user_message
    })

    # 打印会话历史长度用于调试
    print(f"会话 {session_id} 历史长度: {len(memory['sessions'][session_id])}")

    # 调用API处理消息
    response = run_api_loop(
        openai_client=client,
        starting_agent=session["agent"],
        user_input=None,  # 不添加用户消息，因为已经在messages中
        messages=memory['sessions'][session_id],  # 使用完整历史
        stream=stream,
    )

    # 从响应中获取最新的助手消息
    if "messages" in response:
        assistant_messages = [msg for msg in response["messages"]
                              if msg.get("role") == "assistant" and msg.get("content")]

        if assistant_messages:
            # 使用最新的助手消息
            latest_assistant_message = assistant_messages[-1]

            # 添加助手回复到历史记录
            memory['sessions'][session_id].append({
                "role": "assistant",
                "content": latest_assistant_message["content"]
            })

    # 返回当前会话的完整消息历史
    # 注意: 不是返回response["messages"]，而是返回我们自己维护的memory
    return {
        "response": memory['sessions'][session_id],
        "session_id": session_id
    }


def get_session_messages(session_id):
    """获取会话历史消息"""
    return memory['sessions'].get(session_id, [])

# 创建一个字典用于存储会话状态
sessions = {}

def clear_session(session_id):
    """清除会话记忆"""
    memory.clear_session(session_id)
    if session_id in sessions:
        sessions[session_id] = {
            "agent": sessions[session_id]["agent"],
            "created_at": time.time(),
            "last_active": time.time()
        }
    return {"status": "success"}


def get_session_messages(session_id):
    """获取会话历史消息"""
    return memory.get_messages(session_id)


current_agent_config = {
    "model_name": "gpt-4o-mini",
}

def get_current_agent_config():
    """获取当前智能体配置"""
    return current_agent_config

def update_global_agent(model_name=None):
    """更新全局智能体配置"""
    global agent_main

    # 创建新的智能体
    if model_name:
        from agent import init_agent

        if not model_name:
            model_name = agent_main.model
            print("model_name: ", model_name)

        # 初始化新智能体
        agent_main = init_agent(model_name=model_name)

    return agent_main