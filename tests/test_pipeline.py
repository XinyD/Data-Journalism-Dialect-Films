import json
import subprocess
import sys
import unittest
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
TASTE_ROOT = ROOT
sys.path.insert(0, str(TASTE_ROOT / "scripts"))

from data_processor import (  # noqa: E402
    categorize_language,
    categorize_region,
    deduplicate_publication_records,
    first_listed_value,
    genre_code,
    language_code,
    manifest_source_display,
    normalize_identity_title,
)
from data_aggregator import (  # noqa: E402
    DETAIL_SHARD_COUNT,
    DETAIL_SUMMARY_LIMIT,
    detail_shard,
    usable_detail_text,
)
from extract_narrative import standardized_mean  # noqa: E402
from dialect_defs import (  # noqa: E402
    has_strict_dialect_tag,
    has_mandarin_tag,
    has_foreign_tag,
    has_minority_tag,
    normalize_language_tags,
    get_dialect_tags_found,
    first_tag_is_foreign,
    DIALECT_MARKERS_STRICT,
    MANDARIN_MARKERS,
    FOREIGN_MARKERS,
    MINORITY_MARKERS,
    SHORT_LATIN_MARKERS,
    DIALECT_AUDIT_EXCLUDE_MOVIE_IDS,
    OPERA_CONCERT_EXCLUDE_MOVIE_IDS,
)
from freeze_constants import (  # noqa: E402
    CHINA_DIALECT,
    CHINA_MANDARIN,
    CHINA_TOTAL,
    DIALECT_ALL_REGIONS,
    PUBLICATION_RECORDS,
    TIER1_PURE,
    TIER2A_DIALECT_FIRST,
    TIER2B_EXCLUDED,
    TIER2B_MANDARIN_FIRST,
    TIER_BASELINE,
)
from gen_report_strict import classify_strict  # noqa: E402
from gen_dialect_report import classify_v21  # noqa: E402


class TasteAnalysisPipelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        data_dir = TASTE_ROOT / "data"
        cls.manifest = json.loads((data_dir / "cleaned" / "sample_manifest.json").read_text(encoding="utf-8"))
        cls.frontend = json.loads((data_dir / "frontend_dataset.json").read_text(encoding="utf-8"))
        cls.particles = json.loads((data_dir / "frontend" / "particles.json").read_text(encoding="utf-8"))
        cls.detail_shards = [
            json.loads(path.read_text(encoding="utf-8"))
            for path in sorted((data_dir / "frontend" / "details").glob("*.json"))
        ]
        cls.details = {}
        for payload in cls.detail_shards:
            columns = {name: index for index, name in enumerate(payload["columns"])}
            for row in payload["records"]:
                cls.details[str(row[columns["movieId"]])] = {
                    name: row[index] for name, index in columns.items()
                }
        cls.facts = json.loads((data_dir / "narrative_facts.json").read_text(encoding="utf-8"))
        cls.frame = pd.read_csv(
            data_dir / "cleaned" / "derived_movies.csv",
            dtype={"movie_id": "string"},
            low_memory=False,
        )

    def test_bilingual_classification_rules(self):
        self.assertEqual(categorize_region("美国 / 加拿大"), "North_America")
        self.assertEqual(categorize_region("中国大陆 / 法国"), "China")
        self.assertEqual(categorize_region("日本 / 美国"), "East_Asia")
        self.assertEqual(categorize_region("法国 / 美国"), "Europe")
        self.assertEqual(categorize_region("日本 中国香港 韩国"), "East_Asia")
        self.assertEqual(categorize_region("美国 中国大陆"), "North_America")
        self.assertEqual(categorize_region("西德"), "Europe")
        self.assertEqual(categorize_region("东德"), "Europe")
        self.assertEqual(first_listed_value("united states"), "united states")
        self.assertEqual(categorize_language("日本語"), "Japanese")
        self.assertEqual(categorize_language("한국어"), "Korean")
        self.assertEqual(categorize_language("汉语普通话 / 粤语"), "Chinese")
        self.assertEqual(language_code("汉语普通话"), (2, 0))
        self.assertEqual(language_code("汉语普通话 / 粤语"), (3, 1))
        self.assertEqual(language_code("日本語"), (1, 0))
        self.assertEqual(language_code("한국어"), (4, 0))
        self.assertEqual(language_code("法语"), (5, 0))
        self.assertEqual(genre_code("纪录片 / 历史"), 6)

    def test_identity_deduplication_prefers_the_canonical_douban_record(self):
        self.assertEqual(normalize_identity_title(" GENIUS  PARTY "), "geniusparty")
        frame = pd.DataFrame([
            {
                "movie_id": "5040123",
                "片名": "Genius Party",
                "年份": 2007,
                "评价人数": 297,
                "数据来源": "current_project",
                "来源URL": "https://movie.douban.com/subject/26388461/",
            },
            {
                "movie_id": "26388461",
                "片名": "GENIUS PARTY",
                "年份": 2007,
                "评价人数": 297,
                "数据来源": "douban_all_data",
                "来源URL": "https://movie.douban.com/subject/26388461/",
            },
        ])
        deduplicated, stages = deduplicate_publication_records(frame)
        self.assertEqual(deduplicated["movie_id"].tolist(), ["26388461"])
        self.assertEqual(stages["duplicates_removed_by_source_url"], 1)
        self.assertEqual(stages["duplicates_removed"], 1)

    def test_publication_criteria_and_deduplication(self):
        criteria = self.manifest["inclusion_criteria"]
        expected_count = self.manifest["publication_records"]
        self.assertGreaterEqual(expected_count, 50_000)
        self.assertEqual(len(self.frame), expected_count)
        self.assertEqual(self.manifest["stages"]["duplicates_removed"], 37)
        self.assertEqual(self.manifest["stages"]["duplicates_removed_by_source_url"], 2)
        self.assertFalse(self.frame["movie_id"].isin(["5040123", "5014981"]).any())
        self.assertTrue(self.frame["评价人数"].ge(criteria["minimum_vote_count"]).all())
        self.assertTrue(self.frame["年份"].between(*criteria["year_range"]).all())
        self.assertTrue(self.frame["豆瓣评分"].gt(0).all())
        self.assertTrue(self.frame["豆瓣评分"].le(10).all())
        self.assertFalse(self.frame.duplicated(["片名", "年份"]).any())
        normalized_titles = self.frame["片名"].map(normalize_identity_title)
        self.assertFalse(pd.DataFrame({"title": normalized_titles, "year": self.frame["年份"]}).duplicated().any())
        subject_ids = self.frame["来源URL"].str.extract(r"/subject/(\d+)", expand=False)
        self.assertFalse(subject_ids[subject_ids.notna()].duplicated().any())
        self.assertTrue(set(self.frame["Region_Code"]).issubset(set(range(5))))
        self.assertTrue(set(self.frame["Genre_Code"]).issubset(set(range(7))))
        self.assertTrue(set(self.frame["Language_Code"]).issubset(set(range(6))))

    def test_manifest_source_is_portable(self):
        source = self.manifest["source"]
        self.assertNotIn("\\", source)
        self.assertFalse(source[1:3] == ":\\" or (len(source) >= 2 and source[1] == ":"))
        self.assertTrue(
            source.startswith("data/") or source.startswith("source_external:"),
            source,
        )
        repo_root = TASTE_ROOT
        inside = manifest_source_display(repo_root / "data" / "source" / "movies_info_merged.csv", repo_root)
        self.assertEqual(inside, "data/source/movies_info_merged.csv")
        outside = manifest_source_display(Path("/tmp/elsewhere/movies_info.csv"), repo_root)
        self.assertEqual(outside, "source_external:movies_info.csv")

    def test_all_publication_artifacts_share_one_sample(self):
        expected_count = self.manifest["publication_records"]
        fingerprint = self.manifest["sample_fingerprint_sha256"]
        frontend_meta = self.frontend["meta"]
        particle_meta = self.particles["meta"]

        self.assertEqual(frontend_meta["recordCount"], expected_count)
        self.assertEqual(particle_meta["recordCount"], expected_count)
        self.assertEqual(len(self.frontend["records"]), expected_count)
        self.assertEqual(len(self.particles["records"]), expected_count)
        self.assertEqual(frontend_meta["sampleFingerprint"], fingerprint)
        self.assertEqual(particle_meta["sampleFingerprint"], fingerprint)
        geo = json.loads((TASTE_ROOT / "data" / "frontend" / "geo_enrichment.json").read_text(encoding="utf-8"))
        self.assertEqual(geo["meta"]["sampleFingerprint"], fingerprint)
        self.assertEqual(geo["meta"]["recordCount"], expected_count)
        story = json.loads((TASTE_ROOT / "frontend" / "data" / "story_universe.json").read_text(encoding="utf-8"))
        self.assertEqual(story["meta"]["sampleFingerprint"], fingerprint)
        self.assertEqual(len(self.detail_shards), DETAIL_SHARD_COUNT)
        self.assertEqual(len(self.details), expected_count)
        self.assertEqual(frontend_meta["sourceRecordCount"], self.manifest["stages"]["source_rows"])
        self.assertEqual(
            frontend_meta["yearRange"],
            [int(self.frame["年份"].min()), int(self.frame["年份"].max())],
        )

        columns = {name: index for index, name in enumerate(self.frontend["columns"])}
        self.assertFalse({"director", "synopsis", "geminiReview"}.intersection(columns))
        for shard_number, payload in enumerate(self.detail_shards):
            self.assertEqual(payload["meta"]["shard"], shard_number)
            self.assertEqual(payload["meta"]["shardCount"], DETAIL_SHARD_COUNT)
            self.assertEqual(payload["meta"]["sampleFingerprint"], fingerprint)
            self.assertEqual(payload["meta"]["recordCount"], len(payload["records"]))
            shard_columns = {name: index for index, name in enumerate(payload["columns"])}
            self.assertTrue(all(
                detail_shard(row[shard_columns["movieId"]]) == shard_number
                for row in payload["records"]
            ))
        for index in (0, expected_count // 2, expected_count - 1):
            frontend_row = self.frontend["records"][index]
            particle_row = self.particles["records"][index]
            derived_row = self.frame.iloc[index]
            self.assertEqual(frontend_row[columns["movieId"]], str(derived_row["movie_id"]))
            self.assertEqual(frontend_row[columns["title"]], derived_row["片名"])
            detail = self.details[str(derived_row["movie_id"])]
            expected_director = derived_row["导演"] if pd.notna(derived_row["导演"]) else ""
            self.assertEqual(detail["director"], expected_director)
            synopsis = usable_detail_text(derived_row["剧情简介"])
            gemini_review = usable_detail_text(derived_row["Gemini评价"], gemini=True)
            expected_kind = 0 if synopsis else 1 if gemini_review else 2
            expected_summary = synopsis or gemini_review
            if len(expected_summary) > DETAIL_SUMMARY_LIMIT:
                expected_summary = expected_summary[:DETAIL_SUMMARY_LIMIT].rstrip() + "…"
            self.assertEqual(detail["summaryKind"], expected_kind)
            self.assertEqual(detail["summary"], expected_summary)
            self.assertEqual(particle_row[0], derived_row["片名"])
            self.assertEqual(particle_row[1], int(derived_row["年份"]))
            self.assertEqual(particle_row[3], int(derived_row["Region_Code"]) + 1)
        summary_coverage = sum(bool(detail["summary"]) for detail in self.details.values()) / expected_count
        self.assertGreater(summary_coverage, 0.80)

    def test_narrative_facts_match_the_publication_sample(self):
        year_1994 = self.frame[self.frame["年份"] == 1994]
        decade_1990s = self.frame[self.frame["年份"].between(1990, 1999)]
        other_1990s = decade_1990s[decade_1990s["年份"] != 1994]
        year_2011 = self.frame[self.frame["年份"] == 2011]
        north_america = year_2011[year_2011["Region_Code"] == 0]
        east_asia_china = year_2011[year_2011["Region_Code"].isin([2, 3])]
        facts_2011 = self.facts["year_2011"]

        self.assertEqual(self.facts["meta"]["record_count"], len(self.frame))
        self.assertEqual(self.facts["year_1994"]["n"], len(year_1994))
        self.assertAlmostEqual(self.facts["year_1994"]["mean"], year_1994["豆瓣评分"].mean(), places=4)
        year_1994_high_share = year_1994["豆瓣评分"].ge(8.5).mean() * 100
        other_1990s_high_share = other_1990s["豆瓣评分"].ge(8.5).mean() * 100
        self.assertAlmostEqual(self.facts["year_1994"]["high_share"], year_1994_high_share, places=4)
        self.assertAlmostEqual(
            self.facts["other_1990s_excluding_1994"]["high_share"],
            other_1990s_high_share,
            places=4,
        )
        self.assertLess(abs(year_1994_high_share - other_1990s_high_share), 0.3)
        self.assertEqual(facts_2011["north_america"]["n"], len(north_america))
        self.assertEqual(facts_2011["east_asia_china"]["n"], len(east_asia_china))
        raw_delta = east_asia_china["豆瓣评分"].mean() - north_america["豆瓣评分"].mean()
        self.assertEqual(facts_2011["delta"], round(raw_delta, 4))
        self.assertAlmostEqual(
            facts_2011["delta"],
            raw_delta,
            places=3,
        )
        self.assertEqual(len(self.facts["yearly_region_sign_changes_min_n_30"]), 5)

        europe = self.frame[self.frame["Region_Code"] == 1]
        non_europe = self.frame[self.frame["Region_Code"] != 1]
        europe_standardized = standardized_mean(europe, self.frame, ["Decade", "Genre_Code"])
        non_europe_standardized = standardized_mean(non_europe, self.frame, ["Decade", "Genre_Code"])
        expected_standardized_gap = europe_standardized["mean"] - non_europe_standardized["mean"]
        self.assertAlmostEqual(
            self.facts["europe_standardization"]["standardized_gap"],
            expected_standardized_gap,
            places=4,
        )
        self.assertAlmostEqual(
            self.facts["europe_standardization"]["non_europe"]["distribution"]["below_five_share"],
            non_europe["豆瓣评分"].lt(5).mean() * 100,
            places=4,
        )
        self.assertAlmostEqual(
            self.facts["europe_standardization"]["non_europe"]["distribution"]["q1"],
            non_europe["豆瓣评分"].quantile(0.25),
            places=4,
        )
        self.assertEqual(europe_standardized["reference_weight_coverage"], 1.0)

        cutoff_values = self.facts["cutoff_sensitivity"]["values"]
        self.assertEqual(len(cutoff_values), 31)
        self.assertGreater(min(item["mean_gap"] for item in cutoff_values), 0.5)
        language_by_decade = self.facts["mandarin_dialect"]["by_decade"]
        self.assertLess(language_by_decade["1990s"]["mean_delta"], 0)
        self.assertGreater(language_by_decade["2010s"]["mean_delta"], 0)
        # F12 防陈旧口径回归：mandarin_dialect 必须是 Region=China 口径的绝对 n 值
        china_frame = self.frame[self.frame["Region"] == "China"]
        self.assertEqual(
            self.facts["mandarin_dialect"]["dialect_mixed"]["n"],
            int(china_frame["Is_Dialect"].eq(1).sum()),
        )
        self.assertEqual(
            self.facts["mandarin_dialect"]["mandarin"]["n"],
            int(china_frame["Is_Dialect"].eq(0).sum()),
        )
        self.assertIn("口径说明_20260814", self.facts["meta"])
        self.assertEqual(int(self.frame["年份"].eq(2021).sum()), 2170)
        language_labels = {0: "英语", 1: "日语", 2: "普通话", 3: "方言", 4: "韩语", 5: "其他"}
        for code, label in language_labels.items():
            self.assertEqual(
                self.facts["languages"][label]["n"],
                int(self.frame["Language_Code"].eq(code).sum()),
            )

    def test_homepage_has_no_stale_sample_claims_or_compressed_chart(self):
        # 方言主线前端（v4.3 定稿后）：守护动态占位 id 与详情弹窗骨架，
        # 防止旧版"味觉分析"前端的静态断言残留回归。
        html = (TASTE_ROOT / "frontend" / "index.html").read_text(encoding="utf-8")
        app_js = (TASTE_ROOT / "frontend" / "js" / "app.js").read_text(encoding="utf-8")
        story_js = "\n".join(
            (TASTE_ROOT / "frontend" / "js" / name).read_text(encoding="utf-8")
            for name in ("app.js", "core.js", "gallery.js")
        )
        for stale_claim in ("1,354", "只有 11 部", "+0.047", "0.21 分差异"):
            self.assertNotIn(stale_claim, html)
            self.assertNotIn(stale_claim, story_js)
        # 封面与方法论页的动态占位 id（运行时由载荷填充，禁止写死）
        for dynamic_id in (
            "hero-sample-count",
            "sample-year-range",
            "minimum-vote-count",
            "source-record-count",
            "methodology-minimum-vote-count",
            "methodology-sample-count",
            "methodology-year-range",
            "year-2022plus-count",
            "year-2022plus-china-count",
            "china-dialect-2020s-n",
            "particle-sample-count",
            "overall-unweighted-mean",
            "overall-vote-weighted-mean",
        ):
            self.assertIn(f'id="{dynamic_id}"', html)
        self.assertIn('id="movie-detail-dialog"', html)
        self.assertIn('id="movie-detail-gemini-section"', html)
        self.assertIn("openMovieDetail(movie)", app_js)
        self.assertIn("loadMovieDetailShard", story_js)
        self.assertIn('data-movie-id=', story_js)
        self.assertIn("{ left: 0, right: 0, top: 0, bottom: 0", app_js)
        self.assertIn("{ left: 8, right: 8, top: 8, bottom: 8", app_js)
        self.assertNotIn("left: '52%'", app_js)

        stale_titles = (
            "百年电影审美演化史",
            "分母如何改写影史直觉",
            "电影评分里的样本偏差",
            "53,491 部电影能告诉我们什么",
            "电影真的有“高分年代”和“高分地区”吗",
            "好莱坞的同质化通道",
            "东亚星系的突围",
            "算法入侵与商业沉沦",
            "欧洲艺术电影的“高下限”",
            "打破算法霸权",
            "老电影和欧洲电影，为什么评分更高？",
        )
        for stale_title in stale_titles:
            self.assertNotIn(stale_title, html)
        self.assertIn('方言电影为什么“赢”了？', html)

    def test_comparison_scenes_have_direct_reference_lines(self):
        app_js = (TASTE_ROOT / "frontend" / "js" / "app.js").read_text(encoding="utf-8")
        self.assertIn("function horizontalGuide", app_js)
        self.assertIn("function verticalGuide", app_js)
        self.assertIn("function createGuideMarkLine", app_js)
        self.assertIn("function horizontalDifferenceBand", app_js)
        self.assertIn("function standardizedMeanByDecadeGenre", app_js)
        self.assertEqual(app_js.count("markLine: createGuideMarkLine("), 10)
        self.assertGreaterEqual(app_js.count("markArea:"), 5)
        self.assertIn("标准化均值", app_js)
        self.assertIn("编辑高分阈值 8.5", app_js)
        self.assertIn("低分界线 5.0", app_js)
        self.assertIn("'dual-director': () =>", app_js)
        self.assertNotIn("'breakout-2011'", app_js)
        self.assertGreaterEqual(app_js.count("type: 'value', min: -0.8, max:"), 2)
        self.assertIn("const LANGUAGE_DISPLAY_ORDER = [0, 1, 4, 2, 3, 5]", app_js)
        self.assertIn("const languageOrder = LANGUAGE_DISPLAY_ORDER.filter", app_js)
        self.assertIn("verticalGuide(languagePosition(selectedLanguage)", app_js)
        self.assertIn("max: 2020", app_js)

    def test_editorial_copy_leads_with_findings_instead_of_repeated_disclaimers(self):
        # 方言主线前端文案守护：禁止旧版重复免责声明短语回归；
        # "观察性样本"全库仅允许出现一次（方法论页脚）。注：方言叙事正文
        # 合法使用"不是/而是/并非"等转折连词（终章拆对立段落），不再禁断。
        frontend = TASTE_ROOT / "frontend"
        copy = "\n".join(
            path.read_text(encoding="utf-8")
            for path in [
                frontend / "index.html",
                frontend / "vol1_time.html",
                frontend / "vol2_geo.html",
                frontend / "vol3_lang.html",
                frontend / "vol4_memory.html",
                frontend / "js" / "app.js",
            ]
        )
        for stale_phrase in (
            "当前样本",
            "发布样本",
            "样本内",
            "本样本",
            "先看分母",
            "当前筛选分母",
            "而不是全球电影总体",
            "并非完整电影史",
            "这份数据里",
            "该切片",
            "不能说明",
            "无法说明",
            "并不意味着",
        ):
            self.assertNotIn(stale_phrase, copy)
        self.assertEqual(copy.count("观察性样本"), 1)
        self.assertIn("方言电影", copy)

    def test_volume_pages_use_scoped_layout_and_valid_chart_encodings(self):
        frontend_dir = TASTE_ROOT / "frontend"
        style = (frontend_dir / "style.css").read_text(encoding="utf-8")
        vol2_js = (frontend_dir / "js" / "vol2.js").read_text(encoding="utf-8")
        vol3_js = (frontend_dir / "js" / "vol3.js").read_text(encoding="utf-8")
        core_js = (frontend_dir / "js" / "core.js").read_text(encoding="utf-8")
        for name in ("vol1_time.html", "vol2_geo.html", "vol3_lang.html", "vol4_memory.html"):
            html = (frontend_dir / name).read_text(encoding="utf-8")
            self.assertIn('<body class="volume-page">', html)
        self.assertIn(".volume-page .sidebar", style)
        self.assertIn(".volume-page .movie-card {\n    min-height: 164px;\n    padding: 20px;\n    cursor: pointer;", style)
        self.assertIn("lowerWhisker", vol2_js)
        self.assertIn("upperWhisker", vol2_js)
        self.assertNotIn("roseType", vol3_js)
        self.assertIn("type: 'bar'", vol3_js)
        self.assertIn("d.langCode", vol3_js)
        self.assertIn("六组等额", vol3_js)
        self.assertIn("m.langCode !== Number(language)", core_js)
        self.assertNotIn("m.language !== language", core_js)
        self.assertIn("async function openSharedMovieDetail(movie)", core_js)
        self.assertIn("card.type = 'button'", core_js)
        # 详情弹窗的详情填充逻辑已抽到 lib/movie-detail.js：通过 view 委托最终调用
        # DataService.getMovieDetails（core.js 的 view.getMovieDetails 转发）。
        movie_detail_js = (frontend_dir / "js" / "lib" / "movie-detail.js").read_text(encoding="utf-8")
        self.assertIn("view.getMovieDetails(movie.movieId)", movie_detail_js)
        self.assertIn("DataService.getMovieDetails", core_js)
        self.assertIn("renderLocalGallery(results, queryTitle, 'movie-grid', 50)", (frontend_dir / "js" / "vol4.js").read_text(encoding="utf-8"))
        for name in ("index.html", "vol4_memory.html"):
            html = (frontend_dir / name).read_text(encoding="utf-8")
            for code in range(6):
                self.assertIn(f'<option value="{code}">', html)

    def test_repository_documents_and_continuously_checks_reproducibility(self):
        readme = (TASTE_ROOT / "README.md").read_text(encoding="utf-8")
        workflow = (TASTE_ROOT / ".github" / "workflows" / "validate.yml").read_text(encoding="utf-8")
        for heading in (
            "## 核心发现",
            "## 从零重建与验证",
            "## 哪些内容可以复刻",
            "## 数据文件",
            "## 数据口径",
            "## 方言分析子系统",
            "## 已知边界",
        ):
            self.assertIn(heading, readme)
        self.assertIn("docs/preview.webp", readme)
        self.assertIn(self.manifest["sample_fingerprint_sha256"], readme)
        self.assertIn("方言 6.62，普通话 6.11", readme)
        self.assertIn("方言 6.4%，普通话 24.4%", readme)
        self.assertIn("方言 9.5%，普通话 11.9%", readme)
        self.assertIn("geo_enrichment.json", readme)
        self.assertIn("visual_land_masks.json", readme)
        self.assertIn("224 标签", readme)
        self.assertIn("15.4%", readme)
        self.assertIn("239KB", readme)
        self.assertIn("max: 2020", readme)
        self.assertNotIn("220 标签", readme)
        self.assertIn("python rebuild.py", workflow)
        self.assertIn("python -m unittest discover -s tests -v", workflow)
        self.assertIn("git diff --exit-code", workflow)
        self.assertIn("frontend/js/scenes/scene_waves.js", workflow)
        self.assertIn("npm run check:budget", workflow)
        self.assertIn("npm run check:contracts", workflow)
        self.assertIn("verify_freeze_readiness.py", workflow)
        fonts = TASTE_ROOT / "frontend" / "fonts"
        for name in ("outfit-latin-400.woff2", "outfit-latin-700.woff2", "outfit-latin-900.woff2"):
            self.assertTrue((fonts / name).is_file(), name)
        self.assertTrue((TASTE_ROOT / "frontend" / "assets" / "og-cover.jpg").is_file())
        homepage = (TASTE_ROOT / "frontend" / "index.html").read_text(encoding="utf-8")
        self.assertIn("build/echarts-main.", homepage)
        self.assertIn("build/app.", homepage)

    def test_replay_v44_script_documents_the_patch_chain(self):
        path = TASTE_ROOT / "scripts" / "replay_v44_baseline.py"
        self.assertTrue(path.is_file())
        text = path.read_text(encoding="utf-8")
        for name in (
            "apply_tier2b_reclassify_20260815.py",
            "apply_empty_lang_backfill_20260818.py",
            "apply_audit_exclude_20260818.py",
            "apply_f7_region_fix_20260818.py",
            "apply_opera_concert_exclude_20260818.py",
            "apply_ama_lang_fix_20260819.py",
            "apply_first_listed_region_20260824.py",
        ):
            self.assertIn(name, text)
        result = subprocess.run(
            [sys.executable, str(path), "--help"],
            capture_output=True,
            text=True,
            cwd=TASTE_ROOT,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_first_listed_region_on_space_separated_publication_row(self):
        row = self.frame[self.frame["movie_id"].astype(str) == "35594883"]
        self.assertEqual(len(row), 1)
        self.assertEqual(row.iloc[0]["Region"], "East_Asia")
        west = self.frame[self.frame["制片国家/地区"].fillna("").map(first_listed_value).eq("西德")]
        self.assertGreater(len(west), 0)
        self.assertTrue((west["Region"] == "Europe").all())


class DialectDefinitionTests(unittest.TestCase):
    """方言定义 SSOT（dialect_defs.py）核心判定函数测试。"""

    def test_pure_dialect_tags(self):
        self.assertTrue(has_strict_dialect_tag("粤语"))
        self.assertTrue(has_strict_dialect_tag("四川话"))
        self.assertTrue(has_strict_dialect_tag("闽南语"))
        self.assertTrue(has_strict_dialect_tag("上海话"))

    def test_mandarin_not_dialect(self):
        self.assertFalse(has_strict_dialect_tag("汉语普通话"))
        self.assertFalse(has_strict_dialect_tag("国语"))
        self.assertFalse(has_strict_dialect_tag("普通话"))

    def test_foreign_not_dialect(self):
        self.assertFalse(has_strict_dialect_tag("英语"))
        self.assertFalse(has_strict_dialect_tag("日语"))
        self.assertFalse(has_strict_dialect_tag("法语"))

    def test_mixed_dialect_mandarin(self):
        self.assertTrue(has_strict_dialect_tag("粤语 / 汉语普通话"))

    def test_mixed_dialect_foreign(self):
        self.assertTrue(has_strict_dialect_tag("四川话 / 英语"))

    def test_minority_language_is_dialect(self):
        self.assertTrue(has_strict_dialect_tag("藏语"))
        self.assertTrue(has_strict_dialect_tag("蒙古语"))
        self.assertTrue(has_strict_dialect_tag("维吾尔语"))
        self.assertTrue(has_strict_dialect_tag("苗语"))

    def test_empty_and_nan(self):
        self.assertFalse(has_strict_dialect_tag(""))
        self.assertFalse(has_strict_dialect_tag(float("nan")))

    def test_mandarin_normalize(self):
        self.assertEqual(normalize_language_tags("国语 / 粤语"), ["普通话", "粤语"])
        self.assertEqual(normalize_language_tags("台湾国语"), ["台湾国语"])
        self.assertEqual(normalize_language_tags("汉语普通话"), ["普通话"])

    def test_get_dialect_tags_found(self):
        tags = get_dialect_tags_found("粤语 / 英语")
        self.assertIn("粤语", tags)
        self.assertNotIn("英语", tags)

    def test_has_mandarin_tag(self):
        self.assertTrue(has_mandarin_tag("汉语普通话"))
        self.assertTrue(has_mandarin_tag("国语"))
        self.assertFalse(has_mandarin_tag("粤语"))

    def test_has_foreign_tag(self):
        self.assertTrue(has_foreign_tag("英语"))
        self.assertTrue(has_foreign_tag("日语"))
        self.assertFalse(has_foreign_tag("粤语"))

    def test_no_duplicate_markers(self):
        self.assertEqual(len(DIALECT_MARKERS_STRICT), len(set(DIALECT_MARKERS_STRICT)))
        self.assertEqual(len(DIALECT_MARKERS_STRICT), 224)

    def test_dialect_report_baseline_uses_freeze_constants(self):
        source = (TASTE_ROOT / "scripts" / "gen_dialect_report.py").read_text(encoding="utf-8")
        self.assertIn("from freeze_constants import TIER_BASELINE", source)
        self.assertIn("== TIER_BASELINE", source)
        self.assertEqual(
            TIER_BASELINE,
            (CHINA_DIALECT, TIER1_PURE, TIER2A_DIALECT_FIRST, TIER2B_MANDARIN_FIRST),
        )

    def test_short_marker_dai(self):
        # F5：短拉丁标记精确匹配（2026-08-15）
        self.assertTrue(has_strict_dialect_tag("dai"))
        self.assertTrue(has_strict_dialect_tag("傣语"))
        self.assertTrue(has_strict_dialect_tag("傣语 / 汉语普通话"))
        # 关键：含 "dai" 子串的英文单词不应误命中
        self.assertFalse(has_strict_dialect_tag("daily"))
        self.assertFalse(has_strict_dialect_tag("update"))
        self.assertFalse(has_strict_dialect_tag("daisy"))
    
    def test_short_latin_markers_set(self):
        # F5：短拉丁标记集合仅含 ASCII 且 ≤3 字符
        self.assertIn("dai", SHORT_LATIN_MARKERS)
        for m in SHORT_LATIN_MARKERS:
            self.assertTrue(m.isascii(), f"{m} 应为 ASCII")
            self.assertLessEqual(len(m), 3)

    # ---- F10 补测试（2026-08-15）----

    def test_f1_generic_dialect_tag_not_mandarin(self):
        # F1 回归："汉语方言/中文方言"含"汉语/中文"子串，但方言优先，
        # 不得被判为普通话标签或被归一化为"普通话"（否则 6 部误降 Tier 2b）。
        self.assertFalse(has_mandarin_tag("汉语方言"))
        self.assertFalse(has_mandarin_tag("中文方言"))
        self.assertEqual(normalize_language_tags("汉语方言"), ["汉语方言"])
        self.assertTrue(has_strict_dialect_tag("汉语方言"))

    def test_f1_generic_dialect_tag_tier1(self):
        # 语言字段仅为通用方言标签 → Tier 1（纯方言，无普通话标签）
        self.assertEqual(classify_strict({"语言": "汉语方言"})["tier"], "Tier 1")
        self.assertEqual(classify_strict({"语言": "汉语方言"})["is_dialect"], 1)
        is_d, tier, _, _ = classify_v21("汉语方言")
        self.assertEqual((is_d, tier), (1, "Tier 1"))

    def test_compound_dialect_mandarin_tag_tier1(self):
        # 复合标签行为快照（F1 收尾后）："汉语普通话 汉语方言"作为单一 part
        # 含方言白名单子串 → 方言优先，不贡献普通话信号 → Tier 1。
        # 若字段中另有独立普通话 part（如《归去来》"汉语普通话 / 汉语普通话 汉语方言"）
        # 则仍判 Tier 2，见下条。
        info = classify_strict({"语言": "汉语普通话 汉语方言"})
        self.assertEqual(info["is_dialect"], 1)
        self.assertEqual(info["tier"], "Tier 1")

    def test_compound_with_separate_mandarin_part_tier2(self):
        # v4.1（2026-08-15）：Tier 2b（普通话排首+方言标签）默认排除，
        # 仅 Dialect_Evidence 记录补回证据时才计方言。
        info = classify_strict({"语言": "汉语普通话 / 汉语方言"})
        self.assertEqual(info["is_dialect"], 0)
        self.assertEqual(info["tier"], "非方言")
        info_recovered = classify_strict({"语言": "汉语普通话 / 汉语方言", "Dialect_Evidence": "E:E1"})
        self.assertEqual(info_recovered["is_dialect"], 1)
        self.assertEqual(info_recovered["tier"], "Tier 2b")

    def test_taiwanese_mandarin_preserved(self):
        # "台湾国语"保留不归并为"普通话"（既有断言，防回归）
        self.assertEqual(normalize_language_tags("台湾国语"), ["台湾国语"])

    def test_plan_a_first_tag_is_foreign(self):
        # 方案 A 判定：首个标签外语 → True；方言/普通话排首 → False
        self.assertTrue(first_tag_is_foreign("英语 / 粤语"))
        self.assertTrue(first_tag_is_foreign("English / 汉语普通话 / 粤语"))
        self.assertFalse(first_tag_is_foreign("粤语 / 英语"))
        self.assertFalse(first_tag_is_foreign("汉语普通话 / 英语"))
        self.assertFalse(first_tag_is_foreign(""))

    def test_plan_a_exclusion_in_classifiers(self):
        # 方案 A 在两个报告判定函数中生效：外语排首 → 非方言；
        # 外语非首位 → 保留（避免误杀《我不是药神》类）。
        self.assertEqual(classify_strict({"语言": "英语 / 粤语"})["is_dialect"], 0)
        self.assertEqual(classify_strict({"语言": "粤语 / 英语"})["is_dialect"], 1)
        self.assertEqual(classify_v21("英语 / 粤语")[0], 0)
        self.assertEqual(classify_v21("粤语 / 英语")[0], 1)

    def test_audit_exclude_list_completeness(self):
        # 审计排除名单完整性：22 部已知 ID（境外方言 4 + 朝鲜语歧义 17 + 错误行 1）
        self.assertEqual(len(DIALECT_AUDIT_EXCLUDE_MOVIE_IDS), 22)
        for known_id in ("1297614", "3035549", "4745879", "26577728",
                         "3027168", "5279979", "26700520"):
            self.assertIn(known_id, DIALECT_AUDIT_EXCLUDE_MOVIE_IDS)

    # ---- 待审清单第五/六类增补断言（2026-08-15）----

    def test_fifth_type_minority_markers_added(self):
        # 第五类：少数民族语言白名单增补命中 has_minority_tag 与 has_strict_dialect_tag
        for tag in ("赛德克语", "台湾原住民语言"):
            self.assertTrue(has_minority_tag(tag), f"{tag} 应命中 has_minority_tag")
            self.assertTrue(has_strict_dialect_tag(tag), f"{tag} 应命中 has_strict_dialect_tag")
        # 客家话组增补"客话"、闽南语组增补"福建语"
        for tag in ("客话", "福建语"):
            self.assertTrue(has_strict_dialect_tag(tag), f"{tag} 应命中 has_strict_dialect_tag")

    def test_sixth_type_foreign_typo_markers(self):
        # 第六类：FOREIGN_MARKERS 错拼变体增补命中 has_foreign_tag
        typo_tags = ("菏兰语", "土尔其语", "亚美尼加语", "russina", "希伯來", "泰庐固语")
        for tag in typo_tags:
            self.assertTrue(has_foreign_tag(tag), f"{tag} 应命中 has_foreign_tag")
            # 错拼标签不应误命中方言白名单
            self.assertFalse(has_strict_dialect_tag(tag), f"{tag} 不应命中 has_strict_dialect_tag")

    def test_sixth_type_typo_markers_in_foreign_markers_tuple(self):
        # 断言 6 个错拼变体均已加入 FOREIGN_MARKERS 元组
        for tag in ("菏兰语", "土尔其语", "亚美尼加语", "russina", "希伯來", "泰庐固语"):
            self.assertIn(tag, FOREIGN_MARKERS, f"{tag} 应在 FOREIGN_MARKERS 中")

    def test_fifth_type_minority_markers_in_minority_markers_tuple(self):
        # 断言新增少数民族标签已加入 MINORITY_MARKERS 元组
        for tag in ("赛德克语", "台湾原住民语言"):
            self.assertIn(tag, MINORITY_MARKERS, f"{tag} 应在 MINORITY_MARKERS 中")


class Tier2bEvidenceReviewTests(unittest.TestCase):
    """v4.1（2026-08-15）Tier 2b 证据审查：默认排除 + 证据漏斗补回。"""

    @classmethod
    def setUpClass(cls):
        data_dir = TASTE_ROOT / "data"
        cls.frame = pd.read_csv(
            data_dir / "cleaned" / "derived_movies.csv",
            dtype={"movie_id": "string"},
            low_memory=False,
        )

    def _by_title_year(self, title, year):
        return self.frame[(self.frame["片名"] == title) & (self.frame["年份"] == year)]

    def test_classifiers_default_exclude_tier2b_without_evidence(self):
        # 无补回证据 → 两个判定函数均默认排除；TIER2B_EXCLUDED 同样排除
        self.assertEqual(classify_v21("汉语普通话 / 粤语")[0], 0)
        self.assertEqual(classify_v21("汉语普通话 / 粤语", "TIER2B_EXCLUDED")[0], 0)
        self.assertEqual(classify_v21("汉语普通话 / 粤语", "LLM_JUDGE"),
                         (1, "Tier 2b", ["粤语"], ["粤语（广府片/白话）"]))
        self.assertEqual(classify_strict({"语言": "汉语普通话 / 粤语"})["is_dialect"], 0)
        self.assertEqual(
            classify_strict({"语言": "汉语普通话 / 粤语", "Dialect_Evidence": "BENCHMARK"})["is_dialect"], 1)

    def test_benchmark_movies_recovered(self):
        # 用户指定标杆片（公认方言片）必须在新基线内（片名+年份消歧）
        benchmarks = (("疯狂的石头", 2006), ("疯狂的赛车", 2009), ("西藏往事", 2011),
                      ("秘密基地", 2020), ("亲爱的", 2014), ("心花路放", 2014))
        for title, year in benchmarks:
            rows = self._by_title_year(title, year)
            self.assertEqual(len(rows), 1, f"标杆片 {title}({year}) 应唯一存在")
            row = rows.iloc[0]
            self.assertEqual(int(row["Is_Dialect"]), 1, f"{title}({year}) 应计方言片")
            self.assertEqual(int(row["Language_Code"]), 3)
            self.assertNotIn(row["Dialect_Evidence"], ("", "TIER2B_EXCLUDED"))

    def test_shaw_brothers_dubbed_movies_excluded(self):
        # 邵氏国语配音片（假阳性群代表）必须在默认排除清单
        for title in ("少林三十六房", "冷血十三鹰"):
            rows = self.frame[self.frame["片名"] == title]
            self.assertGreaterEqual(len(rows), 1)
            for _, row in rows.iterrows():
                self.assertEqual(int(row["Is_Dialect"]), 0, f"{title} 应被排除")
                self.assertEqual(row["Dialect_Evidence"], "TIER2B_EXCLUDED")
                self.assertEqual(int(row["Language_Code"]), 2)

    def test_tier2b_reclassify_counts_and_invariants(self):
        # 原 702 池 = 348 补回 + 354 排除（含用户复核移出的《芒种》1986783）；
        # 2026-08-16 空语言补全新增出花园"人工复核"补回 1 部 → Tier 2b 共 349。
        # 2026-08-18 戏曲/演唱会审计从补回池中移出 2 部（《卷席筒》E:E1、《五女拜寿》LLM_JUDGE，
        # 改标 AUDIT_EXCLUDED_OPERA_CONCERT）→ 346。
        # 不变量 code2==Chinese&D0、code3==D1
        evidence = self.frame["Dialect_Evidence"].fillna("")
        recovered = evidence.str.startswith(("E:", "BENCHMARK", "LLM_JUDGE", "人工复核"))
        excluded = evidence.eq("TIER2B_EXCLUDED")
        self.assertEqual(int(recovered.sum()), TIER2B_MANDARIN_FIRST)
        self.assertEqual(int(excluded.sum()), TIER2B_EXCLUDED)
        self.assertEqual(int(self.frame.loc[recovered, "Is_Dialect"].astype(int).sum()), TIER2B_MANDARIN_FIRST)
        self.assertEqual(int(self.frame.loc[excluded, "Is_Dialect"].astype(int).sum()), 0)
        china = self.frame["Region"] == "China"
        # 2026-08-19 v4.4：《给阿嬷的情书》语言字段修正后补收（3044→3045）
        self.assertEqual(int((china & self.frame["Is_Dialect"].astype(int).eq(1)).sum()), CHINA_DIALECT)
        # 用户人工复核决定（2026-08-15）：《芒种》不算方言片
        mz = self.frame[self.frame["movie_id"].astype(str) == "1986783"]
        self.assertEqual(len(mz), 1)
        self.assertEqual(int(mz.iloc[0]["Is_Dialect"]), 0)
        self.assertEqual(mz.iloc[0]["Dialect_Evidence"], "TIER2B_EXCLUDED")
        code2 = int((self.frame["Language_Code"] == 2).sum())
        ch_d0 = int(((self.frame["Language_Category"] == "Chinese") & (self.frame["Is_Dialect"] == 0)).sum())
        code3 = int((self.frame["Language_Code"] == 3).sum())
        d1 = int((self.frame["Is_Dialect"] == 1).sum())
        self.assertEqual(code2, ch_d0)
        self.assertEqual(code3, d1)

    def test_report_data_strict_matches_csv_baseline(self):
        # 三方一致之一：report_data_strict.json 汇总 == CSV 基线
        report = json.loads(
            (TASTE_ROOT / "data" / "dialect_films" / "report_data_strict.json").read_text(encoding="utf-8"))
        summary = report["summary"]
        self.assertEqual(summary["total_dialect"], CHINA_DIALECT)
        self.assertEqual(summary["tier1_pure"], TIER1_PURE)
        self.assertEqual(summary["tier2a_dialect_first"], TIER2A_DIALECT_FIRST)
        self.assertEqual(summary["tier2b_mandarin_first"], TIER2B_MANDARIN_FIRST)


class OperaConcertExcludeRegressionTests(unittest.TestCase):
    """2026-08-18 戏曲/演唱会审计：49 部非叙事影片排除出方言口径（定义 E4/E9）。"""

    @classmethod
    def setUpClass(cls):
        cls.frame = pd.read_csv(
            TASTE_ROOT / "data" / "cleaned" / "derived_movies.csv",
            dtype={"movie_id": "string"},
            low_memory=False,
        )

    def test_exclude_list_completeness(self):
        # 名单恰 49 部（戏曲 10 + 演唱会 21 + 音乐纪录片 9 + 颁奖典礼 9）
        self.assertEqual(len(OPERA_CONCERT_EXCLUDE_MOVIE_IDS), 49)
        for known_id in ("4307305", "1918697", "2305317",  # 戏曲片代表
                         "30468861", "33211868",            # 演唱会代表
                         "26740516", "30377813"):           # 颁奖典礼代表
            self.assertIn(known_id, OPERA_CONCERT_EXCLUDE_MOVIE_IDS)

    def test_excluded_movies_not_dialect(self):
        # 名单内影片全部 Is_Dialect=0 且标记 AUDIT_EXCLUDED_OPERA_CONCERT
        rows = self.frame[self.frame["movie_id"].isin(OPERA_CONCERT_EXCLUDE_MOVIE_IDS)]
        self.assertEqual(len(rows), 49)
        self.assertEqual(int(rows["Is_Dialect"].astype(int).sum()), 0)
        self.assertTrue((rows["Dialect_Evidence"].fillna("") == "AUDIT_EXCLUDED_OPERA_CONCERT").all())
        # 名单不出现在任何 Is_Dialect=1 行
        d1_ids = set(self.frame.loc[self.frame["Is_Dialect"].astype(int).eq(1), "movie_id"])
        self.assertFalse(d1_ids & OPERA_CONCERT_EXCLUDE_MOVIE_IDS)

    def test_classifiers_honor_exclude_list(self):
        # 两个报告判定函数均尊重名单：名单内影片即使语言字段含方言标签也不计方言
        self.assertEqual(classify_strict({"语言": "粤语", "movie_id": "30468861"})["is_dialect"], 0)
        self.assertEqual(classify_v21("粤语", "", "30468861")[0], 0)
        # 名单外影片不受影响
        self.assertEqual(classify_strict({"语言": "粤语", "movie_id": "99999999"})["is_dialect"], 1)
        self.assertEqual(classify_v21("粤语", "", "99999999")[0], 1)


class AmaLangFixRegressionTests(unittest.TestCase):
    """2026-08-19 v4.4：《给阿嬷的情书》(37116446) 语言字段修正补收。

    delivery_20260817 不含语言列，该片曾被空语言回填默认成"汉语普通话"；
    豆瓣实页语言 = 潮汕话 / 汉语普通话 / 泰语 / 英语（潮汕话居首），
    按白名单应判 Tier 2a、Is_Dialect=1。
    """

    @classmethod
    def setUpClass(cls):
        cls.frame = pd.read_csv(
            TASTE_ROOT / "data" / "cleaned" / "derived_movies.csv",
            dtype={"movie_id": "string"},
            low_memory=False,
        )

    def test_ama_movie_is_dialect_with_correct_lang(self):
        rows = self.frame[self.frame["movie_id"] == "37116446"]
        self.assertEqual(len(rows), 1)
        row = rows.iloc[0]
        self.assertEqual(row["语言"], "潮汕话 / 汉语普通话 / 泰语 / 英语")
        self.assertEqual(int(row["Is_Dialect"]), 1)
        self.assertEqual(int(row["Language_Code"]), 3)
        self.assertIn("LANG_FIX_20260819", str(row["Dialect_Evidence"]))


class DialectAggregatesTests(unittest.TestCase):
    """方言叙事聚合载荷 dialect_aggregates.json（v4.4 基线）。

    口径固化自 scripts/sync_preview_dialect_v43_20260819.py，由
    scripts/data_aggregator.py build_dialect_aggregates() 正式产出；
    本类锁定关键聚合数值、记录数与样本指纹，防后续回归。
    """

    @classmethod
    def setUpClass(cls):
        cls.payload = json.loads(
            (TASTE_ROOT / "data" / "frontend" / "dialect_aggregates.json").read_text(encoding="utf-8"))
        cls.manifest = json.loads(
            (TASTE_ROOT / "data" / "cleaned" / "sample_manifest.json").read_text(encoding="utf-8"))
        cls.frame = pd.read_csv(
            TASTE_ROOT / "data" / "cleaned" / "derived_movies.csv",
            dtype={"movie_id": "string"},
            low_memory=False,
        )

    def test_meta_fingerprint_matches_manifest(self):
        fp = self.manifest["sample_fingerprint_sha256"]
        self.assertEqual(self.payload["meta"]["sampleFingerprint"], fp)

    def test_baseline_block(self):
        baseline = self.payload["meta"]["baseline"]
        self.assertEqual(baseline["china_dialect"], CHINA_DIALECT)
        self.assertEqual(baseline["china_mandarin"], CHINA_MANDARIN)
        self.assertEqual(baseline["china_total"], CHINA_TOTAL)
        self.assertEqual(baseline["dialect_all_regions"], DIALECT_ALL_REGIONS)
        self.assertEqual(baseline["publication_records"], PUBLICATION_RECORDS)

    def test_by_decade_record_counts(self):
        # 各年代 d/m n 之和恰为 China 方言/普通话总数（记录数锁定）
        by_decade = self.payload["by_decade"]
        self.assertEqual(sum(v["d"]["n"] for v in by_decade.values()), CHINA_DIALECT)
        self.assertEqual(sum(v["m"]["n"] for v in by_decade.values()), CHINA_MANDARIN)

    def test_by_decade_key_values(self):
        by_decade = self.payload["by_decade"]
        self.assertEqual(by_decade["2020s"]["d"], {"n": 57, "mean": 6.34, "below5": 15.8})
        self.assertEqual(by_decade["2020s"]["delta"], 0.6)
        self.assertEqual(by_decade["2010s"]["delta"], 0.95)
        self.assertEqual(by_decade["1990s"]["delta"], -0.39)

    def test_flop_and_type_controlled(self):
        self.assertEqual(self.payload["flop_overall"], {"d": 6.4, "m": 24.4})
        self.assertEqual(self.payload["flop_decade"]["2020s"], {"d": 15.8, "m": 32.6})
        raw = self.payload["type_controlled"]["raw"]
        self.assertEqual(raw["d"]["mean"], 6.62)
        self.assertEqual(raw["m"]["mean"], 6.11)
        # 三口径方向不变：剔除非叙事类型/仅剧情后方言仍领先
        for scope in ("exclude", "drama"):
            pair = self.payload["type_controlled"][scope]
            self.assertGreater(pair["d"]["mean"], pair["m"]["mean"], scope)
        self.assertEqual(self.payload["type_controlled"]["exclude"]["d"]["mean"], 6.58)
        self.assertEqual(self.payload["type_controlled"]["drama"]["d"]["mean"], 6.86)

    def test_cantonese_and_global_layers(self):
        canto = {item["name"]: item for item in self.payload["cantonese_vs_non"]}
        self.assertEqual(canto["非粤语方言"]["n"], 480)
        self.assertEqual(canto["粤语"]["n"], 2565)
        layers = {item["name"]: item for item in self.payload["global_layers"]}
        self.assertEqual(layers["华语 · 方言"]["n"], CHINA_DIALECT)
        self.assertEqual(layers["华语 · 方言"]["below5"], 6.4)
        self.assertEqual(layers["华语 · 普通话"]["n"], CHINA_MANDARIN)
        self.assertTrue(layers["华语 · 普通话"].get("outlier"))

    def test_yearly_2010_breakpoint(self):
        yearly = self.payload["yearly"]
        self.assertEqual(yearly["2010"], 0.54)
        # 2011-2020 无反转：全部年份在载荷中且 delta > 0
        for year in range(2011, 2021):
            self.assertIn(str(year), yearly, f"{year} 应满足双方 n>=5")
            self.assertGreater(yearly[str(year)], 0, f"{year} 反转")

    def test_dual_director_diversity_genre(self):
        director = self.payload["dual_director"]
        self.assertEqual(director["total"], 476)
        self.assertEqual(sum(director["hist"].values()), 476)
        self.assertEqual(director["share_positive"], 70)
        self.assertEqual(director["mean_diff"], 0.65)
        diversity = self.payload["lang_diversity"]
        self.assertEqual(len(diversity), 10)
        self.assertEqual(diversity[0], {"name": "客家话", "mean": 7.88, "n": 10})
        self.assertTrue(all(item["n"] >= 10 for item in diversity))
        genre = self.payload["genre_avg"]
        self.assertEqual(len(genre), 8)
        self.assertEqual(genre[0]["name"], "动画")
        self.assertEqual(genre[0]["mean"], 7.62)
        self.assertEqual(genre[0]["n"], 30)
        self.assertEqual(len(genre[0]["top"]), 3)

    def test_wave_cases_exist_and_match_main_table(self):
        waves = self.payload["wave_cases"]
        self.assertEqual(set(waves), {"hk", "sw", "mn"})
        entries = [entry for films in waves.values() for entry in films]
        self.assertEqual(len(entries), 15)
        for entry in entries:
            rows = self.frame[self.frame["movie_id"] == entry["id"]]
            self.assertEqual(len(rows), 1, f"wave 影片 {entry['id']} 应在主表")
            row = rows.iloc[0]
            self.assertEqual(int(row["Is_Dialect"]), 1, f"{entry['title']} 应为方言片")
            self.assertEqual(entry["rating"], float(row["豆瓣评分"]))
            self.assertEqual(entry["title"], row["片名"])


class HomepageChinaKpiTests(unittest.TestCase):
    def test_index_conclusion_numbers_are_dynamic_placeholders(self):
        html = (TASTE_ROOT / "frontend" / "index.html").read_text(encoding="utf-8")
        for stale in ("6.62", "6.11", "20.1%", "24.4%", "12,858", "7.35", "17,707"):
            self.assertNotIn(stale, html)
        for dynamic_id in (
            "china-n",
            "china-mean",
            "china-below5",
            "china-dialect-mean",
            "china-mandarin-mean",
            "dialect-mean",
            "china-dialect-high8",
        ):
            self.assertIn(f'id="{dynamic_id}"', html)
        self.assertIn("2026 年，一部没有头部 IP、巨额投资与流量明星加持的潮汕方言电影", html)
        self.assertNotIn("后续年份没有进入当前快照", html)
        self.assertIn("这是比较门槛，不是数据截止年份", html)

    def test_dialect_mean_fill_uses_china_type_controlled(self):
        app_js = (TASTE_ROOT / "frontend" / "js" / "app.js").read_text(encoding="utf-8")
        self.assertIn("function fillChinaNarrativeKpis", app_js)
        self.assertIn("setTextById('dialect-mean', dialectMean)", app_js)
        self.assertIn("agg.type_controlled.raw", app_js)
        self.assertNotIn("'dialect-mean': dialect.mean.toFixed(2)", app_js)
        self.assertIn("sampleYearExtent = [1888, 2026]", app_js)
        self.assertIn("function findNearestMovieByPixel", app_js)
        self.assertIn("function isMobileViewport", app_js)
        waves = (TASTE_ROOT / "frontend" / "js" / "scenes" / "scene_waves.js").read_text(encoding="utf-8")
        self.assertIn("window.innerWidth <= 768", waves)
        self.assertNotIn("window.innerWidth <= 700", waves)

    def test_scene_waves_javascript_syntax(self):
        path = TASTE_ROOT / "frontend" / "js" / "scenes" / "scene_waves.js"
        result = subprocess.run(["node", "--check", str(path)], capture_output=True, text=True)
        if result.returncode == 127 or "不是内部或外部命令" in (result.stderr or ""):
            self.skipTest("node 不可用")
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
