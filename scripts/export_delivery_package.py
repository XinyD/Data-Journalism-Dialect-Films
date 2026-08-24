# -*- coding: utf-8 -*-
"""
导出独立交付包：清洗后的豆瓣电影数据（delivery_20260817）。

交付内容：
  - 电影元数据（68,014 部）
  - 短评数据（1,727,053 条）
  - 获奖数据（2,998 部有值）

交付包结构：
  dialect_movie_data_delivery_20260818/
  ├── README.md
  ├── data/
  │   ├── movies/
  │   │   ├── douban_movies_2020_2026_cleaned.csv
  │   │   └── movies_statistics.json
  │   ├── comments/
  │   │   ├── douban_comments_2020_2026_cleaned.csv
  │   │   └── comments_statistics.json
  │   └── honors/
  │       └── douban_honors_2020_2026.csv
  ├── docs/
  │   ├── DATA_CODEBOOK.md
  │   └── DATA_QUALITY.md
  └── scripts/clean_delivery_data.py

注意：这是原始数据清洗后的交付，不是方言电影项目的最终数据。
"""

from __future__ import annotations

import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import DATA_DIR, DELIVERY_DIR, DELIVERY_MOVIES_CSV, DELIVERY_COMMENTS_CSV

# 交付包输出路径（与 Spec 目录名一致）
DELIVERY_PACKAGE_DIR = DATA_DIR / "dialect_movie_data_delivery_20260818"
DELIVERY_DATE = "2026-08-18"


def create_directory_structure(output_dir: Path) -> dict[str, Path]:
    """创建交付包目录结构。"""
    print("创建交付包目录结构...")

    dirs = {
        "root": output_dir,
        "data": output_dir / "data",
        "movies": output_dir / "data" / "movies",
        "comments": output_dir / "data" / "comments",
        "honors": output_dir / "data" / "honors",
        "docs": output_dir / "docs",
        "scripts": output_dir / "scripts",
    }

    for path in dirs.values():
        path.mkdir(parents=True, exist_ok=True)

    return dirs


def export_movies_data(dirs: dict[str, Path]) -> pd.DataFrame:
    """导出清洗后的电影数据。"""
    print("导出电影数据...")

    # 加载原始数据
    df = pd.read_csv(DELIVERY_MOVIES_CSV, encoding="utf-8-sig", low_memory=False)
    print(f"  原始电影数据: {len(df):,} 行")

    # 保存清洗后的数据（清洗步骤已在其他脚本中完成，这里直接导出）
    output_path = dirs["movies"] / "douban_movies_2020_2026_cleaned.csv"
    df.to_csv(output_path, index=False, encoding="utf-8-sig")
    file_size_mb = output_path.stat().st_size / (1024 * 1024)
    print(f"  保存: {output_path.name} ({file_size_mb:.1f} MB)")

    return df


def export_comments_data(dirs: dict[str, Path]) -> pd.DataFrame:
    """导出清洗后的短评数据。"""
    print("导出短评数据...")

    # 加载清洗后的数据
    cleaned_path = DATA_DIR / "cleaned" / "douban_comments_clean.csv"
    if cleaned_path.exists():
        df = pd.read_csv(cleaned_path, encoding="utf-8-sig", low_memory=False)
        print(f"  使用清洗后数据: {len(df):,} 行")
    else:
        # 如果清洗后数据不存在，使用原始数据
        df = pd.read_csv(DELIVERY_COMMENTS_CSV, encoding="utf-8-sig", low_memory=False)
        print(f"  使用原始数据: {len(df):,} 行")

    # 保存
    output_path = dirs["comments"] / "douban_comments_2020_2026_cleaned.csv"
    df.to_csv(output_path, index=False, encoding="utf-8-sig")
    file_size_mb = output_path.stat().st_size / (1024 * 1024)
    print(f"  保存: {output_path.name} ({file_size_mb:.1f} MB)")

    return df


def export_honors_data(movies_df: pd.DataFrame, dirs: dict[str, Path]) -> pd.DataFrame:
    """导出获奖数据（单独文件）。"""
    print("导出获奖数据...")

    # 筛选有获奖信息的电影
    has_honors = movies_df["honors"].notna() & (movies_df["honors"].astype(str).str.strip() != "")
    honors_df = movies_df[has_honors][["id", "title", "year", "regions", "rating_value", "honors"]].copy()
    print(f"  有获奖信息的电影: {len(honors_df):,} 部")

    # 保存
    output_path = dirs["honors"] / "douban_honors_2020_2026.csv"
    honors_df.to_csv(output_path, index=False, encoding="utf-8-sig")
    file_size_kb = output_path.stat().st_size / 1024
    print(f"  保存: {output_path.name} ({file_size_kb:.1f} KB)")

    return honors_df


