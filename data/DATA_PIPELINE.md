# 数据处理与文件映射清单

> 最后更新：2026-08-30（v4.6 豆瓣语言回填 + 《隐入尘烟》补收 · 指纹 883fe6f7fb）| 方言电影数据故事项目

> 口径提示：`narrative_facts.json` 的 `regions` 键名「中国大陆」实为 Region=China 全量（第一制片国为中国，含香港、台湾、澳门，n=12,791），与正文「中国（含港澳台）」同一口径；键名沿用历史命名，勿按字面理解。

## 一、数据流转总览

```
阶段一：原始数据              阶段二：清洗后全量数据          阶段三：中国区筛选        阶段四：方言电影最终数据
─────────────────┐         ┌──────────────────────┐      ┌──────────────────┐    ┌──────────────────────┐
│ source/          │         │ cleaned/              │      │ (内存中间态)      │    │ dialect_films/        │
│ movies_info_merged.csv │ ──> │ derived_movies.csv    │ ───> │ Region==China    │ ──>│ report_data_strict.json│
│ (371,962 行)     │  脚本①  │ (63,025 行)           │ 脚本④│ (12,791 行)      │      │ 方言片明细报告.csv    │
└─────────────────         │ sample_manifest.json  │      ──────────────────┘    └──────────────────────┘
                            │ review_queue.csv      │
                            └──────────────────────┘
                                   │
                          ┌────────────────┐
                          ▼                 ▼
                   data_aggregator    extract_narrative
                          │                 │
                          ▼                 ▼
                   frontend_dataset   narrative_facts
                   aggregated_stats   .json
                   frontend/details/
                          │
          generate_particles / build_geo_enrichment / build_story_universe
                          │
                          ▼
                   frontend/particles.json
                   frontend/geo_enrichment.json
                   frontend/story_universe.json
```

## 二、四阶段核心文件

### 阶段一：原始数据 (Raw Data) — `data/source/`

| 文件 | 说明 | 行数/大小 |
|------|------|-----------|
| `movies_info_merged.csv` | **当前管线实际输入**：豆瓣全量原表 + delivery_20260817 新交付数据合并后的总表，含 movie_id、片名、年份、导演、类型、制片国家/地区、语言、豆瓣评分、评价人数等字段 | 371,962 行 |
| `movies_info.csv` | 合并前的豆瓣全量原表（历史参照，不再直接参与管线） | ~309,817 行 / 238 MB |
| `delivery_20260817/` | 2026-08-17 新数据交付包（douban_movies_2020_2026.csv 68,014 部 + 评论/统计），由 `scripts/merge_delivery_data.py` 于 2026-08-18 并入 movies_info_merged.csv；经清洗筛选后留存 9,541 部（manifest counts.source.douban_delivery_20260817） | — |

### 阶段二：清洗后全量数据 (Cleaned Data) — `data/cleaned/`

| 文件 | 说明 | 行数/大小 |
|------|------|-----------|
| `derived_movies.csv` | 清洗+派生后的发布数据集（v4.6 发布快照）。过滤漏斗：371,962 → 116,796（年份 1888-2026/评分 0-10/片名有效）→ 63,062（评价人数 ≥100）→ **63,025**（去重 37 部）。派生字段：Decade/Region/Language_Category/Region_Code/Genre_Code/Language_Code/Is_Dialect/Language_Provenance；v4.1 起新增 **Dialect_Evidence** 列（Tier 2b 证据审查溯源；另含 `LANG_BACKFILL_20260830` / `EMPTY_LANG_DEFAULTED` / `LANG_FIX_20260819` / `LANG_FIX_20260830`） | 63,025 行 / 48 MB |
| `sample_manifest.json` | 数据指纹（SHA-256）、处理阶段计数、纳入标准元信息 | — |
| `review_queue.csv` | 人工审核排除清单（审计溯源用），记录被剔除影片及原因 | — |
| `language_backfill_candidates.csv` | v4.6：语言不可信的入样清单（delivery 空列 / 默认普通话 / 2020–2026 其他空语言） | — |
| `language_backfill_overrides.csv` | v4.6：豆瓣详情页回填的语言覆盖表（replay 链读取） | — |

### 阶段三：中国区筛选数据 (China Region Data)

