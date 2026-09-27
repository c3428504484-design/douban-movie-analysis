"""
一键运行脚本
串联完整数据链路：爬虫 → 清洗 → 入库。
第一次部署项目或想刷新数据时，运行这一个脚本即可。

运行方式：
    cd douban-movie-analysis
    python run_all.py
"""
import subprocess
import sys

# 按依赖顺序执行的三步，任何一步失败都立即停止
PIPELINE_STEPS = [
    ("爬虫：抓取豆瓣 Top250", ["python", "spider/douban_spider.py"]),
    ("清洗：规整字段并去重", ["python", "data_cleaner.py"]),
    ("入库：写入 MySQL 数据库", ["python", "data_loader.py"]),
]


def main():
    for step_name, command in PIPELINE_STEPS:
        print(f"\n========== {step_name} ==========")
        # 用本机 Python 依次执行子脚本，失败直接终止整条链路
        result = subprocess.run([sys.executable] + command[1:])
        if result.returncode != 0:
            print(f"步骤「{step_name}」执行失败，链路终止")
            sys.exit(1)
    print("\n全链路执行完毕：爬虫 → 清洗 → 入库 ✓")


if __name__ == "__main__":
    main()
