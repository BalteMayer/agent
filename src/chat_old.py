from utils.api_loop import run_api_loop
from agent import agent_main, client, init_agent
from utils.knowledge_graph import KnowledgeGraph
import os


# 创建一个字典用于存储会话
sessions = {}

# 存储当前全局agent配置
current_agent_config = {
    "model_name": "gpt-4o-mini",
}




# 创建知识图谱实例
kg = KnowledgeGraph(nlp_model="zh_core_web_sm")  # 使用中文模型

# 如果存在保存的知识图谱，加载它
kg_filepath = "knowledge_graph.json"
if os.path.exists(kg_filepath):
    kg.load(kg_filepath)

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

    # 处理用户消息，更新知识图谱
    kg.process_message(session_id, "user", user_message)

    # 获取基于知识图谱的增强上下文
    context = kg.get_session_context(session_id, query=user_message)
    print(context)

    # 使用上下文作为消息历史
    session["messages"] = context

    response = run_api_loop(
        openai_client=client,
        starting_agent=session["agent"],
        user_input=None,  # 不传递user_input，因为它已经在context中
        messages=session["messages"],
        stream=stream,
    )

    # 更新会话
    session["messages"] = response["messages"]
    session["agent"] = response["agent"]

    # 记录智能体的响应到知识图谱
    assistant_message = next((msg for msg in response["response_content"] if msg.get("role") == "assistant"), None)
    if assistant_message:
        kg.process_message(session_id, "assistant", assistant_message["content"])

    # 定期保存知识图谱
    kg.save(kg_filepath)

    return response


def clear_session(session_id):
    """清除指定会话的消息历史"""
    if session_id in sessions:
        sessions[session_id] = {
            "messages": [],
            "agent": sessions[session_id]["agent"]
        }
        return True
    return False


def get_session_messages(session_id):
    """获取指定会话的消息历史"""
    if session_id in sessions:
        return sessions[session_id]["messages"]
    return []


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


def get_knowledge_graph_stats():
    """获取知识图谱统计信息"""
    stats = {
        "total_nodes": len(kg.graph.nodes()),
        "total_edges": len(kg.graph.edges()),
        "entity_count": sum(1 for _, data in kg.graph.nodes(data=True) if data.get("type") == "entity"),
        "relation_count": sum(1 for _, data in kg.graph.nodes(data=True) if data.get("type") == "relation"),
        "message_count": sum(1 for _, data in kg.graph.nodes(data=True) if data.get("type") == "message"),
        "session_count": len(kg.session_memories)
    }
    return stats

def get_current_agent_config():
    """获取当前智能体配置"""
    return current_agent_config