当前流程中 China 子集由 `gen_report_strict.py` 在内存中过滤产生（`df[df["Region"] == "China"]`），**不持久化为独立文件**。v4.6 第一制片国口径下该子集为 **12,791 行**（方言 3,067 + 普通话·非方言 9,724，与 manifest counts.region.China 一致）。如需导出，可新增脚本从 `cleaned/derived_movies.csv` 筛选 `Region == "China"` 行。

### 阶段四：方言电影最终数据 (Dialect Films Data) — `data/dialect_films/`

| 文件 | 说明 |
|------|------|
| `report_data_strict.json` | 方言分类结果，含 Tier 1/2a/2b 分层、方言标签、语言列表、占比推断等（~2.8 MB）。**v4.6 发布快照：China 方言片 3,067（Tier 1 2,303 / Tier 2a 418 / Tier 2b 346）**。注意：`derived_movies.csv` 无 Tier 列，Tier 分层由本脚本按 dialect_defs 规则计算并与 Is_Dialect 列交叉校验 |
| `方言片明细报告.csv` | 逐部明细报告：方言片全量 + 普通话对照组分层抽样，含组别、movie_id、片名、年份、评分、类型、Decade、语言字段原文、归一化语言、命中方言标签、方言大区、Tier 层级等 |

### 前端数据 — `data/`（根级，保持不变）

| 文件 | 说明 | 生成脚本 |
|------|------|----------|
| `frontend_dataset.json` | 前端主数据集（紧凑 JSON） | `data_aggregator.py` |
| `aggregated_stats.json` | 聚合统计（年代/地区/语言分组） | `data_aggregator.py` |
| `narrative_facts.json` | 叙事事实数据（滚动叙事文章用） | `extract_narrative.py` |
| `frontend/particles.json` | 粒子可视化数据 | `generate_particles.py` |
| `frontend/details/00.json ~ 3f.json` | 影片详情分片（64 片） | `data_aggregator.py` |
| `frontend/dialect_aggregates.json` | 方言叙事聚合载荷（byDecade/yearly/typeCtl/canto/diversity/global/director/genreAvg/waves，口径固化自 sync_preview_dialect_v43_20260819.py） | `data_aggregator.py` |
| `frontend/geo_enrichment.json` | 第一出品国视觉地理，按行号对齐 frontend_dataset | `scripts/build_geo_enrichment.py` |
| `frontend/story_universe.json` | 回声场景宇宙载荷 | `scripts/build_story_universe.py` |
| `frontend/visual_land_masks.json` | 7 组陆地 polygon，仅用于封面粒子落点 | 手写视觉掩膜 |
| `archive/frontend_dataset.orphan_fe2402ba.json` | **陈旧孤儿副本**（指纹 fe2402ba…，阿嬷补收前）。权威文件是根级 `data/frontend_dataset.json`。见 `data/archive/ORPHAN_FRONTEND_DATASET.md` | 勿用 |

## 三、处理脚本与数据流转逻辑

### 核心管线脚本（按执行顺序）

| 序号 | 脚本 | 输入 | 输出 | 说明 |
|------|------|------|------|------|
| ① | `scripts/data_processor.py` | `data/source/movies_info_merged.csv` | `data/cleaned/derived_movies.csv` + `data/cleaned/sample_manifest.json` | 去重、筛选（年份 1888-2026、评分 0-10、票数 >=100）、派生字段（Decade/Region/Language_Category/Region_Code/Genre_Code/Language_Code/Is_Dialect） |
| ①′ | `scripts/merge_delivery_data.py` | `data/source/movies_info.csv` + `data/delivery_20260817/` | `data/source/movies_info_merged.csv` | 2026-08-18 新交付数据并入原始总表（一次性，已完成；68,014 部并入） |
| ② | `scripts/data_aggregator.py` | `data/cleaned/derived_movies.csv` + `data/cleaned/sample_manifest.json` | `data/frontend_dataset.json` + `data/aggregated_stats.json` + `data/frontend/details/*.json` + `data/frontend/dialect_aggregates.json` | 聚合统计 + 前端紧凑 JSON 导出 + 方言叙事聚合（build_dialect_aggregates） |
| ③ | `scripts/extract_narrative.py` | `data/cleaned/derived_movies.csv` + `data/cleaned/sample_manifest.json` | `data/narrative_facts.json` | 滚动叙事文章所需的量化事实重算 |
| ③a | `scripts/generate_particles.py` | `data/cleaned/derived_movies.csv` | `data/frontend/particles.json` | 粒子可视化载荷 |
| ③b | `scripts/build_geo_enrichment.py` | `data/frontend_dataset.json` | `data/frontend/geo_enrichment.json` | 第一出品国视觉地理 |
| ③c | `scripts/build_story_universe.py` | 前端载荷 + 叙事事实 | `data/frontend/story_universe.json` | 回声场景宇宙载荷 |
| ④ | `scripts/gen_report_strict.py` | `data/cleaned/derived_movies.csv` | `data/dialect_films/report_data_strict.json` | 中国区筛选 + v2.1 严格方言分类（Tier 1/2a/2b），交叉校验 Is_Dialect 列一致性 |
| ⑤ | `scripts/gen_dialect_report.py` | `data/cleaned/derived_movies.csv` + `data/dialect_films/report_data_strict.json` | `data/dialect_films/方言片明细报告.csv` + `方言片详细报告.html` | 逐部明细报告 + HTML 可视化报告 |

