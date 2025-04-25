import numpy as np
import json
from typing import Dict, List, Any, Union, Optional, Tuple
import ast
import math


class DerivedVariableCalculator:
    """衍生变量计算器，用于将多个变量通过公式计算得到新的变量"""

    def __init__(self, formula_str: str):
        """
        初始化衍生变量计算器
        参数:
        - formula_str: 计算公式字符串，例如 "B + C" 或 "sqrt(B**2 + C**2)"
        """
        self.formula_str = formula_str
        self._validate_formula(formula_str)
        # 提取公式中的变量名
        self.variable_names = self._extract_variable_names(formula_str)

    def _extract_variable_names(self, formula_str: str) -> List[str]:
        """提取公式中的变量名"""
        try:
            # 解析AST
            tree = ast.parse(formula_str, mode='eval')
            # 找出所有Name节点
            var_names = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Name) and node.id not in dir(math) and node.id not in ['min', 'max', 'abs',
                                                                                               'round']:
                    var_names.append(node.id)
            return list(set(var_names))  # 去重
        except Exception:
            return []

    def _validate_formula(self, formula_str: str):
        """验证公式的安全性，防止代码注入"""
        allowed_nodes = (
            ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow, ast.USub, ast.UAdd,
            ast.Num, ast.Name, ast.Load, ast.Call, ast.BinOp, ast.UnaryOp, ast.Module,
            ast.Expression, ast.Constant, ast.Expr, ast.Mod, ast.FloorDiv
        )

        # 解析公式
        try:
            node = ast.parse(formula_str, mode='eval')

            # 检查AST节点类型，只允许数学运算相关的节点
            for subnode in ast.walk(node):
                if not isinstance(subnode, allowed_nodes):
                    if isinstance(subnode, ast.Call) and isinstance(subnode.func, ast.Name):
                        # 检查函数调用是否使用了内置的数学函数
                        if subnode.func.id not in dir(math) and subnode.func.id not in ['min', 'max', 'abs', 'round']:
                            raise ValueError(f"公式中包含不允许的函数: {subnode.func.id}")
                    else:
                        raise ValueError(f"公式中包含不允许的操作: {type(subnode).__name__}")

        except SyntaxError as e:
            raise ValueError(f"公式语法错误: {e}")

    def calculate(self, data: Dict[str, Any]) -> float:
        """
        根据公式计算衍生变量

        参数:
        - data: 包含原始变量值的字典

        返回:
        - 计算结果值
        """
        # 创建一个包含数据和数学函数的变量环境
        var_env = {}

        # 检查并添加数据，对于不存在的字段默认为0
        for var_name in self.variable_names:
            if var_name in data and data[var_name] is not None:
                # 处理各种空值情况
                value = data[var_name]
                if value == "" or (isinstance(value, (float,int)) and (value == 0)):
                    var_env[var_name] = 0
                else:
                    # 尝试转换为数值类型
                    try:
                        if isinstance(value, (int, float)):
                            var_env[var_name] = value
                        else:
                            # 尝试转换非数值类型
                            converted = float(value)
                            var_env[var_name] = converted
                    except (ValueError, TypeError):
                        # 无法转换为数值的情况，设为0
                        var_env[var_name] = 0
            else:
                # 字段不存在或为None，设为0
                var_env[var_name] = 0

        # 添加常用数学函数
        math_funcs = {name: getattr(math, name) for name in dir(math) if callable(getattr(math, name))}
        var_env.update(math_funcs)

        # 添加常用的其他函数
        var_env.update({
            'min': min,
            'max': max,
            'abs': abs,
            'round': round
        })

        try:
            # 安全地执行公式计算
            result = eval(self.formula_str, {"__builtins__": {}}, var_env)
            return float(result) if result is not None else 0
        except Exception as e:
            # 如果计算失败，记录错误并返回0
            print(f"计算公式 '{self.formula_str}' 出错: {e}")
            return 0


def calculate_derived_variable(data: List[Dict[str, Any]], formula: str, output_field: str) -> List[Dict[str, Any]]:
    """
    在数据集上应用衍生变量计算

    参数:
    - data: 原始数据列表
    - formula: 计算公式
    - output_field: 输出字段名

    返回:
    - 添加了衍生变量的数据列表
    """
    calculator = DerivedVariableCalculator(formula)
    result = []

    for item in data:
        new_item = item.copy()
        try:
            new_item[output_field] = calculator.calculate(item)
        except Exception as e:
            # 如果计算失败，设为0而不是NaN
            print(f"处理数据项时发生错误: {e}")
            new_item[output_field] = 0
        result.append(new_item)

    return result