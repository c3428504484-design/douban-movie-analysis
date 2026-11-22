"""
全局配置文件
集中管理数据库连接等参数，修改一处即可全局生效。
敏感信息（数据库密码、密钥）一律从环境变量读取，不写入代码，
避免提交到公开仓库造成泄露。
"""
import os


class Config:
    """项目全局配置类"""

    # ---- MySQL 数据库连接配置 ----
    DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
    DB_PORT = int(os.getenv("DB_PORT", "3306"))
    DB_USER = os.getenv("DB_USER", "root")
    # 密码从环境变量 DB_PASSWORD 读取，未设置时为空串
    DB_PASSWORD = os.getenv("DB_PASSWORD", "")
    DB_NAME = os.getenv("DB_NAME", "douban_movie")
    DB_CHARSET = "utf8mb4"

    # ---- 爬虫配置 ----
    SPIDER_BASE_URL = "https://movie.douban.com/top250"
    SPIDER_TOTAL_PAGES = 10         # Top250 一共 10 页，每页 25 条
    SPIDER_DELAY_RANGE = (1.0, 2.5) # 每页之间的随机等待秒数区间（ polite 爬取，别太快 ）
    SPIDER_MAX_RETRY = 3            # 单页最大重试次数

    # ---- Flask 配置 ----
    FLASK_HOST = os.getenv("FLASK_HOST", "127.0.0.1")
    FLASK_PORT = int(os.getenv("FLASK_PORT", "5000"))
    # 密钥从环境变量 SECRET_KEY 读取，未设置时使用开发默认值（生产环境请务必覆盖）
    SECRET_KEY = os.getenv("SECRET_KEY", "change-me-in-production")

    # ---- 文件路径 ----
    RAW_DATA_PATH = "data/movies_raw.csv"       # 爬虫原始数据
    CLEAN_DATA_PATH = "data/movies_clean.csv"   # 清洗后的数据
    MODEL_PATH = "model/rating_model.pkl"       # 训练好的评分预测模型


def get_db_config() -> dict:
    """返回 PyMySQL 连接所需的参数字典"""
    return {
        "host": Config.DB_HOST,
        "port": Config.DB_PORT,
        "user": Config.DB_USER,
        "password": Config.DB_PASSWORD,
        "database": Config.DB_NAME,
        "charset": Config.DB_CHARSET,
    }
