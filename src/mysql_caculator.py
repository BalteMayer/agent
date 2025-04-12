import json
import os
import mysql.connector
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
    def calculate(self, data: List[Dict[str, Any]], value_type: str) -> Dict[str, Any]:
        """计算图表数据的抽象方法"""
        pass


class BarChartCalculator(ChartCalculator):
    def calculate(self, data: List[Dict[str, Any]], value_type: str) -> Dict[str, Any]:
        """计算条形图所需的数据"""
        result = {}
        categories = []
        values = []

        # 根据value_type进行分组计算
        if not data:
            return {"categories": [], "values": [], "statistics": {"mean": 0, "median": 0, "max": 0, "min": 0}}

        value_counts = {}
        for item in data:
            if value_type in item:
                category = item[value_type]
                if category not in value_counts:
                    value_counts[category] = 0
                value_counts[category] += 1

        for category, count in value_counts.items():
            categories.append(category)
            values.append(count)

        # 计算统计值
        stats = {
            "mean": np.mean(values) if values else 0,
            "median": np.median(values) if values else 0,
            "max": max(values) if values else 0,
            "min": min(values) if values else 0,
            "std": np.std(values) if values else 0,
            "variance": np.var(values) if values else 0
        }

        result = {
            "chart_type": "bar",
            "categories": categories,
            "values": values,
            "statistics": stats
        }

        return result


class LineChartCalculator(ChartCalculator):
    def calculate(self, data: List[Dict[str, Any]], value_type: str) -> Dict[str, Any]:
        """计算折线图所需的数据"""
        result = {}
        time_series = []
        values = []

        # 假设数据中有日期字段
        date_field = None
        for field in data[0].keys() if data else []:
            if any(date_keyword in field.lower() for date_keyword in ['日期', 'date', '时间', 'time', 'created_at']):
                date_field = field
                break

        if not date_field and data:
            date_field = list(data[0].keys())[0]  # 如果找不到日期字段，使用第一个字段

        # 按日期排序数据
        if date_field:
            sorted_data = sorted(data, key=lambda x: x.get(date_field, ''))
        else:
            sorted_data = data

        # 根据value_type进行时间序列统计
        date_counts = {}
        for item in sorted_data:
            if date_field and value_type in item:
                date = item.get(date_field, '')
                if date not in date_counts:
                    date_counts[date] = 0
                if item[value_type] == value_type:  # 如果值等于value_type本身
                    date_counts[date] += 1
                elif isinstance(item[value_type], (int, float)):  # 如果值是数字
                    date_counts[date] += item[value_type]
                else:  # 否则计数
                    date_counts[date] += 1

        for date, count in sorted(date_counts.items()):
            time_series.append(date)
            values.append(count)

        # 计算趋势和预测
        if len(values) > 1:
            values_np = np.array(values)
            x = np.arange(len(values))
            z = np.polyfit(x, values_np, 1)
            trend = z[0]  # 线性趋势斜率

            # 简单的下一个周期预测
            next_val_pred = np.polyval(z, len(values))

            # 计算移动平均
            window_size = min(3, len(values))
            moving_avg = np.convolve(values_np, np.ones(window_size) / window_size, mode='valid').tolist()
        else:
            trend = 0
            next_val_pred = values[0] if values else 0
            moving_avg = values

        result = {
            "chart_type": "line",
            "x_axis": time_series,
            "values": values,
            "trend": float(trend),
            "prediction_next": float(next_val_pred),
            "moving_average": moving_avg
        }

        return result


class PieChartCalculator(ChartCalculator):
    def calculate(self, data: List[Dict[str, Any]], value_type: str) -> Dict[str, Any]:
        """计算饼图所需的数据"""
        result = {}
        labels = []
        values = []

        # 根据value_type进行分组计算
        value_counts = {}
        for item in data:
            if value_type in item:
                category = item[value_type]
                if category not in value_counts:
                    value_counts[category] = 0
                value_counts[category] += 1

        for category, count in value_counts.items():
            labels.append(category)
            values.append(count)

        # 计算百分比
        total = sum(values)
        percentages = [round((value / total) * 100, 2) if total > 0 else 0 for value in values]

        result = {
            "chart_type": "pie",
            "labels": labels,
            "values": values,
            "percentages": percentages
        }

        return result


