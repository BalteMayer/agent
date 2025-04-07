import logging
import sys
import os

# 在模块级别直接初始化logger
ROOT = "./"  # 调整为合适的路径
LOG_FILE = os.path.join(ROOT, "app.txt")
LOG_FORMAT = "[%(asctime)s] [%(levelname)s] %(message)s"

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format=LOG_FORMAT,
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)

# 创建logger实例
logger = logging.getLogger("app_logger")

# 可选：如果需要提供一个函数来获取logger
def get_logger():
    """获取应用的logger实例"""
    return logger