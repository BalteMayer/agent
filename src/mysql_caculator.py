import json
import os
from datetime import datetime, date
import numpy as np
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Union, Optional, Tuple
from utils import (
    connect_to_mysql,
    load_db_config,
    enrich_data_with_relations,
    group_and_aggregate,
    calculate_derived_metrics,
    query_data
)
from utils import logger


class ChartCalculator(ABC):
    """基础图表计算器抽象类"""

    @abstractmethod
    def calculate(self, data: List[Dict[str, Any]], x_field: str, y_field: str, x_table: str,
                  y_table: str) -> Dict[str, Any]:
        """计算图表数据的抽象方法"""
        pass


class BarChartCalculator(ChartCalculator):
    def calculate(self, data: List[Dict[str, Any]], x_field: str, y_field: str, x_table: str,
                  y_table: str) -> Dict[str, Any]:
        """计算条形图所需的数据"""
        result = {}
        categories = []
        values = []

        # 根据x_field进行分组计算
        if not data:
            return {"categories": [], "values": [], "statistics": {"mean": 0, "median": 0, "max": 0, "min": 0}}

        value_counts = {}
        for item in data:
            if x_field in item:
                category = item[x_field]
                if category not in value_counts:
                    value_counts[category] = 0
                value_counts[category] += 1

        for category, count in value_counts.items():
            categories.append(category)
            values.append(count)

        result = {
            "chart_type": "bar",
            "xAxisData": categories,
            "barData": values,
            "seriesNames": [x_field],
            "title": f"{x_table}.{x_field} - {y_table}.{y_field} analysis",
        }

        return result


class LineChartCalculator(ChartCalculator):
    def calculate(self, data: List[Dict[str, Any]], x_field: str, y_field: str, x_table: str,
                  y_table: str) -> Dict[str, Any]:
        """计算折线图所需的数据"""
        result = {}
        time_series = []
        values = []

        if not data:
            return {
                "chart_type": "line",
                "data": [],
                "xAxisLabels": [],
                "title": f"{x_field}-{y_field}"
            }

        # 按日期排序数据
        sorted_data = sorted(data, key=lambda x: x.get(x_field, ''))

        # 根据y_field进行时间序列统计
        date_counts = {}
        for item in sorted_data:
            if x_field in item and y_field in item:
                date = item.get(x_field, '')
                if date not in date_counts:
                    date_counts[date] = 0
                if isinstance(item[y_field], (int, float)):  # 如果值是数字
                    date_counts[date] += item[y_field]
                else:  # 否则计数
                    date_counts[date] += 1

        for date, count in sorted(date_counts.items()):
            time_series.append(date)
            values.append(count)

        result = {
            "chart_type": "line",
            "data": values,
            "xAxisLabels": time_series,
            "title": f"{x_table}.{x_field} - {y_table}.{y_field}",
        }

        return result


class PieChartCalculator(ChartCalculator):
    def calculate(self, data: List[Dict[str, Any]], x_field: str, y_field: str, x_table: str,
                  y_table: str) -> Dict[str, Any]:
        """计算饼图所需的数据"""

        logger.info(f"开始计算饼图数据，输入数据量: {len(data)}, X字段: {x_field}, Y字段: {y_field}")
        result = {}
        labels = []
        values = []

        # 根据x_field进行分组计算
        # 记录数据中是否包含y_field和x_field字段
        if data and len(data) > 0:
            sample_keys = list(data[0].keys())
            logger.info(f"数据样本包含的字段: {sample_keys}")
            missing_fields = []
            if y_field not in sample_keys:
                missing_fields.append(y_field)
            if x_field not in sample_keys:
                missing_fields.append(x_field)

            if missing_fields:
                logger.error(f"数据中不存在字段: {missing_fields}，可用字段为: {sample_keys}")
                return {
                    "chart_type": "pie",
                    "error": f"字段 {missing_fields} 不存在",
                    "available_fields": sample_keys,
                    "pieData": []
                }

        value_counts = {}
        for item in data:
            if x_field in item:
                category = item[x_field]
                if category not in value_counts:
                    value_counts[category] = 0
                if y_field in item:
                    if isinstance(item[y_field], (int, float)):
                        value_counts[category] += item[y_field]
                    else:
                        value_counts[category] += 1
                else:
                    logger.warning(f"跳过一条不包含字段 {y_field} 的数据")

        logger.info(f"分组统计结果: {value_counts}")

        for category, count in value_counts.items():
            labels.append(category)
            values.append(count)

        pie_data = [{"name": name, "value": value} for name, value in zip(labels, values)]

        result = {
            "chart_type": "pie",
            "pieData": pie_data,
            "title": f"{x_table}.{x_field} - {y_table}.{y_field}",
        }
        logger.info(f"饼图计算完成: {len(labels)} 个类别")

        return result


