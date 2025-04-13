#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import os
import pymysql
import re
from typing import Dict, List, Any, Union, Optional
from utils import logger, load_db_config


class DatabaseExecutor:
    """
    通过config.json文件访问MySQL数据库,执行智能体生成的查询指令
    """

    def __init__(self):
        """
        初始化数据库执行器

        Args:
            config_path: 配置文件路径,默认为config.json
        """




        self.config = self._load_config()
        self.connection = None

    def _load_config(self) -> Dict:
        """
        加载数据库配置

        Args:
            config_path: 配置文件路径

        Returns:
            配置字典
        """
        try:
            config = load_db_config()
            if 'mysql' not in config:
                raise ValueError("配置文件中缺少MySQL配置项")
            return config['mysql']
        except FileNotFoundError:
            raise FileNotFoundError(f"配置文件不存在")
        except json.JSONDecodeError:
            raise ValueError(f"配置文件格式不正确")

    def connect(self) -> None:
        """
        连接到MySQL数据库
        """
        try:
            self.connection = pymysql.connect(
                host=self.config.get('host', 'localhost'),
                port=self.config.get('port', 3306),
                user=self.config.get('username', 'root'),  # 使用username与配置文件保持一致
                password=self.config.get('password', ''),
                database=self.config.get('database', ''),
                charset=self.config.get('charset', 'utf8mb4')
            )
        except Exception as e:
            raise ConnectionError(f"连接数据库失败: {str(e)}")

    def close(self) -> None:
        """
        关闭数据库连接
        """
        if self.connection and self.connection.open:
            self.connection.close()

    def _is_select_only(self, query: str) -> bool:
        """
        检查SQL查询是否只包含SELECT语句,不包含增删改操作

        Args:
            query: SQL查询字符串

        Returns:
            如果是只读查询则返回True,否则返回False
        """
        # 去除注释和多余空格
        query = re.sub(r'--.*$', '', query, flags = re.MULTILINE)
        query = re.sub(r'/\*[\s\S]*?\*/', '', query)
        query = query.strip()

        # 检查是否为SELECT语句
        if not re.match(r'^SELECT\s', query, re.IGNORECASE):
            return False

        # 检查是否包含INSERT, UPDATE, DELETE, ALTER, CREATE, DROP, TRUNCATE, REPLACE, MERGE等操作
        disallowed_patterns = [
            r'\sINSERT\s', r'\sUPDATE\s', r'\sDELETE\s', r'\sALTER\s',
            r'\sCREATE\s', r'\sDROP\s', r'\sTRUNCATE\s', r'\sREPLACE\s',
            r'\sMERGE\s', r'\sEXEC\s', r'\sEXECUTE\s', r'\sSET\s',
            r';.*INSERT', r';.*UPDATE', r';.*DELETE', r';.*ALTER',
            r';.*CREATE', r';.*DROP', r';.*TRUNCATE', r';.*REPLACE',
            r';.*MERGE', r';.*EXEC', r';.*EXECUTE', r';.*SET'
        ]

        for pattern in disallowed_patterns:
            if re.search(pattern, query, re.IGNORECASE):
                return False

        return True

    def execute_query(self, query: str) -> List[Dict]:
        """
        执行SQL查询

        Args:
            query: SQL查询字符串

        Returns:
            查询结果列表
        """
        if not self.connection or not self.connection.open:
            self.connect()

        # 安全检查,确保只执行SELECT查询
        if not self._is_select_only(query):
            raise ValueError("安全错误：只允许执行SELECT查询,禁止执行增删改操作")

        try:
            with self.connection.cursor(pymysql.cursors.DictCursor) as cursor:
                cursor.execute(query)
                result = cursor.fetchall()
                return result
        except Exception as e:
            self.connection.rollback()
            raise Exception(f"查询执行失败: {str(e)}")


def query_database(query: str, config_path: str = "config.json") -> str:
    """
    主函数：执行SQL查询字符串

    Args:
        query: 智能体生成的SQL查询字符串
        config_path: 配置文件路径

    Returns:
        查询结果列表

    Examples:
        # 简单的查询
        execute_sql_query("SELECT * FROM users WHERE age > 18")

        # 带条件的查询
        execute_sql_query("SELECT id, name FROM products WHERE price BETWEEN 100 AND 200 ORDER BY price ASC")

        # 带聚合函数的查询
        execute_sql_query("SELECT category, COUNT(*) as count FROM products GROUP BY category HAVING count > 5")
    """

    logger.info(f"接收到的查询: {query}")

    # 安全检查
    if any(keyword.upper() in query.upper() for keyword in
           ["INSERT", "UPDATE", "DELETE", "ALTER", "CREATE",
            "DROP", "TRUNCATE", "REPLACE", "MERGE", "EXEC", "EXECUTE"]):
        return {"error": "安全错误：查询包含禁止的操作,只允许SELECT查询"}

    db = DatabaseExecutor()

    logger.info(len(db.execute_query(query)))
    try:
        results = f"{db.execute_query(query)}".replace('"', "").replace("'", "").replace("[","").replace("]","").replace("{","").replace("}","").replace(" ","")
        logger.info(f"查询结果: {results}")
        logger.info(f"查询结果长度: {len(results)}")
        if len(results) > 2000:
            results = results[:2000] + "..."  # 截断结果
        else:
            results = results


        logger.info(f"查询结果: {results}")

        re = f"{results}"

        return db.execute_query(query)
    except ValueError as e:
        return {"error": str(e)}
    except Exception as e:
        return {"error": f"执行查询时出错: {str(e)}"}
    finally:
        db.close()


if __name__ == "__main__":
    try:
        # 简单查询示例 - 根据提供的数据库结构进行查询
        result = query_database("SELECT * FROM Data WHERE jlugroup = '视觉组' AND sex = '女' LIMIT 1;")



    except Exception as e:
        logger.info(f"测试失败: {str(e)}")