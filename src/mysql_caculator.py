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
                  y_table: str, series_field: str = None) -> Dict[str, Any]:
        """
        计算条形图所需的数据，支持多系列

        参数:
        - data: 原始数据列表
        - x_field: X轴分类字段
        - y_field: Y轴数值字段
        - x_table: X表名
        - y_table: Y表名
        - series_field: 可选的系列分组字段，用于多系列柱状图

        返回:
        - 条形图数据，可能包含多个系列
        """
        result = {}

        if not data:
            return {
                "chart_type": "bar",
                "xAxisData": [],
                "barData": [],
                "series": [],
                "statistics": {"mean": 0, "median": 0, "max": 0, "min": 0}
            }

        # 获取所有X轴分类值
        categories = list(set(item.get(x_field) for item in data if x_field in item and item.get(x_field) is not None))
        categories.sort()

        # 检查是否使用多系列模式
        if series_field and any(series_field in item for item in data):
            # 多系列模式: 按series_field分组
            series_values = list(set(item.get(series_field) for item in data
                                     if series_field in item and item.get(series_field) is not None))
            series_values.sort()

            # 初始化多系列数据
            series_data = []
            for series_value in series_values:
                series_data.append({
                    "name": series_value,
                    "data": [0] * len(categories)
                })

            # 计算每个系列每个分类的值
            for item in data:
                if x_field in item and series_field in item:
                    if item[x_field] in categories and item[series_field] in series_values:
                        cat_index = categories.index(item[x_field])
                        series_index = series_values.index(item[series_field])

                        # 累加或更新值
                        if y_field in item:
                            if isinstance(item[y_field], (int, float)):
                                series_data[series_index]["data"][cat_index] += item[y_field]
                            else:
                                # 如果不是数值，计数加1
                                series_data[series_index]["data"][cat_index] += 1

            # 计算统计信息
            statistics = {}
            for series in series_data:
                values = series["data"]
                if values:
                    statistics[series["name"]] = {
                        "mean": np.mean(values),
                        "max": max(values),
                        "min": min(values),
                        "sum": sum(values)
                    }

            result = {
                "chart_type": "bar",
                "xAxisData": categories,
                "series": series_data,
                "seriesNames": series_values,
                "statistics": statistics,
                "title": f"{x_table}.{x_field} 按 {series_field} 分组"
            }
        else:
            # 单系列模式: 使用_series_index或_series_field标记处理多个Y字段
            if any('_series_index' in item for item in data) or any('_series_field' in item for item in data):
                # 识别来自不同Y字段的数据并按系列分组
                series_indices = set()
                series_fields = set()

                for item in data:
                    if '_series_index' in item:
                        series_indices.add(item['_series_index'])
                    if '_series_field' in item:
                        series_fields.add(item['_series_field'])

                # 优先使用_series_field作为系列名称
                if series_fields:
                    # 按_series_field标识系列
                    series_values = sorted(list(series_fields))

                    # 初始化系列数据
                    series_data = []
                    for series_value in series_values:
                        series_data.append({
                            "name": series_value,
                            "data": [0] * len(categories)
                        })

                    # 处理数据
                    for item in data:
                        if x_field in item and '_series_field' in item and item['_series_field'] in series_values:
                            if item[x_field] in categories:
                                cat_index = categories.index(item[x_field])
                                series_index = series_values.index(item['_series_field'])

                                # 对应的Y字段应该是item中的_series_field值
                                y_field_name = item['_series_field']

                                if y_field_name in item and isinstance(item[y_field_name], (int, float)):
                                    series_data[series_index]["data"][cat_index] += item[y_field_name]
                                else:
                                    # 如果找不到对应的值字段或非数值，则计数+1
                                    series_data[series_index]["data"][cat_index] += 1
                else:
                    # 按_series_index标识系列
                    series_values = sorted(list(series_indices))

                    # 初始化系列数据
                    series_data = []
                    for idx in series_values:
                        series_data.append({
                            "name": f"系列 {idx + 1}",
                            "data": [0] * len(categories)
                        })

                    # 处理数据
                    for item in data:
                        if x_field in item and '_series_index' in item and item['_series_index'] in series_values:
                            if item[x_field] in categories:
                                cat_index = categories.index(item[x_field])
                                series_index = series_values.index(item['_series_index'])

                                if y_field in item:
                                    if isinstance(item[y_field], (int, float)):
                                        series_data[series_index]["data"][cat_index] += item[y_field]
                                    else:
                                        # 如果不是数值，计数加1
                                        series_data[series_index]["data"][cat_index] += 1

                # 计算统计信息
                statistics = {}
                for series in series_data:
                    values = series["data"]
                    if values:
                        statistics[series["name"]] = {
                            "mean": np.mean(values),
                            "max": max(values),
                            "min": min(values),
                            "sum": sum(values)
                        }

                result = {
                    "chart_type": "bar",
                    "xAxisData": categories,
                    "series": series_data,
                    "seriesNames": [s["name"] for s in series_data],
                    "statistics": statistics,
                    "title": f"{x_table}.{x_field} 多系列分析"
                }
            else:
                # 常规单系列处理
                values = []

                # 根据x_field进行分组计算
                value_counts = {}
                for item in data:
                    if x_field in item:
                        category = item[x_field]
                        if category not in value_counts:
                            value_counts[category] = 0

                        if y_field in item and isinstance(item[y_field], (int, float)):
                            value_counts[category] += item[y_field]
                        else:
                            value_counts[category] += 1

                for category in categories:
                    values.append(value_counts.get(category, 0))

                # 计算统计数据
                statistics = {
                    "mean": np.mean(values) if values else 0,
                    "median": np.median(values) if values else 0,
                    "max": max(values) if values else 0,
                    "min": min(values) if values else 0
                }

                result = {
                    "chart_type": "bar",
                    "xAxisData": categories,
                    "barData": values,
                    "series": [{
                        "name": y_field,
                        "data": values
                    }],
                    "seriesNames": [y_field],
                    "statistics": statistics,
                    "title": f"{x_table}.{x_field} - {y_table}.{y_field} 分析"
                }

        return result


