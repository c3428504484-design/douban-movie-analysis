"""
剧情简介文本分析模块
从用户输入的影片简介中提取两类辅助信息，作为评分预测的依据：
1. 类型线索：命中关键词推测影片类型（用户未指定类型时兜底）
2. 情感倾向：正面/负面评价词计数，映射成 (-1, 1) 之间的情感分
均为透明可解释的规则方法，不引入额外依赖。
"""
import re

# 类型关键词表：命中即计一票，票数最高者视为推测类型
GENRE_KEYWORDS = {
    "科幻": ["太空", "宇宙", "星际", "外星", "未来", "机器人", "时间旅行",
             "时空", "虚拟", "末日", "星球", "穿越"],
    "喜剧": ["搞笑", "喜剧", "幽默", "滑稽", "爆笑", "乌龙", "趣事", "段子"],
    "爱情": ["爱情", "恋爱", "恋人", "浪漫", "告白", "婚礼", "初恋", "心动", "情侣"],
    "动作": ["动作", "打斗", "追逐", "枪战", "爆炸", "功夫", "格斗", "特工", "赛车"],
    "犯罪": ["犯罪", "黑帮", "谋杀", "案件", "毒品", "监狱", "抢劫", "杀人", "警匪"],
    "悬疑": ["悬疑", "谜团", "真相", "失踪", "秘密", "推理", "诡异", "阴谋"],
    "惊悚": ["惊悚", "恐怖", "鬼魂", "血腥", "噩梦", "诅咒", "灵异"],
    "动画": ["动画", "卡通", "童话", "魔法少女", "精灵", "绘本"],
    "冒险": ["冒险", "旅程", "寻宝", "探险", "荒岛", "漂流", "远征"],
    "战争": ["战争", "战役", "军队", "士兵", "战场", "抗日", "战役"],
    "历史": ["历史", "王朝", "皇帝", "古代", "宫廷", "帝国"],
    "传记": ["传记", "生平", "一生", "真人真事", "原型", "传奇"],
    "奇幻": ["奇幻", "魔法", "神话", "巨龙", "巫师", "神仙", "妖魔"],
    "剧情": ["人生", "家庭", "成长", "命运", "社会", "生活", "亲情", "父亲", "母亲"],
}

# 评价倾向词表（用于估算"简介口吻"对评分的小幅修正）
POSITIVE_WORDS = ["感人", "震撼", "经典", "伟大", "温情", "治愈", "深刻",
                  "热血", "励志", "精彩", "细腻", "史诗", "催泪", "动人"]
NEGATIVE_WORDS = ["狗血", "烂尾", "拖沓", "无聊", "俗套", "尴尬", "崩坏", "失望"]


def infer_genre(plot: str) -> tuple[str, int]:
    """
    统计简介中各类型关键词的命中次数，返回 (推测类型, 命中数)。
    没有任何命中时返回 ("", 0)，调用方应回退到用户选择的类型。
    """
    scores = {}
    for genre, keywords in GENRE_KEYWORDS.items():
        hits = sum(1 for kw in keywords if kw in plot)
        if hits:
            scores[genre] = hits
    if not scores:
        return "", 0
    best = max(scores.items(), key=lambda item: item[1])
    return best[0], best[1]


def plot_sentiment(plot: str) -> float:
    """
    简介情感分：正面词 +1、负面词 -1，归一化到 (-1, 1)。
    中性简介返回 0。
    """
    pos = sum(1 for w in POSITIVE_WORDS if w in plot)
    neg = sum(1 for w in NEGATIVE_WORDS if w in plot)
    total = pos + neg
    if total == 0:
        return 0.0
    return round((pos - neg) / total, 3)


def summarize_plot(plot: str) -> str:
    """去掉多余空白并裁剪到前 200 字，供发给外部 API 时控制长度"""
    text = re.sub(r"\s+", " ", plot).strip()
    return text[:200]


def analyze(plot: str) -> dict:
    """
    综合分析入口：返回推测类型、命中数、情感分和文本长度。
    预测接口用它把"剧情简介"纳入评分依据。
    """
    plot = summarize_plot(plot)
    if not plot:
        return {"genre": "", "genre_hits": 0, "sentiment": 0.0, "length": 0}
    genre, hits = infer_genre(plot)
    return {
        "genre": genre,
        "genre_hits": hits,
        "sentiment": plot_sentiment(plot),
        "length": len(plot),
    }
