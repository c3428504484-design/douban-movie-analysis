"""
数据清洗模块
读取爬虫产出的原始 CSV，做去重、类型转换、字段规整，
输出干净数据 CSV。这是"爬虫 → 清洗 → 入库"链路的第二步。

运行方式：
    cd douban-movie-analysis
    python data_cleaner.py
"""
import csv
import sys

sys.path.append(".")
from config import Config

# 清洗后数据的表头
CLEAN_FIELDS = [
    "rank", "movie_id", "title_cn", "title_en", "alias",
    "director", "actors", "year", "country", "main_genre",
    "genre", "rating", "votes", "quote", "poster_url",
]


def clean_field(text: str) -> str:
    """去掉网页转义留下的多余空字符与首尾空白"""
    if not text:
        return ""
    return text.replace("\xa0", " ").strip()


def to_int(text: str, default: int = 0) -> int:
    """安全转整数，转换失败返回默认值"""
    try:
        return int(float(text))
    except (ValueError, TypeError):
        return default


def to_float(text: str, default: float = 0.0) -> float:
    """安全转浮点数，转换失败返回默认值"""
    try:
        return float(text)
    except (ValueError, TypeError):
        return default


def clean_one_movie(raw: dict) -> dict | None:
    """
    清洗单条电影记录：
    1. 去除 &nbsp; 转义和多余空白
    2. 年份转整数、评分转浮点、评价人数转整数
    3. 国家取第一个（原始可能是"美国 中国"或"中国大陆 中国香港"）
    4. 类型取第一个作为主类型，完整类型保留
    """
    movie = {
        "rank": to_int(raw.get("rank")),
        "movie_id": clean_field(raw.get("movie_id")),
        "title_cn": clean_field(raw.get("title_cn")),
        # 英文名前面的 "/ " 分隔符属于页面噪声，一并去掉
        "title_en": clean_field(raw.get("title_en")).lstrip("/ ").strip(),
        "alias": clean_field(raw.get("alias")),
        "director": clean_field(raw.get("director")),
        "actors": clean_field(raw.get("actors")),
        "year": to_int(raw.get("year")),
        "country": clean_field(raw.get("country")),
        "genre": clean_field(raw.get("genre")),
        "rating": to_float(raw.get("rating")),
        "votes": to_int(raw.get("votes")),
        "quote": clean_field(raw.get("quote")),
        "poster_url": clean_field(raw.get("poster_url")),
    }

    # 关键字段缺失的脏数据直接丢弃
    if not movie["title_cn"] or movie["movie_id"] == "" or movie["rating"] <= 0:
        return None

    # 国家：原始数据里多个国家以空格分隔，取第一个作为主国家
    country = movie["country"].split(" ")[0] if movie["country"] else "其他"

    # 类型：取第一个标签作为主类型（如"犯罪 剧情"→"犯罪"）
    main_genre = movie["genre"].split(" ")[0] if movie["genre"] else "其他"

    movie["country"] = country
    movie["main_genre"] = main_genre

    # 整理字段顺序，与 CLEAN_FIELDS 一致
    return {field: movie[field] for field in CLEAN_FIELDS}


def run():
    """清洗主流程：读原始 CSV → 逐条清洗 → 去重 → 写干净 CSV"""
    try:
        with open(Config.RAW_DATA_PATH, "r", encoding="utf-8-sig") as f:
            raw_rows = list(csv.DictReader(f))
    except FileNotFoundError:
        print(f"找不到原始数据文件 {Config.RAW_DATA_PATH}，请先运行爬虫")
        return []

    print(f"读入原始数据 {len(raw_rows)} 条")

    cleaned, seen_ids = [], set()
    for raw in raw_rows:
        movie = clean_one_movie(raw)
        if movie is None:
            continue
        # 按 movie_id 去重，防止翻页重复抓到同一部电影
        if movie["movie_id"] in seen_ids:
            continue
        seen_ids.add(movie["movie_id"])
        cleaned.append(movie)

    with open(Config.CLEAN_DATA_PATH, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=CLEAN_FIELDS)
        writer.writeheader()
        writer.writerows(cleaned)

    print(f"清洗完成：原始 {len(raw_rows)} 条 → 干净 {len(cleaned)} 条")
    print(f"干净数据已保存到 {Config.CLEAN_DATA_PATH}")
    return cleaned


if __name__ == "__main__":
    run()
