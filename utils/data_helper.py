# 新建文件: utils/data_helper.py

import json
import pymongo
from typing import List, Dict, Any, Optional, Tuple


def connect_to_database(db_info: Dict[str, Any]) -> pymongo.MongoClient:
    """连接到MongoDB数据库"""
    host = db_info.get("host", "localhost")
    port = db_info.get("port", 27017)
    username = db_info.get("username", "")
    password = db_info.get("password", "")
    database_name = db_info.get("database", "")

    connection_string = f"mongodb://"
    if username and password:
        connection_string += f"{username}:{password}@"
    connection_string += f"{host}:{port}/{database_name}"

    client = pymongo.MongoClient(connection_string)
    return client[database_name]


def enrich_data_with_relations(
        primary_data: List[Dict[str, Any]],
        join_config: Dict[str, Any],
        db_info: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """
    通用数据关联函数，用于将主数据集与辅助数据集关联

    参数:
    - primary_data: 主数据列表
    - join_config: 关联配置，格式为:
        {
            "auxiliary_collection": "集合名称", # 辅助数据集合名
            "primary_key": "主数据关联字段",     # 主数据中的关联键
            "auxiliary_key": "辅助数据关联字段", # 辅助数据中的关联键
            "fields_to_include": ["字段1", "字段2"] # 要包含的辅助数据字段列表
        }
    - db_info: 数据库连接信息，如果为None则尝试从config.json读取

    返回:
    - 增强后的数据列表
    """
    if not primary_data or not join_config:
        return primary_data

    # 如果没有提供db_info，尝试从config.json加载
    if db_info is None:
        try:
            with open("config.json", "r", encoding="utf-8") as f:
                db_info = json.load(f)
        except Exception as e:
            print(f"无法加载数据库配置: {str(e)}")
            return primary_data

    # 获取关联配置
    auxiliary_collection = join_config.get("auxiliary_collection")
    primary_key = join_config.get("primary_key")
    auxiliary_key = join_config.get("auxiliary_key")
    fields_to_include = join_config.get("fields_to_include", [])

    if not auxiliary_collection or not primary_key or not auxiliary_key:
        return primary_data

    try:
        # 连接数据库
        db = connect_to_database(db_info)

        # 获取辅助数据集
        auxiliary_data = list(db[auxiliary_collection].find())

        # 创建辅助数据的映射字典
        auxiliary_map = {}
        for item in auxiliary_data:
            if auxiliary_key in item:
                # 以辅助键的值为索引
                key_value = item[auxiliary_key]
                if key_value not in auxiliary_map:
                    auxiliary_map[key_value] = {}

                # 只复制需要的字段
                for field in fields_to_include:
                    if field in item:
                        auxiliary_map[key_value][field] = item[field]

        # 为主数据增加辅助数据中的字段
        enriched_data = []
        for item in primary_data:
            if primary_key in item and item[primary_key] in auxiliary_map:
                # 创建新记录，包含原始数据
                new_item = item.copy()
                # 添加辅助数据的字段
                for field, value in auxiliary_map[item[primary_key]].items():
                    new_item[field] = value
                enriched_data.append(new_item)
            else:
                # 如果找不到匹配的辅助数据，保留原始记录
                enriched_data.append(item)

        return enriched_data

    except Exception as e:
        print(f"关联数据时出错: {str(e)}")
        return primary_data


def group_and_aggregate(
        data: List[Dict[str, Any]],
        group_by: str,
        value_field: str,
        aggregations: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    通用分组和聚合函数

    参数:
    - data: 数据列表
    - group_by: 分组字段
    - value_field: 值字段
    - aggregations: 聚合操作列表，格式为:
        [
            {
                "type": "count", # 聚合类型: count, sum, avg, min, max
                "field": "字段名", # 要聚合的字段
                "condition": {"字段": "值"}, # 可选的筛选条件
                "output": "输出字段名" # 结果字段名
            }
        ]

    返回:
    - 分组聚合后的结果
    """
    if not data or not group_by or not value_field or not aggregations:
        return []

    # 分组数据
    groups = {}
    for item in data:
        if group_by not in item:
            continue

        group_key = item[group_by]
        if group_key not in groups:
            groups[group_key] = []

        groups[group_key].append(item)

    # 对每个组执行聚合操作
    result = []
    for group_key, group_items in groups.items():
        group_result = {group_by: group_key}

        # 执行每种聚合操作
        for agg in aggregations:
            agg_type = agg.get("type", "count")
            agg_field = agg.get("field", value_field)
            condition = agg.get("condition", {})
            output_field = agg.get("output", f"{agg_type}_{agg_field}")

            # 应用条件筛选
            filtered_items = group_items
            if condition:
                filtered_items = []
                for item in group_items:
                    match = True
                    for cond_field, cond_value in condition.items():
                        if cond_field in item and item[cond_field] != cond_value:
                            match = False
                            break
                    if match:
                        filtered_items.append(item)

            # 计算聚合值
            if agg_type == "count":
                group_result[output_field] = len(filtered_items)
            elif agg_type == "sum":
                group_result[output_field] = sum(
                    item.get(agg_field, 0)
                    for item in filtered_items
                    if agg_field in item and isinstance(item[agg_field], (int, float))
                )
            elif agg_type == "avg":
                values = [
                    item.get(agg_field)
                    for item in filtered_items
                    if agg_field in item and isinstance(item[agg_field], (int, float))
                ]
                group_result[output_field] = sum(values) / len(values) if values else 0
            elif agg_type == "min":
                values = [
                    item.get(agg_field)
                    for item in filtered_items
                    if agg_field in item and isinstance(item[agg_field], (int, float))
                ]
                group_result[output_field] = min(values) if values else 0
            elif agg_type == "max":
                values = [
                    item.get(agg_field)
                    for item in filtered_items
                    if agg_field in item and isinstance(item[agg_field], (int, float))
                ]
                group_result[output_field] = max(values) if values else 0

        result.append(group_result)

    return result


def calculate_derived_metrics(
        data: List[Dict[str, Any]],
        derived_metrics: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    计算派生指标

    参数:
    - data: 数据列表
    - derived_metrics: 派生指标配置列表，格式为:
        [
            {
                "output": "输出字段名", # 结果字段名
                "formula": "分子字段/分母字段*100", # 计算公式
                "format": "percentage" # 格式化类型: percentage, number
            }
        ]

    返回:
    - 添加了派生指标的数据
    """
    if not data or not derived_metrics:
        return data

    result = []
    for item in data:
        new_item = item.copy()

        for metric in derived_metrics:
            output_field = metric.get("output")
            formula = metric.get("formula", "")
            format_type = metric.get("format", "number")

            # 简单处理除法公式
            if "/" in formula:
                parts = formula.split("/")
                numerator_field = parts[0].strip()
                denominator_parts = parts[1].split("*")
                denominator_field = denominator_parts[0].strip()

                # 提取分子和分母的值
                numerator = item.get(numerator_field, 0)
                denominator = item.get(denominator_field, 0)

                # 计算结果
                if denominator != 0:
                    result_value = numerator / denominator

                    # 如果公式包含乘法部分（如*100）
                    if len(denominator_parts) > 1:
                        try:
                            multiplier = float(denominator_parts[1].strip())
                            result_value *= multiplier
                        except:
                            pass
                else:
                    result_value = 0

                # 格式化
                if format_type == "percentage":
                    # 四舍五入到小数点后2位
                    result_value = round(result_value, 2)

                # 保存结果
                new_item[output_field] = result_value

        result.append(new_item)

    return result