class LineChartCalculator(ChartCalculator):
    def calculate(self, data: List[Dict[str, Any]], x_field: str, y_field: str, x_table: str,
                  y_table: str, series_field: str = None) -> Dict[str, Any]:
        """
        计算折线图所需的数据，支持多系列

        参数:
        - data: 原始数据列表
        - x_field: X轴字段（通常是时间或序列字段）
        - y_field: Y轴数值字段
        - x_table: X表名
        - y_table: Y表名
        - series_field: 可选的系列分组字段，用于多系列折线图

        返回:
        - 折线图数据，可能包含多个系列
        """
        if not data:
            return {
                "chart_type": "line",
                "data": [],
                "xAxisLabels": [],
                "series": [],
                "title": f"{x_field}-{y_field}"
            }

        # 获取所有X轴的值并排序
        # 在计算日期值时添加NULL值检查
        x_values = list(set(str(item.get(x_field, '')) for item in data if x_field in item and item.get(x_field) is not None))
        x_values.sort()

        # 检查是否使用多系列模式
        if series_field and any(series_field in item for item in data):
            # 多系列模式: 按series_field分组
            series_values = list(set(item.get(series_field) for item in data if series_field in item and item.get(series_field) is not None))
            series_values.sort()

            # 初始化系列数据
            series_data = []
            for series_value in series_values:
                series_data.append({
                    "name": series_value,
                    "data": [0] * len(x_values)
                })

            # 为每个系列每个X值计算Y值
            for i, series_value in enumerate(series_values):
                for j, x_value in enumerate(x_values):
                    # 过滤出属于当前系列和X值的数据
                    matching_items = [
                        item for item in data
                        if series_field in item and item[series_field] == series_value
                           and x_field in item and str(item[x_field]) == x_value
                    ]

                    # 如果有匹配的数据，计算值
                    if matching_items:
                        valid_items = [item for item in matching_items if y_field in item]
                        if valid_items:
                            if all(isinstance(item[y_field], (int, float)) for item in valid_items):
                                # 如果都是数值，计算总和
                                series_data[i]["data"][j] = sum(item[y_field] for item in valid_items)
                            else:
                                # 否则计数
                                series_data[i]["data"][j] = len(valid_items)

            result = {
                "chart_type": "line",
                "xAxisLabels": x_values,
                "series": series_data,
                "title": f"{x_table}.{x_field} 按 {series_field} 分组"
            }
        else:
            # 检查是否有_series_index或_series_field标记的多系列数据
            if any('_series_index' in item for item in data) or any('_series_field' in item for item in data):
                # 识别来自不同Y字段的数据并按系列分组
                series_indices = set()
                series_fields = set()

                for item in data:
                    if '_series_index' in item:
                        series_indices.add(item['_series_index'])
                    if '_series_field' in item:
                        series_fields.add(item['_series_field'])

                # 优先使用_series_field作为系列名称
                if series_fields:
                    # 按_series_field标识系列
                    series_values = sorted(list(series_fields))

                    # 初始化系列数据
                    series_data = []
                    for series_value in series_values:
                        series_data.append({
                            "name": series_value,
                            "data": [0] * len(x_values)
                        })

                    # 处理数据
                    for item in data:
                        if x_field in item and '_series_field' in item and item['_series_field'] in series_values:
                            x_val = str(item[x_field])
                            if x_val in x_values:
                                x_index = x_values.index(x_val)
                                series_index = series_values.index(item['_series_field'])

                                # 对应的Y字段应该是item中的_series_field值
                                y_field_name = item['_series_field']

                                if y_field_name in item and isinstance(item[y_field_name], (int, float)):
                                    series_data[series_index]["data"][x_index] += item[y_field_name]
                                else:
                                    # 如果找不到对应的值字段或非数值，则计数+1
                                    series_data[series_index]["data"][x_index] += 1
                else:
                    # 按_series_index标识系列
                    series_values = sorted(list(series_indices))

                    # 初始化系列数据
                    series_data = []
                    for idx in series_values:
                        series_data.append({
                            "name": f"系列 {idx + 1}",
                            "data": [0] * len(x_values)
                        })

                    # 处理数据
                    for item in data:
                        if x_field in item and '_series_index' in item and item['_series_index'] in series_values:
                            x_val = str(item[x_field])
                            if x_val in x_values:
                                x_index = x_values.index(x_val)
                                series_index = series_values.index(item['_series_index'])

                                if y_field in item:
                                    if isinstance(item[y_field], (int, float)):
                                        series_data[series_index]["data"][x_index] += item[y_field]
                                    else:
                                        # 如果不是数值，计数加1
                                        series_data[series_index]["data"][x_index] += 1

                result = {
                    "chart_type": "line",
                    "xAxisLabels": x_values,
                    "series": series_data,
                    "title": f"{x_table}.{x_field} 多系列趋势"
                }
            else:
                # 常规单系列处理
                # 按日期排序数据
                sorted_data = sorted(data, key=lambda x: x.get(x_field, ''))

                # 根据y_field进行时间序列统计
                date_counts = {}
                for item in sorted_data:
                    if x_field in item and y_field in item:
                        date = str(item.get(x_field, ''))
                        if date not in date_counts:
                            date_counts[date] = 0
                        if isinstance(item[y_field], (int, float)):  # 如果值是数字
                            date_counts[date] += item[y_field]
                        else:  # 否则计数
                            date_counts[date] += 1

                # 确保按排序后的x_values顺序获取数据
                time_series = x_values
                values = [date_counts.get(date, 0) for date in time_series]

                result = {
                    "chart_type": "line",
                    "data": values,
                    "xAxisLabels": time_series,
                    "series": [{
                        "name": y_field,
                        "data": values
                    }],
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
                  y_table: str, series_field: str = None) -> Dict[str, Any]:
        """
        计算散点图所需的数据，支持多系列

        参数:
        - data: 原始数据列表
        - x_field: X轴字段
        - y_field: Y轴字段
        - x_table: X表名
        - y_table: Y表名
        - series_field: 可选的系列分组字段，用于多系列散点图

        返回:
        - 散点图数据，可能包含多个系列
        """
        result = {}

        if not data:
            return {
                "chart_type": "scatter",
                "x": [],
                "y": [],
                "series": [],
                "x_field": x_field,
                "y_field": y_field,
                "correlation": 0,
                "regression": {
                    "slope": 0,
                    "intercept": 0,
                    "line": []
                }
            }

        # 检查是否使用多系列模式
        if series_field and any(series_field in item for item in data):
            # 多系列模式: 按series_field分组
            series_values = list(set(item.get(series_field) for item in data
                                     if series_field in item and item.get(series_field) is not None))
            series_values.sort()

            series_data = []
            correlations = {}
            regressions = {}

            for series_value in series_values:
                # 过滤出当前系列的数据
                series_items = [item for item in data if series_field in item and item[series_field] == series_value]

                x_values = []
                y_values = []

                # 提取数据点
                for item in series_items:
                    if y_field in item and x_field in item:
                        try:
                            x_val = float(item[x_field]) if not isinstance(item[x_field], (int, float)) else item[
                                x_field]
                            y_val = float(item[y_field]) if not isinstance(item[y_field], (int, float)) else item[
                                y_field]
                            x_values.append(x_val)
                            y_values.append(y_val)
                        except (ValueError, TypeError):
                            continue

                # 计算相关系数和回归线
                correlation = 0
                slope = 0
                intercept = 0
                regression_line = []

                if len(x_values) > 1:
                    correlation = np.corrcoef(x_values, y_values)[0, 1] if len(set(x_values)) > 1 and len(
                        set(y_values)) > 1 else 0

                    # 线性回归
                    z = np.polyfit(x_values, y_values, 1) if len(set(x_values)) > 1 else [0, 0]
                    slope = z[0]
                    intercept = z[1]

                    # 回归线上的点
                    regression_line = [slope * x + intercept for x in x_values]

                # 保存系列数据
                series_data.append({
                    "name": series_value,
                    "x": x_values,
                    "y": y_values,
                    "data": list(zip(x_values, y_values))
                })

                # 保存系列统计数据
                correlations[series_value] = float(correlation) if not np.isnan(correlation) else 0
                regressions[series_value] = {
                    "slope": float(slope),
                    "intercept": float(intercept),
                    "line": regression_line
                }

            result = {
                "chart_type": "scatter",
                "series": series_data,
                "x_field": x_field,
                "y_field": y_field,
                "correlations": correlations,
                "regressions": regressions,
                "series_field": series_field
            }
        else:
            # 检查是否有_series_index或_series_field标记的多系列数据
            if any('_series_index' in item for item in data) or any('_series_field' in item for item in data):
                # 识别来自不同Y字段的数据并按系列分组
                series_indices = set()
                series_fields = set()

                for item in data:
                    if '_series_index' in item:
                        series_indices.add(item['_series_index'])
                    if '_series_field' in item:
                        series_fields.add(item['_series_field'])

                series_data = []
                correlations = {}
                regressions = {}

                # 优先使用_series_field作为系列名称
                if series_fields:
                    # 按_series_field标识系列
                    series_values = sorted(list(series_fields))

                    for series_value in series_values:
                        # 过滤出当前系列的数据
                        series_items = [item for item in data if
                                        '_series_field' in item and item['_series_field'] == series_value]

                        x_values = []
                        y_values = []

                        # 提取数据点
                        for item in series_items:
                            if x_field in item:
                                try:
                                    x_val = float(item[x_field]) if not isinstance(item[x_field], (int, float)) else \
                                    item[x_field]

                                    # 使用该系列对应的y字段名
                                    y_field_name = item['_series_field']
                                    if y_field_name in item:
                                        y_val = float(item[y_field_name]) if not isinstance(item[y_field_name],
                                                                                            (int, float)) else item[
                                            y_field_name]
                                        x_values.append(x_val)
                                        y_values.append(y_val)
                                except (ValueError, TypeError):
                                    continue

                        # 计算统计数据和保存系列
                        self._process_scatter_series(
                            series_data, correlations, regressions,
                            series_value, x_values, y_values
                        )
                else:
                    # 按_series_index标识系列
                    series_values = sorted(list(series_indices))

                    for series_idx in series_values:
                        # 过滤出当前系列的数据
                        series_items = [item for item in data if
                                        '_series_index' in item and item['_series_index'] == series_idx]

                        x_values = []
                        y_values = []

                        # 提取数据点
                        for item in series_items:
                            if x_field in item and y_field in item:
                                try:
                                    x_val = float(item[x_field]) if not isinstance(item[x_field], (int, float)) else \
                                    item[x_field]
                                    y_val = float(item[y_field]) if not isinstance(item[y_field], (int, float)) else \
                                    item[y_field]
                                    x_values.append(x_val)
                                    y_values.append(y_val)
                                except (ValueError, TypeError):
                                    continue

                        # 使用系列索引作为名称
                        series_name = f"系列 {series_idx + 1}"

                        # 计算统计数据和保存系列
                        self._process_scatter_series(
                            series_data, correlations, regressions,
                            series_name, x_values, y_values
                        )

                result = {
                    "chart_type": "scatter",
                    "series": series_data,
                    "x_field": x_field,
                    "y_field": y_field,
                    "correlations": correlations,
                    "regressions": regressions
                }
            else:
                # 常规单系列处理
                x_values = []
                y_values = []

                # 提取数据点
                for item in data:
                    if y_field in item and x_field in item:
                        try:
                            x_val = float(item[x_field]) if not isinstance(item[x_field], (int, float)) else item[
                                x_field]
                            y_val = float(item[y_field]) if not isinstance(item[y_field], (int, float)) else item[
                                y_field]
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
                    "series": [{
                        "name": y_field,
                        "x": x_values,
                        "y": y_values,
                        "data": list(zip(x_values, y_values))
                    }],
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

    def _process_scatter_series(self, series_data, correlations, regressions,
                                series_name, x_values, y_values):
        """辅助方法：计算散点图系列的统计数据并添加到结果中"""
        # 计算相关系数和回归线
        correlation = 0
        slope = 0
        intercept = 0
        regression_line = []

        if len(x_values) > 1:
            correlation = np.corrcoef(x_values, y_values)[0, 1] if len(set(x_values)) > 1 and len(
                set(y_values)) > 1 else 0

            # 线性回归
            z = np.polyfit(x_values, y_values, 1) if len(set(x_values)) > 1 else [0, 0]
            slope = z[0]
            intercept = z[1]

            # 回归线上的点
            regression_line = [slope * x + intercept for x in x_values]

        # 保存系列数据
        series_data.append({
            "name": series_name,
            "x": x_values,
            "y": y_values,
            "data": list(zip(x_values, y_values))
        })

        # 保存系列统计数据
        correlations[series_name] = float(correlation) if not np.isnan(correlation) else 0
        regressions[series_name] = {
            "slope": float(slope),
            "intercept": float(intercept),
            "line": regression_line
        }


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