class ScatterChartCalculator(ChartCalculator):
    def calculate(self, data: List[Dict[str, Any]], x_field: str, y_field: str, x_table: str,
                  y_table: str) -> Dict[str, Any]:
        """计算散点图所需的数据"""
        result = {}
        x_values = []
        y_values = []

        if not data:
            return {
                "chart_type": "scatter",
                "x": [],
                "y": [],
                "x_field": x_field,
                "y_field": y_field,
                "correlation": 0,
                "regression": {
                    "slope": 0,
                    "intercept": 0,
                    "line": []
                }
            }

        # 提取数据点
        for item in data:
            if y_field in item and x_field in item:
                try:
                    x_val = float(item[x_field]) if not isinstance(item[x_field], (int, float)) else item[x_field]
                    y_val = float(item[y_field]) if not isinstance(item[y_field], (int, float)) else item[y_field]
                    x_values.append(x_val)
                    y_values.append(y_val)
                except (ValueError, TypeError):
                    continue

        # 计算相关系数
        if len(x_values) > 1:
            correlation = np.corrcoef(x_values, y_values)[0, 1] if len(set(x_values)) > 1 and len(
                set(y_values)) > 1 else 0

            # 线性回归
            z = np.polyfit(x_values, y_values, 1) if len(set(x_values)) > 1 else [0, 0]
            slope = z[0]
            intercept = z[1]

            # 回归线上的点
            regression_line = [slope * x + intercept for x in x_values]
        else:
            correlation = 0
            slope = 0
            intercept = 0
            regression_line = []

        result = {
            "chart_type": "scatter",
            "x": x_values,
            "y": y_values,
            "x_field": x_field,
            "y_field": y_field,
            "correlation": float(correlation) if not np.isnan(correlation) else 0,
            "regression": {
                "slope": float(slope),
                "intercept": float(intercept),
                "line": regression_line
            }
        }

        return result


class HeatMapCalculator(ChartCalculator):
    def calculate(self, data: List[Dict[str, Any]], x_field: str, y_field: str, x_table: str,
                  y_table: str) -> Dict[str, Any]:
        """计算热力图所需的数据"""
        if not data:
            return {
                "chart_type": "heatmap",
                "x_labels": [],
                "y_labels": [],
                "x_field": x_field,
                "y_field": y_field,
                "matrix": [],
                "max_value": 0,
                "min_value": 0
            }

        result = {}

        # 寻找另一个适合作为y轴的字段
        fields = list(data[0].keys())
        fields = [f for f in fields if f != x_field and f != y_field]

        z_field = fields[0] if fields else y_field

        # 提取唯一的x和y值
        x_values = sorted(set(item[x_field] for item in data if x_field in item))
        y_values = sorted(set(item[z_field] for item in data if z_field in item))

        # 创建热力图矩阵
        matrix = np.zeros((len(y_values), len(x_values)))

        # 填充矩阵
        for item in data:
            if x_field in item and z_field in item and y_field in item:
                try:
                    x_idx = x_values.index(item[x_field])
                    y_idx = y_values.index(item[z_field])

                    # 根据y_field累加值
                    if isinstance(item[y_field], (int, float)):
                        matrix[y_idx][x_idx] += item[y_field]
                    else:
                        matrix[y_idx][x_idx] += 1
                except (ValueError, TypeError):
                    continue

        result = {
            "chart_type": "heatmap",
            "x_labels": x_values,
            "y_labels": y_values,
            "x_field": x_field,
            "z_field": z_field,
            "y_field": y_field,
            "matrix": matrix.tolist(),
            "max_value": float(np.max(matrix)),
            "min_value": float(np.min(matrix))
        }

        logger.info(f"热力图计算结果: {result}")

        return result


