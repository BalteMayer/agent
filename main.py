import uvicorn
from fastapi import FastAPI, BackgroundTasks, WebSocket, WebSocketDisconnect, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import uuid
import json

# 导入chat模块
from src.chat import process_message, sessions, update_user_agent, get_current_agent_config, clear_session, get_session_messages

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


# 在现有引入后添加
from fastapi import Request


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

        print(response)

        # 返回响应
        return {
            "response": next(item['content'] for item in reversed(response['response']) if item['role'] == 'assistant'),
            "session_id": session_id
        }
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        print(f"处理聊天请求时出错: {str(e)}\n{error_detail}")
        raise HTTPException(status_code=500, detail=f"处理请求时出错: {str(e)}")


# 修改清除会话API端点
@app.post("/api/sessions/{session_id}/clear")
def api_clear_session(session_id: str, req: Request):
    """API端点：清除会话"""
    user_id = req.headers.get("X-Forwarded-For", req.client.host)
    return clear_session(session_id, user_id)


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


# 类似地，修改 WebSocket 路由
@app.websocket("/api/chat/stream")
async def chat_stream(websocket: WebSocket):
    await websocket.accept()

    try:
        while True:
            # 等待接收消息
            data = await websocket.receive_text()
            request_data = json.loads(data)

            # 提取请求参数
            session_id = request_data.get("session_id") or str(uuid.uuid4())
            message = request_data.get("message", "")

            # 获取用户标识，使用 WebSocket 连接的客户端信息
            user_id = websocket.client.host

            if not message:
                await websocket.send_json({"error": "消息不能为空"})
                continue

            # 处理消息(流式)，传递用户标识
            response = process_message(
                session_id=session_id,
                user_message=message,
                stream=True,
                user_id=user_id
            )

            # 发送流式响应
            for chunk in response.get("stream_chunks", []):
                await websocket.send_json({
                    "session_id": session_id,
                    "chunk": chunk
                })

            # 发送完成信号
            await websocket.send_json({
                "session_id": session_id,
                "status": "complete"
            })

    except WebSocketDisconnect:
        # 处理WebSocket断开连接
        pass

@app.get("/api/sessions/{session_id}")
def get_session(session_id: str):
    """获取指定会话的历史记录"""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="会话不存在")

    return {
        "session_id": session_id,
        "messages": sessions[session_id]["messages"]
    }


@app.delete("/api/sessions/{session_id}")
def delete_session(session_id: str):
    """删除指定的会话"""
    if session_id in sessions:
        del sessions[session_id]

    return {"status": "success"}


@app.get("/api/config")
def get_config():
    """获取当前智能体配置"""
    return get_current_agent_config()


# 健康检查端点
@app.get("/health")
def health_check():
    return {"status": "healthy"}


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)