from fastapi import FastAPI, BackgroundTasks, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from fastapi import Request
import uvicorn
import uuid
import json
import time
import os
import sys

sys.path.append(os.path.dirname(__file__))
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))
from src.chat import process_message, sessions, update_user_agent, get_current_agent_config, clear_session, get_session_messages
from utils import logger


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



def get_current_timestamp():
    return time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())


# 修改现有的聊天API端点
@app.post("/api/chat")
def chat(request: ChatRequest, req: Request):
    """处理聊天请求"""
    time_start = time.time()
    current_timestamp = get_current_timestamp()
    user_id = req.headers.get("X-Forwarded-For", req.client.host)
    session_id = request.session_id if request.session_id else "default"

    try:

        combined_id = f"{user_id}_{session_id}"

        # 调用聊天处理函数
        response = process_message(
            session_id=session_id,
            user_message=request.message,
            stream=request.stream if request.stream is not None and hasattr(request, "stream") else True,
            user_id=user_id  # 传递用户标识
        )

        # 检查是否有错误字段
        if response is not None and "error" in response:
            return {
                "code": 500,
                "data": {
                    "error": response["error"],
                    "message": "抱歉,服务暂时响应超时,请稍后再试...",
                    "session_id": session_id,
                    "timestamp": current_timestamp,
                    "user": user_id
                }
            }


        # 返回正常响应
        time_end = time.time()
        logger.info(f"请求处理耗时: {time_end - time_start:.2f}秒")
        try:
            assistant_message = next(
                (item['content'] for item in reversed(response.get('response', [])) if item.get('role') == 'assistant'),
                ""
            )
        except Exception as e:
            assistant_message = "[系统错误：未能正确解析助手回复内容]"

        return {
            "code": 200,
            "data": {
                "response": assistant_message,
                "session_id": session_id
            }
        }

    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        logger.info(f"处理聊天请求时出错: {str(e)}\n{error_detail}")

        # 提供用户友好的错误信息
        if "timeout" in str(e).lower():
            return {
                "code": 504,  # Gateway Timeout
                "data": {
                    "error": str(e),
                    "message": "抱歉，服务暂时响应超时，请稍后再试...",
                    "session_id": session_id,
                    "timestamp": current_timestamp,
                    "user": user_id
                }
            }
        else:
            return {
                "code": 500,  # Internal Server Error
                "data": {
                    "error": str(e),
                    "message": "处理请求时出错",
                    "session_id": session_id,
                    "timestamp": current_timestamp,
                    "user": user_id
                }
            }

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
    current_timestamp = get_current_timestamp()
    user_id = req.headers.get("X-Forwarded-For", "BalteMayer")
    combined_id = f"{user_id}_{session_id}"

    try:
        # 导入会话管理器
        from src.chat import memory_manager, sessions

        # 删除会话及其文件
        success = memory_manager.delete_session(combined_id)

        # 如果在会话状态字典中也存在该会话，删除它
        if combined_id in sessions:
            del sessions[combined_id]

        if success:
            return {
                "code": 200,
                "data": {
                    "status": "success",
                    "message": "会话已成功删除",
                    "session_id": session_id,
                    "timestamp": current_timestamp,
                    "user": user_id
                }
            }
        else:
            return {
                "code": 404,
                "data": {
                    "status": "not_found",
                    "message": "未找到指定会话",
                    "session_id": session_id,
                    "timestamp": current_timestamp,
                    "user": user_id
                }
            }
    except Exception as e:
        return {
            "code": 500,
            "data": {
                "error": str(e),
                "message": "删除会话失败",
                "session_id": session_id,
                "timestamp": current_timestamp,
                "user": user_id
            }
        }


# 健康检查端点
@app.get("/health")
def health_check(req: Request):

    return {
        "code": 200,
        "data": {
            "status": "healthy",
        }
    }


@app.get("/api/sessions")
def list_sessions(req: Request):
    """获取指定会话的完整记忆"""
    current_timestamp = get_current_timestamp()
    user_id = req.headers.get("user_id", "BalteMayer")
    session_id = req.headers.get("session_id")

    if not session_id:
        return {
            "code": 400,
            "data": {
                "error": "请求头中必须包含 session_id",
                "timestamp": current_timestamp,
                "user": user_id
            }
        }

    # 构造完整的会话ID (user_id_session_id)
    combined_id = f"{user_id}_{session_id}"

    # 导入会话管理器
    from src.chat import memory_manager

    # 获取会话数据
    try:
        # 获取完整的会话消息
        session_data = memory_manager.get_messages(combined_id)

        # 获取会话元数据
        sessions_info = memory_manager.list_available_sessions()
        session_info = next((s for s in sessions_info if s['session_id'] == combined_id), None)

        return {
            "code": 200,
            "data": {
                "messages": session_data,
            }
        }
    except Exception as e:
        return {
            "code": 500,
            "data": {
                "error": f"获取会话数据失败: {str(e)}",
                "timestamp": current_timestamp,
                "user": user_id
            }
        }


@app.get("/api/sessions/list")
def list_all_sessions(req: Request):
    """API端点：获取所有会话列表，每个会话包含title和session_id"""
    current_timestamp = get_current_timestamp()
    user_id = req.headers.get("X-Forwarded-For", req.client.host)

    try:
        # 导入会话管理器
        from src.chat import memory_manager

        # 获取会话文件列表
        sessions_dir = memory_manager.sessions_dir
        session_list = []

        if os.path.exists(sessions_dir):
            for file_name in os.listdir(sessions_dir):
                if file_name.endswith('.json'):
                    file_path = os.path.join(sessions_dir, file_name)
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            # 获取session_id，去掉文件扩展名
                            session_id = file_name[:-5]

                            # 从文件读取title，如果不存在则使用默认值
                            title = data.get('title', '未命名会话')

                            # 添加到会话列表
                            session_list.append({
                                'title': title,
                                'session_id': session_id.replace("_", ":")
                            })
                    except Exception as e:
                        print(f"读取会话文件失败 {file_path}: {str(e)}")

        return {
            "code": 200,
            "data": {
                "sessions": session_list,
            }
        }
    except Exception as e:
        return {
            "code": 500,
            "data": {
                "error": str(e),
                "message": "获取会话列表失败",
                "timestamp": current_timestamp,
                "user": user_id
            }
        }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001, reload=False)