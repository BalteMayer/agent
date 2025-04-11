import logging
import os
import sys
from datetime import datetime

# 日志格式
DEFAULT_LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
# 日志目录
DEFAULT_LOG_DIR = 'data/logs'


def setup_logger(name, log_file=None, level=logging.INFO, formatter=None):
    """配置并返回日志记录器

    参数:
    - name: 日志记录器名称
    - log_file: 日志文件路径(可选)
    - level: 日志级别
    - formatter: 日志格式化器(可选)

    返回:
    - 配置好的日志记录器
    """
    # 创建日志记录器
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # 防止日志重复
    if logger.handlers:
        return logger

    # 设置格式
    if formatter is None:
        formatter = logging.Formatter(DEFAULT_LOG_FORMAT)

    # 创建控制台处理程序
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # 如果指定了文件，则添加文件处理程序
    if log_file:
        # 确保日志目录存在
        log_dir = os.path.dirname(log_file)
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)

        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


def get_default_logger():
    """获取默认的应用日志记录器"""
    # 确保logs目录存在
    os.makedirs(DEFAULT_LOG_DIR, exist_ok=True)

    # 生成日志文件名，包含日期
    current_date = datetime.now().strftime('%Y-%m-%d')
    log_file = os.path.join(DEFAULT_LOG_DIR, f'agent_{current_date}.log')

    return setup_logger('agent', log_file)


# 默认日志记录器实例
logger = get_default_logger()