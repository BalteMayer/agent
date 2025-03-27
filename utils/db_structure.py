import json
import os
from pymongo import MongoClient
from typing import Dict, Any, List, Union
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def get_db_struct_and_dtype(time: str = None, chart_type: str = None, database: str = "config.json") -> str:
    """
    通过数据库配置文件获取MongoDB数据库的结构和数据类型信息

    Args:
        time: 时间信息（可选）
        chart_type: 图表类型（可选）
        database: 数据库配置文件路径

    Returns:
        str: JSON字符串形式的数据库结构和类型信息
    """
    try:
        # 检查并读取配置文件
        if not os.path.exists(database):
            logger.error(f"数据库配置文件 {database} 不存在")
            return json.dumps({"error": f"配置文件 {database} 不存在"}, ensure_ascii=False)

        # 读取配置文件
        with open(database, 'r', encoding='utf-8') as f:
            try:
                config = json.load(f)
            except json.JSONDecodeError:
                logger.error(f"配置文件 {database} 格式错误")
                return json.dumps({"error": "配置文件格式错误"}, ensure_ascii=False)

        # 验证配置文件中是否包含必要信息
        required_fields = ["host", "port", "username", "password", "database"]
        for field in required_fields:
            if field not in config:
                logger.error(f"配置文件中缺少必要字段: {field}")
                return json.dumps({"error": f"配置文件中缺少必要字段: {field}"}, ensure_ascii=False)

        # 连接MongoDB
        try:
            if config.get("username") and config.get("password"):
                client = MongoClient(
                    host=config["host"],
                    port=config["port"],
                    username=config["username"],
                    password=config["password"],
                    serverSelectionTimeoutMS=5000  # 5秒超时
                )
            else:
                client = MongoClient(
                    host=config["host"],
                    port=config["port"],
                    serverSelectionTimeoutMS=5000
                )

            # 检查连接是否成功
            client.admin.command('ping')
            logger.info("已成功连接到MongoDB")

            # 获取指定数据库
            db = client[config["database"]]

            # 获取所有集合
            collection_names = db.list_collection_names()

            # 初始化结果结构
            db_structure = {
                "database_name": config["database"],
                "collections": {}
            }

            # 对每个集合获取结构和数据类型
            for collection_name in collection_names:
                collection = db[collection_name]

                # 获取示例文档来推断字段和类型
                sample_docs = list(collection.find().limit(10))

                if not sample_docs:
                    # 如果集合为空，添加空结构
                    db_structure["collections"][collection_name] = {
                        "fields": {},
                        "count": 0
                    }
                    continue

                # 合并所有文档的字段
                fields = {}
                for doc in sample_docs:
                    for field, value in doc.items():
                        if field not in fields:
                            fields[field] = []

                        # 获取数据类型，确保处理MongoDB特殊类型
                        if value is None:
                            type_name = "null"
                        else:
                            type_name = type(value).__name__

                            # 处理日期和时间类型（MongoDB中常见）
                            if hasattr(value, 'isoformat'):
                                type_name = "datetime"
                            # 处理ObjectId
                            elif hasattr(value, 'binary'):
                                type_name = "ObjectId"

                        if type_name not in fields[field]:
                            fields[field].append(type_name)

                # 对每个字段确定类型
                field_types = {}
                for field, types in fields.items():
                    if len(types) == 1:
                        field_types[field] = types[0]
                    else:
                        field_types[field] = types

                # 获取集合中的文档数量
                doc_count = collection.count_documents({})

                # 添加到结构中
                db_structure["collections"][collection_name] = {
                    "fields": field_types,
                    "count": doc_count
                }

                # 添加一些示例值（为了更好理解数据）
                sample_values = {}
                for field in field_types.keys():
                    values = []
                    for doc in sample_docs[:3]:  # 只取前3个文档的样本值
                        if field in doc and doc[field] is not None:
                            # 处理特殊类型的值
                            if hasattr(doc[field], 'isoformat'):
                                values.append(doc[field].isoformat())
                            elif hasattr(doc[field], 'binary'):
                                values.append(str(doc[field]))
                            else:
                                values.append(doc[field])
                    if values:
                        sample_values[field] = values

                db_structure["collections"][collection_name]["sample_values"] = sample_values

            client.close()
            logger.info("数据库结构获取完成")

            # 转换为JSON字符串并返回
            return json.dumps(db_structure, ensure_ascii=False, indent=2)

        except Exception as e:
            logger.error(f"连接MongoDB失败: {str(e)}")
            return json.dumps({"error": f"连接数据库失败: {str(e)}"}, ensure_ascii=False)

    except Exception as e:
        logger.error(f"获取数据库结构时发生错误: {str(e)}")
        return json.dumps({"error": f"获取数据库结构时发生错误: {str(e)}"}, ensure_ascii=False)


if __name__ == "__main__":
    # 测试函数
    result = get_db_struct_and_dtype(database="config.json")
    print(result)