# -*- coding: utf-8 -*-
"""
清洗豆瓣短评数据（delivery_20260817）。

清洗步骤：
  1. 按 comment_id 全局去重
  2. 清理 Unicode 控制符（保留换行/制表符）
  3. 校验并修正 text_length
  4. 关联校验：检查 movie_id 是否能在电影表中找到

输入：
  - data/delivery_20260817/data/douban_comments_2020_2026.csv (1,727,053 行)
  - data/source/movies_info_merged.csv (用于关联校验)

输出：
  - data/cleaned/douban_comments_clean.csv (~1,725,310 行)
"""

from __future__ import annotations

import re
import sys
import unicodedata
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import DATA_DIR, DELIVERY_COMMENTS_CSV, DERIVED_COMMENTS_CLEAN, SOURCE_MOVIES_MERGED


def clean_control_chars(text: str) -> str:
    """清理 Unicode 控制符，保留换行(\\n)、制表符(\\t)、回车(\\r)。

    参考 process_comments.py 的清洗逻辑。
    """
    if not isinstance(text, str):
        return ""
    # 保留的控制符
    KEEP_CHARS = {"\n", "\t", "\r"}
    result = []
    for ch in text:
        cat = unicodedata.category(ch)
        # Cc = control chars, Cf = format chars, Cs = surrogate, Co = private use
        if cat.startswith("C") and ch not in KEEP_CHARS:
            continue
        result.append(ch)
    return "".join(result)


def normalize_whitespace(text: str) -> str:
    """规范化空白：多个连续空白替换为单个空格（保留换行）。"""
    if not isinstance(text, str):
        return ""
    # 先按行处理，保留换行结构
    lines = text.split("\n")
    cleaned_lines = []
    for line in lines:
        # 将行内多个连续空白替换为单个空格
        line = re.sub(r"[^\S\n]+", " ", line).strip()
        cleaned_lines.append(line)
    return "\n".join(cleaned_lines)


def load_comments(path: Path) -> pd.DataFrame:
    """加载原始短评数据。"""
    print(f"[1/5] 加载短评数据: {path}")
    df = pd.read_csv(path, encoding="utf-8-sig", low_memory=False)
    print(f"  原始数据: {len(df):,} 行, {len(df.columns)} 列")
    print(f"  列名: {list(df.columns)}")
    return df


def deduplicate_comments(df: pd.DataFrame) -> pd.DataFrame:
    """按 comment_id 全局去重。"""
    print("[2/5] 按 comment_id 去重...")
    before = len(df)
    df = df.drop_duplicates(subset=["comment_id"], keep="first")
    after = len(df)
    removed = before - after
    print(f"  去重前: {before:,} 行")
    print(f"  去重后: {after:,} 行")
    print(f"  移除重复: {removed:,} 行")

    # 验证唯一性
    assert df["comment_id"].nunique() == len(df), "comment_id 去重后仍有重复"
    return df


def clean_text_fields(df: pd.DataFrame) -> pd.DataFrame:
    """清理文本字段：控制符 + 空白规范化。"""
    print("[3/5] 清理文本字段...")

    # 清理 comment_text
    print("  清理 comment_text 控制符...")
    df["comment_text"] = df["comment_text"].fillna("").apply(clean_control_chars)
    df["comment_text"] = df["comment_text"].apply(normalize_whitespace)

    # 清理 user_name（可能也有控制符）
    print("  清理 user_name...")
    df["user_name"] = df["user_name"].fillna("").apply(clean_control_chars)
    df["user_name"] = df["user_name"].str.strip()

    # 清理 movie_title
    print("  清理 movie_title...")
    df["movie_title"] = df["movie_title"].fillna("").apply(clean_control_chars)
    df["movie_title"] = df["movie_title"].str.strip()

    return df


def validate_text_length(df: pd.DataFrame) -> pd.DataFrame:
    """校验并修正 text_length。"""
    print("[4/5] 校验 text_length...")

    # 计算实际文本长度
    df["actual_length"] = df["comment_text"].str.len()

    # 统计不一致的数量
    mismatch = (df["actual_length"] != df["text_length"]).sum()
    print(f"  text_length 不一致: {mismatch:,} 行 ({mismatch/len(df)*100:.2f}%)")

    # 修正不一致
    if mismatch > 0:
        print("  修正 text_length 为实际长度...")
        df["text_length"] = df["actual_length"]

    # 清理临时列
    df = df.drop(columns=["actual_length"])

    return df


