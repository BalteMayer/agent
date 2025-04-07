from fastapi import FastAPI, BackgroundTasks, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from src.chat import process_message, sessions, update_user_agent, get_current_agent_config, clear_session, get_session_messages
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from fastapi import Request
import uvicorn
import uuid
import json
import time



#TODO:deepseek调用函数，绘图框架(把数据库信息存放在一个文本文件里，可以更改)，本地部署，嵌入式，其他功能，instruction改为预设(把预设信息存放在一个文本文件里，可以更改)
app = FastAPI(title="Swarm API", description="通过API与Swarm智能体交互的服务")

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 请求和响应模型
class MessageRequest(BaseModel):
    session_id: Optional[str] = None
    message: str
    stream: bool = True


class MessageResponse(BaseModel):
    session_id: str
    responses: List[Dict[str, Any]]


class AgentConfigRequest(BaseModel):
    model_name: Optional[str] = None


class ChatRequest(BaseModel):
    """聊天请求的数据模型"""
    message: str
    session_id: Optional[str] = None
    stream: Optional[bool] = True


class ChatResponse(BaseModel):
    """聊天响应的数据模型"""
    response: List[Dict[str, Any]]
    session_id: str





# 修改现有的聊天API端点
@app.post("/api/chat")
def chat(request: ChatRequest, req: Request):
    """处理聊天请求"""
    try:
        # 获取用户IP或其他标识，优先使用X-Forwarded-For头信息
        user_id = req.headers.get("X-Forwarded-For", req.client.host)

        # 确保使用固定的会话ID来保持状态
        session_id = request.session_id if request.session_id else "default"

        # 调用聊天处理函数
        response = process_message(
            session_id=session_id,
            user_message=request.message,
            stream=request.stream if hasattr(request, "stream") else True,
            user_id=user_id  # 传递用户标识
        )

        # 检查是否有错误字段
        if "error" in response:
            # 返回错误响应，但仍然提供用户友好的信息
            return {
                "response": "抱歉，服务暂时响应超时，请稍后再试...",
                "session_id": session_id,
                "error": response["error"]
            }

        # 返回正常响应
        return {
            "response": next(
                (item['content'] for item in reversed(response['response']) if item['role'] == 'assistant'), ""),
            "session_id": session_id
        }
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        print(f"处理聊天请求时出错: {str(e)}\n{error_detail}")

        # 提供用户友好的错误信息
        if "timeout" in str(e).lower():
            return {
                "response": "抱歉，服务暂时响应超时，请稍后再试...",
                "session_id": session_id,
                "error": str(e)
            }
        else:
            raise HTTPException(status_code=500, detail=f"处理请求时出错: {str(e)}")


# 修改获取会话消息API端点
@app.get("/api/sessions/{session_id}/messages")
def api_get_session_messages(session_id: str, req: Request):
    """API端点：获取会话消息"""
    user_id = req.headers.get("X-Forwarded-For", req.client.host)
    return {"messages": get_session_messages(session_id, user_id)}

class AgentConfigResponse(BaseModel):
    model_name: str
@app.post("/api/init", response_model=AgentConfigResponse)
async def initialize_agent(config: AgentConfigRequest):
    """初始化智能体配置"""
    # 更新全局智能体
    update_user_agent(
        model_name=config.model_name,
    )

    # 返回当前配置
    current_config = get_current_agent_config()
    return current_config


# 以后再说
# @app.websocket("/api/chat/stream")
# async def chat_stream(websocket: WebSocket):
#     await websocket.accept()
#
#     try:
#         while True:
#             # 等待接收消息
#             data = await websocket.receive_text()
#             request_data = json.loads(data)
#
#             # 提取请求参数
#             session_id = request_data.get("session_id") or str(uuid.uuid4())
#             message = request_data.get("message", "")
#
#             # 获取用户标识，使用 WebSocket 连接的客户端信息
#             user_id = websocket.client.host
#
#             if not message:
#                 await websocket.send_json({"error": "消息不能为空"})
#                 continue
#
#             # 处理消息(流式)，传递用户标识
#             response = process_message(
#                 session_id=session_id,
#                 user_message=message,
#                 stream=True,
#                 user_id=user_id
#             )
#
#             # 发送流式响应
#             for chunk in response.get("stream_chunks", []):
#                 await websocket.send_json({
#                     "session_id": session_id,
#                     "chunk": chunk
#                 })
#
#             # 发送完成信号
#             await websocket.send_json({
#                 "session_id": session_id,
#                 "status": "complete"
#             })
#
#     except WebSocketDisconnect:
#         # 处理WebSocket断开连接
#         pass


@app.delete("/api/sessions/{session_id}")
def api_delete_session(session_id: str, req: Request):
    """API端点：删除指定的会话及其文件"""
    user_id = req.headers.get("X-Forwarded-For", req.client.host)
    combined_id = f"{user_id}:{session_id}"

    # 导入会话管理器
    from src.chat import memory_manager, sessions

    # 删除会话及其文件
    success = memory_manager.delete_session(combined_id)

    # 如果在会话状态字典中也存在该会话，删除它
    if combined_id in sessions:
        del sessions[combined_id]

    return {"status": "success" if success else "not_found"}


# 健康检查端点
@app.get("/health")
def health_check():
    return {"status": "healthy"}


@app.get("/api/sessions")
def list_sessions(req: Request):
    """获取当前用户的所有可用会话列表"""
    user_id = req.headers.get("X-Forwarded-For", req.client.host)

    # 导入会话管理器
    from src.chat import memory_manager

    # 获取所有可用会话
    all_sessions = memory_manager.list_available_sessions()

    # 筛选属于当前用户的会话
    user_sessions = []
    for session in all_sessions:
        if session['session_id'].startswith(f"{user_id}:"):
            # 提取实际的会话ID（去除用户ID前缀）
            actual_session_id = session['session_id'].split(':', 1)[1] if ':' in session['session_id'] else session[
                'session_id']

            # 加载会话数据以获取最后消息
            session_data = memory_manager.get_messages(session['session_id'])

            # 提取最后的用户消息和助手回复
            last_user_message = ""
            last_assistant_message = ""
            for msg in reversed(session_data):
                if msg["role"] == "user" and not last_user_message:
                    last_user_message = msg["content"]
                elif msg["role"] == "assistant" and not last_assistant_message:
                    last_assistant_message = msg["content"]

                if last_user_message and last_assistant_message:
                    break

            user_sessions.append({
                "session_id": actual_session_id,
                "last_updated": session['last_modified'],
                "last_updated_str": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(session['last_modified'])),
                "message_count": len(session_data),
                "last_user_message": last_user_message[:50] + ("..." if len(last_user_message) > 50 else ""),
                "last_assistant_message": last_assistant_message[:50] + (
                    "..." if len(last_assistant_message) > 50 else "")
            })

    return {"sessions": user_sessions}



if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)