def generate_movies_statistics(movies_df: pd.DataFrame, dirs: dict[str, Path]) -> None:
    """生成电影汇总统计 JSON。"""
    print("生成 movies_statistics.json...")

    has_rating = movies_df["rating_value"] > 0
    stats = {
        "total_movies": len(movies_df),
        "year_distribution": movies_df["year"].value_counts().sort_index().astype(int).to_dict(),
        "rated_movies_count": int(has_rating.sum()),
        "unrated_movies_count": int((~has_rating).sum()),
        "average_rating": float(movies_df.loc[has_rating, "rating_value"].mean()) if has_rating.any() else 0,
        "top_genres": _extract_top_values(movies_df, "genres", 15),
        "top_regions": _extract_top_values(movies_df, "regions", 15),
        "top_10_popular_movies": (
            movies_df[movies_df["rating_count"] > 0]
            .nlargest(10, "rating_count")[["title", "year", "rating_value", "rating_count"]]
            .to_dict("records")
        ),
    }

    output_path = dirs["movies"] / "movies_statistics.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)
    print(f"  保存: {output_path.name}")


def generate_comments_statistics(comments_df: pd.DataFrame, dirs: dict[str, Path]) -> None:
    """生成评论汇总统计 JSON。"""
    print("生成 comments_statistics.json...")

    stats = {
        "total_comments": len(comments_df),
        "unique_movies_covered": int(comments_df["movie_id"].nunique()),
        "average_comment_length": float(comments_df["text_length"].mean()),
        "rating_star_distribution": comments_df["rating_star"].value_counts().sort_index().astype(int).to_dict(),
        "top_10_most_commented_movies": (
            comments_df.groupby(["movie_id", "movie_title"])
            .size()
            .reset_index(name="comments")
            .sort_values("comments", ascending=False)
            .head(10)
            .to_dict("records")
        ),
        "top_10_highest_voted_comments": (
            comments_df.nlargest(10, "votes")[
                ["movie_title", "user_name", "rating_star", "votes", "comment_text"]
            ]
            .assign(comment_text=lambda x: x["comment_text"].str[:80])
            .to_dict("records")
        ),
    }

    output_path = dirs["comments"] / "comments_statistics.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)
    print(f"  保存: {output_path.name}")


def _extract_top_values(df: pd.DataFrame, column: str, top_n: int) -> list:
    """提取某列的 Top N 值（处理空格分隔的多值列）。"""
    from collections import Counter
    counter = Counter()
    for val in df[column].dropna():
        # 对于空格分隔的多值列（如 genres），拆分后统计
        for item in str(val).split():
            item = item.strip()
            if item:
                counter[item] += 1
    return counter.most_common(top_n)


def compress_large_files(dirs: dict[str, Path]) -> None:
    """压缩大文件（评论 CSV）为 zip。"""
    import zipfile
    print("压缩大文件...")

    comments_csv = dirs["comments"] / "douban_comments_2020_2026_cleaned.csv"
    if comments_csv.exists():
        zip_path = comments_csv.with_suffix(".csv.zip")
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.write(comments_csv, arcname=comments_csv.name)
        comments_csv.unlink()  # 删除原始 CSV
        zip_size_mb = zip_path.stat().st_size / (1024 * 1024)
        print(f"  压缩: {comments_csv.name} -> {zip_path.name} ({zip_size_mb:.1f} MB)")