class YoYMoMCalculator(ChartCalculator):
    """同比环比计算器"""

    def calculate(self, data: List[Dict[str, Any]], x_field: str, y_field: str, x_table: str,
                  y_table: str) -> Dict[str, Any]:
        """计算同比环比数据"""
        if not data:
            return {
                "chart_type": "yoy_mom",
                "current_period": {},
                "previous_period": {},
                "previous_year": {},
                "mom_change": {},
                "yoy_change": {}
            }

        result = {}

        # 解析日期并提取年月信息
        date_data = {}
        for item in data:
            if x_field in item and y_field in item:
                date_str = item[x_field]
                try:
                    # 处理不同的日期格式
                    if 'T' in date_str:  # ISO格式 (2023-04-16T12:30:45)
                        date_str = date_str.split('T')[0]

                    # 假设日期格式为 YYYY-MM-DD
                    parts = date_str.split('-')
                    if len(parts) >= 2:
                        year_month = f"{parts[0]}-{parts[1]}"
                        year = parts[0]
                        month = parts[1]

                        # 对每个年月进行数据聚合
                        if year_month not in date_data:
                            date_data[year_month] = {
                                "year": year,
                                "month": month,
                                "count": 0,
                                "sum": 0,
                                "values": []
                            }

                        # 根据值类型进行聚合
                        if isinstance(item[y_field], (int, float)):
                            date_data[year_month]["sum"] += item[y_field]
                            date_data[year_month]["values"].append(item[y_field])
                        else:
                            date_data[year_month]["count"] += 1
                except Exception:
                    continue

        # 按年月排序
        sorted_year_months = sorted(date_data.keys())

        if not sorted_year_months:
            return {
                "chart_type": "yoy_mom",
                "error": "无有效数据点"
            }

        # 计算当前期间、上期和去年同期
        current_period = sorted_year_months[-1]
        current_data = date_data[current_period]

        # 环比(MoM): 与上个月比较
        mom_period = None
        mom_data = {}
        mom_change = {}
        if len(sorted_year_months) > 1:
            mom_period = sorted_year_months[-2]
            mom_data = date_data[mom_period]

            # 计算环比变化
            current_value = current_data["sum"] if current_data["sum"] > 0 else current_data["count"]
            mom_value = mom_data["sum"] if mom_data["sum"] > 0 else mom_data["count"]

            if mom_value != 0:
                mom_change = {
                    "absolute": current_value - mom_value,
                    "percentage": round(((current_value - mom_value) / mom_value) * 100, 2)
                }
            else:
                mom_change = {"absolute": current_value, "percentage": 100}

        # 同比(YoY): 与去年同月比较
        current_year, current_month = current_data["year"], current_data["month"]
        previous_year = str(int(current_year) - 1)
        yoy_period = f"{previous_year}-{current_month}"
        yoy_data = {}
        yoy_change = {}

        if yoy_period in date_data:
            yoy_data = date_data[yoy_period]

            # 计算同比变化
            current_value = current_data["sum"] if current_data["sum"] > 0 else current_data["count"]
            yoy_value = yoy_data["sum"] if yoy_data["sum"] > 0 else yoy_data["count"]

            if yoy_value != 0:
                yoy_change = {
                    "absolute": current_value - yoy_value,
                    "percentage": round(((current_value - yoy_value) / yoy_value) * 100, 2)
                }
            else:
                yoy_change = {"absolute": current_value, "percentage": 100}

        result = {
            "chart_type": "yoy_mom",
            "current_period": {
                "period": current_period,
                "value": current_data["sum"] if current_data["sum"] > 0 else current_data["count"],
                "avg": np.mean(current_data["values"]) if current_data["values"] else current_data["count"]
            },
            "previous_period": {
                "period": mom_period,
                "value": mom_data.get("sum", 0) if mom_data.get("sum", 0) > 0 else mom_data.get("count", 0)
            },
            "previous_year": {
                "period": yoy_period,
                "value": yoy_data.get("sum", 0) if yoy_data.get("sum", 0) > 0 else yoy_data.get("count", 0)
            },
            "mom_change": mom_change,
            "yoy_change": yoy_change
        }

        return result


