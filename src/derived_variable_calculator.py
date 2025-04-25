import re
from typing import Dict, List, Any, Union, Optional, Callable, Tuple
import numpy as np
import logging

# 创建logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# 创建控制台处理器
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)

# 设置日志格式
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)

# 将处理器添加到logger
logger.addHandler(console_handler)


class DerivedVariableCalculator:
    """
    衍生变量计算器
    用于根据表达式计算新的衍生变量
    """

    def __init__(self):
        logger.info("初始化衍生变量计算器")
        # 支持的基本操作符
        self.operators = {
            '+': lambda x, y: x + y,
            '-': lambda x, y: x - y,
            '*': lambda x, y: x * y,
            '/': lambda x, y: x / y if y != 0 else 0,
            '^': lambda x, y: x ** y,
            '%': lambda x, y: x % y if y != 0 else 0,
        }

        # 支持的函数
        self.functions = {
            'abs': abs,
            'max': max,
            'min': min,
            'sum': sum,
            'avg': lambda x: sum(x) / len(x) if len(x) > 0 else 0,
            'log': np.log,
            'sqrt': np.sqrt,
            'sin': np.sin,
            'cos': np.cos,
            'tan': np.tan,
            'round': round,
        }
        logger.debug(f"已加载 {len(self.operators)} 个操作符和 {len(self.functions)} 个函数")

    def calculate(self, data: List[Dict[str, Any]], expression: str) -> List[Dict[str, Any]]:
        """
        根据表达式计算衍生变量

        参数:
        - data: 原始数据列表
        - expression: 计算表达式，格式如 "new_field = field1 + field2" 或 "new_field = max(field1, field2)"

        返回:
        - 添加了衍生变量的数据列表
        """
        logger.info(f"开始计算衍生变量，表达式：{expression}")
        if not data or not expression:
            logger.warning("数据为空或表达式为空，无法计算衍生变量")
            return data

        # 解析表达式
        match = re.match(r'(\w+)\s*=\s*(.*)', expression.strip())
        if not match:
            error_msg = f"无效的表达式格式: {expression}，应为 'new_field = 表达式'"
            logger.error(error_msg)
            raise ValueError(error_msg)

        output_field, formula = match.groups()
        formula = formula.strip()
        logger.debug(f"解析表达式：输出字段 = {output_field}，公式 = {formula}")

        # 处理每个数据项
        result = []
        success_count = 0
        error_count = 0

        logger.info(f"开始处理 {len(data)} 条数据记录")
        for index, item in enumerate(data):
            new_item = item.copy()

            # 解析并计算表达式
            try:
                # 记录当前数据项的关键字段，帮助调试
                debug_info = {k: v for k, v in item.items()
                              if k in ['_series_index', '_series_field', '_series_table']
                              or k in formula}
                logger.debug(f"处理第 {index + 1} 条记录，关键字段：{debug_info}")

                value = self._evaluate_expression(item, formula)
                new_item[output_field] = value
                success_count += 1

                logger.debug(f"计算结果：{value}")
            except Exception as e:
                # 如果计算出错，设置为None
                new_item[output_field] = None
                error_count += 1

                logger.error(f"计算第 {index + 1} 条记录时出错：{str(e)}")
                # 记录导致错误的数据
                for field_name in re.findall(r'\b(\w+)\b', formula):
                    if field_name in item:
                        logger.error(
                            f"  字段 {field_name} = {item[field_name]} (类型: {type(item[field_name]).__name__})")
                    else:
                        logger.error(f"  字段 {field_name} 不存在于数据中")

            result.append(new_item)

        logger.info(f"衍生变量计算完成：成功 {success_count} 条，失败 {error_count} 条")
        return result

    def _evaluate_expression(self, item: Dict[str, Any], expression: str) -> Any:
        """
        评估表达式并返回计算结果

        这是一个简化版的表达式计算器，支持基本运算和简单函数调用
        对于复杂表达式可能需要扩展
        """
        original_expression = expression
        logger.debug(f"开始评估表达式：{expression}")

        # 替换字段名为实际值
        field_replacements = {}
        for field_name, field_value in item.items():
            # 确保只替换独立的字段名，避免替换字段名的子串
            pattern = r'\b' + field_name + r'\b'
            if re.search(pattern, expression):
                # 尝试将字符串形式的数值转换为实际数值
                try:
                    if isinstance(field_value, str) and field_value.replace('.', '', 1).isdigit():
                        # 字符串形式的数值，转换为float
                        value_str = field_value
                    elif isinstance(field_value, (int, float)):
                        # 已经是数值类型
                        value_str = str(field_value)
                    else:
                        # 非数值类型，使用0
                        value_str = '0'
                        logger.warning(f"字段 {field_name} 的值 {field_value} 不是数值类型，将使用0")
                except Exception as e:
                    value_str = '0'
                    logger.warning(f"处理字段 {field_name} 时出错：{str(e)}，将使用0")

                expression = re.sub(pattern, value_str, expression)
                field_replacements[field_name] = value_str

        if field_replacements:
            logger.debug(f"字段替换：{field_replacements}")
            logger.debug(f"替换后表达式：{expression}")

        # 处理函数调用
        for func_name, func in self.functions.items():
            pattern = r'\b' + func_name + r'\s*\((.*?)\)'
            while re.search(pattern, expression):
                match = re.search(pattern, expression)
                args_str = match.group(1)

                # 分割参数并转换为数值
                args = [arg.strip() for arg in args_str.split(',')]
                args_values = []
                for arg in args:
                    try:
                        if arg.replace('.', '', 1).isdigit():
                            args_values.append(float(arg))
                        else:
                            logger.warning(f"参数 '{arg}' 不是数值，将使用默认值 0")
                            args_values.append(0)
                    except Exception as e:
                        logger.warning(f"处理参数 '{arg}' 时出错：{str(e)}，将使用默认值 0")
                        args_values.append(0)

                # 计算函数结果
                try:
                    if func_name in ('max', 'min', 'sum', 'avg'):
                        logger.debug(f"计算函数 {func_name}{args_values}")
                        result = func(args_values)
                    else:
                        logger.debug(f"计算函数 {func_name}{tuple(args_values)}")
                        result = func(*args_values)

                    logger.debug(f"函数结果：{result}")
                except Exception as e:
                    error_msg = f"函数 {func_name} 计算错误：{str(e)}"
                    logger.error(error_msg)
                    raise ValueError(error_msg)

                # 替换函数调用为结果
                old_expr = expression
                expression = expression[:match.start()] + str(result) + expression[match.end():]
                logger.debug(f"表达式更新：{old_expr} -> {expression}")

        # 安全地计算最终表达式
        try:
            logger.debug(f"最终表达式求值：{expression}")
            result = eval(expression, {"__builtins__": {}}, {})
            logger.debug(f"计算结果：{result}")
            return result
        except Exception as e:
            error_msg = f"表达式计算错误: {expression}, 原因: {str(e)}"
            logger.error(error_msg)
            logger.error(f"原始表达式: {original_expression}")
            logger.error(f"数据项字段: {list(item.keys())}")
            raise ValueError(error_msg)

    def transform_y_data(self, data: List[Dict[str, Any]], y_fields: List[str],
                         derived_expression: str) -> Tuple[List[Dict[str, Any]], str]:
        """
        将多个y字段数据转换为衍生变量

        参数:
        - data: 原始数据列表
        - y_fields: y轴字段列表
        - derived_expression: 衍生变量表达式

        返回:
        - 转换后的数据列表
        - 衍生字段名
        """
        logger.info(f"开始转换Y轴数据，Y字段：{y_fields}，表达式：{derived_expression}")
        logger.debug(f"数据样本（前3条）：{data[:3] if len(data) > 3 else data}")

        # 解析表达式，获取输出字段名
        match = re.match(r'(\w+)\s*=\s*(.*)', derived_expression.strip())
        if not match:
            error_msg = f"无效的表达式格式: {derived_expression}，应为 'new_field = 表达式'"
            logger.error(error_msg)
            raise ValueError(error_msg)

        output_field = match.group(1).strip()
        logger.debug(f"衍生字段名：{output_field}")

        # 计算衍生变量
        transformed_data, output_field = [], ""
        try:
            transformed_data = self.calculate(data, derived_expression)
            match = re.match(r'(\w+)\s*=\s*(.*)', derived_expression.strip())
            output_field = match.group(1).strip() if match else "derived_field"

            # 记录结果统计
            total_count = len(transformed_data)
            valid_count = sum(1 for item in transformed_data if output_field in item and item[output_field] is not None)
            null_count = total_count - valid_count

            logger.info(f"转换完成：总记录数 {total_count}，有效记录数 {valid_count}，空值记录数 {null_count}")

            # 检查计算结果是否有效
            valid_data = [item for item in transformed_data if output_field in item and item[output_field] is not None]

            if not valid_data:
                error_msg = f"衍生变量计算失败，没有有效的计算结果: {derived_expression}"
                logger.error(error_msg)

                # 记录一些数据样本，帮助调试
                if data:
                    logger.error(f"原始数据样本（前3条）：")
                    for i, item in enumerate(data[:3]):
                        logger.error(f"  记录 {i + 1}: {item}")

                # 检查表达式中使用的字段是否存在于数据中
                if data:
                    all_fields = set()
                    for item in data:
                        all_fields.update(item.keys())

                    expr_fields = set(re.findall(r'\b(\w+)\b', match.group(2)))
                    missing_fields = expr_fields - all_fields

                    if missing_fields:
                        logger.error(f"表达式中使用的字段在数据中不存在: {missing_fields}")

                    logger.error(f"数据中可用的字段: {all_fields}")

                raise ValueError(error_msg)

            # 记录一些有效结果样本
            logger.debug(f"有效结果样本（前3条）：")
            for i, item in enumerate(valid_data[:3]):
                logger.debug(f"  记录 {i + 1}: {{{output_field}: {item[output_field]}}}")

        except Exception as e:
            logger.error(f"转换Y轴数据时出错：{str(e)}")
            raise

        return transformed_data, output_field