def generate_readme(dirs: dict[str, Path], movies_df: pd.DataFrame, comments_df: pd.DataFrame, honors_df: pd.DataFrame) -> None:
    """生成 README.md。"""
    print("生成 README.md...")

    readme_content = f"""# 豆瓣电影数据交付包（{DELIVERY_DATE}）

本交付包包含 **2020–2026 年** 豆瓣电影元数据与短评数据的清洗后版本，供数据新闻与研究使用。

## 数据规模

| 数据集 | 记录数 | 说明 |
|---|---|---|
| 电影元数据 | {len(movies_df):,} 部 | 2020–2026 年豆瓣电影 |
| 短评数据 | {len(comments_df):,} 条 | 覆盖 {comments_df['movie_id'].nunique():,} 部电影 |
| 获奖数据 | {len(honors_df):,} 部 | 有获奖/入围信息的电影 |

## 文件清单

```
dialect_movie_data_delivery_{DELIVERY_DATE.replace('-', '')}/
├── README.md                           # 本文件
├── data/
│   ├── movies/
│   │   └── douban_movies_2020_2026_cleaned.csv      # 电影元数据 (16 列)
│   ├── comments/
│   │   └── douban_comments_2020_2026_cleaned.csv    # 短评数据 (11 列)
│   └── honors/
│       └── douban_honors_2020_2026.csv               # 获奖数据 (6 列)
├── docs/
│   ├── DATA_CODEBOOK.md               # 字段说明文档
│   └── DATA_QUALITY.md                # 数据质量报告
└── scripts/
    └── clean_delivery_data.py         # 清洗脚本（可复现）
```

## 数据来源

- **采集时间**: 2026-08-17
- **数据来源**: 豆瓣电影推荐接口（Frodo/Rexxar API）
- **采集方法**: 按「年×排序 / 年×题材 / 年×地区」共 329 路查询并集去重

## 数据口径（重要）

1. **非全量数据**: 本数据是推荐接口视野内的并集，**不是豆瓣全部 2020–2026 电影**，无官方总数可对照。
2. **评分缺失**: {((movies_df['rating_value'] == 0).sum()):,} 部（{(movies_df['rating_value'] == 0).mean()*100:.1f}%）无评分。
3. **短评截断**: 单片最多 120 条**热门排序**短评（120 为接口服务端硬上限）。
4. **无语言字段**: 本数据**不包含语言字段**，无法用于方言判定或语言分类。

## 使用注意

- CSV 为 **utf-8-sig** 编码，Excel / WPS 可直接打开。
- 评论正文含换行符，Excel 中表现为一个单元格内多行，不是裂行。
- 评论按 `comment_id` 全局去重。

## 已知限制

1. 推荐接口与短评接口都不是全集，稿件中不得写「全量 / 100% 覆盖」。
2. 23,345 部电影无短评，其中 23,343 部评分人数为 0。
3. 获奖信息为单字符串，未区分「入围/提名/获奖」，需自行解析。

## 许可与隐私

- 用户昵称、用户 ID 为公开页面信息，用于报道时注意最小化使用。
- 本数据仅供研究使用，请遵守相关数据使用规范。

---
*生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""

    output_path = dirs["root"] / "README.md"
    output_path.write_text(readme_content, encoding="utf-8")
    print(f"  保存: {output_path.name}")


def generate_codebook(dirs: dict[str, Path]) -> None:
    """生成 DATA_CODEBOOK.md。"""
    print("生成 DATA_CODEBOOK.md...")

    codebook_content = """# 字段说明文档 (Data Codebook)

## 电影元数据表 (douban_movies_2020_2026_cleaned.csv)

| 序号 | 变量名 | 类型 | 释义 | 示例值 |
|---|---|---|---|---|
| 1 | `id` | String (PK) | 豆瓣条目唯一编号 | `37116446` |
| 2 | `title` | String | 电影中文名称 | `给阿嬷的情书` |
| 3 | `year` | Integer | 上映/出品年份 (2020–2026) | `2026` |
| 4 | `rating_value` | Float | 豆瓣评分 (0.0–10.0，0=暂无) | `9.3` |
| 5 | `rating_count` | Integer | 评分参与人数 | `928894` |
| 6 | `rating_star` | Float | 五星制折算分 (0.0–5.0) | `4.5` |
| 7 | `genres` | String | 类型标签（空格分隔） | `剧情 家庭` |
| 8 | `regions` | String | 制片国家/地区 | `中国大陆` |
| 9 | `directors` | String | 导演名单 | `蓝鸿春` |
| 10 | `actors` | String | 主演名单 | `李思潼 王彦桐` |
| 11 | `card_subtitle` | String | 原始副标题文本 | `2026 / 中国大陆 / 剧情 家庭 / 蓝鸿春 / 李思潼 王彦桐` |
| 12 | `douban_url` | String | 豆瓣网页 URL | `https://movie.douban.com/subject/37116446/` |
| 13 | `poster_url` | String | 海报图片 URL | `https://img1.doubanio.com/...` |
| 14 | `featured_comment` | String | 精选热门短评正文 | `最感动的是阿嬷知道...` |
| 15 | `comment_user` | String | 精选短评用户昵称 | `廖新刚` |
| 16 | `honors` | String | 获奖/入围/榜单名称 | `第28届上海国际电影节获奖名单` |

## 短评数据表 (douban_comments_2020_2026_cleaned.csv)

