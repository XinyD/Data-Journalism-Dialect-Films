# -*- coding: utf-8 -*-
"""
合并 delivery_20260817 新数据到现有 movies_info.csv。

策略：
  - 旧数据（movies_info.csv）为基础，全部保留
  - 新数据（douban_movies_2020_2026.csv）Schema 转换后追加
  - 按 movie_id 去重：重叠部分以旧数据为准（旧数据有语言字段）
  - 新增列：card_subtitle, rating_star, featured_comment, comment_user, honors

输入：
  - data/source/movies_info.csv (309,817 行, 24 列)
  - data/delivery_20260817/data/douban_movies_2020_2026.csv (68,014 行, 16 列)

输出：
  - data/source/movies_info_merged.csv (~371,962 行, 29 列)
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pandas as pd

# 确保能导入项目模块
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import DATA_DIR, SOURCE_MOVIES_INFO

# ============================================================
# 路径定义
# ============================================================
DELIVERY_DIR = DATA_DIR / "delivery_20260817" / "data"
DELIVERY_MOVIES_CSV = DELIVERY_DIR / "douban_movies_2020_2026.csv"
OUTPUT_MERGED_CSV = DATA_DIR / "source" / "movies_info_merged.csv"

# ============================================================
# 旧数据列名（24 列）
# ============================================================
OLD_COLUMNS = [
    "movie_id", "片名", "年份", "导演", "编剧", "主演", "类型",
    "制片国家/地区", "语言", "上映日期", "片长", "海报URL", "豆瓣评分",
    "剧情简介", "Gemini评价", "评价人数", "IMDb", "来源URL", "数据来源",
    "WikidataID", "联网补齐来源", "联网补齐时间", "本地补齐来源", "本地补齐时间",
]

# ============================================================
# 新数据 → 旧数据列名映射
# ============================================================
NEW_TO_OLD_COLUMN_MAP = {
    "id": "movie_id",
    "title": "片名",
    "year": "年份",
    "rating_value": "豆瓣评分",
    "rating_count": "评价人数",
    "genres": "类型",
    "regions": "制片国家/地区",
    "directors": "导演",
    "actors": "主演",
    "douban_url": "来源URL",
    "poster_url": "海报URL",
    # 新增字段（旧数据没有，需追加到输出）
    "card_subtitle": "card_subtitle",
    "rating_star": "rating_star",
    "featured_comment": "featured_comment",
    "comment_user": "comment_user",
    "honors": "honors",
}

# 新数据无法映射到旧数据的字段（填空）
NEW_DATA_MISSING_COLUMNS = [
    "编剧", "上映日期", "片长", "剧情简介", "Gemini评价",
    "IMDb", "语言", "WikidataID",
    "联网补齐来源", "联网补齐时间", "本地补齐来源", "本地补齐时间",
]

# 输出新增列（旧数据没有的列）
NEW_OUTPUT_COLUMNS = ["card_subtitle", "rating_star", "featured_comment", "comment_user", "honors"]


def normalize_movie_id(value: object) -> str:
    """统一 movie_id 格式：去除 .0 后缀。"""
    if pd.isna(value):
        return ""
    text = str(value).strip()
    return text[:-2] if text.endswith(".0") else text


_CJK_RE = re.compile(r"[\u4e00-\u9fff]")


def normalize_region_list(value: object) -> str:
    """Normalize production-country lists to Douban slash-separated form.

    delivery_20260817 uses spaces between CJK country names
    (``日本 中国香港 韩国``). English multi-word names are left intact.
    """
    if pd.isna(value):
        return ""
    text = re.sub(r"\s+", " ", str(value).strip())
    if not text:
        return ""
    if re.search(r"[/|;；]", text):
        parts = [part.strip() for part in re.split(r"\s*(?:/|\||;|；)\s*", text) if part.strip()]
        return " / ".join(parts)
    if " " in text and _CJK_RE.search(text):
        parts = [part for part in text.split(" ") if part]
        return " / ".join(parts)
    return text


def load_old_data(path: Path) -> pd.DataFrame:
    """加载旧数据 movies_info.csv。"""
    print(f"[1/5] 加载旧数据: {path}")
    df = pd.read_csv(path, encoding="utf-8-sig", low_memory=False)
    print(f"  旧数据: {len(df):,} 行, {len(df.columns)} 列")
    print(f"  列名: {list(df.columns)}")

    # 标准化 movie_id
    df["movie_id"] = df["movie_id"].map(normalize_movie_id)
    if "制片国家/地区" in df.columns:
        df["制片国家/地区"] = df["制片国家/地区"].map(normalize_region_list)
    return df


def load_new_data(path: Path) -> pd.DataFrame:
    """加载新数据 douban_movies_2020_2026.csv 并转换 Schema。"""
    print(f"[2/5] 加载新数据: {path}")
    df = pd.read_csv(path, encoding="utf-8-sig", low_memory=False)
    print(f"  新数据: {len(df):,} 行, {len(df.columns)} 列")
    print(f"  列名: {list(df.columns)}")

    # Schema 转换：英文列名 → 中文列名
    df = df.rename(columns=NEW_TO_OLD_COLUMN_MAP)

    # 标准化 movie_id
    df["movie_id"] = df["movie_id"].map(normalize_movie_id)

    if "制片国家/地区" in df.columns:
        df["制片国家/地区"] = df["制片国家/地区"].map(normalize_region_list)

    # 补填空字段
    for col in NEW_DATA_MISSING_COLUMNS:
        df[col] = ""

    # 数据来源标记
    df["数据来源"] = "douban_delivery_20260817"

    # 确保新增列存在（即使全为空）
    for col in NEW_OUTPUT_COLUMNS:
        if col not in df.columns:
            df[col] = ""

    print(f"  Schema 转换完成: {len(df.columns)} 列")
    return df


def merge_data(old_df: pd.DataFrame, new_df: pd.DataFrame) -> pd.DataFrame:
    """合并新旧数据，旧数据优先。"""
    print("[3/5] 合并数据（旧数据优先）...")

    # 统一列顺序：旧数据列 + 新增列
    all_columns = OLD_COLUMNS + NEW_OUTPUT_COLUMNS

    # 确保旧数据也有新增列（可能部分旧数据已有这些字段）
    for col in NEW_OUTPUT_COLUMNS:
        if col not in old_df.columns:
            old_df[col] = ""

    # 找出仅新数据有的 movie_id
    old_ids = set(old_df["movie_id"].astype(str))
    new_only_mask = ~new_df["movie_id"].astype(str).isin(old_ids)
    new_only_df = new_df[new_only_mask].copy()

    overlap_count = len(new_df) - len(new_only_df)
    print(f"  重叠 ID 数: {overlap_count:,}（以旧数据为准）")
    print(f"  仅新数据有: {len(new_only_df):,}（追加）")

    # 合并
    merged = pd.concat([old_df, new_only_df], ignore_index=True)

    # 确保列顺序
    for col in all_columns:
        if col not in merged.columns:
            merged[col] = ""
    merged = merged[all_columns]

    print(f"  合并后: {len(merged):,} 行, {len(merged.columns)} 列")
    return merged


def validate_merged(df: pd.DataFrame, old_len: int, new_only_len: int) -> None:
    """验证合并结果。"""
    print("[4/5] 验证合并结果...")

    # 行数验证
    expected_len = old_len + new_only_len
    assert len(df) == expected_len, f"行数不匹配: 期望 {expected_len}, 实际 {len(df)}"
    print(f"  行数验证通过: {len(df):,} == {old_len:,} + {new_only_len:,}")

    # movie_id 唯一性验证
    unique_ids = df["movie_id"].nunique()
    assert unique_ids == len(df), f"movie_id 不唯一: {unique_ids} unique / {len(df)} total"
    print(f"  movie_id 唯一性验证通过: {unique_ids:,}")

    # 数据来源分布
    source_counts = df["数据来源"].value_counts()
    print(f"  数据来源分布:")
    for src, cnt in source_counts.items():
        print(f"    {src}: {cnt:,}")

    # 语言字段统计
    has_lang = (df["语言"].notna()) & (df["语言"].astype(str).str.strip() != "")
    print(f"  有语言字段: {has_lang.sum():,} ({has_lang.mean()*100:.1f}%)")
    print(f"  无语言字段: {(~has_lang).sum():,} ({(~has_lang).mean()*100:.1f}%)")


def save_merged(df: pd.DataFrame, path: Path) -> None:
    """保存合并后的数据。"""
    print(f"[5/5] 保存合并数据: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)

    # 原子写入
    temp_path = path.with_suffix(path.suffix + ".tmp")
    df.to_csv(temp_path, index=False, encoding="utf-8-sig")
    temp_path.replace(path)

    file_size_mb = path.stat().st_size / (1024 * 1024)
    print(f"  保存完成: {file_size_mb:.1f} MB")


def main() -> None:
    print("=" * 60)
    print("豆瓣电影数据合并工具")
    print("将 delivery_20260817 合并到 movies_info.csv")
    print("=" * 60)
    print()

    # 检查输入文件
    if not SOURCE_MOVIES_INFO.exists():
        raise FileNotFoundError(f"旧数据文件不存在: {SOURCE_MOVIES_INFO}")
    if not DELIVERY_MOVIES_CSV.exists():
        raise FileNotFoundError(f"新数据文件不存在: {DELIVERY_MOVIES_CSV}")

    # 加载数据
    old_df = load_old_data(SOURCE_MOVIES_INFO)
    old_len = len(old_df)

    new_df = load_new_data(DELIVERY_MOVIES_CSV)

    # 合并
    merged_df = merge_data(old_df, new_df)
    new_only_len = len(merged_df) - old_len

    # 验证
    validate_merged(merged_df, old_len, new_only_len)

    # 保存
    save_merged(merged_df, OUTPUT_MERGED_CSV)

    print()
    print("=" * 60)
    print("合并完成！")
    print(f"  输出文件: {OUTPUT_MERGED_CSV}")
    print(f"  总行数: {len(merged_df):,}")
    print(f"  总列数: {len(merged_df.columns)}")
    print("=" * 60)


if __name__ == "__main__":
    main()