class ScatterChartCalculator(ChartCalculator):
    def calculate(self, data: List[Dict[str, Any]], value_type: str) -> Dict[str, Any]:
        """计算散点图所需的数据"""
        result = {}
        x_values = []
        y_values = []

        if not data:
            return {
                "x": [],
                "y": [],
                "x_field": "",
                "y_field": value_type,
                "correlation": 0,
                "regression": {
                    "slope": 0,
                    "intercept": 0,
                    "line": []
                }
            }

        # 寻找可能的数值字段作为x轴
        numeric_fields = []
        for field in data[0].keys():
            if field != value_type:
                try:
                    # 检查第一个元素是否可以转换为数字
                    if isinstance(data[0][field], (int, float)) or (
                            isinstance(data[0][field], str) and data[0][field].replace('.', '', 1).isdigit()):
                        numeric_fields.append(field)
                except (KeyError, ValueError, TypeError):
                    pass

        x_field = numeric_fields[0] if numeric_fields else list(data[0].keys())[0]

        # 提取数据点
        for item in data:
            if value_type in item and x_field in item:
                try:
                    x_val = float(item[x_field]) if not isinstance(item[x_field], (int, float)) else item[x_field]
                    y_val = float(item[value_type]) if not isinstance(item[value_type], (int, float)) else item[
                        value_type]
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
            "y_field": value_type,
            "correlation": float(correlation) if not np.isnan(correlation) else 0,
            "regression": {
                "slope": float(slope),
                "intercept": float(intercept),
                "line": regression_line
            }
        }

        return result


class HeatMapCalculator(ChartCalculator):
    def calculate(self, data: List[Dict[str, Any]], value_type: str) -> Dict[str, Any]:
        """计算热力图所需的数据"""
        if not data:
            return {
                "x_labels": [],
                "y_labels": [],
                "x_field": "",
                "y_field": "",
                "matrix": [],
                "max_value": 0,
                "min_value": 0
            }

        result = {}

        # 寻找两个适合作为坐标轴的字段
        fields = list(data[0].keys())
        fields = [f for f in fields if f != value_type]

        if len(fields) < 2:
            # 如果没有足够的字段，尝试创建时间段作为第二个维度
            date_field = None
            for field in data[0].keys():
                if any(date_keyword in field.lower() for date_keyword in
                       ['日期', 'date', '时间', 'time', 'created_at']):
                    date_field = field
                    break

            if date_field:
                # 创建时间段
                time_periods = []
                for item in data:
                    time_periods.append(item[date_field])
                unique_periods = sorted(set(time_periods))

                x_field = fields[0]
                y_field = date_field
            else:
                x_field = fields[0]
                y_field = value_type
        else:
            x_field = fields[0]
            y_field = fields[1]

        # 提取唯一的x和y值
        x_values = sorted(set(item[x_field] for item in data if x_field in item))
        y_values = sorted(set(item[y_field] for item in data if y_field in item))

        # 创建热力图矩阵
        matrix = np.zeros((len(y_values), len(x_values)))

        # 填充矩阵
        for item in data:
            if x_field in item and y_field in item and value_type in item:
                try:
                    x_idx = x_values.index(item[x_field])
                    y_idx = y_values.index(item[y_field])

                    # 根据value_type累加值
                    if isinstance(item[value_type], (int, float)):
                        matrix[y_idx][x_idx] += item[value_type]
                    elif item[value_type] == value_type:
                        matrix[y_idx][x_idx] += 1
                    else:
                        matrix[y_idx][x_idx] += 1
                except (ValueError, TypeError):
                    continue

        result = {
            "chart_type": "heatmap",
            "x_labels": x_values,
            "y_labels": y_values,
            "x_field": x_field,
            "y_field": y_field,
            "matrix": matrix.tolist(),
            "max_value": float(np.max(matrix)),
            "min_value": float(np.min(matrix))
        }

        logger.info(f"热力图计算结果: {result}")

        return result


