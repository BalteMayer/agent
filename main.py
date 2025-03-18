import uvicorn
from fastapi import FastAPI, BackgroundTasks, WebSocket, WebSocketDisconnect, Request, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import uuid
import json
import asyncio

# 导入修改后的模块
from agent import process_message, sessions

app = FastAPI(title="Swarm API", description="通过API与Swarm智能体交互的服务")

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 在生产环境中应该使用具体的域名
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


class StreamResponse(BaseModel):
    session_id: str
    chunk: Dict[str, Any]


# API路由
@app.post("/api/chat", response_model=MessageResponse)
async def chat(request: MessageRequest):
    """
    与智能体进行对话
    """
    # 如果没有提供session_id，则创建一个新的
    session_id = request.session_id or str(uuid.uuid4())

    # 处理消息
    response = process_message(
        session_id=session_id,
        user_message=request.message,
        stream=False  # 非流式API调用
    )

    return {
        "session_id": session_id,
        "responses": response["response_content"]
    }


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
    """
    获取指定会话的历史记录
    """
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="会话不存在")

    return {
        "session_id": session_id,
        "messages": sessions[session_id]["messages"]
    }


@app.delete("/api/sessions/{session_id}")
def delete_session(session_id: str):
    """
    删除指定的会话
    """
    if session_id in sessions:
        del sessions[session_id]

    return {"status": "success"}


# 健康检查端点
@app.get("/health")
def health_check():
    return {"status": "healthy"}


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)