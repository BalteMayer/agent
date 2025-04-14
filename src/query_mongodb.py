#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import os
import re
from typing import Dict, List, Any, Union, Optional
from pymongo import MongoClient
from bson import json_util, ObjectId
from utils import logger, load_db_config


class MongoDBExecutor:
    """
    通过config.json文件访问MongoDB数据库,执行智能体生成的查询指令
    """

    def __init__(self):
        """
        初始化数据库执行器
        """
        self.config = self._load_config()
        self.client = None
        self.db = None
        self.collections_info = self.config.get('collections', {})

    def _load_config(self) -> Dict:
        """
        加载数据库配置

        Returns:
            配置字典
        """
        try:
            config = load_db_config()
            # 检查必要的配置项
            required_fields = ['host', 'port', 'database']
            for field in required_fields:
                if field not in config:
                    raise ValueError(f"配置文件中缺少必要的配置项: {field}")
            return config
        except FileNotFoundError:
            raise FileNotFoundError(f"配置文件不存在")
        except json.JSONDecodeError:
            raise ValueError(f"配置文件格式不正确")

    def connect(self) -> None:
        """
        连接到MongoDB数据库
        """
        try:
            # 构建MongoDB连接URI
            username = self.config.get('username', '')
            password = self.config.get('password', '')
            host = self.config.get('host', 'localhost')
            port = self.config.get('port', 27017)

            # 构建连接URI
            if username and password:
                uri = f"mongodb://{username}:{password}@{host}:{port}/"
            else:
                uri = f"mongodb://{host}:{port}/"

            # 连接到MongoDB
            self.client = MongoClient(uri)
            self.db = self.client[self.config.get('database', 'test')]

            # 测试连接
            self.client.admin.command('ping')
            logger.info("MongoDB连接成功")
        except Exception as e:
            raise ConnectionError(f"连接数据库失败: {str(e)}")

    def close(self) -> None:
        """
        关闭数据库连接
        """
        if self.client:
            self.client.close()
            logger.info("MongoDB连接已关闭")

    def _is_query_only(self, query_str: str) -> bool:
        """
        检查MongoDB查询字符串是否只包含查询操作,不包含增删改操作

        Args:
            query_str: MongoDB查询字符串

        Returns:
            如果是只读查询则返回True,否则返回False
        """
        # 去除注释和多余空格
        query_str = re.sub(r'//.*$', '', query_str, flags=re.MULTILINE)
        query_str = re.sub(r'/\*[\s\S]*?\*/', '', query_str)
        query_str = query_str.strip()

        # 检查是否只包含查询操作
        allowed_operations = [
            'find', 'findOne', 'aggregate', 'count', 'distinct', 'explain'
        ]

        # 检查操作是否在允许列表中
        operation_pattern = r'\.(\w+)\('
        operations = re.findall(operation_pattern, query_str)

        for op in operations:
            if op not in allowed_operations:
                return False

        # 检查是否包含危险操作
        dangerous_operations = [
            'insert', 'update', 'delete', 'remove', 'drop', 'createIndex',
            'createCollection', 'renameCollection', 'replaceOne', 'updateOne',
            'updateMany', 'deleteOne', 'deleteMany', 'bulkWrite', 'insertOne',
            'insertMany'
        ]

        for op in dangerous_operations:
            if f".{op}(" in query_str:
                return False

        return True

    def _convert_query_params(self, params_str: str) -> Any:
        """
        将MongoDB查询语法转换为Python对象,处理特殊类型如ObjectId

        Args:
            params_str: 查询参数字符串

        Returns:
            转换后的Python对象
        """
        # 处理ObjectId
        params_str = re.sub(r'ObjectId\([\'"](.+?)[\'"]\)', r'{"$oid": "\1"}', params_str)

        # 处理JavaScript风格的键值对
        params_str = re.sub(r'(\w+):', r'"\1":', params_str)

        # 处理$操作符
        params_str = re.sub(r'(\$\w+):', r'"\1":', params_str)

        # 将单引号替换为双引号（注意要处理字符串内的引号）
        in_string = False
        escaped = False
        result = []

        for char in params_str:
            if char == '\\':
                escaped = not escaped
            elif char == "'" and not escaped:
                in_string = not in_string
                result.append('"')
            elif char == '"' and not escaped:
                result.append('\\"')
            else:
                escaped = False
                result.append(char)

        params_str = ''.join(result)

        # 解析JSON
        try:
            return json.loads(params_str)
        except json.JSONDecodeError:
            # 处理非标准JSON的情况
            return params_str

    def execute_query(self, query_str: str) -> List[Dict]:
        """
        执行MongoDB查询字符串

        Args:
            query_str: MongoDB查询字符串,例如 "db.users.find({age: {$gt: 18}})"

        Returns:
            查询结果列表
        """
        if not self.client or not self.db:
            self.connect()

        # 安全检查,确保只执行查询操作
        if not self._is_query_only(query_str):
            raise ValueError("安全错误：只允许执行查询操作,禁止执行增删改操作")

        try:
            # 解析集合名称
            collection_match = re.search(r'db\.(\w+)\.', query_str)
            if not collection_match:
                raise ValueError("无法解析集合名称,查询格式应为 'db.collection.operation(...)'")

            collection_name = collection_match.group(1)

            # 验证集合是否在配置中
            if collection_name not in self.collections_info and collection_name != 'system':
                raise ValueError(f"未找到集合 '{collection_name}' 的配置信息")

            collection = self.db[collection_name]

            # 获取操作类型
            operation_match = re.search(r'db\.\w+\.(\w+)\(', query_str)
            if not operation_match:
                raise ValueError("无法解析操作类型,查询格式应为 'db.collection.operation(...)'")

            operation = operation_match.group(1)

            # 解析查询参数
            params_str = ""
            if '(' in query_str and ')' in query_str:
                start_idx = query_str.index('(') + 1
                end_idx = len(query_str) - 1

                # 找到最后一个右括号,考虑链式调用如 .find().limit()
                paren_count = 1
                for i in range(start_idx, len(query_str)):
                    if query_str[i] == '(':
                        paren_count += 1
                    elif query_str[i] == ')':
                        paren_count -= 1
                        if paren_count == 0:
                            end_idx = i
                            break

                params_str = query_str[start_idx:end_idx]

            # 解析链式调用的方法
            chain_methods = []
            remaining = query_str[end_idx + 1:]
            chain_pattern = r'\.(\w+)\(([^)]*)\)'
            for match in re.finditer(chain_pattern, remaining):
                method = match.group(1)
                args = match.group(2)
                if args:
                    try:
                        args = self._convert_query_params(args)
                    except:
                        args = args
                chain_methods.append((method, args))

            # 处理查询参数
            params = []
            if params_str.strip():
                # 分割多个参数
                param_parts = []
                depth = 0
                current = ""

                for char in params_str:
                    if char == ',' and depth == 0:
                        param_parts.append(current)
                        current = ""
                    else:
                        if char == '{' or char == '[':
                            depth += 1
                        elif char == '}' or char == ']':
                            depth -= 1
                        current += char

                if current:
                    param_parts.append(current)

                for part in param_parts:
                    try:
                        params.append(self._convert_query_params(part.strip()))
                    except:
                        params.append(part.strip())

            # 执行查询
            result = None

            if operation == 'find':
                query_filter = params[0] if params else {}
                projection = params[1] if len(params) > 1 else None

                cursor = collection.find(query_filter, projection)

                # 应用链式方法
                for method, args in chain_methods:
                    if method == 'limit':
                        cursor = cursor.limit(int(args))
                    elif method == 'skip':
                        cursor = cursor.skip(int(args))
                    elif method == 'sort':
                        cursor = cursor.sort(args)

                result = list(cursor)

            elif operation == 'findOne':
                query_filter = params[0] if params else {}
                projection = params[1] if len(params) > 1 else None

                doc = collection.find_one(query_filter, projection)
                result = [doc] if doc else []

            elif operation == 'aggregate':
                pipeline = params[0] if params else []

                # 安全检查聚合管道
                for stage in pipeline:
                    if isinstance(stage, dict):
                        for key in stage:
                            if key in ['$out', '$merge']:
                                raise ValueError(f"安全错误：禁止使用 {key} 阶段进行数据写入")

                cursor = collection.aggregate(pipeline)

                # 应用链式方法
                for method, args in chain_methods:
                    if method == 'limit':
                        cursor = cursor.limit(int(args))
                    elif method == 'skip':
                        cursor = cursor.skip(int(args))

                result = list(cursor)

            elif operation == 'count' or operation == 'countDocuments':
                query_filter = params[0] if params else {}
                count = collection.count_documents(query_filter)
                result = [{"count": count}]

            elif operation == 'distinct':
                if not params:
                    raise ValueError("distinct操作需要指定字段参数")

                field = params[0]
                query_filter = params[1] if len(params) > 1 else {}

                if isinstance(field, str) and field.startswith('"') and field.endswith('"'):
                    field = field[1:-1]

                values = collection.distinct(field, query_filter)
                result = [{"values": values}]

            else:
                raise ValueError(f"不支持的操作类型: {operation}")

            # 将MongoDB BSON对象转换为可序列化的对象
            return json.loads(json_util.dumps(result))

        except Exception as e:
            raise Exception(f"查询执行失败: {str(e)}")