# class YoYMoMCalculator(ChartCalculator):
#     """同比环比计算器"""
#
#     def calculate(self, data: List[Dict[str, Any]], x_field: str, y_field: str, x_table: str,
#                   y_table: str) -> Dict[str, Any]:
#         """计算同比环比数据"""
#         if not data:
#             return {
#                 "chart_type": "yoy_mom",
#                 "current_period": {},
#                 "previous_period": {},
#                 "previous_year": {},
#                 "mom_change": {},
#                 "yoy_change": {}
#             }
#
#         result = {}
#
#         # 解析日期并提取年月信息
#         date_data = {}
#         for item in data:
#             if x_field in item and y_field in item:
#                 date_str = item[x_field]
#                 try:
#                     # 处理不同的日期格式
#                     if 'T' in date_str:  # ISO格式 (2023-04-16T12:30:45)
#                         date_str = date_str.split('T')[0]
#
#                     # 假设日期格式为 YYYY-MM-DD
#                     parts = date_str.split('-')
#                     if len(parts) >= 2:
#                         year_month = f"{parts[0]}-{parts[1]}"
#                         year = parts[0]
#                         month = parts[1]
#
#                         # 对每个年月进行数据聚合
#                         if year_month not in date_data:
#                             date_data[year_month] = {
#                                 "year": year,
#                                 "month": month,
#                                 "count": 0,
#                                 "sum": 0,
#                                 "values": []
#                             }
#
#                         # 根据值类型进行聚合
#                         if isinstance(item[y_field], (int, float)):
#                             date_data[year_month]["sum"] += item[y_field]
#                             date_data[year_month]["values"].append(item[y_field])
#                         else:
#                             date_data[year_month]["count"] += 1
#                 except Exception:
#                     continue
#
#         # 按年月排序
#         sorted_year_months = sorted(date_data.keys())
#
#         if not sorted_year_months:
#             return {
#                 "chart_type": "yoy_mom",
#                 "error": "无有效数据点"
#             }
#
#         # 计算当前期间、上期和去年同期
#         current_period = sorted_year_months[-1]
#         current_data = date_data[current_period]
#
#         # 环比(MoM): 与上个月比较
#         mom_period = None
#         mom_data = {}
#         mom_change = {}
#         if len(sorted_year_months) > 1:
#             mom_period = sorted_year_months[-2]
#             mom_data = date_data[mom_period]
#
#             # 计算环比变化
#             current_value = current_data["sum"] if current_data["sum"] > 0 else current_data["count"]
#             mom_value = mom_data["sum"] if mom_data["sum"] > 0 else mom_data["count"]
#
#             if mom_value != 0:
#                 mom_change = {
#                     "absolute": current_value - mom_value,
#                     "percentage": round(((current_value - mom_value) / mom_value) * 100, 2)
#                 }
#             else:
#                 mom_change = {"absolute": current_value, "percentage": 100}
#
#         # 同比(YoY): 与去年同月比较
#         current_year, current_month = current_data["year"], current_data["month"]
#         previous_year = str(int(current_year) - 1)
#         yoy_period = f"{previous_year}-{current_month}"
#         yoy_data = {}
#         yoy_change = {}
#
#         if yoy_period in date_data:
#             yoy_data = date_data[yoy_period]
#
#             # 计算同比变化
#             current_value = current_data["sum"] if current_data["sum"] > 0 else current_data["count"]
#             yoy_value = yoy_data["sum"] if yoy_data["sum"] > 0 else yoy_data["count"]
#
#             if yoy_value != 0:
#                 yoy_change = {
#                     "absolute": current_value - yoy_value,
#                     "percentage": round(((current_value - yoy_value) / yoy_value) * 100, 2)
#                 }
#             else:
#                 yoy_change = {"absolute": current_value, "percentage": 100}
#
#         result = {
#             "chart_type": "yoy_mom",
#             "current_period": {
#                 "period": current_period,
#                 "value": current_data["sum"] if current_data["sum"] > 0 else current_data["count"],
#                 "avg": np.mean(current_data["values"]) if current_data["values"] else current_data["count"]
#             },
#             "previous_period": {
#                 "period": mom_period,
#                 "value": mom_data.get("sum", 0) if mom_data.get("sum", 0) > 0 else mom_data.get("count", 0)
#             },
#             "previous_year": {
#                 "period": yoy_period,
#                 "value": yoy_data.get("sum", 0) if yoy_data.get("sum", 0) > 0 else yoy_data.get("count", 0)
#             },
#             "mom_change": mom_change,
#             "yoy_change": yoy_change
#         }
#
#         return result


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
            # "yoy_mom": YoYMoMCalculator,
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
        y_field: Union[str, List[str]],  # 可以是单个字段名或字段名列表
        x_table: str,
        y_table: Union[str, List[str]],  # 可以是单个表名或表名列表
        x_index_field: Optional[str] = None,
        x_start_index: Optional[str] = None,
        x_end_index: Optional[str] = None,
        y_index_field: Union[str, List[str], None] = None,  # 可以是单个索引字段或索引字段列表
        y_start_index: Union[str, List[str], None] = None,  # 可以是单个起始值或起始值列表
        y_end_index: Union[str, List[str], None] = None,  # 可以是单个结束值或结束值列表
        chart_type: str = "bar",
        limit: int = 5,
        ascending: bool = False,
        # 其他参数
        series_field: Optional[str] = None,
        z_field: Optional[str] = None,
        color_field: Optional[str] = None,
        value_fields: Optional[List[str]] = None,
        entity_field: Optional[str] = None
) -> str:
    """
    根据配置连接MySQL数据库，查询指定范围(可选)数据，并根据图表类型进行计算
    支持多系列图表(柱状图、折线图、散点图)的不定数量Y系列

    参数:
    - x_field: X轴字段名
    - y_field: Y轴字段名或字段名列表
    - x_table: X轴字段所在的表名
    - y_table: Y轴字段所在的表名或表名列表
    - x_index_field: X表的索引/过滤字段
    - x_start_index: X表索引字段的起始值
    - x_end_index: X表索引字段的结束值
    - y_index_field: Y表的索引/过滤字段或字段列表
    - y_start_index: Y表索引字段的起始值或值列表
    - y_end_index: Y表索引字段的结束值或值列表
    - chart_type: 图表类型
    - limit: 排名分析时返回的最大数量，默认为5
    - ascending: 排序方向，True为升序，False为降序
    - 其他参数

    返回:
    - JSON格式的计算结果
    """

    # 记录日志
    logger.info(
        f"开始查询MySQL数据: X表={x_table}, X字段={x_field}, Y表={y_table}, Y字段={y_field}, "
        f"图表类型: {chart_type}"
    )

    try:
        # 加载数据库配置
        db_info = load_db_config()
        logger.info(f"数据库配置: {db_info}")

        # 确保使用MySQL配置
        if "mysql" in db_info:
            mysql_info = db_info["mysql"]
        else:
            mysql_info = db_info

        # 连接到MySQL数据库
        logger.info("尝试连接MySQL数据库...")
        connection = connect_to_mysql(mysql_info)
        logger.info(f"成功连接到MySQL数据库: {mysql_info.get('host')}:{mysql_info.get('port')}")

        # 判断是否为需要多y系列的图表类型
        multi_series_chart_types = ["bar", "line", "scatter", "multi_series_bar", "multi_series_line"]
        is_multi_series_chart = chart_type.lower() in multi_series_chart_types

        # 如果是多系列图表且传入了y_field列表
        if is_multi_series_chart and isinstance(y_field, list) and len(y_field) > 0:
            # 标准化参数，确保所有y相关参数都是列表
            y_fields = y_field  # 已经是列表

            # 处理y_table，如果是字符串则转为等长的列表
            if isinstance(y_table, str):
                y_tables = [y_table] * len(y_fields)
            else:
                # 如果y_table是列表但长度不足，则用最后一个值填充
                if len(y_table) < len(y_fields):
                    y_tables = list(y_table) + [y_table[-1]] * (len(y_fields) - len(y_table))
                else:
                    y_tables = y_table

            # 处理y_index_field
            if y_index_field is None:
                y_index_fields = [None] * len(y_fields)
            elif isinstance(y_index_field, str):
                y_index_fields = [y_index_field] * len(y_fields)
            else:
                # 如果y_index_field是列表但长度不足，则用None填充
                if len(y_index_field) < len(y_fields):
                    y_index_fields = list(y_index_field) + [None] * (len(y_fields) - len(y_index_field))
                else:
                    y_index_fields = y_index_field

            # 处理y_start_index
            if y_start_index is None:
                y_start_indices = [None] * len(y_fields)
            elif isinstance(y_start_index, str):
                y_start_indices = [y_start_index] * len(y_fields)
            else:
                # 如果y_start_index是列表但长度不足，则用None填充
                if len(y_start_index) < len(y_fields):
                    y_start_indices = list(y_start_index) + [None] * (len(y_fields) - len(y_start_index))
                else:
                    y_start_indices = y_start_index

            # 处理y_end_index
            if y_end_index is None:
                y_end_indices = [None] * len(y_fields)
            elif isinstance(y_end_index, str):
                y_end_indices = [y_end_index] * len(y_fields)
            else:
                # 如果y_end_index是列表但长度不足，则用None填充
                if len(y_end_index) < len(y_fields):
                    y_end_indices = list(y_end_index) + [None] * (len(y_fields) - len(y_end_index))
                else:
                    y_end_indices = y_end_index

            # 查询每个y系列的数据并合并
            all_data = []
            for i, y_field_item in enumerate(y_fields):
                # 查询单个y系列的数据
                series_data = query_data_from_tables(
                    connection,
                    x_table, y_tables[i],
                    x_field, y_field_item,
                    x_index_field, x_start_index, x_end_index,
                    y_index_fields[i], y_start_indices[i], y_end_indices[i]
                )

                # 为数据添加系列标识
                for item in series_data:
                    item['_series_index'] = i
                    item['_series_field'] = y_field_item
                    item['_series_table'] = y_tables[i]

                all_data.extend(series_data)

            # 创建计算器
            calculator = ChartCalculatorFactory.create_calculator(chart_type)

            # 对于需要多系列处理的图表类型
            if chart_type.lower() in ["multi_series_bar", "multi_series_line"]:
                # 如果提供了series_field，则按该字段分组
                if series_field:
                    calculation_result = calculator.calculate(
                        all_data, x_field, y_fields[0], x_table, y_tables[0], series_field
                    )
                else:
                    # 否则使用y_field名称作为系列标识
                    # 转换数据格式为系列格式
                    series_data = []
                    for item in all_data:
                        series_idx = item.get('_series_index', 0)
                        if 0 <= series_idx < len(y_fields):
                            y_field_name = y_fields[series_idx]
                            if x_field in item and y_field_name in item:
                                series_item = {
                                    x_field: item[x_field],
                                    y_fields[0]: item[y_field_name],  # 统一使用第一个y_field作为值字段
                                    "_series": y_field_name  # 使用y_field名称作为系列标识
                                }
                                series_data.append(series_item)

                    calculation_result = calculator.calculate(
                        series_data, x_field, y_fields[0], x_table, y_tables[0], "_series"
                    )
            else:
                # 对于普通柱状图和折线图，自动转换为多系列形式
                # 转换为适合多系列展示的数据格式
                x_values = list(set(item[x_field] for item in all_data if x_field in item))
                x_values.sort()

                series_data = []
                for y_idx, y_field_name in enumerate(y_fields):
                    series_values = [0] * len(x_values)

                    # 过滤出当前系列的数据
                    current_series_data = [item for item in all_data if item.get('_series_index') == y_idx]

                    # 按x_field值分组
                    for x_idx, x_val in enumerate(x_values):
                        matching_items = [item for item in current_series_data
                                          if x_field in item and item[x_field] == x_val]

                        if matching_items:
                            # 汇总该x值对应的y值
                            valid_items = [item for item in matching_items if y_field_name in item]
                            if valid_items:
                                if all(isinstance(item[y_field_name], (int, float)) for item in valid_items):
                                    series_values[x_idx] = sum(item[y_field_name] for item in valid_items)
                                else:
                                    series_values[x_idx] = len(valid_items)

                    series_data.append({
                        "name": y_field_name,
                        "data": series_values
                    })

                # 构建适合图表类型的结果
                if chart_type.lower() == "bar":
                    calculation_result = {
                        "chart_type": "bar",
                        "xAxisData": x_values,
                        "series": series_data,
                        "title": f"{x_table}.{x_field} - 多系列分析"
                    }
                elif chart_type.lower() == "line":
                    calculation_result = {
                        "chart_type": "line",
                        "xAxisLabels": x_values,
                        "series": series_data,
                        "title": f"{x_table}.{x_field} - 多系列趋势"
                    }
                elif chart_type.lower() == "scatter":
                    # 散点图的处理略有不同
                    scatter_series = []
                    for y_idx, y_field_name in enumerate(y_fields):
                        # 过滤出当前系列的数据
                        current_series_data = [item for item in all_data if item.get('_series_index') == y_idx]

                        x_vals = []
                        y_vals = []

                        for item in current_series_data:
                            if x_field in item and y_field_name in item:
                                try:
                                    x_val = float(item[x_field]) if not isinstance(item[x_field], (int, float)) else \
                                    item[x_field]
                                    y_val = float(item[y_field_name]) if not isinstance(item[y_field_name],
                                                                                        (int, float)) else item[
                                        y_field_name]
                                    x_vals.append(x_val)
                                    y_vals.append(y_val)
                                except (ValueError, TypeError):
                                    continue

                        scatter_series.append({
                            "name": y_field_name,
                            "data": list(zip(x_vals, y_vals))
                        })

                    calculation_result = {
                        "chart_type": "scatter",
                        "series": scatter_series,
                        "x_field": x_field,
                        "y_fields": y_fields,
                        "title": f"{x_table}.{x_field} - 多系列散点分析"
                    }
        else:
            # 对于单y系列的图表或不支持多系列的图表类型，保持原始逻辑
            # 确保y_field是单个字符串
            if isinstance(y_field, list):
                primary_y_field = y_field[0] if y_field else None
            else:
                primary_y_field = y_field

            # 确保y_table是单个字符串
            if isinstance(y_table, list):
                primary_y_table = y_table[0] if y_table else x_table
            else:
                primary_y_table = y_table

            # 确保y索引参数是单个值
            primary_y_index_field = y_index_field[0] if isinstance(y_index_field,
                                                                   list) and y_index_field else y_index_field
            primary_y_start_index = y_start_index[0] if isinstance(y_start_index,
                                                                   list) and y_start_index else y_start_index
            primary_y_end_index = y_end_index[0] if isinstance(y_end_index, list) and y_end_index else y_end_index

            # 查询数据
            data = query_data_from_tables(
                connection,
                x_table, primary_y_table,
                x_field, primary_y_field,
                x_index_field, x_start_index, x_end_index,
                primary_y_index_field, primary_y_start_index, primary_y_end_index
            )

            # 根据图表类型执行计算
            calculator = ChartCalculatorFactory.create_calculator(chart_type)

            if chart_type.lower() == "3d_scatter":
                if not z_field:
                    return json.dumps({"error": "3D散点图需要指定z_field参数"}, ensure_ascii=False)

                if color_field:
                    calculation_result = calculator.calculate(
                        data, x_field, primary_y_field, z_field, x_table, primary_y_table, color_field
                    )
                else:
                    calculation_result = calculator.calculate(
                        data, x_field, primary_y_field, z_field, x_table, primary_y_table
                    )
            elif chart_type.lower() == "radar":
                if not value_fields or len(value_fields) < 3:
                    return json.dumps({"error": "雷达图需要至少3个value_fields参数"}, ensure_ascii=False)

                calculation_result = calculator.calculate(
                    data, x_field, value_fields, entity_field
                )
            elif chart_type.lower() == "ranking":
                calculation_result = calculator.calculate(
                    data, x_field, primary_y_field, x_table, primary_y_table, limit, ascending
                )
            else:
                calculation_result = calculator.calculate(
                    data, x_field, primary_y_field, x_table, primary_y_table
                )

        # 关闭连接
        connection.close()
        logger.info("数据库连接已关闭")

        # 构建结果
        result = {
            "chart_type": chart_type,
            "x_table": x_table,
            "x_field": x_field,
            # 对于多系列图表返回多个y字段信息
            "y_table": y_table,
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
            "data_count": len(all_data) if 'all_data' in locals() else (len(data) if 'data' in locals() else 0),
            "result": calculation_result
        }

        # 如果是多系列图表，添加系列信息
        if is_multi_series_chart and isinstance(y_field, list) and len(y_field) > 0:
            result["series_count"] = len(y_field)
            result["series_info"] = [
                {
                    "field": y_fields[i],
                    "table": y_tables[i],
                    "index_field": y_index_fields[i] if i < len(y_index_fields) else None,
                    "start_index": y_start_indices[i] if i < len(y_start_indices) else None,
                    "end_index": y_end_indices[i] if i < len(y_end_indices) else None
                }
                for i in range(len(y_fields))
            ]

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
            "x_field": x_field,
            "y_table": y_table,
            "y_field": y_field
        }

        return json.dumps(error_result, ensure_ascii=False)