class YoYMoMCalculator(ChartCalculator):
    """同比环比计算器"""

    def calculate(self, data: List[Dict[str, Any]], value_type: str) -> Dict[str, Any]:
        """计算同比环比数据"""
        if not data:
            return {
                "current_period": {},
                "previous_period": {},
                "previous_year": {},
                "mom_change": {},
                "yoy_change": {}
            }

        result = {}
        # 寻找日期字段
        date_field = None
        for field in data[0].keys():
            if any(date_keyword in field.lower() for date_keyword in ['日期', 'date', '时间', 'time', 'created_at']):
                date_field = field
                break

        if not date_field:
            return {"error": "无法找到日期字段"}

        # 解析日期并提取年月信息
        date_data = {}
        for item in data:
            if date_field in item and value_type in item:
                date_str = item[date_field]
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
                        if isinstance(item[value_type], (int, float)):
                            date_data[year_month]["sum"] += item[value_type]
                            date_data[year_month]["values"].append(item[value_type])
                        else:
                            date_data[year_month]["count"] += 1
                except Exception:
                    continue

        # 按年月排序
        sorted_year_months = sorted(date_data.keys())

        if not sorted_year_months:
            return {"error": "无有效数据点"}

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


class MultiFieldAnalysisCalculator(ChartCalculator):
    def calculate(self, data: List[Dict[str, Any]], value_type: str, group_by_fields: List[str] = None) -> Dict[
        str, Any]:
        """多字段组合分析计算

        参数:
        - data: 数据列表
        - value_type: 要分析的数据字段
        - group_by_fields: 分组字段列表 (如果为None，将尝试自动选择合适的分组字段)
        """
        if not data:
            return {"groups": [], "summary": {}}

        if not group_by_fields:
            excluded_fields = [value_type]
            group_by_fields = []

            for field in data[0].keys():
                if field not in excluded_fields and not any(keyword in field.lower()
                                                            for keyword in ['id', '_id', '日期', 'date', '时间', 'time',
                                                                            'created_at']):
                    group_by_fields.append(field)
                    if len(group_by_fields) >= 2:
                        break

        if not group_by_fields:
            return {"error": "无法确定分组字段"}

        grouped_data = {}
        group_values = {field: set() for field in group_by_fields}

        for item in data:
            group_key_parts = []
            valid_item = True

            for field in group_by_fields:
                if field in item:
                    group_key_parts.append(str(item[field]))
                    group_values[field].add(str(item[field]))
                else:
                    valid_item = False
                    break

            if not valid_item:
                continue

            group_key = tuple(group_key_parts)

            if group_key not in grouped_data:
                grouped_data[group_key] = {
                    "count": 0,
                    "sum": 0,
                    "values": []
                }

            if value_type in item:
                grouped_data[group_key]["count"] += 1

                if isinstance(item[value_type], (int, float)):
                    grouped_data[group_key]["sum"] += item[value_type]
                    grouped_data[group_key]["values"].append(item[value_type])
                elif item[value_type] == value_type:
                    grouped_data[group_key]["sum"] += 1
                else:
                    grouped_data[group_key]["values"].append(item[value_type])

        groups = []
        for group_key, group_data in grouped_data.items():
            group_info = {}

            for i, field in enumerate(group_by_fields):
                group_info[field] = group_key[i]

            group_info["count"] = group_data["count"]
            group_info["sum"] = group_data["sum"]
            group_info["avg"] = np.mean(group_data["values"]) if group_data["values"] else 0

            if group_data["values"]:
                group_info["min"] = min(group_data["values"])
                group_info["max"] = max(group_data["values"])

            groups.append(group_info)

        summary = {
            "total_groups": len(groups),
            "dimensions": group_by_fields,
            "total_records": sum(g["count"] for g in groups),
            "total_sum": sum(g["sum"] for g in groups)
        }

        dimension_values = {field: sorted(list(values)) for field, values in group_values.items()}

        return {
            "groups": groups,
            "summary": summary,
            "dimension_values": dimension_values
        }