def query_mongodb(query: str) -> List[Dict]:
    """
    主函数：执行MongoDB查询字符串

    Args:
        query: MongoDB查询字符串,例如 "db.customers.find({P: 0})"

    Returns:
        查询结果列表

    Examples:
        # 简单的查询
        query_mongodb("db.customers.find({P: 0})")

        # 带条件的查询
        query_mongodb("db.customers.find({x0: {$gt: -50}, y0: {$lt: 0}})")

        # 聚合查询
        query_mongodb("db.customers.aggregate([{$group: {_id: '$z', count: {$sum: 1}}}])")
    """

    logger.info(f"接收到的查询: {query}")

    db = MongoDBExecutor()

    try:
        results = db.execute_query(query)

        # 处理结果输出
        str_result = str(results)
        logger.info(f"查询结果长度: {len(str_result)}")

        if len(str_result) > 2000:
            logger.info(f"查询结果(截断): {str_result[:2000]}...")
            str_result = str_result[:2000] + "..."  # 截断结果
        else:
            logger.info(f"查询结果: {str_result}")

        re = str_result.replace('"', "").replace("'", "").replace("[", "").replace("]", "").replace("{", "").replace(
            "}", "").replace(" ", "")
        logger.info(f"格式化结果: {re}")

        return results
    except ValueError as e:
        error_msg = str(e)
        logger.error(f"值错误: {error_msg}")
        return {"error": error_msg}
    except Exception as e:
        error_msg = str(e)
        logger.error(f"执行查询时出错: {error_msg}")
        return {"error": f"执行查询时出错: {error_msg}"}
    finally:
        db.close()


if __name__ == "__main__":
    try:
        # 简单查询示例 - 基于配置文件中的示例数据
        result = query_mongodb("db.customers.find({P: 0}).limit(1)")
        logger.info(f"测试结果: {result}")
    except Exception as e:
        logger.error(f"测试失败: {str(e)}")