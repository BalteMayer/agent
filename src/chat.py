from src.api_loop import run_api_loop
import sys
import os
sys.path.append(os.path.dirname(__file__))

from src.agent import init_agent, client
from src.memory import ConversationMemory
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import httpx
import time
import json

# 创建全局会话记忆实例
memory_manager = ConversationMemory(nlp_model="zh_core_web_sm", max_history=50)

# 在全局变量部分
user_agents = {}

# 创建一个字典用于存储会话状态
sessions = {}


def get_or_create_session(session_id, user_id):
    """获取或创建会话，使用用户ID和会话ID组合作为唯一标识"""
    # 创建组合ID，确保不同用户的会话互不干扰
    combined_id = f"{user_id}:{session_id}"

    # 为每个用户创建独立的agent实例
    if user_id not in user_agents:
        user_agents[user_id] = init_agent(model_name='gpt-4o')

    if combined_id not in sessions:
        sessions[combined_id] = {
            "agent": user_agents[user_id],  # 使用用户专属的agent
            "last_active": time.time(),
            "user_id": user_id
        }

    return sessions[combined_id]


# 添加重试装饰器，针对网络相关错误进行重试
@retry(
    stop=stop_after_attempt(3),  # 最多重试3次
    wait=wait_exponential(multiplier=1, min=2, max=30),  # 指数退避重试等待
    retry=retry_if_exception_type((httpx.TimeoutException, httpx.ConnectTimeout, httpx.ReadTimeout))  # 只对超时错误重试
)
def call_api_with_retry(client, agent, messages, stream):
    """封装API调用的重试逻辑"""
    return run_api_loop(
        openai_client=client,
        starting_agent=agent,
        user_input=None,
        messages=messages,
        stream=stream,
    )


def process_message(session_id, user_message, stream=True, user_id="anonymous"):
    """处理用户消息，返回智能体响应"""
    # 获取或创建会话，使用用户ID和会话ID组合
    combined_id = f"{user_id}:{session_id}"

    session = get_or_create_session(session_id, user_id)

    # 添加用户消息到历史
    memory_manager.add_message(combined_id, "user", user_message)
    # 获取完整的知识图谱
    knowledge_graph = memory_manager.knowledge_graph[combined_id]
    kg_message = {
        "role": "system",  # 使用system角色
        "content": f"知识图谱: {json.dumps(knowledge_graph, ensure_ascii=False)}"  # 将知识图谱作为内容
    }

    # 获取当前会话的消息历史
    messages = memory_manager.get_messages(combined_id)

    # # 打印会话历史长度用于调试
    # print(f"会话 {combined_id} 历史长度: {len(messages)}")

    
    if (messages and isinstance(messages[0], dict) and
            messages[0].get("实体") == knowledge_graph["实体"] and
            messages[0].get("关系") == knowledge_graph["关系"] and
            not (messages[0].get("role") == "" and messages[0].get("content") == "")):
        # 如果完全匹配，则覆盖
        messages.insert(0, kg_message)

    else:
        # 如果有任何一项不满足，则插入
        messages[0] = kg_message

    print(messages)




    try:
        # 使用重试机制调用API处理消息
        response = call_api_with_retry(
            client=client,
            agent=session["agent"],
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
            "session_id": session_id,
            "stream_chunks": response.get("stream_chunks", []) if stream else []
        }
    except Exception as e:
        # 捕获所有异常并返回友好错误消息
        print(f"API调用失败: {str(e)}")
        error_message = "抱歉，服务暂时响应超时，请稍后再试..."

        # 添加错误消息到会话历史
        memory_manager.add_message(combined_id, "assistant", error_message)

        # 获取包含错误消息的历史
        updated_messages = memory_manager.get_messages(combined_id)

        return {
            "response": updated_messages,
            "session_id": session_id,
            "error": str(e)
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


# 修改为与默认agent一致
current_agent_config = {
    "model_name": "gpt-4o",  # 与agent.py中的默认值保持一致
}


def get_current_agent_config():
    """获取当前智能体配置"""
    # 确保配置反映实际的agent_main的模型
    global current_agent_config, agent_main
    current_agent_config["model_name"] = agent_main.model
    return current_agent_config


def update_user_agent(user_id, model_name=None):
    """更新特定用户的智能体配置"""
    global user_agents

    if model_name:
        user_agents[user_id] = init_agent(model_name=model_name)
        print(f"用户 {user_id} 的智能体已更新: 模型={model_name}")

    return user_agents[user_id]