class RankingCalculator(ChartCalculator):
    def calculate(self, data: List[Dict[str, Any]], value_type: str,
                  limit: int = 5, group_by: str = None, ascending: bool = False) -> Dict[str, Any]:
        if not data:
            return {"ranks": [], "stats": {}}

        try:
            db_info = load_db_config()
        except Exception:
            db_info = {}

        if group_by and group_by not in data[0]:
            primary_key = None
            for key in ["姓名", "名字", "学生", "员工", "用户", "name", "nickname"]:
                if key in data[0]:
                    primary_key = key
                    break

            if primary_key:
                tables = db_info.get("mysql", {}).get("tables", {})
                auxiliary_table = None
                auxiliary_key = None

                for table_name, table_info in tables.items():
                    fields = table_info.get("fields", {})
                    if group_by in fields:
                        auxiliary_table = table_name

                        for field in fields:
                            if field in ["姓名", "名字", "学生", "员工", "用户", "name", "nickname"]:
                                auxiliary_key = field
                                break
                        if auxiliary_key:
                            break

                if auxiliary_table and auxiliary_key:
                    join_config = {
                        "auxiliary_table": auxiliary_table,
                        "primary_key": primary_key,
                        "auxiliary_key": auxiliary_key,
                        "fields_to_include": [group_by]
                    }

                    data = enrich_data_with_relations(data, join_config, db_info)

        if group_by and (not data or group_by not in data[0]):
            potential_fields = []
            for field in data[0].keys():
                if field != value_type and not any(keyword in field.lower()
                                                   for keyword in
                                                   ['id', '_id', '日期', 'date', '时间', 'time', 'created_at']):
                    potential_fields.append(field)

            group_by = potential_fields[0] if potential_fields else None

        if not group_by:
            return {"error": "无法确定分组字段"}

        aggregations = [
            {"type": "count", "field": value_type, "output": "total"},
            {"type": "count", "field": value_type, "condition": {value_type: "出勤"}, "output": "matches"}
        ]

        grouped_data = group_and_aggregate(data, group_by, value_type, aggregations)

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
            "group_by": group_by,
            "value_type": value_type,
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
            "multi_field": MultiFieldAnalysisCalculator,
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

def query_and_calculate(start_index: Optional[str] = None, last_index: Optional[str] = None,
                        value_type: str = None, table_name: str = None, chart_type: str = None,
                        group_by_fields: List[str] = None, limit: int = 5, group_by: str = None,
                        ascending: bool = False) -> str:
    """
    根据配置连接MySQL数据库，查询指定范围(可选)数据，并根据图表类型进行计算

    参数:
    - start_index: 可选的起始索引(日期等)
    - last_index: 可选的结束索引
    - value_type: 要分析的数据字段
    - table_name: 表名
    - chart_type: 图表类型
    - group_by_fields: 多字段分析时的分组字段列表
    - limit: 排名分析时返回的最大数量，默认为5
    - group_by: 排名分析的分组字段
    - ascending: 排序方向，True为升序，False为降序

    返回:
    - JSON格式的计算结果
    """

    logger.info(
        f"开始查询MySQL数据: {table_name}, 字段: {value_type}起始索引: {start_index}, 结束索引: {last_index}, 图表类型: {chart_type}")

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
        connection = connect_to_mysql(mysql_info)
        logger.info(f"成功连接到MySQL数据库: {mysql_info}")


        date_field = get_date_field(connection, table_name)

        # 查询数据
        data = query_data(connection, table_name, start_index, last_index, date_field)

        # 根据图表类型执行计算
        if chart_type.lower() == "ranking":
            calculator = RankingCalculator()
            calculation_result = calculator.calculate(data, value_type, limit, group_by, ascending)
        else:
            calculator = ChartCalculatorFactory.create_calculator(chart_type)

            if chart_type.lower() == "multi_field" and group_by_fields:
                calculation_result = calculator.calculate(data, value_type, group_by_fields=group_by_fields)
            else:
                calculation_result = calculator.calculate(data, value_type)

        # 关闭连接
        connection.close()

        # 构建结果
        result = {
            "chart_type": chart_type,
            "table": table_name,
            "value_type": value_type,
            "time_range": {
                "start": start_index if start_index else "全部",
                "end": last_index if last_index else "全部"
            },
            "data_count": len(data),
            "result": calculation_result
        }

        return f"[{chart_type}{json.dumps(result, ensure_ascii=False)}]"

    except Exception as e:
        # 确保任何异常情况下都能关闭连接
        if 'connection' in locals():
            connection.close()

        error_result = {
            "error": str(e),
            "chart_type": chart_type,
            "table": table_name,
            "value_type": value_type,
            "time_range": {
                "start": start_index if start_index else "全部",
                "end": last_index if last_index else "全部"
            }
        }

        return json.dumps(error_result, ensure_ascii=False)