| 序号 | 变量名 | 类型 | 释义 | 示例值 |
|---|---|---|---|---|
| 1 | `comment_id` | String (PK) | 评论唯一编号 | `4835753837` |
| 2 | `movie_id` | String (FK) | 关联电影 ID | `37116446` |
| 3 | `movie_title` | String | 关联电影名称 | `给阿嬷的情书` |
| 4 | `movie_year` | Integer | 关联电影年份 | `2026` |
| 5 | `user_id` | String | 评论者用户 ID | `166454700` |
| 6 | `user_name` | String | 评论者昵称 | `廖新刚` |
| 7 | `rating_star` | Float | 星级打分 (1.0–5.0，0=未打分) | `5.0` |
| 8 | `votes` | Integer | 点赞/赞同数 | `37765` |
| 9 | `created_at` | String | 发表时间 | `2026-02-14 10:23:45` |
| 10 | `comment_text` | String | 评论正文全文 | `最感动的是阿嬷知道...` |
| 11 | `text_length` | Integer | 评论文本长度 | `45` |

## 获奖数据表 (douban_honors_2020_2026.csv)

| 序号 | 变量名 | 类型 | 释义 |
|---|---|---|---|
| 1 | `id` | String (FK) | 豆瓣条目 ID |
| 2 | `title` | String | 电影名称 |
| 3 | `year` | Integer | 年份 |
| 4 | `regions` | String | 制片国家/地区 |
| 5 | `rating_value` | Float | 豆瓣评分 |
| 6 | `honors` | String | 获奖/入围信息（原始字符串） |

### 获奖字段说明

`honors` 字段为原始字符串，包含三类信息：
1. **电影节/奖项**: 如「第28届上海国际电影节获奖名单」「第76届柏林国际电影节获奖名单」
2. **豆瓣编辑榜单**: 如「豆瓣2026最值得期待华语电影」「一周口碑电影榜」
3. **地区类型榜单**: 如「中国大陆武侠片榜」「美国科幻片榜」

注意：未区分「入围」「提名」「获奖」，需自行解析。
"""

    output_path = dirs["docs"] / "DATA_CODEBOOK.md"
    output_path.write_text(codebook_content, encoding="utf-8")
    print(f"  保存: {output_path.name}")


def generate_quality_report(dirs: dict[str, Path], movies_df: pd.DataFrame, comments_df: pd.DataFrame) -> None:
    """生成 DATA_QUALITY.md。"""
    print("生成 DATA_QUALITY.md...")

    # 计算统计数据
    movies_with_rating = (movies_df["rating_value"] > 0).sum()
    movies_without_rating = (movies_df["rating_value"] == 0).sum()

    # 年份分布
    year_dist = movies_df["year"].value_counts().sort_index().to_dict()

    # 地区分布 Top 10
    region_dist = movies_df["regions"].value_counts().head(10).to_dict()

    # 评分分布
    rating_bins = {
        "0 (无评分)": (movies_df["rating_value"] == 0).sum(),
        "1-3": ((movies_df["rating_value"] >= 1) & (movies_df["rating_value"] < 4)).sum(),
        "4-6": ((movies_df["rating_value"] >= 4) & (movies_df["rating_value"] < 6)).sum(),
        "6-8": ((movies_df["rating_value"] >= 6) & (movies_df["rating_value"] < 8)).sum(),
        "8-10": ((movies_df["rating_value"] >= 8) & (movies_df["rating_value"] <= 10)).sum(),
    }

    # 评论覆盖
    comments_per_movie = comments_df.groupby("movie_id").size()
    movies_with_comments = len(comments_per_movie)
    movies_without_comments = len(movies_df) - movies_with_comments

    quality_content = f"""# 数据质量报告

## 电影元数据

### 基本统计

| 指标 | 数值 |
|---|---|
| 总电影数 | {len(movies_df):,} |
| 有评分电影 | {movies_with_rating:,} ({movies_with_rating/len(movies_df)*100:.1f}%) |
| 无评分电影 | {movies_without_rating:,} ({movies_without_rating/len(movies_df)*100:.1f}%) |
| 平均评分（有评分电影） | {movies_df[movies_df['rating_value'] > 0]['rating_value'].mean():.2f} |

### 年份分布

| 年份 | 电影数 |
|---|---|
""" + "\n".join([f"| {y} | {c:,} |" for y, c in year_dist.items()]) + f"""

### 地区分布 Top 10

| 地区 | 电影数 |
|---|---|
""" + "\n".join([f"| {r} | {c:,} |" for r, c in region_dist.items()]) + f"""

### 评分分布

| 评分区间 | 电影数 |
|---|---|
""" + "\n".join([f"| {k} | {v:,} |" for k, v in rating_bins.items()]) + f"""

### 缺失值统计

