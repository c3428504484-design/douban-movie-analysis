"""
相似电影推荐模块
基于电影类型的余弦相似度做"看过这部 → 推荐这几部"。
思路：把每部电影的类型标签转成向量，计算两两相似度，
再叠加同国家加分，取相似度最高的前 N 部作为推荐结果。
"""
import math

from db_helper import query_all


def _genre_vector(genre_text: str) -> set:
    """把"犯罪 剧情"这样的类型串拆成标签集合"""
    return {g for g in str(genre_text).split(" ") if g}


def _cosine_similarity(set_a: set, set_b: set) -> float:
    """
    集合视角的余弦相似度：
        相交标签数 / (sqrt(|A|) * sqrt(|B|))
    标签向量只有 0/1 两种取值，可以化简成这个形式。
    """
    if not set_a or not set_b:
        return 0.0
    common = len(set_a & set_b)
    return common / math.sqrt(len(set_a) * len(set_b))


def get_all_movies() -> list:
    """取出推荐所需的全部电影字段（ID、片名、类型、国家、评分）"""
    return query_all(
        """
        SELECT movie_id, title_cn, genre, country, rating, year, main_genre
        FROM movies
        ORDER BY top_rank
        """
    )


def recommend_by_movie(movie_id: str, top_n: int = 6) -> list:
    """给定一部电影，返回最相似的 top_n 部电影（含相似度得分）"""
    movies = get_all_movies()
    target = next((m for m in movies if m["movie_id"] == movie_id), None)
    if target is None:
        return []

    target_genres = _genre_vector(target["genre"])
    scored = []
    for movie in movies:
        if movie["movie_id"] == target["movie_id"]:
            continue
        similarity = _cosine_similarity(target_genres, _genre_vector(movie["genre"]))
        # 同国家/地区的小幅加分，让推荐更贴近口味
        if movie["country"] and movie["country"] == target["country"]:
            similarity += 0.05
        scored.append((movie, similarity))

    # 相似度降序，平分时评分高的排前面
    scored.sort(key=lambda pair: (pair[1], pair[0]["rating"]), reverse=True)
    return [
        {
            "title_cn": movie["title_cn"],
            "year": int(movie["year"]),
            "country": movie["country"],
            "genre": movie["genre"],
            "rating": float(movie["rating"]),
            "similarity": round(min(similarity, 1.0), 3),
        }
        for movie, similarity in scored[:top_n]
    ]
