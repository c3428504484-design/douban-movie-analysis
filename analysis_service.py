"""
统计分析服务模块
负责从 MySQL 里读取电影数据并聚合成各类统计结果，
供 Flask 接口返回给前端 ECharts 画图使用。
"""
from db_helper import query_all, query_one


def get_overview() -> dict:
    """概览卡片：总数、平均分、最高分、总评价人数"""
    row = query_one(
        """
        SELECT COUNT(*)        AS total,
               AVG(rating)     AS avg_rating,
               MAX(rating)     AS max_rating,
               SUM(votes)      AS total_votes
        FROM movies
        """
    )
    return {
        "total": int(row["total"]),
        "avg_rating": round(float(row["avg_rating"]), 2),
        "max_rating": float(row["max_rating"]),
        "total_votes": int(row["total_votes"]),
    }


def get_rating_distribution() -> list:
    """评分分布直方图：按 0.5 分一档统计电影数量"""
    return [
        {"name": row["score_range"], "value": int(row["count"])}
        for row in query_all(
            """
            SELECT CONCAT(FLOOR(rating * 2) / 2, '分') AS score_range,
                   COUNT(*) AS count
            FROM movies
            GROUP BY score_range
            ORDER BY score_range
            """
        )
    ]


def get_decade_trend() -> list:
    """年代趋势折线：每个年代的平均分与上榜数量"""
    return [
        {
            "decade": f"{row['decade']}s",
            "count": int(row["count"]),
            "avg_rating": round(float(row["avg_rating"]), 2),
        }
        for row in query_all(
            """
            SELECT (year DIV 10) * 10      AS decade,
                   COUNT(*)                AS count,
                   AVG(rating)             AS avg_rating
            FROM movies
            WHERE year > 0
            GROUP BY decade
            ORDER BY decade
            """
        )
    ]


def get_country_rank(top_n: int = 10) -> list:
    """上榜数量 Top N 国家/地区"""
    return [
        {"name": row["country"], "value": int(row["count"])}
        for row in query_all(
            """
            SELECT country, COUNT(*) AS count
            FROM movies
            GROUP BY country
            ORDER BY count DESC
            LIMIT %s
            """,
            (top_n,)
        )
    ]


def get_genre_stats(top_n: int = 12) -> list:
    """类型统计饼图：按主类型统计数量与平均分"""
    return [
        {
            "name": row["main_genre"],
            "value": int(row["count"]),
            "avg_rating": round(float(row["avg_rating"]), 2),
        }
        for row in query_all(
            """
            SELECT main_genre, COUNT(*) AS count, AVG(rating) AS avg_rating
            FROM movies
            GROUP BY main_genre
            ORDER BY count DESC
            LIMIT %s
            """,
            (top_n,)
        )
    ]


def get_votes_rank(top_n: int = 10) -> list:
    """评价人数 Top N 榜（人气榜）"""
    return [
        {
            "title": row["title_cn"],
            "votes": int(row["votes"]),
            "rating": float(row["rating"]),
        }
        for row in query_all(
            """
            SELECT title_cn, votes, rating
            FROM movies
            ORDER BY votes DESC
            LIMIT %s
            """,
            (top_n,)
        )
    ]


def get_director_rank(top_n: int = 10) -> list:
    """上榜作品最多的导演 Top N"""
    return [
        {
            "director": row["director"],
            "count": int(row["count"]),
            "avg_rating": round(float(row["avg_rating"]), 2),
        }
        for row in query_all(
            """
            SELECT director, COUNT(*) AS count, AVG(rating) AS avg_rating
            FROM movies
            WHERE director != ''
            GROUP BY director
            ORDER BY count DESC, avg_rating DESC
            LIMIT %s
            """,
            (top_n,)
        )
    ]


def get_wordcloud_data() -> list:
    """词云数据：把每部电影的完整类型标签拆开计数"""
    rows = query_all("SELECT genre, votes FROM movies")
    counter = {}
    for row in rows:
        for genre in str(row["genre"]).split(" "):
            genre = genre.strip()
            if genre:
                counter[genre] = counter.get(genre, 0) + 1
    # 按出现次数降序，取前 60 个标签画词云
    sorted_items = sorted(counter.items(), key=lambda x: x[1], reverse=True)[:60]
    return [{"name": name, "value": value} for name, value in sorted_items]


def get_movie_table(keyword: str = "", limit: int = 250) -> list:
    """电影明细表格：支持按片名/导演模糊搜索"""
    if keyword:
        rows = query_all(
            """
            SELECT top_rank, title_cn, title_en, director, year, country,
                   main_genre, rating, votes
            FROM movies
            WHERE title_cn LIKE %s OR director LIKE %s OR main_genre LIKE %s
            ORDER BY top_rank
            LIMIT %s
            """,
            (f"%{keyword}%", f"%{keyword}%", f"%{keyword}%", limit),
        )
    else:
        rows = query_all(
            """
            SELECT top_rank, title_cn, title_en, director, year, country,
                   main_genre, rating, votes
            FROM movies
            ORDER BY top_rank
            LIMIT %s
            """,
            (limit,),
        )
    return [
        {
            "rank": int(row["top_rank"]),
            "title_cn": row["title_cn"],
            "title_en": row["title_en"],
            "director": row["director"],
            "year": int(row["year"]),
            "country": row["country"],
            "main_genre": row["main_genre"],
            "rating": float(row["rating"]),
            "votes": int(row["votes"]),
        }
        for row in rows
    ]
