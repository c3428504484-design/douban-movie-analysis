"""
豆瓣电影 Top250 爬虫
负责抓取 https://movie.douban.com/top250 全部 10 页数据，
解析出每部电影的详细信息后保存为 CSV 原始数据文件。

运行方式：
    cd douban-movie-analysis
    python spider/douban_spider.py
"""
import csv
import random
import re
import sys
import time

import requests
from bs4 import BeautifulSoup

sys.path.append(".")  # 保证能导入根目录下的 config
from config import Config

# 请求头：不带 UA 会被豆瓣直接拒绝
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    ),
    "Accept-Language": "zh-CN,zh;q=0.9",
}

# CSV 表头（原始字段，清洗前的样子）
CSV_FIELDS = [
    "rank", "movie_id", "title_cn", "title_en", "alias",
    "director", "actors", "year", "country", "genre",
    "rating", "votes", "quote", "poster_url",
]


def fetch_page(page_no: int) -> str | None:
    """请求指定页码的 HTML，失败重试，最多 Config.SPIDER_MAX_RETRY 次"""
    url = Config.SPIDER_BASE_URL
    params = {"start": (page_no - 1) * 25}
    for attempt in range(1, Config.SPIDER_MAX_RETRY + 1):
        try:
            resp = requests.get(url, params=params, headers=HEADERS, timeout=15)
            if resp.status_code == 200:
                resp.encoding = "utf-8"
                return resp.text
            print(f"  第 {page_no} 页返回状态码 {resp.status_code}，重试 {attempt}")
        except requests.RequestException as exc:
            print(f"  第 {page_no} 页请求异常：{exc}，重试 {attempt}")
        time.sleep(2)
    return None


def parse_movie_item(item) -> dict | None:
    """
    解析单个电影条目的 <div class="item"> 节点。
    返回字段字典；解析失败返回 None。
    """
    try:
        # 排名与电影详情页链接（链接里含唯一 movie_id）
        rank = int(item.select_one("div.pic em").get_text(strip=True))
        link = item.select_one("div.pic a")["href"]
        movie_id = re.search(r"subject/(\d+)", link).group(1)

        # 标题：第一个 title 是中文名，第二个是外文名（可能不存在）
        titles = item.select("span.title")
        title_cn = titles[0].get_text(strip=True)
        title_en = ""
        if len(titles) > 1:
            title_en = titles[1].get_text(strip=True).replace("\xa0/\xa0", "").strip()

        # 别名（可能有，也可能没有）
        alias_node = item.select_one("span.other")
        alias = alias_node.get_text(strip=True).lstrip("/").strip() if alias_node else ""

        # 简介行：第一行是导演/主演，第二行是 年份 / 国家 / 类型
        info_p = item.select_one("div.bd p")
        lines = info_p.get_text().strip().split("\n")
        director, actors = "", ""
        for line in lines:
            if line.strip().startswith("导演"):
                parts = line.strip().split("主演")
                director = parts[0].replace("导演:", "").strip()
                if len(parts) > 1:
                    actors = parts[1].replace(":", "").strip()
        # 第二行形如 "1994 / 美国 / 犯罪 剧情"，按全角斜杠切分
        meta_line = lines[-1].strip()
        meta_parts = [p.strip() for p in meta_line.split("/")]
        year = meta_parts[0] if len(meta_parts) >= 1 else ""
        country = meta_parts[1] if len(meta_parts) >= 2 else ""
        genre = meta_parts[2] if len(meta_parts) >= 3 else ""

        # 评分
        rating = item.select_one("span.rating_num").get_text(strip=True)

        # 评价人数：形如 "3344931人评价"，从评分所在区块的文本里正则提取
        rating_block = item.select_one("span.rating_num").find_parent("div")
        votes_match = re.search(r"(\d+)人评价", rating_block.get_text())
        votes = votes_match.group(1) if votes_match else "0"

        # 一句话影评（可能没有，比如某些条目无 quote）
        quote_node = item.select_one("p.quote span")
        quote = quote_node.get_text(strip=True) if quote_node else ""

        # 海报图片地址
        poster_url = item.select_one("div.pic img")["src"]

        return {
            "rank": rank,
            "movie_id": movie_id,
            "title_cn": title_cn,
            "title_en": title_en,
            "alias": alias,
            "director": director,
            "actors": actors,
            "year": year,
            "country": country,
            "genre": genre,
            "rating": rating,
            "votes": votes,
            "quote": quote,
            "poster_url": poster_url,
        }
    except (AttributeError, IndexError, TypeError) as exc:
        print(f"  解析条目失败，跳过：{exc}")
        return None


def crawl_all() -> list:
    """爬取全部页面，返回所有电影的字典列表"""
    all_movies = []
    for page_no in range(1, Config.SPIDER_TOTAL_PAGES + 1):
        print(f"[{page_no}/{Config.SPIDER_TOTAL_PAGES}] 正在抓取第 {page_no} 页 ...")
        html = fetch_page(page_no)
        if html is None:
            print(f"  第 {page_no} 页重试用尽，跳过该页")
            continue

        soup = BeautifulSoup(html, "html.parser")
        items = soup.select("div.item")
        page_count = 0
        for item in items:
            movie = parse_movie_item(item)
            if movie:
                all_movies.append(movie)
                page_count += 1
        print(f"  本页解析成功 {page_count} 部")

        # 除最后一页外，礼貌等待，避免请求过快被封
        if page_no < Config.SPIDER_TOTAL_PAGES:
            delay = random.uniform(*Config.SPIDER_DELAY_RANGE)
            time.sleep(delay)

    print(f"爬取完成，共获取 {len(all_movies)} 部电影")
    return all_movies


def save_to_csv(movies: list, csv_path: str):
    """把爬取结果保存为 CSV 文件"""
    with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(movies)
    print(f"原始数据已保存到 {csv_path}")


if __name__ == "__main__":
    movie_list = crawl_all()
    if movie_list:
        save_to_csv(movie_list, Config.RAW_DATA_PATH)
    else:
        print("未爬到任何数据，请检查网络或稍后重试")