### 方言定义单一事实来源

| 文件 | 说明 |
|------|------|
| `scripts/dialect_defs.py` | 方言电影定义 SSOT（v2.1 严格中国语言标准），含白名单（DIALECT_MARKERS_STRICT）、普通话标记（MANDARIN_MARKERS）、外语标记（FOREIGN_MARKERS）、审计排除名单（DIALECT_AUDIT_EXCLUDE_MOVIE_IDS）与戏曲/演唱会排除名单（OPERA_CONCERT_EXCLUDE_MOVIE_IDS，49 个 ID，v4.3） |
| `scripts/history/` | 已退出主管线的一次性脚本（方案 A 落地、2016 空语言补丁、旧报告生成器等），勿对现行快照再跑 |

### 配置路径

| 文件 | 说明 |
|------|------|
| `config.py` | 路径常量定义（DERIVED_MOVIES_INFO、SAMPLE_MANIFEST、SOURCE_MOVIES_INFO 等），核心管线脚本通过此文件引用路径 |

## 四、归档文件 — `data/archive/`

### `archive/backups/` — 已移除的本地谱系备份

v1→v4.1 主表/报告 JSON 备份仅存在于本地磁盘、不参与管线。需要历史状态时从 `data/source/` 走 `scripts/replay_v44_baseline.py --full-rebuild` 重建，不要依赖已删除的 `*_backup_*.csv`。

### `archive/analysis/` — 一次性分析/验证/抽样输出

| 文件 | 说明 |
|------|------|
| `codebook_review.csv` / `.tmp` / `_sample.csv` | Codebook 审核记录 |
| `dialect_films_with_foreign_primary.csv/.html/.json` | 外语为主方言片分析 |
| `empty_language_china_sample10.csv` | 空语言 China 影片抽样复核 |
| `empty_lang_backfill_summary_20260816.csv` | 空语言回填变更摘要 |
| `empty_lang_recovery_summary_20260816.csv` | 空语言恢复变更摘要 |
| `f7_cross_border_validation.csv` | F7 跨境验证 |
| `opera_concert_exclude_candidates_20260818.csv` | 戏曲/演唱会排除候选（审计溯源） |
| `false_negative_sample30.csv` | 假阴性探查样本 |
| `foreign_first_language_films.json` | 外语为首语言影片 |
| `foreign_primary_china_region_clean.csv/.html` | 中国区外语为主影片清洗 |
| `plan_a_excluded.csv` / `plan_a_foreign_annotated.csv` | 方案 A 排除/标注清单 |
| `tier2b_evidence.csv` / `tier2b_gray_zone_review.csv` / `tier2b_recovered.csv` | Tier 2b 证据审查的 **v4.1 归档快照**（与根级 `data/tier2b_*.csv` 哈希不同；现行脚本只读根级文件） |
| `空语言补全结果_84部.csv/.html` | 84 部空语言影片补全结果 |

## 五、命名规范

