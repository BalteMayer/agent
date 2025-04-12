import json
import os
from typing import Dict, Any, Optional


def get_db_config() -> Dict[str, Any]:
    """
    读取config.json文件中的数据库配置信息

    Returns:
        Dict[str, Any]: 包含数据库配置信息的字典
    """
    try:
        # 获取config.json文件的绝对路径（假设它在项目根目录）
        config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data/mongodb_config.json')

        # 读取config.json文件
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)

        return config
    except Exception as e:
        print(f"读取数据库配置信息失败: {e}")
        return {}


def get_db_info() -> Dict[str, Any]:
    """
    获取数据库基本信息并以结构化方式返回

    Returns:
        Dict[str, Any]: 数据库基本信息，包括连接信息和集合结构
    """
    config = get_db_config()
    if not config:
        return {"error": "无法获取数据库配置信息"}

    # 构建数据库基本信息
    db_info = {
        "连接信息": {
            "主机": config.get("host", ""),
            "端口": config.get("port", ""),
            "数据库名": config.get("database", ""),
            "需要认证": bool(config.get("username") and config.get("password"))
        },
        "集合信息": {}
    }

    # 添加集合信息
    collections = config.get("collections", {})
    for collection_name, collection_data in collections.items():
        fields = collection_data.get("fields", {})

        db_info["集合信息"][collection_name] = {
            "字段数量": len(fields),
            "字段列表": [{"名称": field_name, "类型": field_type} for field_name, field_type in fields.items()]
        }

        # 如果有示例数据，添加到信息中
        if "sample_data" in collection_data:
            try:
                # 示例数据通常是JSON字符串，需要解析
                db_info["集合信息"][collection_name]["示例数据"] = collection_data["sample_data"]
            except Exception:
                pass

    return db_info


def describe_db_info() -> str:
    """
    生成数据库信息的自然语言描述

    Returns:
        str: 描述数据库基本信息的文本
    """
    db_info = get_db_info()
    if "error" in db_info:
        return f"抱歉，{db_info['error']}。"

    # 构建自然语言描述
    description = []

    # 添加连接信息描述
    conn_info = db_info["连接信息"]
    description.append(f"数据库位于{conn_info['主机']}:{conn_info['端口']}，")
    description.append(f"数据库名为{conn_info['数据库名']}，")
    description.append(f"{'需要' if conn_info['需要认证'] else '不需要'}认证。\n")

    # 添加集合信息描述
    collections_info = db_info["集合信息"]
    description.append(f"数据库包含{len(collections_info)}个集合：\n")

    for coll_name, coll_info in collections_info.items():
        description.append(f"- {coll_name}：包含{coll_info['字段数量']}个字段")
        fields = [f"{field['名称']}({field['类型']})" for field in coll_info['字段列表']]
        description.append(f"  字段包括：{', '.join(fields)}")
        if "示例数据" in coll_info:
            description.append(f"  示例数据：{coll_info['示例数据']}\n")
        else:
            description.append("\n")

    return "".join(description)