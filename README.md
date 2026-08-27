# 「言」之有物：从数据看中国电影的答案

[![Validate publication](https://github.com/XinyD/Data-Journalism-Dialect-Films/actions/workflows/validate.yml/badge.svg)](https://github.com/XinyD/Data-Journalism-Dialect-Films/actions/workflows/validate.yml)

一篇由 **63,025 部电影**构成的交互式数据新闻。读者向下阅读时，电影粒子会按类型、地区、年代和语言重排；每一幕都能改变比较条件、核对统计量，并点开具体电影查看简介与来源记录。

![数据新闻首页预览](docs/preview.webp)

这个仓库是独立发布项目。页面、ECharts、规范数据快照、浏览器载荷、统计事实和 64 个电影详情分片都已纳入仓库，运行和重建均不读取其他工作目录。

## 核心发现

| 比较 | 当前发布数据中的结果（v4.5，Region=China，第一制片国） |
| --- | --- |
| 方言 vs 普通话均分 | 方言 6.62，普通话 6.11，差 +0.51 |
| 烂片率（<5 分） | 方言 6.4%，普通话 24.4% |
| 高分率（≥8 分） | 方言 9.5%，普通话 11.9%——方言守住下限，没有赢在天花板 |
| 2010 反超 | 1990s 方言落后 0.39；2010s 反超 +0.95；2020s 延续 +0.60 |
| 全球参照 | 方言均分仍低于欧洲 7.16、北美 6.76；「赢」不外溢到欧美 |
| 同导演 | 476 位双栖导演中 70% 的方言片更高，平均分差 +0.65 |

这些结果描述的是当前发布数据中的评分结构。抽样边界、平台用户构成和因果解释集中列在本文的“数据、方法与局限”区以及本 README 的方法部分。

## 页面组成

- **首页宇宙**：63,025 颗全屏电影粒子，覆盖封面与引言、十幕叙事（对照 / 拐点 / 全球参照 / 失败路径 / 同导演 / 三波浪潮 / 五维 / 刻度坐标系 / 下限 / 立尺）及终章回响。
- **每幕数据卡**：筛选、均值、中位数、标准差、四分位数、高分占比和随机打捞。
- **比较辅助线**：横向统计基准、纵向组别定位线，以及差距色带。
- **电影详情**：首页粒子、探索舱和四个分卷的电影卡片均可打开简介、导演、语言、评价人数和来源记录。
- **四个分卷**：年代变化、地区分布、语言构成与交叉筛选。

## 快速预览

预览已生成的数据新闻不需要安装第三方包，只需要 Python 自带的 HTTP 服务器：

```bash
git clone https://github.com/XinyD/Data-Journalism-Dialect-Films.git
cd Data-Journalism-Dialect-Films
python serve.py
```

浏览器打开：

<http://127.0.0.1:8000/frontend/index.html>

如果 8000 端口已占用：

```bash
python serve.py --port 8011
```

请通过 HTTP 访问页面，不要直接双击 HTML；浏览器需要读取仓库中的 JSON 数据和详情分片。

前端打包产物已提交在 `frontend/build/`。修改 `frontend/js` 或 ECharts 入口后需要 Node.js 20+：

```bash
npm ci
npm run build
npm run check
```

`npm run check` 聚合 JS 语法、gzip 预算，以及 HTML 与 `frontend/build/manifest.json` 的 hashed 资源对照，不依赖 git。社交分享预览图需要绝对地址时，构建前设置 `SITE_URL`；未设置则 `og:image` 保持相对路径，本地预览可用：

```powershell
$env:SITE_URL="https://example.com"
npm run build
```

```bash
SITE_URL=https://example.com npm run build
```

终章「故事宇宙」交互舱（Three.js 星空 + ECharts 地图）已从正式前端下线（画风与正文差异较大），完整板块作为独立副本归档至 [`archive/story-universe.html`](archive/story-universe.html)，通过本地服务器打开（`python serve.py` 后访问 `http://127.0.0.1:8000/archive/story-universe.html`）。该副本复用主站的构建 chunk、数据与 echarts，故以下产物仍需保留且修改后需重新构建：

- `frontend/js/scenes/echo_universe.js`（副本直接 `<script src>` 引入）
- `frontend/js/echo/`、`frontend/src/echo-universe-chunk.js`（构建 chunk 的来源）
- `frontend/data/story_universe.json`（故事宇宙数据，可用以下命令从方言电影聚合重新生成）

若修改了 `frontend/js/echo/` 或 `frontend/src/echo-universe-chunk.js`，仍需 `npm run build`，副本会通过 `frontend/build/manifest.json` 拾取新的 chunk 文件名。

```bash
python scripts/build_story_universe.py
```

主站 JS（ECharts 主包 + `app`）gzip 预算为 300KB；当前约 239KB（以 `npm run check:budget` 为准）。

## 从零重建与验证

推荐使用 Python 3.12；项目的直接依赖记录在 `requirements.txt` 中（含 pandas==2.2.3）。官方复现环境与 CI（`.github/workflows/validate.yml`）一致：Python 3.12 + 该锁文件。若发布快照由其他版本生成，以 CI 复跑结果为准。

### Windows PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python rebuild.py
python -m unittest discover -s tests -v
```

### macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python rebuild.py
python -m unittest discover -s tests -v
```

重建顺序如下：

```text
data/cleaned/derived_movies.csv
        │
        ├── scripts/data_aggregator.py
        │      ├── data/aggregated_stats.json
        │      ├── data/frontend_dataset.json
        │      ├── data/frontend/dialect_aggregates.json
        │      └── data/frontend/details/*.json
        ├── scripts/extract_narrative.py
        │      └── data/narrative_facts.json
        ├── scripts/generate_particles.py
        │      └── data/frontend/particles.json
        ├── scripts/build_geo_enrichment.py
        │      └── data/frontend/geo_enrichment.json
        ├── scripts/build_story_universe.py
        │      └── frontend/data/story_universe.json
        └── scripts/gen_report_strict.py
               └── data/dialect_films/report_data_strict.json
```

成功时应看到：

- 63,025 条发布记录；
- 64 个详情分片；
- 61 项数据、叙事和页面测试通过；冻结校验含 geo / story_universe 指纹；
- 核心发布载荷（含 `geo_enrichment.json`、`story_universe.json`）使用同一数据指纹；
- 重新生成后 `git diff --exit-code` 无差异。

GitHub Actions 会在每次 Push 和 Pull Request 中自动执行上述重建、测试、JavaScript 语法检查和确定性检查。

## 哪些内容可以复刻

| 内容 | 是否包含 | 说明 |
| --- | --- | --- |
| 当前数据新闻页面 | 是 | HTML、CSS、JavaScript 与 `frontend/build` 中的 hashed 包均在仓库内 |
| 63,025 部电影规范快照 | 是 | `data/cleaned/derived_movies.csv`，使用普通 Git 保存，不依赖 Git LFS |
| 图表与统计结果 | 是 | 可从规范快照重新生成（`python rebuild.py`） |
| 电影详情与简介 | 是 | 64 个按电影 ID 分片的 JSON 文件 |
| 方言手工补丁链 | 是 | 从源重建后须运行 `python scripts/replay_v44_baseline.py`（6 个幂等 apply 脚本） |
| 最初 309,817 条上游原始数据 | 否 | 原始文件在发布后继续变化，已无法与当前报道版本严格对应 |
| 从数据采集网站重新抓取 | 否 | 仓库不包含抓取器、账号或外部 API 凭据 |

因此，Fork 或 Clone 后可以完整复刻**当前发布版本及其计算过程**；最初的数据采集过程不在本仓库的复现范围内。

## 数据文件

| 路径 | 用途 |
| --- | --- |
| `data/cleaned/derived_movies.csv` | 规范发布快照，也是所有重建任务的默认输入 |
| `data/cleaned/sample_manifest.json` | 筛选条件、处理阶段计数、去重规则和 SHA-256 指纹 |
| `data/dialect_films/report_data_strict.json` | 中国区方言分类结果（Tier 1/2a/2b） |
| `data/aggregated_stats.json` | 年代、地区、类型等聚合统计 |
| `data/narrative_facts.json` | 正文数字、标准化分析和敏感性分析 |
| `data/frontend_dataset.json` | 首页、分卷和探索舱使用的紧凑浏览器载荷 |
| `data/frontend/particles.json` | 全部电影的粒子坐标编码 |
| `data/frontend/details/*.json` | 导演、制片地区、原始语言、简介和来源链接 |
| `data/frontend/dialect_aggregates.json` | 方言叙事聚合载荷（分年代/逐年/类型控制/粤语/语言多样性/全球六层/双栖导演/类型均分/三波片单，口径固化自 sync_preview_dialect_v43_20260819.py） |
| `data/frontend/geo_enrichment.json` | 第一出品国视觉地理（lat/lng/geoRegion），按行号对齐 frontend_dataset |
| `data/frontend/visual_land_masks.json` | 7 组陆地 polygon，仅用于封面粒子落点 |
| `方言片详细报告.html` | `scripts/gen_dialect_report.py` 输出的逐部明细 HTML（仓库根目录） |

### 规范快照主要字段

| 字段 | 含义 |
| --- | --- |
| `movie_id` | 数据集中的电影标识，优先使用豆瓣条目 ID |
| `片名`、`年份` | 电影名称与上映年份 |
| `导演`、`类型`、`制片国家/地区`、`语言` | 原始电影元数据 |
| `豆瓣评分`、`评价人数` | 本报道使用的评分与评价规模 |
| `剧情简介`、`Gemini评价` | 详情弹窗可使用的文本字段 |
| `数据来源`、`来源URL` | 来源标记与可核对链接 |
| `Decade` | 页面使用的年代组 |
| `Region`、`Region_Code` | 第一制片国家／地区映射得到的分析地区 |
| `Genre_Code` | 类型列表第一项映射得到的主类型 |
| `Language_Code`、`Is_Dialect` | 六个分析语言组（英语、日语、韩语、普通话、方言、其他）及中国方言标记 |

## 数据口径

- 上游记录数：371,962 条（原 309,817 + 新增 62,145）。
- 发布记录数：63,025 部电影。
- 年份范围：1888–2026。
- 必需字段：片名、年份、评分和评价人数。
- 评分范围：大于 0 且不高于 10。
- 评价人数：至少 100 人。
- 身份去重：优先按豆瓣条目 URL，再按规范化片名＋年份。
- 条目范围：沿用豆瓣电影频道宽口径，包含长片、短片、纪录片、动画、演出影像及部分电视条目。
- 统计权重：每部电影等权计入；页面同时披露按评价人数加权的总体均分。
- 高分参考线：各幕数据卡用 8.5 分；正文方言／普通话高分率用 ≥8.0（9.5% vs 11.9%）。
- 时间覆盖：2026-08-18 合并 delivery_20260817 后覆盖至 2026 年；2022 年后共 7,190 部，以北美/欧洲/东亚为主，中国大陆占 15.4%；2020s 中国方言片仅 57 部，该年代结论谨慎引用。

当前发布指纹：

```text
ecd258a80e818d735b427ed457b816a677e9de36c0ed7379ae36ee156da35503
```

## 项目结构

```text
.
├── .github/workflows/validate.yml    自动重建与验证
├── data/                             规范快照与全部发布载荷（含 frontend/geo_enrichment.json、visual_land_masks.json）
├── docs/preview.webp                 README 页面预览图
├── frontend/
│   ├── index.html                    数据新闻首页
│   ├── vol1_time.html                年代分卷
│   ├── vol2_geo.html                 地区分卷
│   ├── vol3_lang.html                语言分卷
│   ├── vol4_memory.html              交叉筛选分卷
│   ├── build/                        esbuild 产物（内容 hash 文件名）
│   ├── fonts/                        自托管 Outfit（拉丁 + 数字）
│   ├── js/                           数据服务、叙事和图表源码
│   ├── src/                          ECharts 双包与页面入口
│   ├── style.css                     首页与分卷样式
│   └── vendor/echarts.min.js         全量 ECharts 备份，页面已改用 build/
├── scripts/                          清洗、聚合、事实提取和粒子生成
├── tests/test_pipeline.py            数据与叙事防回归测试
├── config.py                         仅基于仓库根目录的可移植路径
├── rebuild.py                        一键重建发布载荷
├── serve.py                          零依赖本地静态服务器
└── requirements.txt                  重建所需 Python 依赖
```

## 方言分析子系统

v4.5 发布快照（Region=China，第一制片国；方言判定与 v4.4 相同）：方言片 **3,045** 部 / 普通话·非方言 9,746 部。空语言 China 电影已清零（详见《方言电影定义_最终版_v4.1_Final.md》）。

| 脚本 | 用途 |
| --- | --- |
| `scripts/dialect_defs.py` | 方言定义 SSOT（224 标签、17 组），所有脚本的唯一白名单来源 |
| `scripts/gen_report_strict.py` | 方言片严格分析报告（支持 `--output` CLI 参数） |
| `scripts/gen_dialect_report.py` | 方言片逐部明细报告 + HTML 输出 |
| `scripts/analyze_v21_foreign_risk.py` | 外语标签风险分析 |
| `scripts/score_tier2b.py` | Tier 2b 证据漏斗打分（v4.1，产出 `data/tier2b_evidence.csv`） |
| `scripts/llm_judge_tier2b.py` | Tier 2b 灰区逐部补判（v4.1，`--apply` 生成白名单 `data/tier2b_recovered.csv`） |
| `scripts/apply_tier2b_reclassify_20260815.py` | Tier 2b 重分类一次性落地脚本（写回 `Dialect_Evidence` 列） |
| `scripts/apply_empty_lang_backfill_20260818.py` | 空语言 China 电影回填（replay 链；含 v4.1.1 的 8+1+4 修正） |
| `scripts/gen_opera_concert_candidates_20260818.py` | 戏曲/演唱会类误判候选清单生成（审计溯源） |
| `scripts/apply_opera_concert_exclude_20260818.py` | 49 部戏曲/演唱会类影片排除落地（定义 E4/E8） |
| `scripts/replay_v44_baseline.py` | 按序重放 v4.4 六步补丁 + v4.5 第一制片国补丁并断言终态；`--full-rebuild` 可从源一键回到基线（链末会自动跑 `rebuild.py`） |
| `scripts/apply_first_listed_region_20260824.py` | v4.5：空格分隔制片国取首位 + 西德/东德归入 Europe（不改 Is_Dialect；已纳入 replay 链） |

方言层级（v4.5 发布快照，与 v4.4 判定相同）：Tier 1 纯方言片（2,289 部）/ Tier 2a 混合方言片-方言排首位（410 部）/ Tier 2b 混合方言片-普通话排首位（346 部，默认排除后经证据漏斗+逐部补判白名单补回；详见《方言电影定义_最终版_v4.1_Final.md》§5.5）。

## 使用自备上游数据

如果取得了版本明确、字段兼容的 `movies_info.csv`，不要直接依赖 `rebuild.py --from-source` 一键出刊（它会停在 `data_processor`，以免用未打补丁的主表覆盖发布载荷）。正确顺序只需一条命令：补丁链已含 v4.5 Region 修正，且 `--full-rebuild` 会在断言终态后自动跑 `rebuild.py`。

```bash
python scripts/replay_v44_baseline.py --full-rebuild --source /path/to/movies_info.csv
```

新数据会产生新的记录数、统计结果和数据指纹。提交前应重新进行数据审计、编辑审校和浏览器检查。

## 已知边界

- 数据没有按全球电影总体进行概率抽样。
- 地区取第一制片国家／地区，合拍片会被归入单一分析地区。
- 主类型取类型列表第一项。
- 分析语言组为英语、日语、韩语、普通话、方言、其他六组；方言沿用中国方言清单，其余组按主要语言（片单首位）归组。
- 页面未进行显著性检验、因果识别或跨平台评分校准。
- 评分差异可能同时受到年代留存、跨地区传播、类型构成、平台用户与收录门槛影响。

## 私有仓库与 Fork

仓库当前为 Private。协作者需要先获得访问权限；是否显示 Fork 按钮取决于 GitHub 的私有仓库权限设置。拥有访问权限后，Clone、Fork 和从规范快照重建均不需要原工作目录。

## 数据使用提示

代码和页面可用于研究、教学与数据新闻实践。电影元数据、剧情简介、来源链接及 AI 生成文本的再分发，应继续遵守相应数据来源、平台和模型服务的使用条款。本仓库没有为第三方数据声明额外授权。
