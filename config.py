"""
全局配置文件
集中管理数据库连接等参数，修改一处即可全局生效。
"""


class Config:
    """项目全局配置类"""

    # ---- MySQL 数据库连接配置 ----
    DB_HOST = "127.0.0.1"
    DB_PORT = 3306
    DB_USER = "root"
    DB_PASSWORD = "060521"          # ← 改成你自己的 MySQL 密码
    DB_NAME = "douban_movie"
    DB_CHARSET = "utf8mb4"

    # ---- 爬虫配置 ----
    SPIDER_BASE_URL = "https://movie.douban.com/top250"
    SPIDER_TOTAL_PAGES = 10         # Top250 一共 10 页，每页 25 条
    SPIDER_DELAY_RANGE = (1.0, 2.5) # 每页之间的随机等待秒数区间（ polite 爬取，别太快 ）
    SPIDER_MAX_RETRY = 3            # 单页最大重试次数

    # ---- Flask 配置 ----
    FLASK_HOST = "127.0.0.1"
    FLASK_PORT = 5000
    SECRET_KEY = "douban-movie-analysis-2026"

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