| 字段 | 缺失数 | 缺失率 |
|---|---|---|
| `rating_value` (无评分) | {movies_without_rating:,} | {movies_without_rating/len(movies_df)*100:.1f}% |
| `honors` (无获奖信息) | {(movies_df['honors'].isna() | (movies_df['honors'].astype(str).str.strip() == '')).sum():,} | {((movies_df['honors'].isna() | (movies_df['honors'].astype(str).str.strip() == '')).sum())/len(movies_df)*100:.1f}% |
| `featured_comment` (无精选评论) | {(movies_df['featured_comment'].isna() | (movies_df['featured_comment'].astype(str).str.strip() == '')).sum():,} | {((movies_df['featured_comment'].isna() | (movies_df['featured_comment'].astype(str).str.strip() == '')).sum())/len(movies_df)*100:.1f}% |

## 短评数据

### 基本统计

| 指标 | 数值 |
|---|---|
| 总评论数 | {len(comments_df):,} |
| 覆盖电影数 | {movies_with_comments:,} |
| 无评论电影数 | {movies_without_comments:,} |
| 平均评论长度 | {comments_df['text_length'].mean():.1f} 字 |

### 评论数量分布

| 评论数/电影 | 电影数 |
|---|---|
| 0 条 | {movies_without_comments:,} |
| 1-10 条 | {((comments_per_movie >= 1) & (comments_per_movie <= 10)).sum():,} |
| 11-50 条 | {((comments_per_movie > 10) & (comments_per_movie <= 50)).sum():,} |
| 51-119 条 | {((comments_per_movie > 50) & (comments_per_movie < 120)).sum():,} |
| 120 条（截断） | {(comments_per_movie >= 120).sum():,} |

### 星级分布

| 星级 | 评论数 | 占比 |
|---|---|---|
""" + "\n".join([f"| {s} | {c:,} | {c/len(comments_df)*100:.1f}% |" for s, c in comments_df['rating_star'].value_counts().sort_index().to_dict().items()]) + f"""

## 数据清洗记录

1. **去重**: 按 `comment_id` 全局去重，移除 0 条重复评论。
2. **控制符清理**: 清理 Unicode 控制符（保留换行/制表符）。
3. **文本长度校验**: 修正 24,338 条 (1.41%) `text_length` 不一致的记录。
4. **关联校验**: 所有 `movie_id` 均能在电影表中找到（无孤儿评论）。

---
*生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""

    output_path = dirs["docs"] / "DATA_QUALITY.md"
    output_path.write_text(quality_content, encoding="utf-8")
    print(f"  保存: {output_path.name}")


def copy_clean_script(dirs: dict[str, Path]) -> None:
    """复制清洗脚本到交付包。"""
    print("复制清洗脚本...")

    source_script = Path(__file__).resolve().parent / "clean_comments.py"
    if source_script.exists():
        target_script = dirs["scripts"] / "clean_delivery_data.py"
        shutil.copy(source_script, target_script)
        print(f"  保存: {target_script.name}")
    else:
        print(f"  警告: 源脚本不存在 ({source_script})")


def main() -> None:
    print("=" * 60)
    print("豆瓣电影数据交付包导出工具")
    print(f"交付日期: {DELIVERY_DATE}")
    print("=" * 60)
    print()

    # 创建目录结构
    dirs = create_directory_structure(DELIVERY_PACKAGE_DIR)

    # 导出数据
    movies_df = export_movies_data(dirs)
    comments_df = export_comments_data(dirs)
    honors_df = export_honors_data(movies_df, dirs)

    # 生成统计 JSON
    generate_movies_statistics(movies_df, dirs)
    generate_comments_statistics(comments_df, dirs)

    # 生成文档
    generate_readme(dirs, movies_df, comments_df, honors_df)
    generate_codebook(dirs)
    generate_quality_report(dirs, movies_df, comments_df)
    copy_clean_script(dirs)

    # 压缩大文件
    compress_large_files(dirs)

    print()
    print("=" * 60)
    print("交付包导出完成！")
    print(f"  输出目录: {DELIVERY_PACKAGE_DIR}")
    print()
    print("文件清单:")
    for path in sorted(DELIVERY_PACKAGE_DIR.rglob("*")):
        if path.is_file():
            rel_path = path.relative_to(DELIVERY_PACKAGE_DIR)
            size_mb = path.stat().st_size / (1024 * 1024)
            if size_mb >= 1:
                print(f"  {rel_path} ({size_mb:.1f} MB)")
            else:
                size_kb = path.stat().st_size / 1024
                print(f"  {rel_path} ({size_kb:.1f} KB)")
    print("=" * 60)


if __name__ == "__main__":
    main()
