# 豆瓣电影数据分析可视化系统

基于 Python Flask + MySQL + ECharts 的全栈数据分析项目。
完整数据链路：**爬虫采集 → 数据清洗 → 入库存储 → 可视化展示 → 评分预测 / 相似推荐**。

## 项目结构

```
douban-movie-analysis/
├── app.py                  # Flask 主应用（页面路由 + 数据接口）
├── config.py               # 全局配置（数据库连接、爬虫参数）
├── run_all.py              # 一键运行：爬虫 → 清洗 → 入库
├── data_cleaner.py         # 数据清洗模块
├── data_loader.py          # 数据入库模块（自动建库建表）
├── db_helper.py            # MySQL 操作工具封装
├── analysis_service.py     # 统计分析服务（各类图表数据）
├── spider/
│   └── douban_spider.py    # 豆瓣 Top250 爬虫
├── model/
│   ├── rating_model.py     # 评分预测模型（线性回归 vs 随机森林）
│   └── recommender.py      # 相似电影推荐（余弦相似度）
├── sql/
│   └── douban_movie.sql    # 建表 + 数据 SQL 脚本（免爬虫直接导入）
├── data/
│   ├── movies_raw.csv      # 爬虫原始数据
│   └── movies_clean.csv    # 清洗后数据
├── templates/              # 前端页面（Jinja2 模板）
└── static/js/              # ECharts 本地文件（离线可用）
```

## 主要功能

| 模块 | 说明 |
|------|------|
| 数据采集 | 爬取豆瓣电影 Top250 全部 250 部（带重试、随机延时防封） |
| 数据清洗 | 去重、字段规整、类型转换、缺失处理 |
| 数据可视化 | 评分分布、年代趋势、国家/地区榜、类型占比、人气榜、导演榜、类型词云 |
| 评分预测 | 机器学习模型，输入年份/类型/国家/热度预测评分 |
| 相似推荐 | 类型标签余弦相似度，"看过这部 → 推荐这几部" |
| 明细检索 | 按片名 / 导演 / 类型模糊搜索 |

## 部署步骤

### 1. 环境要求

- Python 3.10+
- MySQL 8.0（5.7 亦可）

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置数据库

编辑 `config.py`，把 `DB_PASSWORD` 改成你自己的 MySQL 密码：

```python
DB_HOST = "127.0.0.1"
DB_PORT = 3306
DB_USER = "root"
DB_PASSWORD = "你的密码"    # ← 只需改这一行
DB_NAME = "douban_movie"
```

### 4. 初始化数据（二选一）

**方式 A：完整链路（推荐，体验爬虫 → 清洗 → 入库全过程）**

```bash
python run_all.py
```

**方式 B：直接导入现成 SQL（不想爬的时候）**

```bash
mysql -u root -p < sql/douban_movie.sql
```

### 5. 训练评分预测模型

```bash
python model/rating_model.py
```

### 6. 启动 Web 服务

```bash
python app.py
```

浏览器打开 <http://127.0.0.1:5000> 即可看到数据大屏。

## 常见问题

- **爬虫被限流**：适当调大 `config.py` 里的 `SPIDER_DELAY_RANGE`，或直接用方式 B 导入 SQL。
- **数据库连接失败**：确认 MySQL 服务已启动、账号密码与 `config.py` 一致。
- **预测页提示模型未训练**：先执行第 5 步训练模型。
