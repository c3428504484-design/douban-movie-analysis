"""
数据库工具模块
封装 PyMySQL 的连接与常用增删查操作，其他模块统一从这里拿连接。
"""
import pymysql

from config import get_db_config


def get_connection():
    """获取一个 MySQL 数据库连接（每次调用新建，用完记得 close）"""
    return pymysql.connect(**get_db_config())


def execute(sql: str, params: tuple = ()) -> int:
    """执行写操作（INSERT / UPDATE / DELETE），返回受影响行数"""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            affected = cursor.execute(sql, params)
        conn.commit()
        return affected
    finally:
        conn.close()


def execute_many(sql: str, params_list: list) -> int:
    """批量执行写操作，适合一次性导入几百条数据"""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            affected = cursor.executemany(sql, params_list)
        conn.commit()
        return affected
    finally:
        conn.close()


def query_all(sql: str, params: tuple = ()) -> list:
    """查询多行结果，返回字典列表（列名作 key）"""
    conn = get_connection()
    try:
        with conn.cursor(pymysql.cursors.DictCursor) as cursor:
            cursor.execute(sql, params)
            return cursor.fetchall()
    finally:
        conn.close()


def query_one(sql: str, params: tuple = ()) -> dict | None:
    """查询单行结果，没有结果时返回 None"""
    rows = query_all(sql + " LIMIT 1", params)
    return rows[0] if rows else None
