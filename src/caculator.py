import json
import os
import sys
import pymongo
import numpy as np
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Union, Optional, Tuple
from utils.data_helper import enrich_data_with_relations, group_and_aggregate, calculate_derived_metrics
from utils.logger import logger


def get_base_path():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../Users/Balte'))


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


def connect_to_database(db_info: Dict[str, Any]) -> pymongo.MongoClient:
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


def query_data(db, collection_name: str,
               start_index: Optional[str] = None, last_index: Optional[str] = None,
               date_field: str = "日期") -> List[Dict[str, Any]]:
    collection = db[collection_name]

    query = {}
    if start_index and last_index:
        query[date_field] = {
            "$gte": start_index,
            "$lte": last_index
        }

    cursor = collection.find(query)

    result = []
    for doc in cursor:
        if '_id' in doc:
            doc['_id'] = str(doc['_id'])
        result.append(doc)

    return result


def query_data_from_collections(connection, x_collection, y_collection, x_field, y_field,
                           x_index_field=None, x_start_index=None, x_end_index=None,
                           y_index_field=None, y_start_index=None, y_end_index=None):
    """
    从两个集合中查询数据并合并结果，支持对两集合分别应用过滤条件

    参数:
    - connection: 数据库连接
    - x_collection: X轴字段所在的集合
    - y_collection: Y轴字段所在的集合
    - x_field: X轴字段名
    - y_field: Y轴字段名
    - x_index_field: X集合的索引/过滤字段
    - x_start_index: X集合索引字段的起始值
    - x_end_index: X集合索引字段的结束值
    - y_index_field: Y集合的索引/过滤字段
    - y_start_index: Y集合索引字段的起始值
    - y_end_index: Y集合索引字段的结束值

    返回:
    - 包含两个集合中字段的数据列表
    """
    try:
        # 检查两个集合是否相同
        if x_collection == y_collection:
            # 如果在同一个集合，直接查询
            query = {}
            
            # X的过滤条件
            if x_index_field and x_start_index and x_end_index:
                query[x_index_field] = {"$gte": x_start_index, "$lte": x_end_index}
            elif x_index_field and x_start_index:
                query[x_index_field] = {"$gte": x_start_index}
            elif x_index_field and x_end_index:
                query[x_index_field] = {"$lte": x_end_index}
                
            # Y的过滤条件（如果与X不同）
            if y_index_field and y_index_field != x_index_field:
                if y_start_index and y_end_index:
                    query[y_index_field] = {"$gte": y_start_index, "$lte": y_end_index}
                elif y_start_index:
                    query[y_index_field] = {"$gte": y_start_index}
                elif y_end_index:
                    query[y_index_field] = {"$lte": y_end_index}
            
            # 执行查询
            collection = connection[x_collection]
            cursor = collection.find(query)
            
            # 转换为列表并处理_id
            result = []
            for doc in cursor:
                if '_id' in doc:
                    doc['_id'] = str(doc['_id'])
                result.append(doc)
                
            return result
        else:
            # 如果在不同集合，需要分别查询并在应用层合并
            # 查询X集合
            x_query = {}
            if x_index_field:
                if x_start_index and x_end_index:
                    x_query[x_index_field] = {"$gte": x_start_index, "$lte": x_end_index}
                elif x_start_index:
                    x_query[x_index_field] = {"$gte": x_start_index}
                elif x_end_index:
                    x_query[x_index_field] = {"$lte": x_end_index}
            
            x_collection_obj = connection[x_collection]
            x_cursor = x_collection_obj.find(x_query)
            x_data = []
            for doc in x_cursor:
                if '_id' in doc:
                    doc['_id'] = str(doc['_id'])
                x_data.append(doc)
                
            # 查询Y集合
            y_query = {}
            if y_index_field:
                if y_start_index and y_end_index:
                    y_query[y_index_field] = {"$gte": y_start_index, "$lte": y_end_index}
                elif y_start_index:
                    y_query[y_index_field] = {"$gte": y_start_index}
                elif y_end_index:
                    y_query[y_index_field] = {"$lte": y_end_index}
                    
            y_collection_obj = connection[y_collection]
            y_cursor = y_collection_obj.find(y_query)
            y_data = []
            for doc in y_cursor:
                if '_id' in doc:
                    doc['_id'] = str(doc['_id'])
                y_data.append(doc)
                
            # 尝试寻找共同字段进行关联
            common_fields = set()
            if x_data and y_data:
                x_fields = set(x_data[0].keys())
                y_fields = set(y_data[0].keys())
                common_fields = x_fields.intersection(y_fields)
                
            # 如果有共同字段，尝试使用它们进行关联
            if common_fields:
                join_field = next((f for f in common_fields 
                                 if f != '_id' and any(keyword in f.lower() 
                                                     for keyword in ['id', 'key', 'code', 'name'])), None)
                
                if join_field:
                    # 根据共同字段合并数据
                    combined_data = []
                    x_dict = {doc[join_field]: doc for doc in x_data if join_field in doc}
                    
                    for y_doc in y_data:
                        if join_field in y_doc and y_doc[join_field] in x_dict:
                            merged_doc = {}
                            merged_doc.update(x_dict[y_doc[join_field]])
                            
                            # 避免字段冲突
                            for k, v in y_doc.items():
                                if k != join_field and k in merged_doc:
                                    merged_doc[f"{y_collection}_{k}"] = v
                                else:
                                    merged_doc[k] = v
                                    
                            combined_data.append(merged_doc)
                            
                    return combined_data
            
            # 如果没有合适的关联字段，创建笛卡尔积
            combined_data = []
            for x_doc in x_data:
                for y_doc in y_data:
                    merged_doc = {}
                    merged_doc.update(x_doc)
                    
                    # 避免字段冲突
                    for k, v in y_doc.items():
                        if k in merged_doc and k != y_field:
                            merged_doc[f"{y_collection}_{k}"] = v
                        else:
                            merged_doc[k] = v
                            
                    combined_data.append(merged_doc)
                    
            return combined_data
            
    except Exception as e:
        logger.error(f"查询数据时出错: {e}")
        return []


