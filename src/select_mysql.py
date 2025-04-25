import os
import json
from datetime import datetime, date
from typing import Dict, List, Any, Union, Optional, Tuple
from utils import logger


def get_date_field(connection, table_name):
    """
    动态确定表中最适合作为日期or索引字段的列名

    参数:
    - connection: 数据库连接
    - table_name: 表名

    返回:
    - 适合用于查询的字段名
    """
    if not connection:
        return None

    cursor = None
    try:
        cursor = connection.cursor()

        # 1. 获取表字段信息
        cursor.execute(f"DESCRIBE `{table_name}`")
        columns = cursor.fetchall()

        # 存储候选字段and其优先级
        candidates = []

        for column in columns:
            column_name = column[0]
            column_type = column[1].lower() if len(column) > 1 else ""

            # 检查字段类型是否为日期类型
            if any(date_type in column_type for date_type in ['date', 'time', 'datetime', 'timestamp']):
                candidates.append((column_name, 3))
                continue

            # 检查字段名是否包含日期相关关键词
            if any(keyword in column_name.lower() for keyword in
                   ['date', 'time', 'day', 'created', 'updated', '日期', '时间']):
                candidates.append((column_name, 2))
                continue

            # 字段是主键or索引
            is_key = column[3].lower() if len(column) > 3 else ""
            if is_key == 'pri' or is_key == 'uni' or is_key == 'mul':
                # 主键但不是ID类型
                if is_key == 'pri' and not ('id' == column_name.lower() or column_name.lower().endswith('_id')):
                    candidates.append((column_name, 1))

        # 2. 如果存在候选字段,按优先级返回
        if candidates:
            # 按优先级排序
            candidates.sort(key=lambda x: x[1], reverse=True)
            return candidates[0][0]

        # 3. 如果没有找到候选字段,尝试查询一行数据,分析字段类型
        cursor.execute(f"SELECT * FROM `{table_name}` LIMIT 1")
        row = cursor.fetchone()
        if row:
            column_names = [desc[0] for desc in cursor.description]

            for i, value in enumerate(row):
                # 如果是日期时间类型值
                if isinstance(value, (datetime, date)):
                    return column_names[i]
                # 如果是字符串且看起来像日期
                elif isinstance(value, str) and (
                        ('-' in value and value.count('-') >= 2) or
                        ('/' in value and value.count('/') >= 2)
                ):
                    return column_names[i]

        # 4. 回退方案：寻找看起来像排序字段的列
        for column in columns:
            column_name = column[0]
            # 字段名包含序号相关关键词
            if any(keyword in column_name.lower() for keyword in ['order', 'seq', 'num', 'no', '序号', '编号']):
                return column_name

        # 5. 最后的回退方案：返回第一个非ID的字段,or者主键
        for column in columns:
            if 'id' != column[0].lower() and not column[0].lower().endswith('_id'):
                return column[0]

        # 实在找不到,返回第一个字段
        return columns[0][0] if columns else None

    except Exception as e:
        logger.error(f"获取日期字段时出错: {e}")
        return None
    finally:
        if cursor:
            cursor.close()