if __name__ == "__main__":
    print("======= 测试1: 单系列柱状图 =======")
    # 柱状图示例 - 分析不同组别的人数
    result = mysql_caculator(
        x_field="jlugroup",  # X轴字段名 - 组别
        y_field="ID",  # Y轴字段名 - 使用ID进行计数
        x_table="Data",  # X轴字段所在的表名
        y_table="Data",  # Y轴字段所在的表名
        x_index_field="school",  # X表的索引/过滤字段 - 根据校区筛选
        x_start_index="南湖校区",  # X表索引字段的起始值
        x_end_index="南湖校区",  # X表索引字段的结束值
        y_index_field="identity",  # Y表的索引/过滤字段 - 根据身份筛选
        y_start_index="正式队员",  # Y表索引字段的起始值
        y_end_index="正式队员",  # Y表索引字段的结束值
        chart_type="bar"  # 图表类型 - 生成柱状图
    )
    print(result)

    print("\n======= 测试2: 多系列柱状图 =======")
    # 多系列柱状图示例 - 比较不同身份类型在各组的分布
    multi_bar_result = mysql_caculator(
        x_field="jlugroup",  # X轴字段名 - 组别
        y_field=["ID", "totaltime"],  # 多个Y轴字段 - 计数和总时间
        x_table="Data",  # X轴字段所在的表名
        y_table=["Data", "sign_person"],  # Y轴字段所在的表名
        x_index_field="school",  # X表的索引/过滤字段 - 根据校区筛选
        x_start_index="南湖校区",  # X表索引字段的起始值
        x_end_index="南湖校区",  # X表索引字段的结束值
        y_index_field=["identity", "identity"],  # Y表的索引/过滤字段 - 根据身份筛选
        y_start_index=["正式队员", "正式队员"],  # Y表索引字段的起始值
        y_end_index=["正式队员", "正式队员"],  # Y表索引字段的结束值
        chart_type="bar"  # 图表类型 - 生成柱状图
    )
    print(multi_bar_result)

    print("\n======= 测试3: 多系列折线图 =======")
    # 多系列折线图示例 - 比较不同组别的签到情况随时间变化
    multi_line_result = mysql_caculator(
        x_field="lasttime",  # X轴字段名 - 最后一次时间
        y_field=["totaltime", "totaltime"],  # Y轴字段 - 总时间
        x_table="sign_daytask",  # X轴字段所在的表名
        y_table="sign_daytask",  # Y轴字段所在的表名
        y_index_field=["jlugroup", "jlugroup"],  # Y表的索引/过滤字段 - 按组别筛选
        y_start_index=["电控组", "机械组"],  # 分别筛选电控组和机械组
        y_end_index=["电控组", "机械组"],  # 分别筛选电控组和机械组
        chart_type="line"  # 图表类型 - 生成折线图
    )
    print(multi_line_result)

    print("\n======= 测试4: 饼图 =======")
    # 饼图示例 - 分析不同组别的人数占比
    pie_result = mysql_caculator(
        x_field="jlugroup",  # X轴字段名 - 组别 (作为饼图的类别)
        y_field="ID",  # Y轴字段名 - 使用ID进行计数 (作为饼图的值)
        x_table="Data",  # X轴字段所在的表名
        y_table="Data",  # Y轴字段所在的表名
        x_index_field="school",  # X表的索引/过滤字段 - 根据校区筛选
        x_start_index="南湖校区",  # X表索引字段的起始值
        x_end_index="南湖校区",  # X表索引字段的结束值
        chart_type="pie"  # 图表类型 - 生成饼图
    )
    print(pie_result)

    print("\n======= 测试5: 多系列散点图 =======")
    # 多系列散点图示例 - 比较不同组别的签到时间和总时长的关系
    scatter_result = mysql_caculator(
        x_field="signin",  # X轴字段名 - 签到时间
        y_field=["totaltime", "totaltime"],  # Y轴字段 - 总时长
        x_table="sign_daytask",  # X轴字段所在的表名
        y_table="sign_daytask",  # Y轴字段所在的表名
        y_index_field=["jlugroup", "jlugroup"],  # Y表的索引/过滤字段 - 按组别筛选
        y_start_index=["电控组", "AI组"],  # 分别筛选电控组和AI组
        y_end_index=["电控组", "AI组"],  # 分别筛选电控组和AI组
        chart_type="scatter"  # 图表类型 - 生成散点图
    )
    print(scatter_result)