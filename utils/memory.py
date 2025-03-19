import spacy
import numpy as np
from typing import List, Dict, Any, Optional


class ConversationMemory:
    """基于内存的会话记忆系统，支持上下文理解与实体识别"""

    def __init__(self, nlp_model="zh_core_web_sm", max_history=50):
        """初始化会话记忆系统"""
        # 加载NLP模型用于实体识别
        try:
            self.nlp = spacy.load(nlp_model)
        except:
            # 如果模型不存在，下载并加载
            import subprocess
            subprocess.run(["python", "-m", "spacy", "download", nlp_model])
            self.nlp = spacy.load(nlp_model)

        # 会话消息记录 - 完整保存所有消息
        self.sessions = {}
        self.max_history = max_history

        # 实体存储 - 每个会话的实体记忆
        self.entity_memory = {}

    def add_message(self, session_id: str, role: str, content: str) -> None:
        """添加消息到会话记忆"""
        if session_id not in self.sessions:
            self.sessions[session_id] = []
            self.entity_memory[session_id] = {}

        # 添加消息到历史
        self.sessions[session_id].append({
            "role": role,
            "content": content
        })

        # 保持历史长度在限制内
        if len(self.sessions[session_id]) > self.max_history:
            self.sessions[session_id] = self.sessions[session_id][-self.max_history:]

        # 如果是用户消息，提取实体并存储
        if role == "user":
            self._extract_entities(session_id, content)

    def _extract_entities(self, session_id: str, text: str) -> None:
        """从文本中提取命名实体"""
        doc = self.nlp(text)

        # 提取命名实体
        for ent in doc.ents:
            # 使用实体文本作为主键，类型作为附加信息，以便合并相同实体
            entity_key = ent.text.lower()

            if entity_key not in self.entity_memory[session_id]:
                self.entity_memory[session_id][entity_key] = {
                    "text": ent.text,
                    "type": ent.label_,
                    "mentions": 1,
                    "contexts": [text]
                }
            else:
                # 更新已有实体信息
                self.entity_memory[session_id][entity_key]["mentions"] += 1
                # 只保存不同的上下文
                if text not in self.entity_memory[session_id][entity_key]["contexts"]:
                    if len(self.entity_memory[session_id][entity_key]["contexts"]) < 5:
                        self.entity_memory[session_id][entity_key]["contexts"].append(text)

    def get_messages(self, session_id: str, include_entities=True) -> List[Dict[str, str]]:
        """获取会话消息历史，包括实体记忆增强"""
        if session_id not in self.sessions:
            return []

        # 首先创建实体记忆的系统消息
        messages = []

        if include_entities and session_id in self.entity_memory and self.entity_memory[session_id]:
            entity_info = "以下是本次对话中提到的重要信息:\n"
            for entity_key, entity in self.entity_memory[session_id].items():
                # 只包括被提到多次或有多个上下文的实体
                if entity["mentions"] > 1 or len(entity["contexts"]) > 1:
                    entity_info += f"- {entity['text']} ({entity['type']}): 在对话中出现了{entity['mentions']}次\n"
                    if entity["contexts"]:
                        for i, context in enumerate(entity["contexts"]):
                            if i < 3:  # 限制上下文数量
                                entity_info += f"  - 上下文: \"{context}\"\n"

            if len(entity_info) > len("以下是本次对话中提到的重要信息:\n"):
                messages.append({
                    "role": "system",
                    "content": entity_info
                })

        # 然后添加历史消息
        messages.extend(self.sessions[session_id])

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
        if session_id in self.sessions:
            self.sessions[session_id] = []
            self.entity_memory[session_id] = {}
            return True
        return False

    def get_entity_info(self, session_id: str, entity_text: str) -> Optional[Dict]:
        """获取特定实体的信息"""
        if session_id not in self.entity_memory:
            return None

        # 尝试直接匹配
        if entity_text.lower() in self.entity_memory[session_id]:
            return self.entity_memory[session_id][entity_text.lower()]

        # 尝试部分匹配
        for key, entity in self.entity_memory[session_id].items():
            if entity_text.lower() in key or key in entity_text.lower():
                return entity

        return None

    def print_session_debug(self, session_id: str) -> None:
        """打印会话调试信息"""
        if session_id not in self.sessions:
            print(f"会话 {session_id} 不存在")
            return

        print(f"会话 {session_id} 包含 {len(self.sessions[session_id])} 条消息")
        print(f"实体记忆: {len(self.entity_memory.get(session_id, {}))} 个实体")
        print("实体列表:")
        for key, entity in self.entity_memory.get(session_id, {}).items():
            print(f"  - {entity['text']} ({entity['type']}): 提到 {entity['mentions']} 次")