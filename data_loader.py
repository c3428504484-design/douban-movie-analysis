"""
数据入库模块
把清洗后的 CSV 数据写入 MySQL 的 movies 表。
入库前会自动建库建表（不存在时），并清空旧数据保证可重复运行。

运行方式：
    cd douban-movie-analysis
    python data_loader.py
"""
import csv
import sys

import pymysql

sys.path.append(".")
from config import Config, get_db_config

# 电影信息表结构（注：rank 是 MySQL 8.0 保留字，故列名用 top_rank）
CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS movies (
    id         INT PRIMARY KEY AUTO_INCREMENT COMMENT '自增主键',
    top_rank   INT          NOT NULL COMMENT 'Top250 排名',
    movie_id   VARCHAR(20)  NOT NULL UNIQUE COMMENT '豆瓣条目 ID',
    title_cn   VARCHAR(100) NOT NULL COMMENT '中文名',
    title_en   VARCHAR(200) DEFAULT '' COMMENT '外文名',
    alias      VARCHAR(300) DEFAULT '' COMMENT '别名',
    director   VARCHAR(200) DEFAULT '' COMMENT '导演',
    actors     VARCHAR(500) DEFAULT '' COMMENT '主演',
    year       INT          DEFAULT 0 COMMENT '上映年份',
    country    VARCHAR(50)  DEFAULT '' COMMENT '主国家/地区',
    main_genre VARCHAR(50)  DEFAULT '' COMMENT '主类型',
    genre      VARCHAR(100) DEFAULT '' COMMENT '完整类型标签',
    rating     DECIMAL(3,1) DEFAULT 0 COMMENT '豆瓣评分',
    votes      INT          DEFAULT 0 COMMENT '评价人数',
    quote      VARCHAR(500) DEFAULT '' COMMENT '一句话影评',
    poster_url VARCHAR(300) DEFAULT '' COMMENT '海报图片地址',
    INDEX idx_year (year),
    INDEX idx_country (country),
    INDEX idx_main_genre (main_genre)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='豆瓣电影 Top250 数据表';
"""

INSERT_SQL = """
INSERT INTO movies
    (top_rank, movie_id, title_cn, title_en, alias, director, actors,
     year, country, main_genre, genre, rating, votes, quote, poster_url)
VALUES
    (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
"""


def ensure_database():
    """连 MySQL 服务器（不指定库），不存在则创建目标数据库"""
    cfg = get_db_config()
    cfg.pop("database")
    conn = pymysql.connect(**cfg)
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                f"CREATE DATABASE IF NOT EXISTS `{Config.DB_NAME}` "
                f"DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            )
        conn.commit()
        print(f"数据库 `{Config.DB_NAME}` 已就绪")
    finally:
        conn.close()


def run():
    """建库建表 → 清空旧数据 → 批量导入干净 CSV"""
    ensure_database()

    try:
        with open(Config.CLEAN_DATA_PATH, "r", encoding="utf-8-sig") as f:
            rows = list(csv.DictReader(f))
    except FileNotFoundError:
        print(f"找不到干净数据文件 {Config.CLEAN_DATA_PATH}，请先运行 data_cleaner.py")
        return 0

    conn = pymysql.connect(**get_db_config())
    try:
        with conn.cursor() as cursor:
            cursor.execute(CREATE_TABLE_SQL)
            # 清空旧数据，保证脚本可以反复执行
            cursor.execute("TRUNCATE TABLE movies")

            params_list = [
                (
                    int(row["rank"]), row["movie_id"], row["title_cn"],
                    row["title_en"], row["alias"], row["director"], row["actors"],
                    int(row["year"]), row["country"], row["main_genre"],
                    row["genre"], float(row["rating"]), int(row["votes"]),
                    row["quote"], row["poster_url"],
                )
                for row in rows
            ]
            cursor.executemany(INSERT_SQL, params_list)
        conn.commit()
        print(f"成功导入 {len(rows)} 条电影数据到 MySQL")
    finally:
        conn.close()
    return len(rows)


if __name__ == "__main__":
    run()