def query_data_from_tables(connection, x_table, y_table, x_field, y_field,
                           x_index_field=None, x_start_index=None, x_end_index=None,
                           y_index_field=None, y_start_index=None, y_end_index=None):
    """
    从两个表中查询数据并合并结果,支持对两表分别应用过滤条件

    参数:
    - connection: 数据库连接
    - x_table: X轴字段所在的表
    - y_table: Y轴字段所在的表
    - x_field: X轴字段名
    - y_field: Y轴字段名
    - x_index_field: X表的索引/过滤字段
    - x_start_index: X表索引字段的起始值
    - x_end_index: X表索引字段的结束值
    - y_index_field: Y表的索引/过滤字段
    - y_start_index: Y表索引字段的起始值
    - y_end_index: Y表索引字段的结束值

    返回:
    - 包含两个表中字段的数据列表
    """
    cursor = None
    try:
        import pymysql
        cursor = connection.cursor(pymysql.cursors.DictCursor)

        # 检查两个表是否相同
        if x_table == y_table:
            # 如果在同一个表,直接查询
            query = f"SELECT * FROM `{x_table}`"
            conditions = []

            # 合并XandY的过滤条件
            if x_index_field and x_start_index:
                conditions.append(f"`{x_index_field}` >= %s")
            if x_index_field and x_end_index:
                conditions.append(f"`{x_index_field}` <= %s")

            if y_index_field and y_start_index and y_index_field != x_index_field:
                conditions.append(f"`{y_index_field}` >= %s")
            if y_index_field and y_end_index and y_index_field != x_index_field:
                conditions.append(f"`{y_index_field}` <= %s")

            if conditions:
                query += " WHERE " + " AND ".join(conditions)

            params = []
            if x_index_field and x_start_index:
                params.append(x_start_index)
            if x_index_field and x_end_index:
                params.append(x_end_index)

            if y_index_field and y_start_index and y_index_field != x_index_field:
                params.append(y_start_index)
            if y_index_field and y_end_index and y_index_field != x_index_field:
                params.append(y_end_index)

            cursor.execute(query, params)
            return cursor.fetchall()
        else:
            # 如果在不同表,需要查找关联字段并执行联合查询
            # 首先检查两个表是否有共同的ID字段
            cursor.execute(f"DESCRIBE `{x_table}`")
            x_table_columns = [col[0] for col in cursor.fetchall()]

            cursor.execute(f"DESCRIBE `{y_table}`")
            y_table_columns = [col[0] for col in cursor.fetchall()]

            # 寻找可能的连接键
            common_columns = set(x_table_columns) & set(y_table_columns)
            join_keys = [col for col in common_columns if 'id' in col.lower() or col.lower().endswith('_id')]

            if join_keys:
                join_key = join_keys[0]
                # 构建JOIN查询
                query = f"""
                SELECT 
                    x.`{x_field}`, 
                    y.`{y_field}`,
                    x.*,
                    y.*
                FROM 
                    `{x_table}` x
                JOIN 
                    `{y_table}` y ON x.`{join_key}` = y.`{join_key}`
                """

                conditions = []
                # X表过滤条件
                if x_index_field and x_start_index:
                    conditions.append(f"x.`{x_index_field}` >= %s")
                if x_index_field and x_end_index:
                    conditions.append(f"x.`{x_index_field}` <= %s")

                # Y表过滤条件
                if y_index_field and y_start_index:
                    conditions.append(f"y.`{y_index_field}` >= %s")
                if y_index_field and y_end_index:
                    conditions.append(f"y.`{y_index_field}` <= %s")

                if conditions:
                    query += " WHERE " + " AND ".join(conditions)

                params = []
                if x_index_field and x_start_index:
                    params.append(x_start_index)
                if x_index_field and x_end_index:
                    params.append(x_end_index)

                if y_index_field and y_start_index:
                    params.append(y_start_index)
                if y_index_field and y_end_index:
                    params.append(y_end_index)

                cursor.execute(query, params)
                return cursor.fetchall()
            else:
                # 如果找不到共同键,则分别查询两个表并在应用层合并
                x_query = f"SELECT * FROM `{x_table}`"
                y_query = f"SELECT * FROM `{y_table}`"

                # X表过滤条件
                x_conditions = []
                if x_index_field and x_start_index:
                    x_conditions.append(f"`{x_index_field}` >= %s")
                if x_index_field and x_end_index:
                    x_conditions.append(f"`{x_index_field}` <= %s")

                if x_conditions:
                    x_query += " WHERE " + " AND ".join(x_conditions)

                x_params = []
                if x_index_field and x_start_index:
                    x_params.append(x_start_index)
                if x_index_field and x_end_index:
                    x_params.append(x_end_index)

                # Y表过滤条件
                y_conditions = []
                if y_index_field and y_start_index:
                    y_conditions.append(f"`{y_index_field}` >= %s")
                if y_index_field and y_end_index:
                    y_conditions.append(f"`{y_index_field}` <= %s")

                if y_conditions:
                    y_query += " WHERE " + " AND ".join(y_conditions)

                y_params = []
                if y_index_field and y_start_index:
                    y_params.append(y_start_index)
                if y_index_field and y_end_index:
                    y_params.append(y_end_index)

                cursor.execute(x_query, x_params)
                x_data = cursor.fetchall()

                cursor.execute(y_query, y_params)
                y_data = cursor.fetchall()

                # 合并数据 - 创建笛卡尔积
                combined_data = []
                for x_item in x_data:
                    for y_item in y_data:
                        merged_item = {}
                        merged_item.update(x_item)
                        # 避免字段名冲突
                        for k, v in y_item.items():
                            if k in merged_item and k != y_field:
                                merged_item[f"{y_table}_{k}"] = v
                            else:
                                merged_item[k] = v
                        combined_data.append(merged_item)

                return combined_data
    except Exception as e:
        logger.error(f"查询数据时出错: {e}")
        return []
    finally:
        if cursor:
            cursor.close()