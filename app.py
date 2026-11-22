"""
Flask 主应用
Web 服务入口：提供页面路由 + JSON 数据接口。
页面：数据可视化大屏 / 评分预测 / 相似电影推荐
接口：/api/* 系列供前端 ECharts 异步取数

运行方式：
    cd douban-movie-analysis
    python app.py
    浏览器打开 http://127.0.0.1:5000
"""
from flask import Flask, jsonify, render_template, request

import analysis_service
from config import Config
from model import deepseek_client, plot_analyzer, rating_model, recommender

app = Flask(__name__)
app.config["SECRET_KEY"] = Config.SECRET_KEY

# 预测模型懒加载：第一次用到才加载，避免启动时模型文件不存在而报错
_model_payload = None


def get_model_payload():
    global _model_payload
    if _model_payload is None:
        _model_payload = rating_model.load_model()
    return _model_payload


# ---------------- 页面路由 ----------------

@app.route("/")
def page_index():
    """数据可视化大屏首页"""
    return render_template("index.html")


@app.route("/predict")
def page_predict():
    """评分预测页"""
    return render_template("predict.html")


@app.route("/recommend")
def page_recommend():
    """相似电影推荐页"""
    return render_template("recommend.html")


@app.route("/movie")
def page_movie():
    """影片详情查询页"""
    return render_template("movie.html")


# ---------------- 数据接口 ----------------

@app.route("/api/overview")
def api_overview():
    """概览卡片数据"""
    return jsonify(analysis_service.get_overview())


@app.route("/api/charts")
def api_charts():
    """一次返回全部图表数据，减少前端请求次数"""
    return jsonify({
        "rating_distribution": analysis_service.get_rating_distribution(),
        "decade_trend": analysis_service.get_decade_trend(),
        "country_rank": analysis_service.get_country_rank(),
        "genre_stats": analysis_service.get_genre_stats(),
        "votes_rank": analysis_service.get_votes_rank(),
        "director_rank": analysis_service.get_director_rank(),
        "wordcloud": analysis_service.get_wordcloud_data(),
        "scatter": analysis_service.get_rating_votes_scatter(),
    })


@app.route("/api/movies")
def api_movies():
    """电影明细表格数据，支持 ?keyword= 模糊搜索"""
    keyword = request.args.get("keyword", "").strip()
    return jsonify(analysis_service.get_movie_table(keyword))


@app.route("/api/predict", methods=["POST"])
def api_predict():
    """
    评分预测接口：入参 JSON {year, genre, country, votes, plot?}
    plot（剧情简介）可选：用于推断类型（未选类型时兜底）并给出情感修正。
    """
    data = request.get_json(silent=True) or {}
    try:
        year = int(data.get("year", 2000))
        votes = int(data.get("votes", 100000))
        genre = str(data.get("genre", "剧情"))
        country = str(data.get("country", "中国大陆"))
        plot = str(data.get("plot", "") or "")
    except (ValueError, TypeError):
        return jsonify({"error": "参数格式不正确"}), 400

    if not (1900 <= year <= 2030):
        return jsonify({"error": "年份应在 1900~2030 之间"}), 400
    if votes < 0:
        return jsonify({"error": "评价人数不能为负"}), 400

    # 剧情简介分析：推测类型 + 情感倾向（作为预测依据的一部分）
    plot_info = plot_analyzer.analyze(plot)
    genre_source = "用户选择"
    if genre == "自动识别":
        if plot_info["genre"]:
            genre = plot_info["genre"]
            genre_source = "简介识别"
        else:
            genre = "剧情"  # 简介无类型线索时回退到最常见的剧情类
            genre_source = "自动回退"

    try:
        payload = get_model_payload()
    except FileNotFoundError:
        return jsonify({"error": "模型尚未训练，请先运行 python model/rating_model.py"}), 503

    base_rating = rating_model.predict_rating(payload, year, genre, country, votes)
    # 简介情感分做小幅修正（±0.15 以内），体现"剧情口碑"对评分的影响
    adjust = round(plot_info["sentiment"] * 0.15, 2)
    final_rating = round(min(max(base_rating + adjust, 1.0), 10.0), 1)

    return jsonify({
        "predicted_rating": final_rating,
        "base_rating": base_rating,
        "plot_adjust": adjust,
        "model_name": payload["model_name"],
        "model_r2": round(float(payload["r2"]), 4),
        "plot_analysis": {
            "genre": plot_info["genre"],
            "genre_hits": plot_info["genre_hits"],
            "sentiment": plot_info["sentiment"],
            "genre_used": genre,
            "genre_source": genre_source,
        },
    })


@app.route("/api/predict/deepseek", methods=["POST"])
def api_predict_deepseek():
    """
    DeepSeek API 辅助预测：入参 JSON 与 /api/predict 相同，
    另需 api_key；api_url、model 可选（不填用默认值）。
    """
    data = request.get_json(silent=True) or {}
    try:
        info = {
            "year": int(data.get("year", 2000)),
            "votes": int(data.get("votes", 100000)),
            "genre": str(data.get("genre", "剧情")),
            "country": str(data.get("country", "中国大陆")),
            "plot": plot_analyzer.summarize_plot(str(data.get("plot", "") or "")),
        }
    except (ValueError, TypeError):
        return jsonify({"error": "参数格式不正确"}), 400

    result = deepseek_client.deepseek_predict(
        info,
        api_url=str(data.get("api_url", "")),
        api_key=str(data.get("api_key", "")),
        model=str(data.get("model", "")),
    )
    if "error" in result:
        return jsonify(result), 502
    return jsonify(result)


@app.route("/api/movie/detail")
def api_movie_detail():
    """影片详情查询：?name=片名（支持精确/模糊匹配）"""
    name = request.args.get("name", "").strip()
    if not name:
        return jsonify({"error": "缺少 name 参数"}), 400
    detail = analysis_service.get_movie_detail(name)
    if detail is None:
        return jsonify({"error": f"未找到与「{name}」相关的电影，请换个关键词试试"}), 404
    return jsonify(detail)


@app.route("/api/recommend")
def api_recommend():
    """相似推荐接口：?movie_id=xxxx 返回最相似的电影列表"""
    movie_id = request.args.get("movie_id", "").strip()
    if not movie_id:
        return jsonify({"error": "缺少 movie_id 参数"}), 400
    result = recommender.recommend_by_movie(movie_id)
    if not result:
        return jsonify({"error": "未找到该电影"}), 404
    return jsonify({"recommendations": result})


@app.route("/api/recommend/movies")
def api_recommend_movies():
    """推荐页下拉框用的全部电影列表（精简字段）"""
    movies = [
        {
            "movie_id": row["movie_id"],
            "title_cn": row["title_cn"],
            "genre": row["genre"],
        }
        for row in recommender.get_all_movies()
    ]
    return jsonify(movies)


# ---------------- 启动 ----------------

if __name__ == "__main__":
    print(f"服务启动中：http://{Config.FLASK_HOST}:{Config.FLASK_PORT}")
    app.run(
        host=Config.FLASK_HOST,
        port=Config.FLASK_PORT,
        debug=True,
    )
