import json
import os
from datetime import datetime, date
import numpy as np
from typing import Dict, List, Any, Union, Optional, Tuple
# 在现有导入语句下方添加
from src.derived_variable_calculator import DerivedVariableCalculator  # 导入衍生变量计算器

from utils import (
    connect_to_mysql,
    load_db_config,
    enrich_data_with_relations,
    group_and_aggregate,
    calculate_derived_metrics,
    query_data
)
from utils import logger
from src.chart_caculator import ChartCalculatorFactory
from src.select_mysql import get_date_field, query_data_from_tables


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
        derived_expression: Optional[str] = None
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
    - series_field: 系列字段
    - derived_expression: 衍生变量表达式，格式如 "new_field = field1 + field2"

    返回:
    - JSON格式的计算结果
    """

    # 记录日志
    # 记录日志
    logger.info(
        f"开始查询MySQL数据: X表={x_table}, X字段={x_field}, Y表={y_table}, Y字段={y_field}, "
        f"图表类型: {chart_type}"
    )
    # 新增日志记录
    if derived_expression:
        logger.info(f"使用衍生变量表达式: {derived_expression}")

    try:
        # 加载数据库配置
        db_info = load_db_config()
        # logger.info(f"数据库配置: {db_info[:15]}")

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
            if derived_expression:
                calculator = DerivedVariableCalculator()
                all_data, derived_y_field = calculator.transform_y_data(all_data, y_fields, derived_expression)
                # 使用衍生变量替换原始y_fields
                if derived_y_field:
                    # 将多系列转为单系列（衍生变量）
                    y_fields = [derived_y_field]

                    # 更新图表类型为单系列版本（如果是多系列特定类型）
                    if chart_type.lower() == "multi_series_bar":
                        chart_type = "bar"
                    elif chart_type.lower() == "multi_series_line":
                        chart_type = "line"

                    # 标记不再是多系列图表
                    is_multi_series_chart = False

                # 更新数据项中的_series_field
                for item in all_data:
                    item['_series_field'] = derived_y_field

                # 创建新的series_data列表，包含一个系列（衍生变量）
                series_data = []
                for item in all_data:
                    if x_field in item and derived_y_field in item:
                        series_item = {
                            x_field: item[x_field],
                            derived_y_field: item[derived_y_field],
                            "_series_index": 0,
                        "_series_field": derived_y_field,
                        "_series_table": y_tables[0] if y_tables else ""
                        }
                        series_data.append(series_item)

                # 替换all_data
                all_data = series_data

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
                x_values = list(set(item[x_field] for item in all_data if x_field in item and item[x_field] is not None))
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
                        "barData": [[v if v is not None else 0 for v in item["data"]] for item in series_data],
                        "seriesName":[item["name"] for item in series_data],
                        "title": f"{x_table}.{x_field} - 多系列分析"
                    }
                elif chart_type.lower() == "line":
                    calculation_result = {
                        "chart_type": "line",
                        # "xAxisLabels": x_values,
                        "data": [[v if v is not None else 0 for v in item["data"]] for item in series_data],
                        "title": f"{x_table}.{x_field} - 多系列趋势"
                    }
                    logger.info(f"计算结果: {calculation_result}")
                elif chart_type.lower() == "scatter":
                    # 散点图的处理略有不同
                    scatter_series = []
                    for y_idx, y_field_name in enumerate(y_fields):
                        # 过滤出当前系列的数据
                        current_series_data = [item for item in all_data if item.get('_series_index') == y_idx]

                        x_vals = []
                        y_vals = []

                        for item in current_series_data:
                            if x_field in item and y_field_name in item and item[x_field] is not None and item[y_field_name] is not None:
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
        else:  # 这个else对应于前面的if is_multi_series_chart条件判断
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

            derived_y_field = None
            if derived_expression and data:
                calculator = DerivedVariableCalculator()
                data, derived_y_field = calculator.transform_y_data(data, [primary_y_field], derived_expression)
                if derived_y_field:
                    # 使用衍生变量替换原始y字段
                    primary_y_field = derived_y_field

            # 根据图表类型执行计算
            calculator = ChartCalculatorFactory.create_calculator(chart_type)

            # if chart_type.lower() == "3d_scatter":
            #     if not z_field:
            #         return json.dumps({"error": "3D散点图需要指定z_field参数"}, ensure_ascii=False)
            #
            #     if color_field:
            #         calculation_result = calculator.calculate(
            #             data, x_field, primary_y_field, z_field, x_table, primary_y_table, color_field
            #         )
            #     else:
            #         calculation_result = calculator.calculate(
            #             data, x_field, primary_y_field, z_field, x_table, primary_y_table
            #         )
            # elif chart_type.lower() == "radar":
            #     if not value_fields or len(value_fields) < 3:
            #         return json.dumps({"error": "雷达图需要至少3个value_fields参数"}, ensure_ascii=False)
            #
            #     calculation_result = calculator.calculate(
            #         data, x_field, value_fields, entity_field
            #     )
            if chart_type.lower() == "ranking":
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

        logger.info(f"查询结果: {calculation_result}")

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

        if derived_expression:
            result["derived_expression"] = derived_expression
            if 'derived_y_field' in locals():
                result["derived_y_field"] = derived_y_field

        # 如果是多系列图表，添加系列信息
        elif is_multi_series_chart and isinstance(y_field, list) and len(y_field) > 0:
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
        error_msg = f"查询计算出错: {str(e)}"
        logger.error(error_msg)
        import traceback
        logger.error(traceback.format_exc())
        return json.dumps({"error": error_msg}, ensure_ascii=False)


if __name__ == "__main__":
    # print("======= 测试1: 单系列柱状图 =======")
    # # 柱状图示例 - 分析不同组别的人数
    # result = mysql_caculator(
    #     x_field="jlugroup",  # X轴字段名 - 组别
    #     y_field="ID",  # Y轴字段名 - 使用ID进行计数
    #     x_table="Data",  # X轴字段所在的表名
    #     y_table="Data",  # Y轴字段所在的表名
    #     x_index_field="school",  # X表的索引/过滤字段 - 根据校区筛选
    #     x_start_index="南湖校区",  # X表索引字段的起始值
    #     x_end_index="南湖校区",  # X表索引字段的结束值
    #     y_index_field="identity",  # Y表的索引/过滤字段 - 根据身份筛选
    #     y_start_index="正式队员",  # Y表索引字段的起始值
    #     y_end_index="正式队员",  # Y表索引字段的结束值
    #     chart_type="bar"  # 图表类型 - 生成柱状图
    # )
    # print(result)
    #
    # print("\n======= 测试2: 多系列柱状图 =======")
    # # 多系列柱状图示例 - 比较不同身份类型在各组的分布
    # multi_bar_result = mysql_caculator(
    #     x_field="jlugroup",  # X轴字段名 - 组别
    #     y_field=["ID", "totaltime"],  # 多个Y轴字段 - 计数和总时间
    #     x_table="Data",  # X轴字段所在的表名
    #     y_table=["Data", "sign_person"],  # Y轴字段所在的表名
    #     x_index_field="school",  # X表的索引/过滤字段 - 根据校区筛选
    #     x_start_index="南湖校区",  # X表索引字段的起始值
    #     x_end_index="南湖校区",  # X表索引字段的结束值
    #     y_index_field=["identity", "identity"],  # Y表的索引/过滤字段 - 根据身份筛选
    #     y_start_index=["正式队员", "正式队员"],  # Y表索引字段的起始值
    #     y_end_index=["正式队员", "正式队员"],  # Y表索引字段的结束值
    #     chart_type="bar"  # 图表类型 - 生成柱状图
    # )
    # print(multi_bar_result)

    # print("\n======= 测试3: 多系列折线图 =======")
    # # 多系列折线图示例 - 比较不同组别的签到情况随时间变化
    # multi_line_result = mysql_caculator(
    #     x_field="lasttime",  # X轴字段名 - 最后一次时间
    #     y_field=["totaltime", "totaltime"],  # Y轴字段 - 总时间
    #     x_table="sign_daytask",  # X轴字段所在的表名
    #     y_table="sign_daytask",  # Y轴字段所在的表名
    #     y_index_field=["jlugroup", "jlugroup"],  # Y表的索引/过滤字段 - 按组别筛选
    #     y_start_index=["电控组", "机械组"],  # 分别筛选电控组和机械组
    #     y_end_index=["电控组", "机械组"],  # 分别筛选电控组和机械组
    #     chart_type="bar",  # 图表类型 - 生成折线图
    #     derived_expression = "combined_time = totaltime + totaltime"  # 衍生变量表达式 - 两组的totaltime相加
    #
    # )
    # print(multi_line_result)
    #
    # print("\n======= 测试3: 多系列折线图 =======")
    # # 多系列折线图示例 - 比较不同组别的签到情况随时间变化
    # multi_line_result = mysql_caculator(
    #     x_field="lasttime",  # X轴字段名 - 最后一次时间
    #     y_field=["totaltime", "totaltime"],  # Y轴字段 - 总时间
    #     x_table="sign_daytask",  # X轴字段所在的表名
    #     y_table="sign_daytask",  # Y轴字段所在的表名
    #     y_index_field=["jlugroup", "jlugroup"],  # Y表的索引/过滤字段 - 按组别筛选
    #     y_start_index=["电控组", "机械组"],  # 分别筛选电控组和机械组
    #     y_end_index=["电控组", "机械组"],  # 分别筛选电控组和机械组
    #     chart_type="bar",  # 图表类型 - 生成折线图
    #
    # )
    # print(multi_line_result)

    multi_line_result = mysql_caculator(
        x_field="quantity",  # X轴字段名 - 采购数量
        y_field="price",  # Y轴字段 - 单价
        x_table="Financial_Log",  # X轴字段所在的表名
        y_table="Financial_Log",  # Y轴字段所在的表名
        y_index_field="ID",  # 用唯一标识字段（如ID）避免分组
        y_start_index="",  # 无需筛选范围
        y_end_index="",  # 无需筛选范围
        chart_type="line",  # 图表类型 - 折线图
    )
    print(multi_line_result)

    # print("\n======= 测试4: 饼图 =======")
    # # 饼图示例 - 分析不同组别的人数占比
    # pie_result = mysql_caculator(
    #     x_field="jlugroup",  # X轴字段名 - 组别 (作为饼图的类别)
    #     y_field="ID",  # Y轴字段名 - 使用ID进行计数 (作为饼图的值)
    #     x_table="Data",  # X轴字段所在的表名
    #     y_table="Data",  # Y轴字段所在的表名
    #     x_index_field="school",  # X表的索引/过滤字段 - 根据校区筛选
    #     x_start_index="南湖校区",  # X表索引字段的起始值
    #     x_end_index="南湖校区",  # X表索引字段的结束值
    #     chart_type="pie"  # 图表类型 - 生成饼图
    # )
    # print(pie_result)
    #
    # print("\n======= 测试5: 多系列散点图 =======")
    # # 多系列散点图示例 - 比较不同组别的签到时间和总时长的关系
    # scatter_result = mysql_caculator(
    #     x_field="signin",  # X轴字段名 - 签到时间
    #     y_field=["totaltime", "totaltime"],  # Y轴字段 - 总时长
    #     x_table="sign_daytask",  # X轴字段所在的表名
    #     y_table="sign_daytask",  # Y轴字段所在的表名
    #     y_index_field=["jlugroup", "jlugroup"],  # Y表的索引/过滤字段 - 按组别筛选
    #     y_start_index=["电控组", "AI组"],  # 分别筛选电控组和AI组
    #     y_end_index=["电控组", "AI组"],  # 分别筛选电控组和AI组
    #     chart_type="scatter"  # 图表类型 - 生成散点图
    # )
    # print(scatter_result)