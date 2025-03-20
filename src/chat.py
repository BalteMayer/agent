from utils.api_loop import run_api_loop
from agent import agent_main, client
from utils.memory import ConversationMemory
import time

# 创建全局会话记忆实例
memory_manager = ConversationMemory(nlp_model="zh_core_web_sm", max_history=50)

# 创建一个字典用于存储会话状态
sessions = {}


def get_or_create_session(session_id, user_id):
    """获取或创建会话，使用用户ID和会话ID组合作为唯一标识"""
    # 创建组合ID，确保不同用户的会话互不干扰
    combined_id = f"{user_id}:{session_id}"

    if combined_id not in sessions:
        sessions[combined_id] = {
            "agent": agent_main,
            "last_active": time.time(),
            "user_id": user_id
        }

    return sessions[combined_id]


def process_message(session_id, user_message, stream=True, user_id="anonymous"):
    """处理用户消息，返回智能体响应"""
    # 获取或创建会话，使用用户ID和会话ID组合
    session = get_or_create_session(session_id, user_id)
    combined_id = f"{user_id}:{session_id}"

    # 添加用户消息到历史
    memory_manager.add_message(combined_id, "user", user_message)

    # 获取当前会话的消息历史
    messages = memory_manager.get_messages(combined_id)

    # 打印会话历史长度用于调试
    print(f"会话 {combined_id} 历史长度: {len(messages)}")

    # 调用API处理消息
    response = run_api_loop(
        openai_client=client,
        starting_agent=session["agent"],
        user_input=None,  # 不添加用户消息，因为已经在messages中
        messages=messages,  # 使用完整历史
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
            memory_manager.add_message(combined_id, "assistant", latest_assistant_message["content"])

    # 获取更新后的消息列表
    updated_messages = memory_manager.get_messages(combined_id)

    # 返回当前会话的完整消息历史
    return {
        "response": updated_messages,
        "session_id": session_id
    }


def clear_session(session_id, user_id="anonymous"):
    """清除会话记忆"""
    combined_id = f"{user_id}:{session_id}"
    memory_manager.clear_session(combined_id)

    if combined_id in sessions:
        sessions[combined_id] = {
            "agent": sessions[combined_id]["agent"],
            "created_at": time.time(),
            "last_active": time.time(),
            "user_id": user_id
        }
    return {"status": "success"}


def get_session_messages(session_id, user_id="anonymous"):
    """获取会话历史消息"""
    combined_id = f"{user_id}:{session_id}"
    return memory_manager.get_messages(combined_id)


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