class RankingCalculator(ChartCalculator):
    def calculate(self, data: List[Dict[str, Any]], x_field: str, y_field: str, x_table: str,
                  y_table: str, limit: int = 5, ascending: bool = False) -> Dict[str, Any]:
        if not data:
            return {
                "chart_type": "ranking",
                "ranks": [],
                "stats": {}
            }

        aggregations = [
            {"type": "count", "field": y_field, "output": "total"},
            {"type": "count", "field": y_field, "condition": {y_field: "出勤"}, "output": "matches"}
        ]

        grouped_data = group_and_aggregate(data, x_field, y_field, aggregations)

        derived_metrics = [
            {
                "output": "percentage",
                "formula": "matches/total*100",
                "format": "percentage"
            }
        ]

        result_data = calculate_derived_metrics(grouped_data, derived_metrics)

        result_data.sort(key=lambda x: x.get("percentage", 0), reverse=not ascending)

        if limit > 0 and len(result_data) > limit:
            result_data = result_data[:limit]

        for i, item in enumerate(result_data):
            item["rank"] = i + 1

        percentages = [item.get("percentage", 0) for item in result_data]
        overall_stats = {
            "average_percentage": round(sum(percentages) / len(percentages), 2) if percentages else 0,
            "max_percentage": max(percentages) if percentages else 0,
            "min_percentage": min(percentages) if percentages else 0
        }

        return {
            "chart_type": "ranking",
            "ranks": result_data,
            "group_by": x_field,
            "value_field": y_field,
            "stats": overall_stats
        }


class ChartCalculatorFactory:
    @staticmethod
    def create_calculator(chart_type: str) -> ChartCalculator:
        calculator_map = {
            "bar": BarChartCalculator,
            "line": LineChartCalculator,
            "pie": PieChartCalculator,
            "scatter": ScatterChartCalculator,
            "heatmap": HeatMapCalculator,
            "yoy_mom": YoYMoMCalculator,
            # "multi_field": MultiFieldAnalysisCalculator,
            "ranking": RankingCalculator
        }

        calculator_class = calculator_map.get(chart_type.lower())
        if not calculator_class:
            raise ValueError(f"不支持的图表类型: {chart_type}")

        return calculator_class()


