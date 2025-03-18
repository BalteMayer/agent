import uvicorn
from fastapi import FastAPI, BackgroundTasks, WebSocket, WebSocketDisconnect, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import uuid
import json

# 导入chat模块
from src.chat import process_message, sessions, update_global_agent, get_current_agent_config

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






# API路由
@app.post("/api/chat", response_model=MessageResponse)
async def chat(request: MessageRequest):
    """与智能体进行对话"""
    # 如果没有提供session_id，则创建一个新的
    session_id = request.session_id or str(uuid.uuid4())

    # 处理消息
    response = process_message(
        session_id=session_id,
        user_message=request.message,
        stream=False,  # 非流式API调用
    )

    return {
        "session_id": session_id,
        "responses": response["response_content"]
    }

class AgentConfigResponse(BaseModel):
    model_name: str
@app.post("/api/init", response_model=AgentConfigResponse)
async def initialize_agent(config: AgentConfigRequest):
    """初始化智能体配置"""
    # 更新全局智能体
    update_global_agent(
        model_name=config.model_name,
    )

    # 返回当前配置
    current_config = get_current_agent_config()
    return current_config


# WebSocket路由用于流式响应
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

            if not message:
                await websocket.send_json({"error": "消息不能为空"})
                continue

            # 处理消息(流式)
            response = process_message(
                session_id=session_id,
                user_message=message,
                stream=True
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
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)