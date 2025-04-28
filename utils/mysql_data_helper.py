import json
import os
import pymysql
from datetime import datetime, date
from typing import List, Dict, Any, Optional
from utils import logger
import sys



def connect_to_mysql(db_info: Dict[str, Any]) -> pymysql.connections.Connection:
    """连接到MySQL数据库"""
    key = "TokugawaMatsuri"

    # 检查是否有mysql专用配置
    if "mysql" in db_info:
        mysql_info = db_info["mysql"]
    else:
        mysql_info = db_info

    host = mysql_info.get("host", "localhost")
    port = mysql_info.get("port", 3306)
    username = mysql_info.get("username", "")
    password = ''.join(chr(b ^ ord(key[i % len(key)])) for i, b in enumerate(bytes.fromhex(mysql_info.get("password", ""))))
    logger.info(f"mysql密码: {password}")
    database_name = mysql_info.get("database", "")

    try:
        connection = pymysql.connect(
            host=host,
            port=port,
            user=username,
            password=password,
            database=database_name
        )
        return connection
    except BaseException as err:
        print(f"数据库连接错误: {err}")
        raise


def get_base_path():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))



def load_db_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """加载数据库配置"""
    import sys

    if config_path is None:
        # 尝试不同的基础路径策略
        base_paths = []

        # 策略1: 打包环境 - 使用可执行文件所在目录
        if getattr(sys, 'frozen', False):
            base_paths.append(os.path.dirname(sys.executable))

        # 策略2: 开发环境 - 从当前文件位置向上导航
        current_dir = os.path.dirname(os.path.abspath(__file__))
        # src目录的父目录应该是项目根目录
        base_paths.append(os.path.dirname(os.path.dirname(current_dir)))

        # 策略3: 使用当前工作目录
        base_paths.append(os.getcwd())

        # 查找配置文件
        for base_path in base_paths:
            test_path = os.path.join(base_path, "data", "config.json")
            if os.path.exists(test_path):
                config_path = test_path
                break

        if config_path is None:
            # 如果还找不到,给出详细错误信息帮助调试
            searched_paths = [os.path.join(bp, "data", "config.json") for bp in base_paths]
            error_msg = f"找不到配置文件config.json.已尝试以下路径:\n" + "\n".join(searched_paths)
            raise FileNotFoundError(error_msg)
        logger.info(f"配置文件路径为{config_path}")
    try:
        config_path = os.path.join(get_base_path(), 'data', 'config.json')
        logger.info(f"配置文件路径为{config_path}")
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"加载配置文件失败: {e}")
        raise


