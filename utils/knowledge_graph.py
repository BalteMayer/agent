import networkx as nx
import spacy
import json
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple, Set


class KnowledgeGraph:
    """基于知识图谱的智能体记忆系统"""

    def __init__(self, nlp_model="en_core_web_sm"):
        """初始化知识图谱"""
        # 加载NLP模型用于实体识别
        try:
            self.nlp = spacy.load(nlp_model)
        except:
            # 如果模型不存在，下载并加载
            import subprocess
            subprocess.run(["python", "-m", "spacy", "download", nlp_model])
            self.nlp = spacy.load(nlp_model)

        # 初始化图谱
        self.graph = nx.DiGraph()

        # 会话记忆映射
        self.session_memories = {}

    def process_message(self, session_id: str, role: str, content: str) -> None:
        """处理消息并提取知识到图谱中"""
        # 确保会话存在
        if session_id not in self.session_memories:
            self.session_memories[session_id] = []

        # 记录原始消息
        message_id = str(uuid.uuid4())
        timestamp = datetime.now().isoformat()

        # 向会话记忆中添加消息
        self.session_memories[session_id].append({
            "id": message_id,
            "role": role,
            "content": content,
            "timestamp": timestamp
        })

        # 只处理用户消息中的知识
        if role == "user":
            # 使用spaCy进行命名实体识别
            doc = self.nlp(content)

            # 提取实体并添加到图谱
            entities = {}
            for ent in doc.ents:
                entity_id = f"{ent.text.lower()}_{ent.label_}"
                if entity_id not in entities:
                    # 添加实体节点
                    self.graph.add_node(entity_id,
                                        type="entity",
                                        text=ent.text,
                                        label=ent.label_,
                                        first_seen=timestamp,
                                        sessions={session_id},
                                        mentions=[{
                                            "message_id": message_id,
                                            "session_id": session_id,
                                            "timestamp": timestamp
                                        }]
                                        )
                    entities[entity_id] = entity_id
                else:
                    # 更新节点属性
                    self.graph.nodes[entity_id]["sessions"].add(session_id)
                    self.graph.nodes[entity_id]["mentions"].append({
                        "message_id": message_id,
                        "session_id": session_id,
                        "timestamp": timestamp
                    })

            # 添加消息节点
            self.graph.add_node(message_id,
                                type="message",
                                role=role,
                                content=content,
                                session_id=session_id,
                                timestamp=timestamp,
                                entities=list(entities.values())
                                )

            # 建立消息与实体的连接
            for entity_id in entities.values():
                self.graph.add_edge(message_id, entity_id,
                                    type="contains",
                                    timestamp=timestamp
                                    )
                self.graph.add_edge(entity_id, message_id,
                                    type="mentioned_in",
                                    timestamp=timestamp
                                    )

            # 尝试提取关系（简化版）
            self._extract_relationships(doc, message_id, entities, timestamp, session_id)

    def _extract_relationships(self, doc, message_id: str, entities: Dict, timestamp: str, session_id: str) -> None:
        """提取实体间的关系（简化实现）"""
        # 基于依存句法分析建立简单关系
        for token in doc:
            if token.dep_ in ["nsubj", "dobj", "pobj"] and token.head.pos_ == "VERB":
                # 查找主语和宾语
                subject = None
                object = None
                verb = token.head.text

                # 检查是否有主语或宾语是已识别的实体
                for ent in doc.ents:
                    if token in ent:
                        if token.dep_ == "nsubj":
                            subject_id = f"{ent.text.lower()}_{ent.label_}"
                            if subject_id in entities:
                                subject = subject_id
                        elif token.dep_ in ["dobj", "pobj"]:
                            object_id = f"{ent.text.lower()}_{ent.label_}"
                            if object_id in entities:
                                object = object_id

                # 如果找到了主语和宾语，建立关系
                if subject and object:
                    relation_id = f"{subject}_{verb}_{object}"

                    # 添加关系节点
                    self.graph.add_node(relation_id,
                                        type="relation",
                                        verb=verb,
                                        first_seen=timestamp,
                                        sessions={session_id},
                                        mentions=[{
                                            "message_id": message_id,
                                            "session_id": session_id,
                                            "timestamp": timestamp
                                        }]
                                        )

                    # 建立关系连接
                    self.graph.add_edge(subject, relation_id,
                                        type="subject_of",
                                        timestamp=timestamp
                                        )
                    self.graph.add_edge(relation_id, object,
                                        type="object_is",
                                        timestamp=timestamp
                                        )
                    self.graph.add_edge(message_id, relation_id,
                                        type="contains_relation",
                                        timestamp=timestamp
                                        )

    def get_session_context(self, session_id: str, query: Optional[str] = None, limit: int = 10) -> List[Dict]:
        """获取会话上下文，包括相关实体信息"""
        if session_id not in self.session_memories:
            return []

        # 获取原始消息历史
        messages = self.session_memories[session_id][-limit:]

        # 如果有查询，尝试查找相关信息来增强上下文
        if query:
            doc = self.nlp(query)
            relevant_entities = []

            # 提取查询中的实体
            for ent in doc.ents:
                entity_id = f"{ent.text.lower()}_{ent.label_}"
                if self.graph.has_node(entity_id):
                    relevant_entities.append(entity_id)

            # 查找相关的消息
            relevant_messages = set()
            for entity_id in relevant_entities:
                # 获取有关此实体的所有消息
                for neighbor in self.graph.neighbors(entity_id):
                    if self.graph.nodes[neighbor]["type"] == "message" and \
                            self.graph.nodes[neighbor]["session_id"] == session_id:
                        relevant_messages.add(neighbor)

            # 将相关消息按时间排序
            sorted_messages = sorted(
                [self.graph.nodes[mid] for mid in relevant_messages],
                key=lambda x: x["timestamp"]
            )

            # 构建增强上下文
            context = []
            if relevant_entities:
                entity_info = []
                for entity_id in relevant_entities:
                    entity = self.graph.nodes[entity_id]
                    # 获取与该实体相关的信息
                    related_info = self._get_entity_related_info(entity_id, session_id)
                    entity_info.append({
                        "text": entity["text"],
                        "type": entity["label"],
                        "related_info": related_info
                    })

                if entity_info:
                    context.append({
                        "role": "system",
                        "content": f"以下是与当前查询相关的信息：\n{json.dumps(entity_info, ensure_ascii=False, indent=2)}"
                    })

            # 如果有足够的相关消息，用它们来构建上下文
            if len(sorted_messages) > 2:
                for msg in sorted_messages[-5:]:  # 取最近的5条
                    context.append({
                        "role": msg["role"],
                        "content": msg["content"]
                    })
                return context

        # 如果没有查询或没找到相关消息，返回原始消息历史
        return [{"role": msg["role"], "content": msg["content"]} for msg in messages]

    def _get_entity_related_info(self, entity_id: str, session_id: str) -> List[Dict]:
        """获取与实体相关的信息"""
        related_info = []

        # 查找与该实体相关的关系
        for neighbor in self.graph.neighbors(entity_id):
            node = self.graph.nodes[neighbor]
            if node["type"] == "relation" and session_id in node["sessions"]:
                # 找到关系的主语和宾语
                subject = None
                object = None

                for s, t, data in self.graph.edges(neighbor, data=True):
                    if data["type"] == "object_is":
                        object_id = t
                        object = self.graph.nodes[object_id]["text"]

                for s, t, data in self.graph.in_edges(neighbor, data=True):
                    if data["type"] == "subject_of":
                        subject_id = s
                        subject = self.graph.nodes[subject_id]["text"]

                if subject and object:
                    related_info.append({
                        "relation": node["verb"],
                        "subject": subject,
                        "object": object
                    })

        return related_info

    def save(self, filepath: str) -> None:
        """保存知识图谱到文件"""
        # 将图谱转换为可序列化的数据
        # 注意：需要处理set等不可直接序列化的数据类型
        graph_data = {
            "nodes": {},
            "edges": []
        }

        # 处理节点
        for node_id, attrs in self.graph.nodes(data=True):
            node_data = {}
            for key, value in attrs.items():
                if isinstance(value, set):
                    node_data[key] = list(value)
                else:
                    node_data[key] = value
            graph_data["nodes"][node_id] = node_data

        # 处理边
        for s, t, attrs in self.graph.edges(data=True):
            edge_data = {"source": s, "target": t}
            for key, value in attrs.items():
                edge_data[key] = value
            graph_data["edges"].append(edge_data)

        # 保存会话记忆和图谱数据
        data = {
            "graph": graph_data,
            "session_memories": self.session_memories
        }

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def load(self, filepath: str) -> None:
        """从文件加载知识图谱"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # 重建图谱
            self.graph = nx.DiGraph()

            # 添加节点
            for node_id, attrs in data["graph"]["nodes"].items():
                node_attrs = {}
                for key, value in attrs.items():
                    if key == "sessions":
                        node_attrs[key] = set(value)
                    else:
                        node_attrs[key] = value
                self.graph.add_node(node_id, **node_attrs)

            # 添加边
            for edge in data["graph"]["edges"]:
                s = edge.pop("source")
                t = edge.pop("target")
                self.graph.add_edge(s, t, **edge)

            # 恢复会话记忆
            self.session_memories = data["session_memories"]

            return True
        except Exception as e:
            print(f"加载知识图谱失败: {e}")
            return False