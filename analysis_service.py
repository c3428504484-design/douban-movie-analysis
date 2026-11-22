"""
统计分析服务模块
负责从 MySQL 里读取电影数据并聚合成各类统计结果，
供 Flask 接口返回给前端 ECharts 画图使用。
"""
import math

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
    # 表为空时 AVG/MAX/SUM 返回 NULL，统一兜底为 0，避免 float(None) 报错
    row = row or {}
    return {
        "total": int(row.get("total") or 0),
        "avg_rating": round(float(row.get("avg_rating") or 0), 2),
        "max_rating": float(row.get("max_rating") or 0),
        "total_votes": int(row.get("total_votes") or 0),
    }


def get_rating_distribution() -> list:
    """评分分布直方图：按 0.5 分一档统计电影数量"""
    return [
        {"name": row["score_range"], "value": int(row["count"])}
        for row in query_all(
            """
            SELECT CONCAT(ROUND(FLOOR(rating * 2) / 2, 1), '分') AS score_range,
                   COUNT(*) AS count
            FROM movies
            GROUP BY score_range
            ORDER BY MIN(rating)
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


def get_rating_votes_scatter() -> list:
    """评分 × 评价人数散点：观察高评分与高人气之间的关系"""
    return [
        {
            "name": row["title_cn"],
            "rating": float(row["rating"]),
            "votes": int(row["votes"]),
        }
        for row in query_all("SELECT title_cn, rating, votes FROM movies")
    ]


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


# ---------------- 单片详情分析（按片名查询页用） ----------------

# 基于类型的受众画像推测（启发式规则，非真实用户数据，前端已注明）
AUDIENCE_PROFILES = {
    "动画": {"18岁以下": 35, "18-25岁": 30, "26-35岁": 22, "36岁以上": 13},
    "喜剧": {"18岁以下": 15, "18-25岁": 35, "26-35岁": 30, "36岁以上": 20},
    "爱情": {"18岁以下": 12, "18-25岁": 42, "26-35岁": 30, "36岁以上": 16},
    "动作": {"18岁以下": 10, "18-25岁": 38, "26-35岁": 34, "36岁以上": 18},
    "科幻": {"18岁以下": 12, "18-25岁": 40, "26-35岁": 32, "36岁以上": 16},
    "悬疑": {"18岁以下": 6, "18-25岁": 34, "26-35岁": 38, "36岁以上": 22},
    "惊悚": {"18岁以下": 5, "18-25岁": 40, "26-35岁": 35, "36岁以上": 20},
    "犯罪": {"18岁以下": 4, "18-25岁": 28, "26-35岁": 40, "36岁以上": 28},
    "战争": {"18岁以下": 4, "18-25岁": 22, "26-35岁": 36, "36岁以上": 38},
    "历史": {"18岁以下": 4, "18-25岁": 20, "26-35岁": 36, "36岁以上": 40},
    "传记": {"18岁以下": 5, "18-25岁": 25, "26-35岁": 38, "36岁以上": 32},
    "冒险": {"18岁以下": 18, "18-25岁": 36, "26-35岁": 30, "36岁以上": 16},
    "奇幻": {"18岁以下": 20, "18-25岁": 38, "26-35岁": 28, "36岁以上": 14},
}
DEFAULT_AUDIENCE = {"18岁以下": 8, "18-25岁": 32, "26-35岁": 36, "36岁以上": 24}


def _find_movie(keyword: str) -> dict | None:
    """先精确匹配片名，找不到再模糊匹配，取排名最靠前的一部"""
    row = query_one(
        "SELECT * FROM movies WHERE title_cn = %s", (keyword,)
    )
    if row is None:
        row = query_one(
            "SELECT * FROM movies WHERE title_cn LIKE %s ORDER BY top_rank",
            (f"%{keyword}%",),
        )
    return row


def get_movie_detail(keyword: str) -> dict | None:
    """
    按片名汇总一部电影的全方位分析：
    基本信息、评分/热度分位、与同类型/同年代/全体均分对比、
    评分定位、同类型年代口碑趋势、受众画像、同导演作品、相似推荐。
    """
    movie = _find_movie(keyword)
    if movie is None:
        return None

    rating = float(movie["rating"])
    votes = int(movie["votes"])
    decade = (int(movie["year"]) // 10) * 10

    # 分位数：本片评分/评价人数在 Top250 中超过百分之多少的电影
    total = int(query_one("SELECT COUNT(*) AS c FROM movies")["c"])
    rating_below = int(query_one(
        "SELECT COUNT(*) AS c FROM movies WHERE rating < %s", (rating,)
    )["c"])
    votes_below = int(query_one(
        "SELECT COUNT(*) AS c FROM movies WHERE votes < %s", (votes,)
    )["c"])

    # 对比基准：同类型均分、同年代均分、全体均分
    genre_row = query_one(
        "SELECT AVG(rating) AS a, COUNT(*) AS c FROM movies WHERE main_genre = %s",
        (movie["main_genre"],),
    )
    decade_avg = query_one(
        "SELECT AVG(rating) AS a FROM movies WHERE (year DIV 10) * 10 = %s",
        (decade,),
    )
    overall_avg = query_one("SELECT AVG(rating) AS a FROM movies")

    # 口碑趋势：同类型影片随年代的平均分走势（真实数据，供参考）
    genre_trend = [
        {
            "decade": f"{row['decade']}s",
            "avg_rating": round(float(row["avg_rating"]), 2),
            "count": int(row["count"]),
        }
        for row in query_all(
            """
            SELECT (year DIV 10) * 10 AS decade,
                   AVG(rating) AS avg_rating, COUNT(*) AS count
            FROM movies
            WHERE main_genre = %s AND year > 0
            GROUP BY decade
            ORDER BY decade
            """,
            (movie["main_genre"],),
        )
    ]

    # 同导演其他作品（按评分降序）
    director_works = [
        {
            "title_cn": row["title_cn"],
            "year": int(row["year"]),
            "rating": float(row["rating"]),
        }
        for row in query_all(
            """
            SELECT title_cn, year, rating FROM movies
            WHERE director = %s AND movie_id != %s
            ORDER BY rating DESC
            LIMIT 8
            """,
            (movie["director"], movie["movie_id"]),
        )
    ] if movie["director"] else []

    # 相似推荐（复用推荐模块，延迟导入避免循环依赖）
    from model import recommender
    similar = recommender.recommend_by_movie(movie["movie_id"], top_n=5)

    return {
        "movie": {
            "rank": int(movie["top_rank"]),
            "movie_id": movie["movie_id"],
            "title_cn": movie["title_cn"],
            "title_en": movie["title_en"],
            "director": movie["director"],
            "actors": movie["actors"],
            "year": int(movie["year"]),
            "country": movie["country"],
            "main_genre": movie["main_genre"],
            "genre": movie["genre"],
            "rating": rating,
            "votes": votes,
            "quote": movie["quote"],
            "poster_url": movie["poster_url"],
        },
        "percentile": {
            "rating": round(rating_below / total * 100, 1) if total else 0,
            "votes": round(votes_below / total * 100, 1) if total else 0,
        },
        "compare": {
            "self": rating,
            "genre": movie["main_genre"],
            "genre_avg": round(float(genre_row["a"]), 2) if genre_row and genre_row["a"] else 0,
            "genre_count": int(genre_row["c"]) if genre_row else 0,
            "decade": f"{decade}s",
            "decade_avg": round(float(decade_avg["a"]), 2) if decade_avg and decade_avg["a"] else 0,
            "overall_avg": round(float(overall_avg["a"]), 2) if overall_avg and overall_avg["a"] else 0,
        },
        "rating_dist": get_rating_distribution(),
        # 本片所在的评分档位标签（与评分分布图的分档口径一致）
        "rating_bucket": f"{math.floor(rating * 2) / 2}分",
        "genre_trend": genre_trend,
        "audience": AUDIENCE_PROFILES.get(movie["main_genre"], DEFAULT_AUDIENCE),
        "director_works": director_works,
        "similar": similar,
    }