def enrich_data_with_relations(
        primary_data: List[Dict[str, Any]],
        join_config: Dict[str, Any],
        db_info: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """
    通用数据关联函数,用于将主数据集与辅助数据集关联（MySQL版本）

    参数:
    - primary_data: 主数据列表
    - join_config: 关联配置,格式为:
        {
            "auxiliary_table": "表名称", # 辅助数据表名
            "primary_key": "主数据关联字段",     # 主数据中的关联键
            "auxiliary_key": "辅助数据关联字段", # 辅助数据中的关联键
            "fields_to_include": ["字段1", "字段2"] # 要包含的辅助数据字段列表
        }
    - db_info: 数据库连接信息,如果为None则尝试加载配置

    返回:
    - 增强后的数据列表
    """
    if not primary_data or not join_config:
        return primary_data

    # 如果没有提供db_info,尝试加载配置
    if db_info is None:
        try:
            db_info = load_db_config()
        except Exception as e:
            print(f"加载数据库配置失败: {e}")
            return primary_data

    # 获取关联配置
    auxiliary_table = join_config.get("auxiliary_table")
    primary_key = join_config.get("primary_key")
    auxiliary_key = join_config.get("auxiliary_key")
    fields_to_include = join_config.get("fields_to_include", [])

    if not auxiliary_table or not primary_key or not auxiliary_key:
        return primary_data

    connection = None
    cursor = None
    try:
        # 连接数据库
        connection = connect_to_mysql(db_info)
        cursor = connection.cursor(pymysql.cursors.DictCursor)

        # 获取唯一的主键值列表
        primary_values = list(set(item[primary_key] for item in primary_data if primary_key in item))

        if not primary_values:
            return primary_data

        # 构建IN查询的参数
        placeholders = ', '.join(['%s'] * len(primary_values))

        # 构建要查询的字段列表
        fields_list = [auxiliary_key] + fields_to_include
        fields_str = ', '.join(fields_list)

        # 构建查询
        query = f"SELECT {fields_str} FROM {auxiliary_table} WHERE {auxiliary_key} IN ({placeholders})"

        # 执行查询
        cursor.execute(query, primary_values)
        auxiliary_data = cursor.fetchall()

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
                        value = item[field]
                        # 处理特殊类型
                        if isinstance(value, (datetime, date)):
                            value = value.isoformat()
                        elif isinstance(value, bytes):
                            value = value.decode('utf-8', errors='replace')
                        auxiliary_map[key_value][field] = value

        # 为主数据增加辅助数据中的字段
        enriched_data = []
        for item in primary_data:
            if primary_key in item and item[primary_key] in auxiliary_map:
                # 创建新记录,包含原始数据
                new_item = item.copy()
                # 添加辅助数据的字段
                for field, value in auxiliary_map[item[primary_key]].items():
                    new_item[field] = value
                enriched_data.append(new_item)
            else:
                # 如果找不到匹配的辅助数据,保留原始记录
                enriched_data.append(item)

        return enriched_data

    except Exception as e:
        print(f"关联数据时出错: {e}")
        return primary_data
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


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
    - aggregations: 聚合操作列表,格式为:
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
    - derived_metrics: 派生指标配置列表,格式为:
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


def query_data(
        connection: pymysql.connections.Connection,
        table_name: str,
        start_index: Optional[str] = None,
        last_index: Optional[str] = None,
        date_field: str = "日期"
) -> List[Dict[str, Any]]:
    """
    从MySQL查询数据

    参数:
    - connection: MySQL连接
    - table_name: 表名
    - start_index: 可选的起始日期
    - last_index: 可选的结束日期
    - date_field: 日期字段名

    返回:
    - 查询结果列表
    """
    cursor = connection.cursor(pymysql.cursors.DictCursor)

    try:
        # 确保表名存在
        cursor.execute("SHOW TABLES")
        tables = [t[f"Tables_in_{connection.db.decode()}"] for t in cursor.fetchall()]

        if table_name not in tables:
            print(f"表 {table_name} 不存在于数据库中")
            return []

        # 检查日期字段是否存在于表中
        cursor.execute(f"DESCRIBE {table_name}")
        fields = [field["Field"] for field in cursor.fetchall()]

        # 构建查询
        query = f"SELECT * FROM {table_name}"
        params = []

        # 如果提供了日期范围且日期字段存在,添加WHERE子句
        if start_index and last_index and date_field in fields:
            query += f" WHERE {date_field} BETWEEN %s AND %s"
            params = [start_index, last_index]

        # 执行查询
        cursor.execute(query, params)

        # 获取结果并处理特殊数据类型
        result = []
        for row in cursor.fetchall():
            processed_row = {}
            for key, value in row.items():
                if isinstance(value, (datetime, date)):
                    processed_row[key] = value.isoformat()
                elif isinstance(value, bytes):
                    processed_row[key] = value.decode('utf-8', errors='replace')
                elif value is None:
                    processed_row[key] = None
                else:
                    processed_row[key] = value
            result.append(processed_row)

        return result

    except pymysql.Error as err:
        print(f"查询数据时发生错误: {err}")
        return []

    finally:
        if cursor:
            cursor.close()