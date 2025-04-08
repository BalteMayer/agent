import spacy
import numpy as np
from typing import List, Dict, Any, Optional
import json
import os
import time
import sys


class ConversationMemory:
    def __init__(self, nlp_model="zh_core_web_sm", max_history=50):
        # 判断是否为打包环境
        if getattr(sys, 'frozen', False):
            # 打包后模型应位于临时目录的根下
            model_path = os.path.join(sys._MEIPASS, nlp_model)
        else:
            model_path = nlp_model

        try:
            self.nlp = spacy.load(model_path)
        except:
            # 如果是打包环境，直接报错（无法在exe中下载）
            if getattr(sys, 'frozen', False):
                raise RuntimeError(f"模型 {nlp_model} 未找到，请在打包时包含模型文件！")
            # 非打包环境则下载
            import subprocess
            subprocess.run(["python", "-m", "spacy", "download", nlp_model])
            self.nlp = spacy.load(model_path)


        # 会话消息记录 - 完整保存所有消息
        self.sessions = {}
        self.max_history = max_history

        # 实体存储 - 每个会话的实体记忆
        self.entity_memory = {}

        # 知识图谱 - 存储实体和关系
        self.knowledge_graph = {}

        # 确保存储目录存在
        self.storage_dir = './data/memory'
        self.sessions_dir = os.path.join(self.storage_dir, 'sessions')
        self.entity_dir = os.path.join(self.storage_dir, 'entities')
        self.kg_dir = os.path.join(self.storage_dir, 'knowledge_graphs')

        os.makedirs(self.sessions_dir, exist_ok=True)
        os.makedirs(self.entity_dir, exist_ok=True)
        os.makedirs(self.kg_dir, exist_ok=True)

        # 关系类型映射 - 实体属性关系
        self.relation_types = {
            ("PERSON", "AGE"): "年龄",
            ("PERSON", "ORG"): "隶属于",
            ("PERSON", "GPE"): "来自",
            ("PERSON", "SPORT"): "爱好",
            ("PERSON", "DATE"): "在日期",
            ("PERSON", "WORK_OF_ART"): "喜欢",
            ("PERSON", "PRODUCT"): "使用",
            ("ORG", "GPE"): "位于",
            ("ORG", "PRODUCT"): "生产",
            # 可以根据需要添加更多关系类型
        }

        # 实体间关系类型
        self.entity_relation_types = {
            ("PERSON", "PERSON"): ["朋友", "同事", "亲戚", "上司", "下属"],
            ("ORG", "ORG"): ["竞争", "合作", "子公司", "母公司", "供应商", "客户"],
            ("PERSON", "WORK_OF_ART"): ["作者", "粉丝"],
            ("PERSON", "PRODUCT"): ["创造者", "用户"],
            # 可以根据需要添加更多关系类型
        }

        # 关系关键词映射
        self.relation_keywords = {
            "朋友": ["朋友", "好友", "伙伴", "友谊"],
            "同事": ["同事", "同僚", "一起工作"],
            "竞争": ["竞争", "对手", "敌人", "敌对"],
            "合作": ["合作", "伙伴", "合伙", "合作伙伴"],
            "上司": ["上司", "老板", "领导", "主管"],
            "下属": ["下属", "手下", "团队成员"],
        }


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

        # 加载实体记忆
        entity_file = self._get_file_path(self.entity_dir, session_id)
        if os.path.exists(entity_file):
            try:
                with open(entity_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.entity_memory[session_id] = data.get('entity_memory', {})
            except Exception as e:
                print(f"加载实体记忆失败 {session_id}: {str(e)}")
                if session_id not in self.entity_memory:
                    self.entity_memory[session_id] = {}
        else:
            # 如果文件不存在，创建空实体记忆
            self.entity_memory[session_id] = {}

        # 加载知识图谱
        kg_file = self._get_file_path(self.kg_dir, session_id)
        if os.path.exists(kg_file):
            try:
                with open(kg_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.knowledge_graph[session_id] = data.get('knowledge_graph', {"实体": {}, "关系": []})
            except Exception as e:
                print(f"加载知识图谱失败 {session_id}: {str(e)}")
                if session_id not in self.knowledge_graph:
                    self.knowledge_graph[session_id] = {"实体": {}, "关系": []}
        else:
            # 如果文件不存在，创建空知识图谱
            self.knowledge_graph[session_id] = {"实体": {}, "关系": []}

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

        # 保存实体记忆
        if session_id in self.entity_memory:
            entity_file = self._get_file_path(self.entity_dir, session_id)
            try:
                with open(entity_file, 'w', encoding='utf-8') as f:
                    json.dump({
                        'session_id': session_id,
                        'entity_memory': self.entity_memory[session_id],
                        'last_updated': time.time()
                    }, f, ensure_ascii=False, indent=2)
            except Exception as e:
                print(f"保存实体记忆失败 {session_id}: {str(e)}")

        # 保存知识图谱
        if session_id in self.knowledge_graph:
            kg_file = self._get_file_path(self.kg_dir, session_id)
            try:
                with open(kg_file, 'w', encoding='utf-8') as f:
                    json.dump({
                        'session_id': session_id,
                        'knowledge_graph': self.knowledge_graph[session_id],
                        'last_updated': time.time()
                    }, f, ensure_ascii=False, indent=2)
            except Exception as e:
                print(f"保存知识图谱失败 {session_id}: {str(e)}")


    def add_message(self, session_id: str, role: str, content: str) -> None:
        """添加消息到会话记忆"""

        # 先加载最新会话数据
        self._load_session_data(session_id)

        if session_id not in self.sessions:
            self.sessions[session_id] = []
            self.entity_memory[session_id] = {}
            self.knowledge_graph[session_id] = {
                "实体": {},  # 实体及其属性
                "关系": []  # 实体间关系
            }

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
            self._update_knowledge_graph(session_id, content)

        # 保存更新后的数据
        self._save_session_data(session_id)

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

            self._save_session_data(session_id)

    def _identify_relation_type(self, text, entity1_type, entity2_type):
        """基于文本内容识别两个实体之间的关系类型"""
        # 检查实体类型对是否有预定义的关系
        if (entity1_type, entity2_type) in self.entity_relation_types:
            possible_relations = self.entity_relation_types[(entity1_type, entity2_type)]

            # 检查文本中是否包含关系关键词
            for relation in possible_relations:
                if relation in self.relation_keywords:
                    for keyword in self.relation_keywords[relation]:
                        if keyword in text:
                            return relation

            # 如果找不到具体关系，返回第一个可能的关系
            return possible_relations[0]

        return None

    def _update_knowledge_graph(self, session_id: str, text: str) -> None:
        """更新知识图谱，提取实体、属性和关系"""
        doc = self.nlp(text)

        # 提取所有实体
        entities = {}
        for ent in doc.ents:
            entity_key = ent.text.lower()
            entities[entity_key] = {
                "text": ent.text,
                "type": ent.label_
            }

            # 确保实体在知识图谱中存在
            if ent.text not in self.knowledge_graph[session_id]["实体"]:
                self.knowledge_graph[session_id]["实体"][ent.text] = {
                    "类型": ent.label_,
                    "属性": {}
                }

        # 处理年龄特殊情况 - 如果文本中有数字后接"岁"
        age_matches = [token for token in doc if token.text.endswith("岁") and any(c.isdigit() for c in token.text)]
        for token in age_matches:
            if token.text.lower() not in entities:
                entities[token.text.lower()] = {"text": token.text, "type": "AGE"}
                if token.text not in self.knowledge_graph[session_id]["实体"]:
                    self.knowledge_graph[session_id]["实体"][token.text] = {
                        "类型": "AGE",
                        "属性": {}
                    }

        # 处理属性关系 - 主要是PERSON和其属性
        person_entities = [e for e, data in entities.items() if data["type"] == "PERSON"]
        for person in person_entities:
            person_text = entities[person]["text"]

            for entity, data in entities.items():
                if person != entity:  # 排除自身
                    relation_key = ("PERSON", data["type"])
                    if relation_key in self.relation_types:
                        relation_type = self.relation_types[relation_key]
                        target_text = data["text"]

                        # 将关系作为人物实体的属性
                        if person_text in self.knowledge_graph[session_id]["实体"]:
                            self.knowledge_graph[session_id]["实体"][person_text]["属性"][relation_type] = target_text

        # 处理实体间关系 - 寻找同类实体间的关系
        # 例如 PERSON-PERSON, ORG-ORG
        entity_pairs = []
        for i, (entity1, data1) in enumerate(entities.items()):
            for j, (entity2, data2) in enumerate(entities.items()):
                if i != j:  # 排除自身
                    type_pair = (data1["type"], data2["type"])
                    if type_pair in self.entity_relation_types:
                        entity_pairs.append((data1["text"], data2["text"], type_pair))

        # 对每对实体尝试识别关系
        for entity1, entity2, type_pair in entity_pairs:
            relation_type = self._identify_relation_type(text, type_pair[0], type_pair[1])
            if relation_type:
                # 创建关系三元组
                relation = [entity1, relation_type, entity2]

                # 检查是否已存在相同关系
                if relation not in self.knowledge_graph[session_id]["关系"]:
                    self.knowledge_graph[session_id]["关系"].append(relation)

        self._save_session_data(session_id)

    def get_messages(self, session_id: str, include_entities=True) -> List[Dict[str, str]]:
        """获取会话消息历史，包括实体记忆增强和知识图谱"""

        """获取会话消息历史，包括实体记忆增强和知识图谱"""
        # 先尝试从文件加载最新数据
        self._load_session_data(session_id)

        if session_id not in self.sessions:
            return []

        # 首先创建知识图谱的系统消息
        messages = []

        # 添加知识图谱信息
        if session_id in self.knowledge_graph:
            # 过滤出重要实体（多次提及的实体）
            important_entities = {}
            for entity_name, entity_data in self.knowledge_graph[session_id]["实体"].items():
                entity_key = entity_name.lower()
                if (entity_key in self.entity_memory[session_id] and
                        self.entity_memory[session_id][entity_key]["mentions"] > 1):
                    # 只保留有属性的实体
                    if entity_data["属性"]:
                        important_entities[entity_name] = entity_data

            # 过滤出重要关系（涉及重要实体的关系）
            important_relations = []
            important_entity_names = set(important_entities.keys())
            for relation in self.knowledge_graph[session_id]["关系"]:
                if relation[0] in important_entity_names or relation[2] in important_entity_names:
                    important_relations.append(relation)

            # 只有当有重要实体或关系时才添加知识图谱
            if important_entities or important_relations:
                kg_obj = {
                    "实体": important_entities,
                    "关系": important_relations
                }
                kg_str = json.dumps(kg_obj, ensure_ascii=False)
                messages.append({
                    "role": "system",
                    "content": f"知识图谱: {kg_str}"
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
        # 先加载最新会话数据，确保文件存在
        self._load_session_data(session_id)

        # 清空内存中的数据
        if session_id in self.sessions:
            self.sessions[session_id] = []
            self.entity_memory[session_id] = {}
            self.knowledge_graph[session_id] = {"实体": {}, "关系": []}

            # 保存空数据
            self._save_session_data(session_id)
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

    def delete_session(self, session_id: str) -> bool:
        """删除会话及其文件"""
        # 删除文件
        session_file = self._get_file_path(self.sessions_dir, session_id)
        entity_file = self._get_file_path(self.entity_dir, session_id)
        kg_file = self._get_file_path(self.kg_dir, session_id)

        files = [session_file, entity_file, kg_file]
        deleted = False

        for file_path in files:
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    deleted = True
                except Exception as e:
                    print(f"删除文件失败 {file_path}: {str(e)}")

        # 从内存中删除
        if session_id in self.sessions:
            del self.sessions[session_id]

        if session_id in self.entity_memory:
            del self.entity_memory[session_id]

        if session_id in self.knowledge_graph:
            del self.knowledge_graph[session_id]

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