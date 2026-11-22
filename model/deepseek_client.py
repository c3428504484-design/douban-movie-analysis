"""
DeepSeek API 辅助预测模块
后端代理调用 DeepSeek（或任何 OpenAI 兼容）的 chat completions 接口：
前端把可配置的 API 地址 / Key / 模型名传进来，由后端发起请求，
避免浏览器跨域问题，也方便统一超时与错误处理。
"""
import re

import requests

# 默认配置：前端未填写时使用
DEFAULT_API_URL = "https://api.deepseek.com/chat/completions"
DEFAULT_MODEL = "deepseek-chat"
REQUEST_TIMEOUT = 45  # 大模型响应较慢，放宽到 45 秒


def _build_prompt(info: dict) -> str:
    """把影片信息组装成请模型打分的提示词"""
    plot = info.get("plot") or "（未提供）"
    return (
        "你是电影评分预测专家。请根据以下影片信息，预测它在豆瓣电影上最可能获得的评分"
        "（1.0~10.0，参考豆瓣 Top250 的评分水平）。\n"
        f"上映年份：{info.get('year')}\n"
        f"类型：{info.get('genre')}\n"
        f"国家/地区：{info.get('country')}\n"
        f"预计评价人数：{info.get('votes')}\n"
        f"剧情简介：{plot}\n"
        "只回答一个数字（评分本身），不要输出任何其他文字。"
    )


def _extract_rating(text: str) -> float | None:
    """从模型回复里提取第一个 1~10 的数值作为预测评分"""
    match = re.search(r"(\d+(?:\.\d+)?)", text)
    if not match:
        return None
    value = float(match.group(1))
    if 1.0 <= value <= 10.0:
        return value
    return None


def deepseek_predict(info: dict, api_url: str = "", api_key: str = "",
                     model: str = "") -> dict:
    """
    调用 DeepSeek API 预测评分。
    返回 {"rating": 分数, "raw": 模型原文}；失败返回 {"error": 原因}。
    """
    api_url = (api_url or DEFAULT_API_URL).strip()
    model = (model or DEFAULT_MODEL).strip()
    api_key = (api_key or "").strip()
    if not api_key:
        return {"error": "未提供 API Key，请在 DeepSeek 配置区填写"}

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "你是严谨的电影评分预测助手。"},
            {"role": "user", "content": _build_prompt(info)},
        ],
        "temperature": 0.3,
        "max_tokens": 32,
    }
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }
    try:
        resp = requests.post(api_url, json=payload, headers=headers,
                             timeout=REQUEST_TIMEOUT)
    except requests.RequestException as exc:
        return {"error": f"请求 DeepSeek API 失败：{exc}"}

    if resp.status_code != 200:
        return {"error": f"DeepSeek API 返回 {resp.status_code}：{resp.text[:200]}"}

    try:
        content = resp.json()["choices"][0]["message"]["content"]
    except (KeyError, IndexError, ValueError):
        return {"error": "无法解析 DeepSeek API 的响应格式"}

    rating = _extract_rating(content)
    if rating is None:
        return {"error": f"模型回复中未找到有效评分：{content[:100]}"}
    return {"rating": rating, "raw": content.strip()[:100]}