def get_date_field(connection, table_name):
    """
    动态确定表中最适合作为日期或索引字段的列名

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

        # 存储候选字段和其优先级
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

            # 字段是主键或索引
            is_key = column[3].lower() if len(column) > 3 else ""
            if is_key == 'pri' or is_key == 'uni' or is_key == 'mul':
                # 主键但不是ID类型
                if is_key == 'pri' and not ('id' == column_name.lower() or column_name.lower().endswith('_id')):
                    candidates.append((column_name, 1))

        # 2. 如果存在候选字段，按优先级返回
        if candidates:
            # 按优先级排序
            candidates.sort(key=lambda x: x[1], reverse=True)
            return candidates[0][0]

        # 3. 如果没有找到候选字段，尝试查询一行数据，分析字段类型
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

        # 5. 最后的回退方案：返回第一个非ID的字段，或者主键
        for column in columns:
            if 'id' != column[0].lower() and not column[0].lower().endswith('_id'):
                return column[0]

        # 实在找不到，返回第一个字段
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
    从两个表中查询数据并合并结果，支持对两表分别应用过滤条件

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
            # 如果在同一个表，直接查询
            query = f"SELECT * FROM `{x_table}`"
            conditions = []

            # 合并X和Y的过滤条件
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
            # 如果在不同表，需要查找关联字段并执行联合查询
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
                # 如果找不到共同键，则分别查询两个表并在应用层合并
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


def mysql_caculator(
        x_field: str,
        y_field: str,
        x_table: str,
        y_table: str,
        x_index_field: Optional[str] = None,
        x_start_index: Optional[str] = None,
        x_end_index: Optional[str] = None,
        y_index_field: Optional[str] = None,
        y_start_index: Optional[str] = None,
        y_end_index: Optional[str] = None,
        chart_type: str = "bar",
        limit: int = 5,
        ascending: bool = False
) -> str:
    """
    根据配置连接MySQL数据库，查询指定范围(可选)数据，并根据图表类型进行计算

    参数:
    - x_field: X轴字段名
    - y_field: Y轴字段名
    - x_table: X轴字段所在的表名
    - y_table: Y轴字段所在的表名
    - x_index_field: X表的索引/过滤字段
    - x_start_index: X表索引字段的起始值
    - x_end_index: X表索引字段的结束值
    - y_index_field: Y表的索引/过滤字段
    - y_start_index: Y表索引字段的起始值
    - y_end_index: Y表索引字段的结束值
    - chart_type: 图表类型，默认为柱状图
    - limit: 排名分析时返回的最大数量，默认为5
    - ascending: 排序方向，True为升序，False为降序

    返回:
    - JSON格式的计算结果
    """

    logger.info(
        f"开始查询MySQL数据: X表={x_table}, X字段={x_field}, Y表={y_table}, Y字段={y_field}, "
        f"X索引字段={x_index_field}, X起始={x_start_index}, X结束={x_end_index}, "
        f"Y索引字段={y_index_field}, Y起始={y_start_index}, Y结束={y_end_index}, "
        f"图表类型: {chart_type}")

    try:
        # 加载数据库配置
        db_info = load_db_config()
        logger.info(f"数据库配置: {db_info}")

        # 确保使用MySQL配置
        if "mysql" in db_info:
            mysql_info = db_info["mysql"]
        else:
            # 如果没有mysql子键，使用顶级配置
            mysql_info = db_info

        # 连接到MySQL数据库
        logger.info("尝试连接MySQL数据库...")
        connection = connect_to_mysql(mysql_info)
        logger.info(f"成功连接到MySQL数据库: {mysql_info.get('host')}:{mysql_info.get('port')}")

        # 查询数据
        logger.info(f"查询表 {x_table} 和 {y_table} 的数据...")
        data = query_data_from_tables(
            connection,
            x_table, y_table,
            x_field, y_field,
            x_index_field, x_start_index, x_end_index,
            y_index_field, y_start_index, y_end_index
        )
        logger.info(f"查询完成，获取到 {len(data)} 条记录")

        # 根据图表类型执行计算
        logger.info(f"开始计算 {chart_type} 类型的图表数据...")
        calculator = ChartCalculatorFactory.create_calculator(chart_type)

        if chart_type.lower() == "ranking":
            # 使用RankingCalculator时传入额外的limit和ascending参数
            ranking_calculator = RankingCalculator()
            calculation_result = ranking_calculator.calculate(
                data, x_field, y_field, x_table, y_table, limit, ascending
            )
        else:
            calculation_result = calculator.calculate(data, x_field, y_field, x_table, y_table)

        # 关闭连接
        connection.close()
        logger.info("数据库连接已关闭")

        # 构建结果
        result = {
            "chart_type": chart_type,
            "x_table": x_table,
            "y_table": y_table,
            "x_field": x_field,
            "y_field": y_field,
            "filters": {
                "x_filter": {
                    "field": x_index_field,
                    "start": x_start_index,
                    "end": x_end_index
                },
                "y_filter": {
                    "field": y_index_field,
                    "start": y_start_index,
                    "end": y_end_index
                }
            },
            "data_count": len(data),
            "result": calculation_result
        }
        logger.info(f"计算完成，返回结果")
        return f"[{chart_type}{json.dumps(result, ensure_ascii=False)}]"

    except Exception as e:
        # 确保任何异常情况下都能关闭连接
        if 'connection' in locals():
            connection.close()
            logger.info("异常情况下关闭数据库连接")

        error_result = {
            "error": str(e),
            "chart_type": chart_type,
            "x_table": x_table,
            "y_table": y_table,
            "x_field": x_field,
            "y_field": y_field,
            "filters": {
                "x_filter": {
                    "field": x_index_field,
                    "start": x_start_index,
                    "end": x_end_index
                },
                "y_filter": {
                    "field": y_index_field,
                    "start": y_start_index,
                    "end": y_end_index
                }
            }
        }

        return json.dumps(error_result, ensure_ascii=False)


if __name__ == "__main__":
    # 校区人员分布分析
    result = mysql_caculator(
        x_field="school",  # X轴使用校区
        y_field="ID",  # Y轴用ID计数
        x_table="Data",  # 从人员数据表获取数据
        y_table="Data",
        chart_type="pie"  # 生成饼图
    )
    print(result)