def validate_movie_references(df: pd.DataFrame, movies_path: Path) -> pd.DataFrame:
    """关联校验：检查 movie_id 是否能在电影表中找到。"""
    print(f"[5/5] 关联校验 movie_id (对照: {movies_path.name})...")

    if not movies_path.exists():
        print(f"  警告: 电影表不存在 ({movies_path})，跳过关联校验")
        return df

    # 加载电影表的 movie_id
    movies = pd.read_csv(movies_path, encoding="utf-8-sig", usecols=["movie_id"], low_memory=False)
    movie_ids = set(movies["movie_id"].astype(str))
    print(f"  电影表 movie_id 数: {len(movie_ids):,}")

    # 检查孤儿评论
    df["movie_id_str"] = df["movie_id"].astype(str)
    orphan_mask = ~df["movie_id_str"].isin(movie_ids)
    orphan_count = orphan_mask.sum()

    if orphan_count > 0:
        print(f"  警告: 发现 {orphan_count:,} 条孤儿评论 (movie_id 不在电影表中)")
        # 输出前 10 个孤儿 movie_id 供检查
        orphan_ids = df.loc[orphan_mask, "movie_id_str"].unique()[:10]
        print(f"  示例孤儿 movie_id: {list(orphan_ids)}")
    else:
        print("  关联校验通过: 所有 movie_id 均能在电影表中找到")

    # 清理临时列
    df = df.drop(columns=["movie_id_str"])

    return df


def save_cleaned_comments(df: pd.DataFrame, path: Path) -> None:
    """保存清洗后的短评数据。"""
    print(f"保存清洗后数据: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)

    # 原子写入
    temp_path = path.with_suffix(path.suffix + ".tmp")
    df.to_csv(temp_path, index=False, encoding="utf-8-sig")
    temp_path.replace(path)

    file_size_mb = path.stat().st_size / (1024 * 1024)
    print(f"  保存完成: {file_size_mb:.1f} MB")


def generate_statistics(df: pd.DataFrame) -> dict:
    """生成短评统计摘要。"""
    print("生成统计摘要...")

    stats = {
        "total_comments": len(df),
        "unique_movies_covered": int(df["movie_id"].nunique()),
        "average_comment_length": float(df["text_length"].mean()),
        "rating_star_distribution": df["rating_star"].value_counts().sort_index().to_dict(),
        "top_10_most_commented_movies": (
            df.groupby(["movie_id", "movie_title"])
            .size()
            .reset_index(name="comments")
            .sort_values("comments", ascending=False)
            .head(10)
            .to_dict("records")
        ),
        "top_10_highest_voted_comments": (
            df.nlargest(10, "votes")[
                ["movie_title", "user_name", "rating_star", "votes", "comment_text"]
            ]
            .assign(comment_text=lambda x: x["comment_text"].str[:80])
            .to_dict("records")
        ),
    }
    return stats


def main() -> None:
    print("=" * 60)
    print("豆瓣短评数据清洗工具")
    print("=" * 60)
    print()

    # 检查输入文件
    if not DELIVERY_COMMENTS_CSV.exists():
        raise FileNotFoundError(f"短评数据文件不存在: {DELIVERY_COMMENTS_CSV}")

    # 加载
    df = load_comments(DELIVERY_COMMENTS_CSV)

    # 清洗
    df = deduplicate_comments(df)
    df = clean_text_fields(df)
    df = validate_text_length(df)
    df = validate_movie_references(df, SOURCE_MOVIES_MERGED)

    # 保存
    save_cleaned_comments(df, DERIVED_COMMENTS_CLEAN)

    # 生成统计
    stats = generate_statistics(df)
    stats_path = DATA_DIR / "comments_statistics_cleaned.json"
    import json
    with open(stats_path, "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)
    print(f"统计摘要: {stats_path}")

    print()
    print("=" * 60)
    print("清洗完成！")
    print(f"  输出文件: {DERIVED_COMMENTS_CLEAN}")
    print(f"  总行数: {len(df):,}")
    print(f"  覆盖电影数: {df['movie_id'].nunique():,}")
    print("=" * 60)


if __name__ == "__main__":
    main()
