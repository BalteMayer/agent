from typing import List, Dict, Any, Optional
import json
import os
import time
import sys


class ConversationMemory:
    def __init__(self, max_history=50):
        # 会话消息记录 - 完整保存所有消息
        self.sessions = {}
        self.max_history = max_history

        # 确保存储目录存在
        self.storage_dir = './data/memory'
        self.sessions_dir = os.path.join(self.storage_dir, 'sessions')

        os.makedirs(self.sessions_dir, exist_ok=True)


    def _get_file_path(self, directory, session_id):
        """获取文件路径，将会话ID转换为安全的文件名"""
        safe_id = session_id.replace('/', '_').replace(':', '_')
        return os.path.join(directory, f"{safe_id}.json")

    def _load_session_data(self, session_id):
        """从文件加载会话数据"""
        # 加载会话消息
        session_file = self._get_file_path(self.sessions_dir, session_id)
        if os.path.exists(session_file):
            try:
                with open(session_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.sessions[session_id] = data.get('messages', [])
            except Exception as e:
                print(f"加载会话消息失败 {session_id}: {str(e)}")
                if session_id not in self.sessions:
                    self.sessions[session_id] = []
        else:
            # 如果文件不存在，创建空会话
            self.sessions[session_id] = []

    def _save_session_data(self, session_id):
        """保存会话数据到文件"""
        # 保存会话消息
        if session_id in self.sessions:
            session_file = self._get_file_path(self.sessions_dir, session_id)
            try:
                with open(session_file, 'w', encoding='utf-8') as f:
                    json.dump({
                        'session_id': session_id,
                        'messages': self.sessions[session_id],
                        'last_updated': time.time()
                    }, f, ensure_ascii=False, indent=2)
            except Exception as e:
                print(f"保存会话消息失败 {session_id}: {str(e)}")


    def add_message(self, session_id: str, role: str, content: str) -> None:
        """添加消息到会话记忆"""

        # 先加载最新会话数据
        self._load_session_data(session_id)

        if session_id not in self.sessions:
            self.sessions[session_id] = []

        # 添加消息到历史
        self.sessions[session_id].append({
            "role": role,
            "content": content
        })

        # 保持历史长度在限制内
        if len(self.sessions[session_id]) > self.max_history:
            self.sessions[session_id] = self.sessions[session_id][-self.max_history:]

        # 保存更新后的数据
        self._save_session_data(session_id)

    def get_messages(self, session_id: str) -> List[Dict[str, str]]:
        """获取会话消息历史"""
        # 先尝试从文件加载最新数据
        self._load_session_data(session_id)

        if session_id not in self.sessions:
            return []

        # 添加历史消息
        messages = self.sessions[session_id].copy()

        # 确保总消息数不超过最大历史限制
        if len(messages) > self.max_history:
            # 保留系统消息和最近的消息
            system_messages = [msg for msg in messages if msg["role"] == "system"]
            recent_messages = messages[-self.max_history + len(system_messages):]

            # 重组消息，确保系统消息在前
            messages = system_messages + [msg for msg in recent_messages if msg["role"] != "system"]

        return messages

    def clear_session(self, session_id: str) -> bool:
        """清除会话记忆"""
        # 先加载最新会话数据，确保文件存在
        self._load_session_data(session_id)

        # 清空内存中的数据
        if session_id in self.sessions:
            self.sessions[session_id] = []

            # 保存空数据
            self._save_session_data(session_id)
            return True
        return False

    def print_session_debug(self, session_id: str) -> None:
        """打印会话调试信息"""
        if session_id not in self.sessions:
            print(f"会话 {session_id} 不存在")
            return

        print(f"会话 {session_id} 包含 {len(self.sessions[session_id])} 条消息")

    def delete_session(self, session_id: str) -> bool:
        """删除会话及其文件"""
        # 删除文件
        session_file = self._get_file_path(self.sessions_dir, session_id)

        deleted = False

        if os.path.exists(session_file):
            try:
                os.remove(session_file)
                deleted = True
            except Exception as e:
                print(f"删除文件失败 {session_file}: {str(e)}")

        # 从内存中删除
        if session_id in self.sessions:
            del self.sessions[session_id]

        return deleted

    def list_available_sessions(self) -> List[Dict[str, Any]]:
        """列出所有可用的会话"""
        sessions = []
        try:
            for file_name in os.listdir(self.sessions_dir):
                if file_name.endswith('.json'):
                    session_id = file_name[:-5].replace('_', ':')  # 还原会话ID

                    # 获取最后修改时间
                    file_path = os.path.join(self.sessions_dir, file_name)
                    last_modified = os.path.getmtime(file_path)

                    # 添加到列表
                    sessions.append({
                        'session_id': session_id,
                        'last_modified': last_modified
                    })

            # 按最后修改时间排序，最新的在前
            sessions.sort(key=lambda x: x['last_modified'], reverse=True)
        except Exception as e:
            print(f"列出会话失败: {str(e)}")

        return sessions