def load_db_config():
    """加载数据库配置"""
    try:
        config_path = os.path.join(get_base_path(), 'data', 'config.json')
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"加载数据库配置失败: {e}")
        return {}


def query_and_calculate(
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
    根据配置连接MongoDB数据库，查询指定范围(可选)数据，并根据图表类型进行计算

    参数:
    - x_field: X轴字段名
    - y_field: Y轴字段名
    - x_table: X轴字段所在的集合名
    - y_table: Y轴字段所在的集合名
    - x_index_field: X集合的索引/过滤字段
    - x_start_index: X集合索引字段的起始值
    - x_end_index: X集合索引字段的结束值
    - y_index_field: Y集合的索引/过滤字段
    - y_start_index: Y集合索引字段的起始值
    - y_end_index: Y集合索引字段的结束值
    - chart_type: 图表类型，默认为柱状图
    - limit: 排名分析时返回的最大数量，默认为5
    - ascending: 排序方向，True为升序，False为降序

    返回:
    - JSON格式的计算结果
    """

    logger.info(
        f"开始查询MongoDB数据: X表={x_table}, X字段={x_field}, Y表={y_table}, Y字段={y_field}, "
        f"X索引字段={x_index_field}, X起始={x_start_index}, X结束={x_end_index}, "
        f"Y索引字段={y_index_field}, Y起始={y_start_index}, Y结束={y_end_index}, "
        f"图表类型: {chart_type}")

    try:
        # 加载数据库配置
        db_info = load_db_config()
        logger.info(f"数据库配置: {db_info}")

        # 连接到MongoDB数据库
        logger.info("尝试连接MongoDB数据库...")
        connection = connect_to_database(db_info)
        logger.info(f"成功连接到MongoDB数据库: {db_info.get('host')}:{db_info.get('port')}")

        # 查询数据
        logger.info(f"查询集合 {x_table} 和 {y_table} 的数据...")
        data = query_data_from_collections(
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

    # 柱状图示例 - 分析不同组别的人数
    result = query_and_calculate(
        x_field="jlugroup",  # X轴字段名 - 组别
        y_field="ID",  # Y轴字段名 - 使用ID进行计数
        x_table="Data",  # X轴字段所在的集合名
        y_table="Data",  # Y轴字段所在的集合名
        x_index_field="school",  # X集合的索引/过滤字段 - 根据校区筛选
        x_start_index="南湖校区",  # X集合索引字段的起始值
        x_end_index="南湖校区",  # X集合索引字段的结束值
        y_index_field="identity",  # Y集合的索引/过滤字段 - 根据身份筛选
        y_start_index="正式队员",  # Y集合索引字段的起始值
        y_end_index="正式队员",  # Y集合索引字段的结束值
        chart_type="bar"  # 图表类型 - 生成柱状图
    )

    print(result)