| 类别 | 命名模式 | 示例 |
|------|----------|------|
| 原始数据 | 描述性名词 | `movies_info.csv` |
| 清洗后数据 | 描述性名词（保留历史名称） | `derived_movies.csv` |
| 元信息/清单 | 描述性名词 + `.json`/`.csv` | `sample_manifest.json` |
| 方言分析输出 | 描述性中文/英文 | `report_data_strict.json`、`方言片明细报告.csv` |
| 前端数据 | 功能描述 | `frontend_dataset.json`、`aggregated_stats.json` |
| 历史备份 | `{原文件名}_backup_{日期}.csv` | `derived_movies_v21_backup_20260815.csv` |
| 一次性脚本 | `apply_{操作}_{日期}.py` | `apply_empty_lang_backfill_20260818.py` |

## 六、重跑管线命令

```bash
# 在仓库根目录执行（不要 cd 到过时的目录名）

# 步骤①：从原始数据重建清洗后数据集
python scripts/data_processor.py

# 步骤②：生成前端数据
python scripts/data_aggregator.py

# 步骤③：重算叙事事实
python scripts/extract_narrative.py

# 步骤③a–③c：粒子 / 地理 / 故事宇宙（与 rebuild.py 一致）
python scripts/generate_particles.py
python scripts/build_geo_enrichment.py
python scripts/build_story_universe.py

# 步骤④：生成方言分类结果
python scripts/gen_report_strict.py

# 步骤⑤：生成逐部明细报告
python scripts/gen_dialect_report.py
```

## 七、注意事项

1. **方言定义修改**：仅修改 `scripts/dialect_defs.py`，`data_processor.py` 与 `gen_report_strict.py` 共用此 SSOT
2. **重建后必须重放手工修正链**：重跑 `data_processor.py` 会用 `language_code()` 重算 Is_Dialect/Language_Code，**撤销全部手工修正**（Tier 2b 证据审查 / 空语言回填 / 2020–2026 语言回填 / 审计排除名单 / F7 Region 修正 / 戏曲演唱会排除 / 阿嬷语言修正 / 《隐入尘烟》语言修正）。重建须加 `--overwrite-tier2b`。推荐一键重放：

```bash
python scripts/replay_v44_baseline.py --full-rebuild --source data/source/movies_info_merged.csv
```

补丁链已含 v4.5 `apply_first_listed_region_20260824.py`、v4.6 `apply_language_backfill_20260830.py` 与 `apply_yinruchenyan_lang_fix_20260830.py`；`--full-rebuild` 在断言终态后会自动跑 `rebuild.py`，不必再手工执行一次。

手工逐步重放时顺序如下（重跑 fixed_count=0 属正常），然后执行 §六 全链路重生成：
   1. `scripts/apply_tier2b_reclassify_20260815.py`
   2. `scripts/apply_empty_lang_backfill_20260818.py`
   3. `scripts/apply_language_backfill_20260830.py`（v4.6：按 `language_backfill_overrides.csv` 回填豆瓣语言；须先跑 `list_untrusted_languages.py` + `fetch_douban_languages.py`）
   4. `scripts/apply_audit_exclude_20260818.py`
   5. `scripts/apply_f7_region_fix_20260818.py --apply`
   6. `scripts/apply_opera_concert_exclude_20260818.py`
   7. `scripts/apply_ama_lang_fix_20260819.py`
   8. `scripts/apply_yinruchenyan_lang_fix_20260830.py`（《隐入尘烟》按豆瓣现页补收为甘肃方言片）
   9. `scripts/apply_first_listed_region_20260824.py`（v4.5：空格分隔制片国取首位；`Dialect_Evidence` 不在 `OUTPUT_COLUMNS` 中，本步不改该列）
3. **大文件**：`movies_info.csv`（238 MB）、`movies_info_merged.csv` 与 `derived_movies.csv`（48 MB）移动时需确保磁盘空间
4. **归档文件**：`archive/` 下的文件为历史产物，不参与当前管线运行，仅供审计溯源
5. **2020–2026 语言缺列**：`delivery_20260817` 源表无「语言」列。入样候选见 `data/cleaned/language_backfill_candidates.csv`；豆瓣/Wikidata 回填结果见 `language_backfill_overrides.csv`。Wikidata P364 只填充 `Language_Code` 空缺，**不**把非豆瓣标签算进 China 方言。将来交付包若自带语言列，`merge_delivery_data.py` 会映射该列而不再整列置空。抓取缓存 `language_backfill_cache.jsonl` 仅本地保留。剩余空语言与 `EMPTY_LANG_DEFAULTED` 条数以 `sample_manifest.json` 的 `language_backfill_20260830` 块为准。
