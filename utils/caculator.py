import json
import pymongo
from datetime import datetime
import numpy as np
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Union, Optional


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
            if any(date_keyword in field.lower() for date_keyword in ['日期', 'date', '时间', 'time']):
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
                if any(date_keyword in field.lower() for date_keyword in ['日期', 'date', '时间', 'time']):
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
            "x_labels": x_values,
            "y_labels": y_values,
            "x_field": x_field,
            "y_field": y_field,
            "matrix": matrix.tolist(),
            "max_value": float(np.max(matrix)),
            "min_value": float(np.min(matrix))
        }

        return result


class ChartCalculatorFactory:
    """图表计算器工厂类"""

    @staticmethod
    def create_calculator(chart_type: str) -> ChartCalculator:
        """创建对应类型的计算器"""
        calculator_map = {
            "bar": BarChartCalculator,
            "line": LineChartCalculator,
            "pie": PieChartCalculator,
            "scatter": ScatterChartCalculator,
            "heatmap": HeatMapCalculator
        }

        calculator_class = calculator_map.get(chart_type.lower())
        if not calculator_class:
            raise ValueError(f"不支持的图表类型: {chart_type}")

        return calculator_class()


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


def query_data(db, collection_name: str,
               start_index: Optional[str] = None, last_index: Optional[str] = None,
               date_field: str = "日期") -> List[Dict[str, Any]]:
    """查询指定集合中的数据，支持可选的日期范围筛选"""
    collection = db[collection_name]

    # 构建查询条件
    query = {}
    if start_index and last_index:
        query[date_field] = {
            "$gte": start_index,
            "$lte": last_index
        }

    # 执行查询
    cursor = collection.find(query)

    # 转换为列表并删除MongoDB的_id字段(因为它不能被直接序列化为JSON)
    result = []
    for doc in cursor:
        if '_id' in doc:
            doc['_id'] = str(doc['_id'])
        result.append(doc)

    return result


def query_and_calculate(start_index: Optional[str] = None, last_index: Optional[str] = None,
                       value_type: str = None, coll_info: str = None, chart_type: str = None) -> str:
    """
    根据配置连接数据库，查询指定范围(可选)数据，并根据图表类型进行计算

    参数:
    - start_index: 可选的起始索引(日期等)
    - last_index: 可选的结束索引
    - value_type: 要分析的数据字段
    - coll_info: 集合(表)名称
    - chart_type: 图表类型

    返回:
    - JSON格式的计算结果
    """
    try:
        # 读取配置文件
        with open("config.json", "r", encoding="utf-8") as f:
            db_info = json.load(f)

        # 连接数据库
        db = connect_to_database(db_info)

        # 查询数据
        data = query_data(db, coll_info, start_index, last_index)

        # 创建对应的图表计算器
        calculator = ChartCalculatorFactory.create_calculator(chart_type)

        # 计算结果
        calculation_result = calculator.calculate(data, value_type)

        # 添加元数据
        result = {
            "chart_type": chart_type,
            "collection": coll_info,
            "value_type": value_type,
            "time_range": {
                "start": start_index if start_index else "全部",
                "end": last_index if last_index else "全部"
            },
            "data_count": len(data),
            "result": calculation_result
        }

        # 将结果转换为JSON字符串并返回
        return json.dumps(result, ensure_ascii=False)

    except Exception as e:
        error_result = {
            "error": str(e),
            "chart_type": chart_type,
            "collection": coll_info,
            "value_type": value_type,
            "time_range": {
                "start": start_index if start_index else "全部",
                "end": last_index if last_index else "全部"
            }
        }
        return json.dumps(error_result, ensure_ascii=False)