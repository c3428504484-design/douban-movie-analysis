"""
评分预测模型模块
基于 sklearn 训练"电影评分预测"模型：
    特征：上映年份、评价人数（取对数）、类型、国家/地区
    目标：豆瓣评分
用线性回归与随机森林两种算法对比，保留效果更好的模型存盘。

运行方式（训练并保存模型）：
    cd douban-movie-analysis
    python model/rating_model.py
"""
import math
import os
import pickle
import sys

import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import train_test_split

sys.path.append(".")
from config import Config
from db_helper import query_all

# 参与建模的类别特征取值（训练时确定，预测时复用）
TOP_GENRES = ["剧情", "喜剧", "爱情", "科幻", "动作", "犯罪",
              "动画", "悬疑", "惊悚", "冒险", "传记", "奇幻"]
TOP_COUNTRIES = ["中国大陆", "美国", "日本", "中国香港", "韩国",
                 "法国", "英国", "意大利", "德国", "印度"]


def load_dataframe() -> pd.DataFrame:
    """从 MySQL 读取电影数据并整理成特征矩阵"""
    rows = query_all(
        """
        SELECT title_cn, year, country, genre, rating, votes
        FROM movies
        WHERE year > 0 AND votes > 0 AND rating > 0
        """
    )
    if not rows:
        raise RuntimeError("数据库里没有电影数据，请先运行 run_all.py")

    df = pd.DataFrame(rows)
    # 评价人数跨度过大（几千到几千万），取对数压缩
    df["votes_log"] = df["votes"].apply(lambda v: math.log10(int(v) + 1))
    return df


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    """把原始字段转成模型特征：数值列 + 类型/国家独热列"""
    features = pd.DataFrame()
    features["year"] = df["year"].astype(int)
    features["votes_log"] = df["votes_log"].astype(float)
    for genre in TOP_GENRES:
        features[f"genre_{genre}"] = df["genre"].astype(str).apply(
            lambda g: 1 if genre in g else 0
        )
    for country in TOP_COUNTRIES:
        features[f"country_{country}"] = df["country"].astype(str).apply(
            lambda c: 1 if c == country else 0
        )
    return features


def train_and_save():
    """训练两个模型对比，保存更优者到本地 pkl 文件"""
    df = load_dataframe()
    X = build_features(df)
    y = df["rating"].astype(float)

    # 随机划分训练/测试集，测试集占 20%
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )
    print(f"训练集 {len(X_train)} 条 / 测试集 {len(X_test)} 条")

    candidates = {
        "线性回归": LinearRegression(),
        "随机森林": RandomForestRegressor(
            n_estimators=200, max_depth=8, random_state=42
        ),
    }

    best_name, best_model, best_score = None, None, -1
    for name, model in candidates.items():
        model.fit(X_train, y_train)
        pred = model.predict(X_test)
        r2 = r2_score(y_test, pred)
        mae = mean_absolute_error(y_test, pred)
        print(f"  {name}: R² = {r2:.4f}, 平均绝对误差 MAE = {mae:.4f} 分")
        if r2 > best_score:
            best_name, best_model, best_score = name, model, r2

    # 模型连同特征取值表一起存盘，预测时需要用同一套类别特征
    payload = {
        "model": best_model,
        "model_name": best_name,
        "r2": best_score,
        "genres": TOP_GENRES,
        "countries": TOP_COUNTRIES,
    }
    os.makedirs(os.path.dirname(Config.MODEL_PATH), exist_ok=True)
    with open(Config.MODEL_PATH, "wb") as f:
        pickle.dump(payload, f)
    print(f"已选用「{best_name}」，模型保存到 {Config.MODEL_PATH}")


def load_model() -> dict:
    """加载已训练的模型（Flask 启动时调用一次）"""
    with open(Config.MODEL_PATH, "rb") as f:
        return pickle.load(f)


def predict_rating(payload: dict, year: int, genre: str,
                   country: str, votes: int) -> float:
    """
    用已保存的模型预测评分。
    payload 是 load_model() 返回的字典。
    """
    row = {
        "year": [year],
        "votes_log": [math.log10(votes + 1)],
    }
    for g in payload["genres"]:
        row[f"genre_{g}"] = [1 if g in genre else 0]
    for c in payload["countries"]:
        row[f"country_{c}"] = [1 if c == country else 0]
    X = pd.DataFrame(row)
    prediction = float(payload["model"].predict(X)[0])
    # 豆瓣评分范围 1~10，把结果裁剪回合法区间
    return round(min(max(prediction, 1.0), 10.0), 1)


if __name__ == "__main__":
    train_and_save()
