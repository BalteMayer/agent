import json
import numpy as np
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Union, Optional, Tuple
from datetime import datetime, date
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
        计算条形图所需的数据,支持多系列

        参数:
        - data: 原始数据列表
        - x_field: X轴分类字段
        - y_field: Y轴数值字段
        - x_table: X表名
        - y_table: Y表名
        - series_field: 可选的系列分组字段,用于多系列柱状图

        返回:
        - 条形图数据,可能包含多个系列
        """
        result = {}

        if not data:
            return {
                "chart_type": "bar",
                "xAxisData": [],
                "barData": [],
                "seriesNames": [],
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

                        # 累加or更新值
                        if y_field in item:
                            if isinstance(item[y_field], (int, float)):
                                series_data[series_index]["data"][cat_index] += item[y_field]
                            else:
                                # 如果不是数值,计数加1
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

            # 修改返回格式：分开barDataandseriesNames
            barData = []
            seriesNames = []
            for series in series_data:
                barData.append(series["data"])
                seriesNames.append(series["name"])

            result = {
                "chart_type": "bar",
                "xAxisData": categories,
                "barData": barData,
                "seriesNames": seriesNames,
                "statistics": statistics,
                "title": f"{x_table}。{x_field} 按 {series_field} 分组"
            }
        else:
            # 单系列模式: 使用_series_indexor_series_field标记处理多个Y字段
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
                                    # 如果找不到对应的值字段or非数值,则计数+1
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
                                        # 如果不是数值,计数加1
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

                # 修改返回格式：分开barDataandseriesNames
                barData = []
                seriesNames = []
                for series in series_data:
                    barData.append(series["data"])
                    seriesNames.append(series["name"])

                result = {
                    "chart_type": "bar",
                    "xAxisData": categories,
                    "barData": barData,
                    "seriesNames": seriesNames,
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



                # 单系列时barData仍然是二维数组,只是只有一个元素
                result = {
                    "chart_type": "bar",
                    "xAxisData": categories,
                    "barData": [values],
                    "seriesNames": [y_field],
                    "statistics": statistics,
                    "title": f"{x_table}.{x_field} - {y_table}.{y_field} 分析"
                }

        return result



class LineChartCalculator(ChartCalculator):
    def calculate(self, data: List[Dict[str, Any]], x_field: str, y_field: str, x_table: str,
                  y_table: str, series_field: str = None) -> Dict[str, Any]:
        """
        计算折线图所需的数据,支持多系列

        参数:
        - data: 原始数据列表
        - x_field: X轴字段（通常是时间or序列字段）
        - y_field: Y轴数值字段
        - x_table: X表名
        - y_table: Y表名
        - series_field: 可选的系列分组字段,用于多系列折线图

        返回:
        - 折线图数据,可能包含多个系列
        """
        if not data:
            return {
                "chart_type": "line",
                "data": [],
                "xAxisLabels": [],
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
                    # 过滤出属于当前系列andX值的数据
                    matching_items = [
                        item for item in data
                        if series_field in item and item[series_field] == series_value
                           and x_field in item and str(item[x_field]) == x_value
                    ]

                    # 如果有匹配的数据,计算值
                    if matching_items:
                        valid_items = [item for item in matching_items if y_field in item]
                        if valid_items:
                            if all(isinstance(item[y_field], (int, float)) for item in valid_items):
                                # 如果都是数值,计算总and
                                series_data[i]["data"][j] = sum(item[y_field] for item in valid_items)
                            else:
                                # 否则计数
                                series_data[i]["data"][j] = len(valid_items)

            result = {
                "chart_type": "line",
                "data": [series["data"] for series in series_data],
                "xAxisLabels": x_values,
                "title": f"{x_table}.{x_field} 按 {series_field} 分组"
            }
        else:
            # 检查是否有_series_indexor_series_field标记的多系列数据
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
                                    # 如果找不到对应的值字段or非数值,则计数+1
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
                                        # 如果不是数值,计数加1
                                        series_data[series_index]["data"][x_index] += 1

                result = {
                    "chart_type": "line",
                    "data": [series["data"] for series in series_data],
                    "xAxisLabels": x_values,
                    # "series": series_data,
                    "title": f"{x_table}.{x_field} 多系列趋势"
                }
            else:
                # 常规单系列处理
                # 按日期排序数据
                try:
                    data.sort(key=lambda x: float(x.get(x_field, 0) or 0))
                except Exception:
                    pass  # 保留原顺序


                # 按排序后的顺序收集唯一 x 值，并统计 y
                date_counts = {}
                unique_x_order = []  # 记录排序后去重的 x 顺序

                for item in data:
                    x_val = str(item.get(x_field, ''))
                    y_val = item.get(y_field, 0)

                    # 统计逻辑
                    if x_val not in date_counts:
                        date_counts[x_val] = 0
                        unique_x_order.append(x_val)  # 记录首次出现的顺序

                    if isinstance(y_val, (int, float)):
                        date_counts[x_val] += y_val
                    else:
                        date_counts[x_val] += 1

                # 直接使用排序后的唯一 x 顺序
                x_values = unique_x_order
                values = [date_counts[x] for x in unique_x_order]
                logger.info(f"折线图数据计算完成, X轴值: {x_values}, Y轴值: {values}")

                result = {
                    "chart_type": "line",
                    "data": values,
                    "xAxisLabels": x_values,
                    # "series": [{
                    #     "name": y_field,
                    #     "data": values
                    # }],
                    "title": f"{x_table}.{x_field} - {y_table}.{y_field}",
                }

        return result


class PieChartCalculator(ChartCalculator):
    def calculate(self, data: List[Dict[str, Any]], x_field: str, y_field: str, x_table: str,
                  y_table: str) -> Dict[str, Any]:
        """计算饼图所需的数据"""

        logger.info(f"开始计算饼图数据,输入数据量: {len(data)}, X字段: {x_field}, Y字段: {y_field}")
        result = {}
        labels = []
        values = []

        # 根据x_field进行分组计算
        # 记录数据中是否包含y_fieldandx_field字段
        if data and len(data) > 0:
            sample_keys = list(data[0].keys())
            logger.info(f"数据样本包含的字段: {sample_keys}")
            missing_fields = []
            if y_field not in sample_keys:
                missing_fields.append(y_field)
            if x_field not in sample_keys:
                missing_fields.append(x_field)

            if missing_fields:
                logger.error(f"数据中不存在字段: {missing_fields},可用字段为: {sample_keys}")
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
        计算散点图所需的数据,支持多系列

        参数:
        - data: 原始数据列表
        - x_field: X轴字段
        - y_field: Y轴字段
        - x_table: X表名
        - y_table: Y表名
        - series_field: 可选的系列分组字段,用于多系列散点图

        返回:
        - 散点图数据,可能包含多个系列
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

                # 计算相关系数and回归线
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
            # 检查是否有_series_indexor_series_field标记的多系列数据
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

                        # 计算统计数据and保存系列
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

                        # 计算统计数据and保存系列
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
        # 计算相关系数and回归线
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

        # 提取唯一的xandy值
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


class RankingCalculator(ChartCalculator):
    def calculate(self, data: List[Dict[str, Any]], x_field: str, y_field: str, x_table: str,
                  y_table: str, limit: int = 5, ascending: bool = False) -> Dict[str, Any]:
        if not data:
            return {
                "chart_type": "ranking",
                "ranks": [],
                "stats": {}
            }

        from utils import group_and_aggregate, calculate_derived_metrics

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