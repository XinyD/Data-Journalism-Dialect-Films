import { runtime } from './runtime.js';
import { escapeHtml } from './lib/dom.js';
import { populateMovieDetail } from './lib/movie-detail.js';
import { prefersReducedMotion, rafThrottle, debounce } from './lib/schedule.js';
import { initGallery } from './gallery.js';
import { initChapterNav, initScrollytelling } from './scrolly.js';
import { initExplorerScene, exitExplorer, isExplorerOpen } from './scenes/explorer_scene.js';
import { createFlopLinkSync } from './scenes/flop-overlay.js';
import { createPrologueMotionLayer, syncCoverReveal } from './scenes/prologue.js';
import { dialectHandoffStyle, shouldPlayCoverToIntroHandoff } from './lib/cover-handoff.js';

let particleChart = null;
let particleData = [];
let plottedSeriesData = [];
let visualKeepIsMobile = false;
let prologueMotionLayer = null;
let universeMotionOverlay = false;
let universeHandoffToken = 0;
let universeHandoffTimer = 0;
let universeExitHandoff = false;
let universeHandoffT0 = 0;
const DIALECT_HANDOFF_MS = 1600;
let universeFinishedHandler = null;
let prologueLandRows = [];
let prologueDustRows = [];

// Dark-theme palette shared by the particle scenes and their guide lines.
const COLORS = {
    hollywood: '#5470C6',
    hollywoodDim: 'rgba(84, 112, 198, 0.1)',
    asian: '#E53935',
    otherDim: 'rgba(255, 255, 255, 0.05)',
    dialect: '#FFB300',
    particleBase: 'rgba(255, 255, 255, 0.3)',
    text: '#E2E2E2',
    grid: 'rgba(255, 255, 255, 0.05)',
    tooltipBg: 'rgba(10, 10, 12, 0.85)',
    selectedRegion: '#2ECC71',
    chinaBlue: '#2196F3',
    // v2: Design-spec region colors for the geographic universe scene
    chinaAmber: '#FFB300',
    eastAsiaTeal: '#26A69A',
    europeViolet: '#7E57C2',
    northAmericaPurple: '#AB47BC',
    southAmericaGreen: '#66BB6A',
    africaOrange: '#FF7043',
    oceaniaPink: '#EC407A',
    southAsiaLime: '#9CCC65',
    southeastAsiaCyan: '#00BCD4',
    westAsiaRose: '#F06292',
    centralAmber: '#FFA726'
};

const GUIDE_COLORS = {
    northAmerica: '#8FB2FF',
    comparison: '#FF7A73',
    overall: '#F4F4F5',
    standardized: '#5CC8A1',
    selected: '#FFD166',
    before: '#84B6F4',
    after: '#FF8A65',
    q1: '#5CC8A1',
    median: '#F4F4F5',
    threshold: '#FF7A73',
    mandarin: '#62B0FF',
    dialect: '#FFD166'
};

const REGION_LABELS = ['北美', '欧洲', '东亚', '中国', '其他'];
const REGIONS = REGION_LABELS;
const GENRES = ['剧情', '喜剧', '动作/冒险', '爱情', '悬疑/惊悚', '科幻/奇幻', '其他（纪录/动画等）'];
const GENRE_AXIS_LABELS = ['剧情', '喜剧', '动作', '爱情', '悬疑', '科幻', '其他'];
const LANGUAGE_LABELS = ['英语', '日语', '普通话', '方言', '韩语', '其他'];
const LANGUAGE_DISPLAY_ORDER = [0, 1, 4, 2, 3, 5];
const LANGUAGE_COLORS = {
    0: '#5470C6',
    1: '#E85D4C',
    2: '#62B0FF',
    3: '#FFD166',
    4: '#5CC8A1',
    5: 'rgba(255, 255, 255, 0.22)'
};

function languageOptionList(includeAll) {
    const options = LANGUAGE_DISPLAY_ORDER.map(code => ({
        value: String(code),
        label: LANGUAGE_LABELS[code]
    }));
    return includeAll ? [{ value: 'all', label: '全部' }, ...options] : options;
}

function languageDisplayIndex(code) {
    const index = LANGUAGE_DISPLAY_ORDER.indexOf(Number(code));
    return index < 0 ? LANGUAGE_DISPLAY_ORDER.length - 1 : index;
}

let activeSceneId = 'universe';
let activeSceneFilter = () => true;
const sceneState = {};
let sceneSelectionTimer = null;
let sampleYearExtent = [1888, 2026];
let sampleRatingExtent = [0, 10];
let dialectAgg = null;
let narrativeFacts = null;
let globalLayersPhase = 'mandarin-outlier';
let flopPhase = 'isolate';
let flopCasesBound = false;
let directorCasesBound = false;
let flopCaseLinkBound = false;
let flopStatsCache = null;
let flopGenreCache = null;
let flopCaseMovies = null;
let flopRevealToken = 0;
let flopOverlayTimer = 0;
let flopCardTimer = 0;
let flopLinksReady = false;

const FLOP_CASE_PATHS = [
    { movieId: '26796665', path: '动作片' },
    { movieId: '22557335', path: '特效片' },
    { movieId: '6068516', path: '喜剧翻拍' },
    { movieId: '3874981', path: '科幻片' }
];
const FLOP_CASE_IDS = new Set(FLOP_CASE_PATHS.map(item => item.movieId));
const FLOP_GENRE_PATHS = [
    { tag: '剧情', label: '剧情片' },
    { tag: '喜剧', label: '商业喜剧' },
    { tag: '动作', label: '动作类型' },
    { tag: '家庭', label: '家庭类型' },
    { tag: '纪录片', label: '纪录片' }
];
const FLOP_LAB_PHASES = new Set(['isolate', 'tail', 'cases', 'flopsOnly']);

const GLOBAL_LAYER_GROUPS = [
    { index: 0, jsonName: '欧洲 · 非主导语言', label: '欧洲非主导语言', short: '欧非主导', fallback: '1.5%' },
    { index: 1, jsonName: '欧洲 · 英语', label: '英语', short: '英语', fallback: '3.6%' },
    { index: 2, jsonName: '日韩', label: '日韩', short: '日韩', fallback: '5.8%' },
    { index: 3, jsonName: '华语 · 方言', label: '华语方言', short: '方言', fallback: '6.4%' },
    { index: 4, jsonName: '华语 · 普通话', label: '华语普通话', short: '普通话', fallback: '24.4%' }
];
const BOUNDARY_LAYER_GROUPS = [
    ...GLOBAL_LAYER_GROUPS.slice(0, 4),
    { index: 4, jsonName: '北美 · 英语', label: '北美英语', short: '北美英', fallback: '8.8%' },
    { ...GLOBAL_LAYER_GROUPS[4], index: 5 }
];
const OUTLIER_COLUMN_X = [0, 0.72, 1.44, 2.16, 3.55];

function globalLayerRowRegion(row) {
    return row.region || (row.detail && row.detail.region);
}

function globalLayerRowLanguage(row) {
    return row.language || (row.detail && row.detail.language);
}

function isNorthAmericaEnglish(row) {
    return globalLayerRowRegion(row) === 'North_America' && globalLayerRowLanguage(row) === 'English';
}

function globalLayerOf(row) {
    const region = globalLayerRowRegion(row);
    const language = globalLayerRowLanguage(row);
    if (region === 'Europe' && language === 'European_Languages') return 0;
    if (region === 'Europe' && language === 'English') return 1;
    if (region === 'East_Asia') return 2;
    if (region === 'China' && row.isDialect) return 3;
    if (region === 'China' && !row.isDialect) return 4;
    return -1;
}

function globalLayerRate(jsonName, fallback) {
    const layer = dialectAgg && Array.isArray(dialectAgg.global_layers)
        ? dialectAgg.global_layers.find(item => item.name === jsonName)
        : null;
    return layer ? `${layer.below5}%` : fallback;
}

function globalLayerXMax(phase) {
    if (phase === 'pull-back') return 5.8;
    if (phase === 'four-groups') return 3.5;
    if (phase === 'boundary') return 5.6;
    return 4.7;
}

function globalLayerX(row, group, phase) {
    if (phase === 'pull-back') {
        return languageDisplayIndex(row.langCode) + row.jitterGenreX * 2.2 + row.jitterX * 1.6;
    }
    if (phase === 'boundary') {
        if (isNorthAmericaEnglish(row)) return 4 + row.jitterGenreX;
        if (group === 4) return 5 + row.jitterGenreX;
        if (group < 0) return -0.55 + row.jitterGenreX * 0.2;
        return group + row.jitterGenreX;
    }
    if (group < 0) {
        return -0.55 + row.jitterGenreX * 0.2;
    }
    if (phase === 'four-groups') {
        if (group === 4) return 4.2 + row.jitterGenreX * 0.15;
        return group + row.jitterGenreX;
    }
    if (phase === 'mandarin-outlier') {
        if (group === 4) return OUTLIER_COLUMN_X[4] + row.jitterGenreX * 1.35;
        return group * OUTLIER_COLUMN_X[1] + row.jitterGenreX * 0.85;
    }
    return group + row.jitterGenreX;
}

function isChinaDialect(row) {
    return row.region === 'China' && row.isDialect;
}

function isChinaMandarin(row) {
    return row.region === 'China' && !row.isDialect;
}

function isChinaLanguagePair(row) {
    return isChinaMandarin(row) || isChinaDialect(row);
}

function filmCountry(row) {
    return row.country || '';
}

function isHkDialect(row) {
    return isChinaDialect(row) && filmCountry(row) === '中国香港';
}

function isMainlandMandarin(row) {
    return isChinaMandarin(row) && filmCountry(row) === '中国';
}

function isMainlandDialect(row) {
    return isChinaDialect(row) && filmCountry(row) === '中国';
}

function isLaterWaveDialect(row) {
    return isChinaDialect(row) && filmCountry(row) !== '中国香港' && Number(row.year) >= 2008;
}

function isStorySpanDialect(row) {
    return isChinaDialect(row) && Number(row.year) >= 1985;
}

function inYearRange(row, start, end) {
    const year = Number(row.year);
    return Number.isFinite(year) && year >= start && year <= end;
}

function isDialectFlop(row) {
    return isChinaDialect(row) && Number(row.rating) < 5;
}

function dialectFlopStats() {
    if (flopStatsCache) return flopStatsCache;
    const dialect = particleData.filter(isChinaDialect);
    const flops = dialect.filter(row => Number(row.rating) < 5);
    flopStatsCache = {
        n: dialect.length,
        flopN: flops.length,
        rate: dialect.length ? (flops.length / dialect.length) * 100 : 0
    };
    return flopStatsCache;
}

function movieGenres(row) {
    return String((row && (row.genres || (row.detail && row.detail.genres))) || '');
}

function computeGenreFlopRates() {
    if (flopGenreCache) return flopGenreCache;
    const rows = particleData.filter(isChinaDialect);
    flopGenreCache = FLOP_GENRE_PATHS.map(({ tag, label }) => {
        const subset = rows.filter(row => movieGenres(row).includes(tag));
        const n = subset.length;
        const flopN = subset.filter(row => Number(row.rating) < 5).length;
        return { tag, label, n, flopN, rate: n ? (flopN / n) * 100 : 0 };
    });
    return flopGenreCache;
}

function caseMovieById(movieId) {
    if (!flopCaseMovies) {
        flopCaseMovies = new Map();
        FLOP_CASE_PATHS.forEach(item => {
            const movie = particleData.find(row => String(row.movieId) === item.movieId);
            if (movie) flopCaseMovies.set(item.movieId, movie);
        });
    }
    return flopCaseMovies.get(movieId);
}

function resolveFlopPhase(phase) {
    return FLOP_LAB_PHASES.has(phase) ? phase : 'isolate';
}

function dialectFlopRole(row) {
    if (FLOP_CASE_IDS.has(String(row.movieId))) return 3;
    if (isDialectFlop(row)) return 2;
    if (isChinaDialect(row)) return 1;
    return 0;
}

function dialectFlopX(row, phase) {
    if (isDialectFlop(row) && (phase === 'tail' || phase === 'cases' || phase === 'flopsOnly')) {
        return 2.46 + row.jitterGenreX * 0.48;
    }
    return 1.90 + row.jitterGenreX * 1.12;
}

function isFlopLit(row, phase) {
    return phase === 'flopsOnly' ? isDialectFlop(row) : isChinaDialect(row);
}

function cancelFlopOverlay() {
    flopRevealToken += 1;
    flopLinksReady = false;
    runtime.flopLinksReady = false;
    if (flopOverlayTimer) {
        clearTimeout(flopOverlayTimer);
        flopOverlayTimer = 0;
    }
    if (flopCardTimer) {
        clearTimeout(flopCardTimer);
        flopCardTimer = 0;
    }
}

function scheduleFlopOverlay(delayMs) {
    const token = ++flopRevealToken;
    flopLinksReady = false;
    runtime.flopLinksReady = false;
    if (flopOverlayTimer) {
        clearTimeout(flopOverlayTimer);
        flopOverlayTimer = 0;
    }
    if (flopCardTimer) {
        clearTimeout(flopCardTimer);
        flopCardTimer = 0;
    }
    const revealCards = flopPhase === 'cases';
    const paint = () => {
        flopOverlayTimer = 0;
        if (token !== flopRevealToken || activeSceneId !== 'dialect-flops' || !particleChart) return;
        flopLinksReady = true;
        runtime.flopLinksReady = true;
        paintDialectFlopOverlay();
        if (!revealCards) return;
        if (delayMs <= 0) {
            syncFlopCaseCards(true);
            return;
        }
        flopCardTimer = setTimeout(() => {
            flopCardTimer = 0;
            if (token !== flopRevealToken || activeSceneId !== 'dialect-flops' || flopPhase !== 'cases') return;
            syncFlopCaseCards(true);
        }, 350);
    };
    if (delayMs <= 0) {
        paint();
        return;
    }
    flopOverlayTimer = setTimeout(paint, delayMs);
}

function syncFlopCaseCards(lit) {
    document.querySelectorAll('#step-8c .flop-case-card').forEach(card => {
        card.classList.toggle('is-lit', Boolean(lit));
    });
}

function paintDialectFlopOverlay() {
    if (activeSceneId !== 'dialect-flops' || !particleChart) return;
    particleChart.setOption({
        animation: false,
        graphic: dialectFlopGraphics(flopPhase)
    }, { notMerge: false, lazyUpdate: true, silent: true });
}

const onFlopCaseLinkSync = createFlopLinkSync(paintDialectFlopOverlay);

function bindFlopCaseLinkSync() {
    if (flopCaseLinkBound) return;
    window.addEventListener('scroll', onFlopCaseLinkSync, { passive: true, capture: true });
    window.addEventListener('resize', onFlopCaseLinkSync);
    flopCaseLinkBound = true;
}

function unbindFlopCaseLinkSync() {
    if (!flopCaseLinkBound) return;
    window.removeEventListener('scroll', onFlopCaseLinkSync, { capture: true });
    window.removeEventListener('resize', onFlopCaseLinkSync);
    flopCaseLinkBound = false;
}

function setFlopPhase(phase, { render = true, refreshLab = false } = {}) {
    const nextPhase = resolveFlopPhase(phase);
    const samePhase = nextPhase === flopPhase
        && activeSceneId === 'dialect-flops'
        && document.documentElement.dataset.flopPhase === nextPhase;
    flopPhase = nextPhase;
    runtime.flopPhase = flopPhase;
    runtime.activeSceneId = activeSceneId;
    document.documentElement.dataset.flopPhase = flopPhase;
    sceneState['dialect-flops'] = flopPhase;
    if (!samePhase) syncFlopCaseCards(false);
    if (flopPhase === 'cases') bindFlopCaseLinkSync();
    else unbindFlopCaseLinkSync();
    runtime.flopLinksReady = flopLinksReady;
    if (refreshLab) updateSceneLab('dialect-flops');
    if (render && activeSceneId === 'dialect-flops') {
        renderParticleScene('dialect-flops');
    }
}

function dialectFlopGraphics(phase) {
    const elements = [];
    if (phase === 'tail' || phase === 'cases' || phase === 'flopsOnly') {
        const stats = dialectFlopStats();
        elements.push({
            type: 'group',
            id: 'flop-count',
            right: 36,
            bottom: 92,
            silent: true,
            animation: false,
            children: [
                {
                    type: 'text',
                    animation: false,
                    style: {
                        text: `${stats.flopN.toLocaleString('zh-CN')} 部`,
                        fill: '#FF7A73',
                        font: '800 22px Noto Sans SC, PingFang SC, sans-serif'
                    }
                },
                {
                    type: 'text',
                    y: 26,
                    animation: false,
                    style: {
                        text: '<5分',
                        fill: '#C8C8CC',
                        font: '700 13px Noto Sans SC, PingFang SC, sans-serif'
                    }
                }
            ]
        });
    }
    if (phase === 'cases' && particleChart) {
        const chartDom = particleChart.getDom();
        const chartRect = chartDom ? chartDom.getBoundingClientRect() : null;
        const measured = FLOP_CASE_PATHS.map(item => {
            const movie = caseMovieById(item.movieId);
            const card = document.querySelector(`#step-8c .flop-case-card[data-movie-id="${item.movieId}"]`);
            const rect = card ? card.getBoundingClientRect() : null;
            return { item, movie, rect };
        });
        measured.forEach(({ item, movie, rect }) => {
            if (!movie || !chartRect || !rect || rect.width < 2 || rect.height < 2) return;
            const pixel = particleChart.convertToPixel({ seriesIndex: 0 }, [
                dialectFlopX(movie, phase),
                movie.rating
            ]);
            if (!pixel || !Number.isFinite(pixel[0])) return;
            const cardLeft = rect.left - chartRect.left;
            const cardRight = rect.right - chartRect.left;
            const cardMid = (cardLeft + cardRight) / 2;
            elements.push({
                type: 'line',
                id: `flop-link-${item.movieId}`,
                silent: true,
                animation: false,
                shape: {
                    x1: pixel[0],
                    y1: pixel[1],
                    x2: pixel[0] >= cardMid ? cardRight : cardLeft,
                    y2: rect.top + rect.height / 2 - chartRect.top
                },
                style: {
                    stroke: 'rgba(255, 179, 0, 0.5)',
                    lineWidth: 1.15
                }
            });
        });
    }
    return elements;
}

// Prologue particle narrative (cover + intro only).
// data geography = first production country / geoRegion (read-only)
// visual particle placement = region-correct land sampling (not filming GPS)
const VISUAL_GROUP_ORDER = ['north_america', 'europe', 'asia', 'china', 'south_america', 'africa', 'oceania'];
const VISUAL_GROUP_LABELS = {
    north_america: '北美洲',
    europe: '欧洲',
    asia: '亚洲',
    china: '中国',
    south_america: '南美洲',
    africa: '非洲',
    oceania: '大洋洲'
};
const VISUAL_GROUP_COLORS = {
    china: '#d4a574',
    asia: '#4f8f86',
    europe: '#6b5f8a',
    north_america: '#7a5d82',
    south_america: '#5d7a5f',
    africa: '#b56a4a',
    oceania: '#a36b7a',
    unknown: '#9a9aa2'
};
const COVER_CHINA_HEX = '#e6bc86';
const PROLOGUE_STATES = {
    WORLD_MAP: 'WORLD_MAP',
    STAR_FIELD: 'STAR_FIELD',
    REGION_FOCUS: 'REGION_FOCUS'
};
let prologueState = PROLOGUE_STATES.WORLD_MAP;
let prologueFocusGroup = null;
let prologuePrevGroup = null;
let prologueFlyToMap = false;
let visualMaskGrids = null;
let coverLayout = { centroids: {}, packed: {}, rings: {}, scales: {} };
let universeRaf = 0;
let lastUniverseMotionKey = '';
let universePlotCache = [];
let universePaintNow = 0;
let universeBreathMix = 0;
let universeIdleSince = 0;
let universeIdleEchartsPainted = false;
let lastUniverseIdlePaint = 0;
let universeIdlePoseValid = false;
let universeIdlePoseCount = 0;
let universeIdlePoseX = new Float32Array(0);
let universeIdlePoseY = new Float32Array(0);
let universeIdlePoseOnMap = new Float32Array(0);
let universeIdlePoseAppear = new Float32Array(0);
const VISUAL_BUDGET_DESKTOP = 10800;
const VISUAL_BUDGET_MOBILE = 7200;
const DUST_BUDGET_DESKTOP = 7500;
const DUST_BUDGET_MOBILE = 4800;
const COVER_PACK = 0.42;
const COVER_PACK_TARGET = { x: 46, y: 52 };
const COVER_SCALES = {
    china: 2.25,
    oceania: 2.2,
    africa: 2.05,
    south_america: 2.05,
    north_america: 1.87,
    asia: 1.76,
    europe: 1.7
};
const prologueMotion = {
    reveal: 0,
    fly: 0,
    release: 0,
    gather: 0,
    t0: 0
};
runtime.prologueMotion = prologueMotion;

document.addEventListener('DOMContentLoaded', async () => {
    // 首屏骨架屏：数据到达前，把所有承载动态数字的占位 span（初始文本为
    // “加载中”或“--”）标为 pending，渲染为灰色扫光条；数字填入时由
    // setTextById / values 填充逻辑逐个撤除。hero-sample-count 走数字滚动
    // 动画，跳过。
    document.querySelectorAll('[id]').forEach(node => {
        if (node.id === 'hero-sample-count') return;
        const text = (node.textContent || '').trim();
        if (text === '加载中' || text === '--') node.classList.add('is-pending');
    });

    // 1. 初始化数据服务
    await window.DataService.init();
    const publicationData = window.DataService.dataset || [];
    if (!publicationData.length) return;

    const years = publicationData.map(movie => movie.year).filter(Number.isFinite);
    const ratings = publicationData.map(movie => movie.rating).filter(Number.isFinite);
    const payloadYears = window.DataService.meta.yearRange;
    sampleYearExtent = Array.isArray(payloadYears) && payloadYears.length === 2
        ? payloadYears.map(Number)
        : [Math.min(...years), Math.max(...years)];
    sampleRatingExtent = [
        Math.max(0, Math.floor(Math.min(...ratings))),
        Math.min(10, Math.ceil(Math.max(...ratings)))
    ];
    updateDatasetKpis(publicationData);

    // 2. Reuse the compact publication payload for the particle engine. This
    // avoids downloading a second copy of 53k titles and keeps record indexes
    // aligned across charts, filters, tooltips, and the gallery.
    particleData = window.DataService.dataset.map((movie, index) => {
        const key = `${movie.movieId}|${movie.title}|${movie.year}`;
        const geoRegion = movie.geoRegion !== undefined ? movie.geoRegion : movie.regionCode;
        return {
            id: index,
            movieId: movie.movieId,
            title: movie.title,
            year: movie.year,
            decade: movie.decade,
            rating: movie.rating,
            votes: movie.votes,
            regionCode: movie.regionCode,
            region: movie.region,
            country: movie.country || '',
            language: movie.language,
            geoRegion,
            visualGroup: visualGroupFromGeo(geoRegion),
            isHollywood: movie.regionCode === 0,
            isDialect: movie.isDialect,
            genres: movie.genres,
            genreCode: movie.genreCode,
            langCode: movie.langCode,
            detail: movie,
            randX: stableUnit(key, 11) * 100,
            randY: stableUnit(key, 29) * 100,
            starX: 50,
            starY: 50,
            visualX: 50,
            visualY: 50,
            cloudX: 50,
            cloudY: 50,
            visualEdge: 0.5,
            visualVoid: 0,
            visualPhase: stableUnit(key, 13) * Math.PI * 2,
            visualFreq: 0.14 + stableUnit(key, 19) * 0.09,
            visualSize: stableUnit(key, 23),
            brightness: Math.max(0.3, Math.min(1, Number(movie.rating) / 10)),
            jitterX: (stableUnit(key, 47) - 0.5) * 0.6,
            jitterGenreX: (stableUnit(key, 71) - 0.5) * 0.5,
            mobileKeep: true,
            dustKeep: false,
            dustOk: false,
            dustX: 50,
            dustY: 50,
            dustDepth: 0.45,
            dustSpeck: 0.3,
            dustStray: false
        };
    });
    assignVisualPlacement(window.DataService.visualMasks);
    assignVisualKeep();

    // 3. 初始化粒子引擎、逐幕互动和探索舱
    initParticleEngine();
    initVisualRegionDock();
    initSceneInteractions();
    fillFlopNarrative();
    fillDialectFlopsCards();
    runtime.openMovieDetail = openMovieDetail;
    runtime.bindMovieDetailDialog = bindMovieDetailDialog;
    runtime.activeSceneId = activeSceneId;
    initGallery();
    initExplorerScene();
    bindWaveScene();

    // 3b. 并行加载方言聚合数据（用于 Part 3e/3f/3g/3h/4 内嵌卡片）
    window.DataService.fetchJson('../data/frontend/dialect_aggregates.json')
        .then(agg => {
            dialectAgg = agg;
            fillFlopNarrative();
            fillDialectFlopsCards();
            fillFinaleData();
            fillChinaNarrativeKpis();
            fillWaveCases();
            bindWaveScene();
            updateSceneLab('global-layers');
            updateSceneLab('dialect-flops');
            updateSceneLab('dual-director');
            updateSceneLab('three-waves');
            updateSceneLab('scale');
        })
        .catch(() => console.warn('dialect_aggregates 加载失败，内嵌卡片显示占位值'));

    window.DataService.fetchJson('../data/narrative_facts.json')
        .then(facts => {
            narrativeFacts = facts;
            fillChinaNarrativeKpis();
            updateSceneLab('scale');
        })
        .catch(() => console.warn('narrative_facts 加载失败，部分正文数字使用聚合载荷'));

    bindMovieDetailDialog();
    initChapterNav();
    document.getElementById('back-to-cover')?.addEventListener('click', event => {
        event.preventDefault();
        event.stopPropagation();
        if (isExplorerOpen()) exitExplorer();
        document.getElementById('step-0')?.scrollIntoView({ behavior: StoryUI.prefersReducedMotion() ? 'auto' : 'smooth', block: 'center' });
    });

    // 4. 绑定滚动控制
    initScrollytelling({
        setPrologueState,
        PROLOGUE_STATES,
        activateSceneInteraction,
        renderParticleScene,
        syncCoverReveal,
        maybeCountSceneStats
    });
    if (window.ScaleScene) window.ScaleScene.init();
    if (StoryUI.prefersReducedMotion()) syncCoverReveal(true);

    const onParticleResizeFrame = rafThrottle(() => {
        if (particleChart) particleChart.resize();
        if (prologueMotionLayer) prologueMotionLayer.resize();
        if (window.WaveScene) window.WaveScene.onResize();
        if (activeSceneId === 'universe') {
            lastUniverseMotionKey = '';
            resetUniverseIdlePaint();
            paintUniverseLive();
            startUniverseLoop();
        }
    });
    const onParticleResizeDebounced = debounce(() => {
        if (isMobileViewport() !== visualKeepIsMobile) assignVisualKeep();
        if (particleChart) renderParticleScene(activeSceneId, { animate: false });
    }, 200);
    window.addEventListener('resize', () => {
        onParticleResizeFrame();
        onParticleResizeDebounced();
    });
});

function hexToRgb(hex) {
    return [
        parseInt(hex.slice(1, 3), 16),
        parseInt(hex.slice(3, 5), 16),
        parseInt(hex.slice(5, 7), 16)
    ];
}

function hexToRgba(hex, alpha) {
    const rgb = hexToRgb(hex);
    return `rgba(${rgb[0]}, ${rgb[1]}, ${rgb[2]}, ${alpha})`;
}

function clamp01(value) {
    return Math.max(0, Math.min(1, value));
}

function lerp(a, b, t) {
    return a + (b - a) * t;
}

function smooth01(value) {
    const t = clamp01(value);
    return t * t * (3 - 2 * t);
}

const MOVIE_DETAIL_FIELD_IDS = {
    year: 'movie-detail-year',
    title: 'movie-detail-title',
    rating: 'movie-detail-rating',
    genres: 'movie-detail-genres',
    votes: 'movie-detail-votes',
    groups: 'movie-detail-groups',
    id: 'movie-detail-id',
    director: 'movie-detail-director',
    countries: 'movie-detail-countries',
    languages: 'movie-detail-languages',
    source: 'movie-detail-data-source',
    synopsis: 'movie-detail-synopsis',
    gemini: 'movie-detail-gemini'
};

function createIndexDetailView(dialog) {
    return {
        setField(name, value) {
            const id = MOVIE_DETAIL_FIELD_IDS[name];
            const el = id && document.getElementById(id);
            if (el) el.textContent = value || '未知';
        },
        formatGroups(movie) {
            return `${REGION_LABELS[movie.regionCode] || movie.region || '未知地区'} · ${LANGUAGE_LABELS[movie.langCode] || movie.languageGroup || '其他'}`;
        },
        setSynopsisVisible(visible) {
            document.getElementById('movie-detail-synopsis-section').hidden = !visible;
        },
        setGeminiVisible(visible) {
            document.getElementById('movie-detail-gemini-section').hidden = !visible;
        },
        getSourceLink() {
            return document.getElementById('movie-detail-source');
        },
        resolveSourceUrl(movie, details) {
            return window.DataService.resolveSourceUrl(movie, details);
        },
        applySourceLink(linkEl, url) {
            window.DataService.applySourceLink(linkEl, url);
        },
        getMovieDetails(movieId) {
            return window.DataService.getMovieDetails(movieId);
        },
        setBusy(busy) {
            if (busy) dialog.setAttribute('aria-busy', 'true');
            else dialog.removeAttribute('aria-busy');
        },
        open() {
            if (!dialog.open) dialog.showModal();
        },
        isCurrent(movieId) {
            return dialog.dataset.movieId === String(movieId);
        }
    };
}

async function openMovieDetail(movie) {
    const dialog = document.getElementById('movie-detail-dialog');
    if (!dialog || !movie) return;
    dialog.dataset.movieId = String(movie.movieId);
    await populateMovieDetail(movie, createIndexDetailView(dialog));
}

function stableUnit(value, salt = 0) {
    let hash = (2166136261 ^ salt) >>> 0;
    const text = String(value);
    for (let index = 0; index < text.length; index += 1) {
        hash ^= text.charCodeAt(index);
        hash = Math.imul(hash, 16777619);
    }
    return (hash >>> 0) / 4294967295;
}

function hash2(ix, iy, salt) {
    return stableUnit(`${ix}|${iy}`, salt);
}

function fadeUnit(t) {
    return t * t * (3 - 2 * t);
}

function valueNoise(x, y, salt) {
    const x0 = Math.floor(x);
    const y0 = Math.floor(y);
    const fx = fadeUnit(x - x0);
    const fy = fadeUnit(y - y0);
    const v00 = hash2(x0, y0, salt);
    const v10 = hash2(x0 + 1, y0, salt);
    const v01 = hash2(x0, y0 + 1, salt);
    const v11 = hash2(x0 + 1, y0 + 1, salt);
    return v00 * (1 - fx) * (1 - fy) + v10 * fx * (1 - fy) + v01 * (1 - fx) * fy + v11 * fx * fy;
}

function fbm2(x, y, salt) {
    return valueNoise(x, y, salt) * 0.55
        + valueNoise(x * 2.15 + 8, y * 2.15, salt + 3) * 0.3
        + valueNoise(x * 4.3, y * 4.3 + 3, salt + 7) * 0.15;
}

function distPointSeg(px, py, ax, ay, bx, by) {
    const dx = bx - ax;
    const dy = by - ay;
    const len2 = dx * dx + dy * dy || 1e-12;
    const t = Math.max(0, Math.min(1, ((px - ax) * dx + (py - ay) * dy) / len2));
    return Math.hypot(px - (ax + t * dx), py - (ay + t * dy));
}

function distToRings(lng, lat, rings) {
    let min = Infinity;
    rings.forEach(ring => {
        for (let i = 0; i < ring.length; i += 1) {
            const a = ring[i];
            const b = ring[(i + 1) % ring.length];
            min = Math.min(min, distPointSeg(lng, lat, a[0], a[1], b[0], b[1]));
        }
    });
    return min;
}

function gaussianPair(u, v) {
    const r = Math.sqrt(-2 * Math.log(Math.max(1e-6, u)));
    const ang = v * Math.PI * 2;
    return [r * Math.cos(ang), r * Math.sin(ang)];
}

function visualGroupFromGeo(geoRegion) {
    const code = Number(geoRegion);
    if (code === 3) return 'china';
    if (code === 0) return 'north_america';
    if (code === 1) return 'europe';
    if (code === 5) return 'south_america';
    if (code === 6) return 'africa';
    if (code === 7) return 'oceania';
    if (code === 2 || code === 8 || code === 9 || code === 10 || code === 11) return 'asia';
    return 'unknown';
}

function pointInRing(lng, lat, ring) {
    let inside = false;
    for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
        const xi = ring[i][0];
        const yi = ring[i][1];
        const xj = ring[j][0];
        const yj = ring[j][1];
        const intersect = ((yi > lat) !== (yj > lat))
            && (lng < (xj - xi) * (lat - yi) / ((yj - yi) || 1e-12) + xi);
        if (intersect) inside = !inside;
    }
    return inside;
}

function pointInRings(lng, lat, rings) {
    return rings.some(ring => pointInRing(lng, lat, ring));
}

function cross2(o, a, b) {
    return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0]);
}

function convexHull(points) {
    const pts = points
        .map(point => [point[0], point[1]])
        .sort((a, b) => a[0] - b[0] || a[1] - b[1]);
    if (pts.length <= 2) return pts;
    const lower = [];
    pts.forEach(point => {
        while (lower.length >= 2 && cross2(lower[lower.length - 2], lower[lower.length - 1], point) <= 0) {
            lower.pop();
        }
        lower.push(point);
    });
    const upper = [];
    for (let i = pts.length - 1; i >= 0; i -= 1) {
        const point = pts[i];
        while (upper.length >= 2 && cross2(upper[upper.length - 2], upper[upper.length - 1], point) <= 0) {
            upper.pop();
        }
        upper.push(point);
    }
    lower.pop();
    upper.pop();
    const hull = lower.concat(upper);
    if (hull.length && (hull[0][0] !== hull[hull.length - 1][0] || hull[0][1] !== hull[hull.length - 1][1])) {
        hull.push([hull[0][0], hull[0][1]]);
    }
    return hull;
}

function samplingRings(group, rings) {
    if (group !== 'asia' || !rings.length) return rings;
    const points = [];
    rings.forEach(ring => ring.forEach(point => points.push(point)));
    const hull = convexHull(points);
    return hull.length >= 3 ? [hull] : rings;
}

function projectLngLat(lng, lat) {
    const clampedLat = Math.max(-55, Math.min(75, lat));
    const x = (lng + 180) / 360 * 100;
    const toMerc = value => Math.log(Math.tan(Math.PI / 4 + value * Math.PI / 360));
    const merc = toMerc(clampedLat);
    const mercMin = toMerc(-55);
    const mercMax = toMerc(75);
    const y = (merc - mercMin) / (mercMax - mercMin) * 100;
    return [x, y];
}

const COVER_MARGIN = 2;
const COVER_LIMIT = 98;

function clampCover(value) {
    return Math.max(COVER_MARGIN, Math.min(COVER_LIMIT, value));
}

function coverRingBBox(rawRings, cx, cy, packed, scale) {
    let minX = Infinity;
    let maxX = -Infinity;
    let minY = Infinity;
    let maxY = -Infinity;
    rawRings.forEach(ring => ring.forEach(([x, y]) => {
        const px = packed.x + (x - cx) * scale;
        const py = packed.y + (y - cy) * scale;
        minX = Math.min(minX, px);
        maxX = Math.max(maxX, px);
        minY = Math.min(minY, py);
        maxY = Math.max(maxY, py);
    }));
    if (!Number.isFinite(minX)) {
        return { minX: packed.x, maxX: packed.x, minY: packed.y, maxY: packed.y };
    }
    return { minX, maxX, minY, maxY };
}

function shiftIntoCover(min, max) {
    const lo = COVER_MARGIN - min;
    const hi = COVER_LIMIT - max;
    if (lo > hi) return (lo + hi) / 2;
    return Math.max(lo, Math.min(hi, 0));
}

function fitCoverGroup(rawRings, cx, cy, packed, desiredScale) {
    let scale = desiredScale;
    let origin = { x: packed.x, y: packed.y };
    let box = coverRingBBox(rawRings, cx, cy, origin, scale);
    const maxSpan = COVER_LIMIT - COVER_MARGIN;
    const fit = Math.min(
        1,
        maxSpan / Math.max(box.maxX - box.minX, 1e-6),
        maxSpan / Math.max(box.maxY - box.minY, 1e-6)
    );
    if (fit < 1) {
        scale *= fit;
        box = coverRingBBox(rawRings, cx, cy, origin, scale);
    }
    origin.x += shiftIntoCover(box.minX, box.maxX);
    origin.y += shiftIntoCover(box.minY, box.maxY);
    return { scale, packed: origin };
}

function applyCoverTransform(x, y, centroid, packed, scale) {
    return [
        packed.x + (x - centroid.x) * scale,
        packed.y + (y - centroid.y) * scale
    ];
}

function buildCoverLayout(masks) {
    const centroids = {};
    const packed = {};
    const rings = {};
    const scales = {};
    if (!masks || !masks.groups) return { centroids, packed, rings, scales };
    Object.entries(masks.groups).forEach(([group, spec]) => {
        const rawRings = samplingRings(group, spec.rings || [])
            .map(ring => ring.map(([lng, lat]) => projectLngLat(lng, lat)));
        let sx = 0;
        let sy = 0;
        let n = 0;
        rawRings.forEach(ring => ring.forEach(([x, y]) => {
            sx += x;
            sy += y;
            n += 1;
        }));
        const cx = n ? sx / n : 50;
        const cy = n ? sy / n : 52;
        centroids[group] = { x: cx, y: cy };
        const fitted = fitCoverGroup(
            rawRings,
            cx,
            cy,
            {
                x: lerp(cx, COVER_PACK_TARGET.x, COVER_PACK),
                y: lerp(cy, COVER_PACK_TARGET.y, COVER_PACK)
            },
            COVER_SCALES[group] || 1
        );
        packed[group] = fitted.packed;
        scales[group] = fitted.scale;
        rings[group] = rawRings.map(ring => ring.map(([x, y]) => (
            applyCoverTransform(x, y, centroids[group], packed[group], fitted.scale)
        )));
    });
    return { centroids, packed, rings, scales };
}

function layoutCoverPoint(x, y, group) {
    const centroid = coverLayout.centroids[group];
    const packed = coverLayout.packed[group];
    if (!centroid || !packed) return [x, y];
    const scale = coverLayout.scales[group] || COVER_SCALES[group] || 1;
    return applyCoverTransform(x, y, centroid, packed, scale);
}

function sampleOceanDust(movieId) {
    return [
        0.8 + stableUnit(movieId, 201) * 98.4,
        0.8 + stableUnit(movieId, 223) * 98.4
    ];
}

function placeCoverDust() {
    particleData.forEach(movie => {
        if (!movie.dustKeep) return;
        const dust = sampleOceanDust(movie.movieId);
        movie.dustX = dust[0];
        movie.dustY = dust[1];
        movie.dustDepth = movie.visualSize;
        movie.dustSpeck = movie.visualSize;
        movie.dustStray = false;
    });
}

function groupCorePower(group) {
    if (group === 'asia') return 1.05;
    if (group === 'north_america') return 1.45;
    if (group === 'europe') return 1.35;
    if (group === 'china') return 1.3;
    return 1.15;
}

function buildMaskGrids(masks) {
    const grids = {};
    if (!masks || !masks.groups) return grids;
    Object.entries(masks.groups).forEach(([group, spec]) => {
        const rings = samplingRings(group, spec.rings || []);
        let minLng = 180;
        let maxLng = -180;
        let minLat = 90;
        let maxLat = -90;
        rings.forEach(ring => {
            ring.forEach(([lng, lat]) => {
                minLng = Math.min(minLng, lng);
                maxLng = Math.max(maxLng, lng);
                minLat = Math.min(minLat, lat);
                maxLat = Math.max(maxLat, lat);
            });
        });
        const cols = 48;
        const rows = 32;
        const raw = [];
        let maxEdge = 0;
        const salt = Math.floor(stableUnit(group, 5) * 90);
        for (let i = 0; i < cols; i += 1) {
            for (let j = 0; j < rows; j += 1) {
                const lng = minLng + (i + 0.5) / cols * (maxLng - minLng);
                const lat = minLat + (j + 0.5) / rows * (maxLat - minLat);
                if (!pointInRings(lng, lat, rings)) continue;
                const edgeDist = distToRings(lng, lat, rings);
                maxEdge = Math.max(maxEdge, edgeDist);
                raw.push({ lng, lat, edgeDist });
            }
        }
        const corePower = groupCorePower(group);
        const even = group === 'asia';
        const cells = raw.map(cell => {
            const edgeT = maxEdge > 0 ? cell.edgeDist / maxEdge : 0;
            const nx = (cell.lng - minLng) / Math.max(1e-6, maxLng - minLng);
            const ny = (cell.lat - minLat) / Math.max(1e-6, maxLat - minLat);
            const voidness = clamp01((fbm2(nx * 4.6, ny * 4.6, salt) - 0.4) / 0.42);
            const centerBias = even
                ? 1
                : 1 - Math.min(1, Math.hypot(nx - 0.48, ny - 0.52) * 0.85);
            const core = Math.pow(Math.max(0, (edgeT - 0.06) / 0.94), corePower);
            const weight = even
                ? (0.72 + 0.28 * core) * (0.75 + 0.25 * (1 - voidness * 0.35))
                : (0.18 + 0.82 * core)
                    * (0.28 + 0.72 * (1 - voidness * 0.55))
                    * (0.72 + 0.28 * centerBias);
            return {
                lng: cell.lng,
                lat: cell.lat,
                edgeT,
                voidness,
                weight: Math.max(0.05, weight)
            };
        });
        const totals = cells.reduce((sum, cell) => sum + cell.weight, 0);
        let running = 0;
        cells.forEach(cell => {
            running += cell.weight / Math.max(1e-9, totals);
            cell.cdf = running;
        });
        let cx = 0;
        let cy = 0;
        let cn = 0;
        rings.forEach(ring => ring.forEach(([lng, lat]) => {
            cx += lng;
            cy += lat;
            cn += 1;
        }));
        grids[group] = {
            rings,
            cells,
            cellW: (maxLng - minLng) / cols,
            cellH: (maxLat - minLat) / rows,
            cx: cn ? cx / cn : 0,
            cy: cn ? cy / cn : 0
        };
    });
    return grids;
}

function sampleVisualCell(movieId, group) {
    const grid = visualMaskGrids && visualMaskGrids[group];
    if (!grid || !grid.cells.length) return null;
    const pick = stableUnit(movieId, 17);
    let chosen = grid.cells[0];
    for (let i = 0; i < grid.cells.length; i += 1) {
        if (pick <= grid.cells[i].cdf) {
            chosen = grid.cells[i];
            break;
        }
        chosen = grid.cells[i];
    }
    const jScale = 0.85 + stableUnit(movieId, 41) * 1.15;
    const edgeBoost = 0.7 + (1 - chosen.edgeT) * 0.55;
    let lng = chosen.lng + (stableUnit(movieId, 53) - 0.5) * grid.cellW * jScale * edgeBoost;
    let lat = chosen.lat + (stableUnit(movieId, 71) - 0.5) * grid.cellH * jScale * edgeBoost;
    const inset = Math.min(0.16, 0.04 + (1 - chosen.edgeT) * 0.08 + chosen.voidness * 0.04);
    lng = lerp(lng, grid.cx, inset);
    lat = lerp(lat, grid.cy, inset);
    const inside = pointInRings(lng, lat, grid.rings);
    return {
        lng: inside ? lng : chosen.lng,
        lat: inside ? lat : chosen.lat,
        edgeT: chosen.edgeT,
        voidness: chosen.voidness
    };
}

function sampleStarField(movieId) {
    return [
        0.8 + stableUnit(movieId, 11) * 98.4,
        0.8 + stableUnit(movieId, 29) * 98.4
    ];
}

function assignVisualPlacement(masks) {
    visualMaskGrids = buildMaskGrids(masks);
    coverLayout = buildCoverLayout(masks);
    particleData.forEach(movie => {
        const star = sampleStarField(movie.movieId, movie.rating);
        movie.starX = star[0];
        movie.starY = star[1];
        movie.randX = star[0];
        movie.randY = star[1];
        if (movie.visualGroup === 'unknown') {
            movie.visualX = movie.starX;
            movie.visualY = movie.starY;
            movie.visualEdge = 0;
            movie.visualVoid = 0.35;
        } else {
            const sampled = sampleVisualCell(movie.movieId, movie.visualGroup);
            if (!sampled) {
                movie.visualX = movie.starX;
                movie.visualY = movie.starY;
                movie.visualEdge = 0.35;
                movie.visualVoid = 0.2;
            } else {
                const projected = projectLngLat(sampled.lng, sampled.lat);
                const laid = layoutCoverPoint(projected[0], projected[1], movie.visualGroup);
                movie.visualX = laid[0];
                movie.visualY = laid[1];
                movie.visualEdge = sampled.edgeT;
                movie.visualVoid = sampled.voidness;
            }
        }
        const dust = sampleOceanDust(movie.movieId);
        movie.dustOk = Boolean(dust);
        movie.dustX = dust ? dust[0] : movie.starX;
        movie.dustY = dust ? dust[1] : movie.starY;
    });
    const centroids = {};
    particleData.forEach(movie => {
        if (movie.visualGroup === 'unknown') return;
        const bucket = centroids[movie.visualGroup] || { x: 0, y: 0, n: 0 };
        bucket.x += movie.visualX;
        bucket.y += movie.visualY;
        bucket.n += 1;
        centroids[movie.visualGroup] = bucket;
    });
    Object.values(centroids).forEach(bucket => {
        if (bucket.n) {
            bucket.x /= bucket.n;
            bucket.y /= bucket.n;
        }
    });
    particleData.forEach(movie => {
        const center = centroids[movie.visualGroup] || { x: 50, y: 50 };
        movie.cloudX = lerp(center.x, movie.visualX, 0.42)
            + (stableUnit(movie.movieId, 61) - 0.5) * 10;
        movie.cloudY = lerp(center.y, movie.visualY, 0.42)
            + (stableUnit(movie.movieId, 67) - 0.5) * 8;
    });
}

function visualKeepPriority(movie) {
    return (movie.rating >= 8.5 ? 1.3 : 0)
        + (movie.isDialect ? 1 : 0)
        + movie.rating / 10 * 0.35
        + stableUnit(movie.movieId, 31) * 0.15;
}

function takeBand(rows, count) {
    return rows
        .map(movie => ({
            id: movie.id,
            priority: visualKeepPriority(movie),
            tie: stableUnit(movie.movieId, 99)
        }))
        .sort((a, b) => b.priority - a.priority || a.tie - b.tie)
        .slice(0, Math.max(0, count))
        .map(item => item.id);
}

function assignVisualKeep() {
    const mobile = window.innerWidth <= 768;
    const budget = mobile ? VISUAL_BUDGET_MOBILE : VISUAL_BUDGET_DESKTOP;
    const keep = new Set();
    const sparseGroups = new Set(['africa', 'south_america', 'oceania', 'unknown']);
    particleData.forEach(movie => {
        if (sparseGroups.has(movie.visualGroup)) keep.add(movie.id);
    });
    const remaining = Math.max(0, budget - keep.size);
    const shares = { china: 0.24, asia: 0.26, europe: 0.26, north_america: 0.24 };
    Object.entries(shares).forEach(([group, share]) => {
        const quota = Math.max(60, Math.floor(remaining * share));
        const rows = particleData.filter(movie => movie.visualGroup === group);
        const core = rows.filter(movie => movie.visualEdge >= 0.55);
        const mid = rows.filter(movie => movie.visualEdge >= 0.22 && movie.visualEdge < 0.55);
        const rim = rows.filter(movie => movie.visualEdge < 0.22);
        const nCore = Math.floor(quota * 0.4);
        const nMid = Math.floor(quota * 0.4);
        const nRim = Math.max(6, quota - nCore - nMid);
        [...takeBand(core, nCore), ...takeBand(mid, nMid), ...takeBand(rim, nRim)]
            .forEach(id => keep.add(id));
    });
    if (keep.size < budget) {
        particleData
            .filter(movie => !keep.has(movie.id))
            .map(movie => ({
                id: movie.id,
                priority: visualKeepPriority(movie),
                tie: stableUnit(movie.movieId, 99)
            }))
            .sort((a, b) => b.priority - a.priority || a.tie - b.tie)
            .slice(0, budget - keep.size)
            .forEach(item => keep.add(item.id));
    }
    const dustBudget = mobile ? DUST_BUDGET_MOBILE : DUST_BUDGET_DESKTOP;
    const dust = new Set(
        particleData
            .filter(movie => !keep.has(movie.id) && movie.dustOk)
            .map(movie => ({
                id: movie.id,
                priority: visualKeepPriority(movie),
                tie: stableUnit(movie.movieId, 103)
            }))
            .sort((a, b) => b.priority - a.priority || a.tie - b.tie)
            .slice(0, dustBudget)
            .map(item => item.id)
    );
    particleData.forEach(movie => {
        movie.mobileKeep = keep.has(movie.id);
        movie.dustKeep = dust.has(movie.id);
    });
    visualKeepIsMobile = window.innerWidth <= 768;
    placeCoverDust();
    refreshPrologueRowCache();
    universeIdlePoseValid = false;
}

function coverDustVisible() {
    if (prologueState === PROLOGUE_STATES.WORLD_MAP) return true;
    return universeExitHandoff && prologueMotion.release < 0.999;
}

function isCoverDust(movie) {
    return Boolean(movie && movie.dustKeep && !movie.mobileKeep);
}

function universeIdleBreathing() {
    return activeSceneId === 'universe' && !prefersReducedMotion();
}

function resetUniverseIdlePaint() {
    universeIdleEchartsPainted = false;
    lastUniverseIdlePaint = 0;
    universeIdlePoseValid = false;
}

function ensureIdlePoseCapacity(next) {
    if (next <= universeIdlePoseX.length) return;
    const size = Math.max(next, Math.ceil((universeIdlePoseX.length || 1024) * 1.5));
    const grow = prev => {
        const copy = new Float32Array(size);
        if (prev.length) copy.set(prev);
        return copy;
    };
    universeIdlePoseX = grow(universeIdlePoseX);
    universeIdlePoseY = grow(universeIdlePoseY);
    universeIdlePoseOnMap = grow(universeIdlePoseOnMap);
    universeIdlePoseAppear = grow(universeIdlePoseAppear);
}

function setUniverseHitLayerHidden(hidden) {
    if (hidden) document.documentElement.dataset.universeIdle = 'true';
    else delete document.documentElement.dataset.universeIdle;
}

function universeBreathStarry(movie, dim) {
    return isCoverDust(movie)
        || prologueState === PROLOGUE_STATES.STAR_FIELD
        || (prologueState === PROLOGUE_STATES.REGION_FOCUS && dim);
}

function universeBreathScale(movie, dim, kind) {
    if (universeBreathMix <= 0.001) return 1;
    const t = universePaintNow * 0.001;
    const freq = movie && Number.isFinite(movie.visualFreq) ? movie.visualFreq : 0.18;
    const phase = movie && Number.isFinite(movie.visualPhase) ? movie.visualPhase : 0;
    const wave = Math.sin(t * freq * Math.PI * 2 + phase);
    const starry = universeBreathStarry(movie, dim);
    const amp = kind === 'size' ? (starry ? 0.08 : 0.03) : (starry ? 0.28 : 0.12);
    return 1 + wave * amp * universeBreathMix;
}

function refreshPrologueRowCache() {
    prologueLandRows = [];
    prologueDustRows = [];
    for (let i = 0; i < particleData.length; i += 1) {
        const movie = particleData[i];
        if (movie.mobileKeep) prologueLandRows.push(movie);
        else if (movie.dustKeep) prologueDustRows.push(movie);
    }
}

function prologueVisibleRows() {
    return coverDustVisible() ? prologueDustRows.concat(prologueLandRows) : prologueLandRows;
}

function eachPrologueRow(fn) {
    if (coverDustVisible()) {
        for (let i = 0; i < prologueDustRows.length; i += 1) fn(prologueDustRows[i]);
    }
    for (let i = 0; i < prologueLandRows.length; i += 1) fn(prologueLandRows[i]);
}

function ratingBrightness(rating) {
    return Math.max(0.3, Math.min(1, Number(rating) / 10));
}

function universePose(movie, ar) {
    if (isCoverDust(movie)) {
        let appear = 1;
        if (prologueState === PROLOGUE_STATES.WORLD_MAP) {
            const delay = movie.visualSize * 0.12;
            appear = smooth01((prologueMotion.reveal - delay) / 0.6);
        } else if (prologueState === PROLOGUE_STATES.STAR_FIELD) {
            appear = 1 - prologueMotion.release;
        } else {
            appear = 0;
        }
        return { x: movie.dustX * ar, y: movie.dustY, onMap: 0, appear };
    }
    let x = movie.starX;
    let y = movie.starY;
    let onMap = 0;
    let appear = 1;
    if (prologueState === PROLOGUE_STATES.WORLD_MAP) {
        const delay = (1 - movie.visualEdge) * 0.36 + movie.visualSize * 0.05;
        const fly = smooth01((prologueMotion.fly - delay) / 0.74);
        x = lerp(movie.starX, movie.visualX, fly);
        y = lerp(movie.starY, movie.visualY, fly);
        appear = smooth01((prologueMotion.reveal - delay * 0.72) / 0.48);
        onMap = fly > 0.5 ? 1 : 0;
    } else if (prologueState === PROLOGUE_STATES.STAR_FIELD) {
        const rel = prologueMotion.release;
        x = lerp(movie.visualX, movie.starX, rel);
        y = lerp(movie.visualY, movie.starY, rel);
        onMap = rel < 0.32 ? 1 : 0;
    } else {
        const gather = prologueMotion.gather;
        if (movie.visualGroup === prologueFocusGroup) {
            if (gather < 0.42) {
                const t = gather / 0.42;
                x = lerp(movie.starX, movie.cloudX, t);
                y = lerp(movie.starY, movie.cloudY, t);
            } else {
                const t = smooth01((gather - 0.42) / 0.58);
                x = lerp(movie.cloudX, movie.visualX, t);
                y = lerp(movie.cloudY, movie.visualY, t);
            }
            onMap = gather > 0.38 ? 1 : 0;
        } else if (movie.visualGroup === prologuePrevGroup) {
            x = lerp(movie.visualX, movie.starX, gather);
            y = lerp(movie.visualY, movie.starY, gather);
            onMap = gather < 0.45 ? 1 : 0;
        }
    }
    return { x: x * ar, y, onMap, appear };
}

function visualGroupRgba(group, brightness, mapped, movie, appear, dim) {
    let rgba;
    if (isCoverDust(movie)) {
        const depth = movie ? movie.visualSize : 0.4;
        const alpha = (0.08 + brightness * 0.16 + depth * 0.12) * Math.max(0, appear);
        rgba = [220, 220, 226, Math.max(0.08, Math.min(0.36, alpha))];
    } else {
        const edge = movie ? movie.visualEdge : 0.55;
        const voidness = movie ? movie.visualVoid : 0;
        const falloff = mapped ? 0.35 + 0.65 * Math.pow(Math.max(0.08, edge), 1.05) : 1;
        const air = 1 - voidness * 0.28;
        const shown = Math.max(0.2, appear);
        const onCover = prologueState === PROLOGUE_STATES.WORLD_MAP;
        if (!mapped) {
            const depth = movie ? movie.visualSize : 0.4;
            if (prologueState === PROLOGUE_STATES.STAR_FIELD) {
                const alpha = (0.08 + brightness * 0.16 + depth * 0.12) * Math.max(0, appear);
                rgba = [220, 220, 226, Math.max(0.08, Math.min(0.36, alpha))];
            } else if (prologueState === PROLOGUE_STATES.REGION_FOCUS && dim) {
                const alpha = (0.06 + brightness * 0.08 + depth * 0.06) * Math.max(0, appear);
                rgba = [220, 220, 226, Math.max(0.06, Math.min(0.20, alpha))];
            } else {
                const alpha = (0.22 + brightness * 0.33) * air * shown * (dim ? 0.62 : 1);
                rgba = [220, 220, 226, Math.max(0.16, Math.min(0.55, alpha))];
            }
        } else {
            let hex = VISUAL_GROUP_COLORS[group] || VISUAL_GROUP_COLORS.unknown;
            if (onCover && group === 'china') hex = COVER_CHINA_HEX;
            const coverBoost = onCover ? (group === 'china' ? 1.10 : 1) : 1;
            const alpha = (0.38 + brightness * 0.47) * falloff * air * shown * coverBoost;
            const focused = prologueState === PROLOGUE_STATES.REGION_FOCUS && !dim;
            const minA = onCover ? (group === 'china' ? 0.46 : 0.42) : focused ? 0.42 : 0.28;
            const maxA = onCover ? (group === 'china' ? 0.92 : 0.86) : focused ? 0.88 : 0.85;
            const rgb = hexToRgb(hex);
            rgba = [rgb[0], rgb[1], rgb[2], Math.max(minA, Math.min(maxA, alpha))];
        }
    }
    rgba[3] = Math.max(0.02, rgba[3] * universeBreathScale(movie, dim, 'alpha'));
    return rgba;
}

function visualGroupColor(group, brightness, mapped, movie, appear, dim) {
    const rgba = visualGroupRgba(group, brightness, mapped, movie, appear, dim);
    return `rgba(${rgba[0]}, ${rgba[1]}, ${rgba[2]}, ${rgba[3]})`;
}

function universeSymbolSize(movie, brightness, appear, dim) {
    const size = movie ? movie.visualSize : 0.4;
    const shown = Math.max(0.55, appear);
    const glow = brightness >= 0.85 ? 0.3 : brightness >= 0.72 ? 0.1 : 0;
    let result;
    if (isCoverDust(movie)) {
        const depth = 1.1 + size * 1.05 + glow * 0.15;
        result = Math.max(1.1, Math.min(2.3, depth * Math.max(0.45, appear)));
    } else if (prologueState === PROLOGUE_STATES.WORLD_MAP) {
        const base = 2 + size * 0.55;
        result = Math.max(2, Math.min(2.8, (base + glow * 0.5) * shown));
    } else if (prologueState === PROLOGUE_STATES.STAR_FIELD) {
        const depth = 1.1 + size * 1.05 + glow * 0.15;
        result = Math.max(1.1, Math.min(2.3, depth * Math.max(0.45, appear)));
    } else if (dim) {
        const depth = 1.1 + size * 0.7;
        result = Math.max(1.1, Math.min(1.9, depth * Math.max(0.45, appear)));
    } else {
        const base = 2.3 + size * 1.05 + glow * 0.2;
        result = Math.max(2.3, Math.min(3.5, base * shown));
    }
    return Math.max(0.6, result * universeBreathScale(movie, dim, 'size'));
}

function beginPrologueMotion(nextState, focusGroup) {
    if (nextState === PROLOGUE_STATES.REGION_FOCUS && prologueFocusGroup && prologueFocusGroup !== focusGroup) {
        prologuePrevGroup = prologueFocusGroup;
    } else if (nextState !== PROLOGUE_STATES.REGION_FOCUS) {
        prologuePrevGroup = null;
    }
    prologueMotion.t0 = performance.now();
    prologueMotion.reveal = nextState === PROLOGUE_STATES.WORLD_MAP ? 0 : 1;
    prologueMotion.fly = 0;
    prologueMotion.release = 0;
    prologueMotion.gather = 0;
    prologueFlyToMap = nextState === PROLOGUE_STATES.WORLD_MAP;
}

function advancePrologueMotion(now) {
    const elapsed = (now - prologueMotion.t0) / 1000;
    const reduced = prefersReducedMotion();
    if (reduced) {
        prologueMotion.reveal = 1;
        prologueMotion.fly = prologueState === PROLOGUE_STATES.WORLD_MAP ? 1 : 0;
        prologueMotion.release = prologueState === PROLOGUE_STATES.STAR_FIELD ? 1 : 0;
        prologueMotion.gather = prologueState === PROLOGUE_STATES.REGION_FOCUS ? 1 : 0;
        prologueFlyToMap = prologueState === PROLOGUE_STATES.WORLD_MAP;
        return;
    }
    if (prologueState === PROLOGUE_STATES.WORLD_MAP) {
        prologueMotion.reveal = smooth01(elapsed / 3.05);
        prologueMotion.fly = smooth01((elapsed - 0.2) / 2.15);
        prologueFlyToMap = prologueMotion.fly > 0.06;
    } else if (prologueState === PROLOGUE_STATES.STAR_FIELD) {
        const releaseMs = universeExitHandoff ? DIALECT_HANDOFF_MS : 1150;
        prologueMotion.release = smooth01((now - prologueMotion.t0) / releaseMs);
        prologueMotion.reveal = 1;
        prologueFlyToMap = false;
    } else {
        prologueMotion.gather = smooth01(elapsed / 1.15);
        prologueMotion.reveal = 1;
        prologueMotion.release = 1;
        prologueFlyToMap = false;
    }
}

function setPrologueState(nextState, focusGroup = null) {
    beginPrologueMotion(nextState, focusGroup);
    prologueState = nextState;
    prologueFocusGroup = nextState === PROLOGUE_STATES.REGION_FOCUS ? focusGroup : null;
    document.documentElement.dataset.prologueState = nextState;
    if (focusGroup) document.documentElement.dataset.prologueFocus = focusGroup;
    else delete document.documentElement.dataset.prologueFocus;
    lastUniverseMotionKey = '';
    universeHandoffToken += 1;
    universeMotionOverlay = false;
    resetUniverseIdlePaint();
    universeIdleSince = 0;
    setUniverseHitLayerHidden(false);
    syncVisualRegionDock();
    startUniverseLoop();
}

function syncVisualRegionDock() {
    const dock = document.getElementById('visual-region-dock');
    if (!dock) return;
    dock.querySelectorAll('[data-visual-group]').forEach(button => {
        const value = button.dataset.visualGroup;
        const active = prologueState === PROLOGUE_STATES.REGION_FOCUS
            ? value === prologueFocusGroup
            : value === 'all';
        button.classList.toggle('is-selected', active);
    });
}

function initVisualRegionDock() {
    const dock = document.getElementById('visual-region-dock');
    if (!dock) return;
    dock.addEventListener('click', event => {
        const button = event.target.closest('[data-visual-group]');
        if (!button) return;
        const group = button.dataset.visualGroup;
        if (group === 'all') setPrologueState(PROLOGUE_STATES.STAR_FIELD);
        else setPrologueState(PROLOGUE_STATES.REGION_FOCUS, group);
        if (activeSceneId === 'universe') startUniverseLoop();
    });
    syncVisualRegionDock();
}

function updateDatasetKpis(data) {
    const ratings = data
        .map(item => Number(item.rating))
        .filter(Number.isFinite);
    const average = ratings.length
        ? ratings.reduce((sum, rating) => sum + rating, 0) / ratings.length
        : 0;
    const voteWeight = data.reduce((sum, item) => sum + Math.max(0, Number(item.votes) || 0), 0);
    const voteWeightedAverage = voteWeight
        ? data.reduce((sum, item) => sum + Number(item.rating) * Math.max(0, Number(item.votes) || 0), 0) / voteWeight
        : 0;

    const meta = window.DataService.meta || {};
    const count = Number(meta.recordCount) || data.length;
    const minimumVotes = Number(meta.minimumVoteCount) || 0;
    const yearRange = Array.isArray(meta.yearRange) && meta.yearRange.length === 2
        ? meta.yearRange.map(Number)
        : sampleYearExtent;
    const formattedCount = count.toLocaleString('zh-CN');
    const formattedYearRange = `${yearRange[0]}–${yearRange[1]}`;
    const regionStats = REGION_LABELS.map((_, code) => summarize(data.filter(movie => movie.regionCode === code)));
    const english = summarize(data.filter(movie => movie.langCode === 0));
    const europeRows = data.filter(movie => movie.regionCode === 1);
    const nonEuropeRows = data.filter(movie => movie.regionCode !== 1);
    const europe = summarize(europeRows);
    const nonEurope = summarize(nonEuropeRows);
    const europeStandardized = standardizedMeanByDecadeGenre(europeRows, data);
    const nonEuropeStandardized = standardizedMeanByDecadeGenre(nonEuropeRows, data);
    const europeRawGap = europe.mean - nonEurope.mean;
    const europeStandardizedGap = europeStandardized.mean - nonEuropeStandardized.mean;
    const values = {
        'particle-sample-count': formattedCount,
        'methodology-sample-count': formattedCount,
        'methodology-minimum-vote-count': minimumVotes.toLocaleString('zh-CN'),
        'methodology-year-range': formattedYearRange,
        'source-record-count': Number(meta.sourceRecordCount || 0).toLocaleString('zh-CN'),
        'europe-count': regionStats[1].n.toLocaleString('zh-CN'),
        'europe-mean': regionStats[1].mean.toFixed(2),
        'non-europe-count': nonEurope.n.toLocaleString('zh-CN'),
        'non-europe-mean': nonEurope.mean.toFixed(2),
        'europe-raw-gap': europeRawGap.toFixed(2),
        'europe-standardized-gap': europeStandardizedGap.toFixed(2),
        'europe-gap-reduction': (europeRawGap - europeStandardizedGap).toFixed(2),
        'english-count': english.n.toLocaleString('zh-CN'),
        'english-share': `${(english.n / data.length * 100).toFixed(1)}%`,
        'europe-detail-count': regionStats[1].n.toLocaleString('zh-CN'),
        'europe-q1': regionStats[1].q1.toFixed(1),
        'europe-below-five': `${regionStats[1].belowFive.toFixed(1)}%`,
        'non-europe-q1': nonEurope.q1.toFixed(1),
        'non-europe-below-five': `${nonEurope.belowFive.toFixed(1)}%`,
        'year-2022plus-count': data.filter(movie => movie.year >= 2022).length.toLocaleString('zh-CN'),
        'year-2022plus-china-count': data.filter(movie => movie.year >= 2022 && movie.regionCode === 3).length.toLocaleString('zh-CN'),
        'year-2022plus-china-share': (() => {
            const total = data.filter(movie => movie.year >= 2022).length;
            const china = data.filter(movie => movie.year >= 2022 && movie.regionCode === 3).length;
            return total ? `${Math.round(china / total * 100)}%` : '--';
        })(),
        'methodology-year-range-repeat': formattedYearRange,
        'overall-unweighted-mean': average.toFixed(2),
        'overall-vote-weighted-mean': voteWeightedAverage.toFixed(2)
    };
    Object.entries(values).forEach(([id, value]) => {
        const node = document.getElementById(id);
        if (!node) return;
        node.innerText = value;
        if (node.classList.contains('is-pending')) node.classList.remove('is-pending');
    });
    fillChinaNarrativeKpis();
}

function decadeOf(year) {
    if (year < 1990) return 'Pre-1990s';
    if (year < 2000) return '1990s';
    if (year < 2010) return '2000s';
    if (year < 2020) return '2010s';
    return '2020s';
}

function summarize(rows) {
    const ratings = rows.map(row => Number(row.rating)).filter(Number.isFinite).sort((a, b) => a - b);
    const n = ratings.length;
    const mean = n ? ratings.reduce((sum, rating) => sum + rating, 0) / n : 0;
    const median = n
        ? (ratings[Math.floor((n - 1) / 2)] + ratings[Math.ceil((n - 1) / 2)]) / 2
        : 0;
    const variance = n ? ratings.reduce((sum, rating) => sum + (rating - mean) ** 2, 0) / n : 0;
    const quantile = q => {
        if (!n) return 0;
        const position = (n - 1) * q;
        const lower = Math.floor(position);
        const fraction = position - lower;
        return ratings[lower + 1] === undefined
            ? ratings[lower]
            : ratings[lower] + fraction * (ratings[lower + 1] - ratings[lower]);
    };
    return {
        n,
        mean,
        median,
        sd: Math.sqrt(variance),
        q1: quantile(0.25),
        highShare: n ? rows.filter(row => row.rating >= 8.5).length / n * 100 : 0,
        belowFive: n ? rows.filter(row => row.rating < 5).length / n * 100 : 0
    };
}

function standardizedMeanByDecadeGenre(rows, referenceRows) {
    const keyFor = row => `${row.decade || decadeOf(row.year)}|${row.genreCode}`;
    const referenceCounts = new Map();
    referenceRows.forEach(row => {
        const key = keyFor(row);
        referenceCounts.set(key, (referenceCounts.get(key) || 0) + 1);
    });
    const grouped = new Map();
    rows.forEach(row => {
        const key = keyFor(row);
        const cell = grouped.get(key) || { sum: 0, n: 0 };
        cell.sum += Number(row.rating);
        cell.n += 1;
        grouped.set(key, cell);
    });
    let coveredReference = 0;
    let weightedTotal = 0;
    grouped.forEach((cell, key) => {
        const referenceCount = referenceCounts.get(key) || 0;
        if (!referenceCount || !cell.n) return;
        coveredReference += referenceCount;
        weightedTotal += (cell.sum / cell.n) * referenceCount;
    });
    return {
        mean: coveredReference ? weightedTotal / coveredReference : 0,
        coverage: referenceRows.length ? coveredReference / referenceRows.length : 0
    };
}

function metric(label, value, detail = '') {
    return { label, value, detail };
}

function standardMetrics(rows) {
    const stats = summarize(rows);
    return [
        metric('电影数 n', stats.n.toLocaleString('zh-CN'), '当前筛选结果'),
        metric('平均评分', stats.n ? stats.mean.toFixed(2) : '--', '算术平均数'),
        metric('中位数', stats.n ? stats.median.toFixed(2) : '--', '对极端值更稳健'),
        metric('高分占比', stats.n ? `${stats.highShare.toFixed(1)}%` : '--', '评分 ≥ 8.5')
    ];
}

function horizontalGuide(value, label, color, position = 'insideEndTop') {
    return { axis: 'y', value, label, color, position };
}

function verticalGuide(value, label, color = GUIDE_COLORS.selected, position = 'insideEndTop') {
    return { axis: 'x', value, label, color, position };
}

function horizontalDifferenceBand(first, second, color = 'rgba(255, 209, 102, 0.10)') {
    if (!Number.isFinite(first) || !Number.isFinite(second)) return undefined;
    return {
        silent: true,
        label: { show: false },
        data: [[
            { yAxis: Math.min(first, second), itemStyle: { color } },
            { yAxis: Math.max(first, second) }
        ]]
    };
}

function compactGuideLabel(label) {
    return String(label)
        .replace(/北美(?: \d{4})? 均值 /, '北美 ')
        .replace(/东亚＋中国(?: \d{4})? 均值 /, '东亚组 ')
        .replace('其他地区均值 ', '其他 ')
        .replace('全部电影均值 ', '总体 ')
        .replace('标准化均值 ', '标准化 ')
        .replace('此前均值 ', '此前 ')
        .replace('此后均值 ', '此后 ')
        .replace('普通话均值 ', '普通话 ')
        .replace('方言/混合均值 ', '方言组 ')
        .replace('方言均值 ', '方言组 ')
        .replace('编辑高分阈值 8.5', '8.5 阈值')
        .replace('低分界线 5.0', '5.0 界线')
        .replace('5.0｜低分下限', '5.0 下限')
        .replace('不到 5 分', '5 分')
        .replace('5 分线', '5 分')
        .replace('方言片低分线', '低分线')
        .replace('比较组分界', '组别分界')
        .replace('两组分界', '组别分界')
        .replace(/^所选(?:类型|地区|组)：/, '')
        .replace('中位数 ', '中位 ')
        .replace(' 均值 ', ' ')
        .replace(/ 年$/, '');
}

function createGuideMarkLine(guides) {
    const compactLabels = window.innerWidth <= 700;
    return {
        silent: true,
        symbol: ['none', 'none'],
        animation: false,
        z: 12,
        lineStyle: { type: 'dashed', width: 1.25, opacity: 0.9 },
        label: {
            show: true,
            distance: 5,
            padding: [3, 5],
            borderRadius: 3,
            backgroundColor: 'rgba(5, 5, 7, 0.82)',
            fontFamily: 'Noto Sans SC, PingFang SC, sans-serif',
            fontSize: compactLabels ? 9 : 11,
            fontWeight: 700
        },
        data: guides
            .filter(guide => Number.isFinite(Number(guide.value)))
            .map(guide => ({
                name: guide.label,
                [guide.axis === 'x' ? 'xAxis' : 'yAxis']: Number(guide.value),
                lineStyle: {
                    color: guide.color,
                    type: guide.type || 'dashed',
                    width: guide.width || 1.25,
                    opacity: guide.opacity || 0.9
                },
                label: {
                    formatter: compactLabels ? compactGuideLabel(guide.label) : guide.label,
                    color: guide.color,
                    position: guide.position || 'insideEndTop'
                }
            }))
    };
}

const SCENE_INTERACTIONS = {
    universe: {
        label: '星图 · 全样本',
        prompt: '选择一个地区，查看电影数、平均分和年份跨度。',
        type: 'buttons',
        defaultValue: 'all',
        options: [{ value: 'all', label: '全部' }, ...REGION_LABELS.map((label, index) => ({ value: String(index), label }))],
        filter: (row, value) => value === 'all' || row.regionCode === Number(value),
        metrics: value => {
            const rows = particleData.filter(row => SCENE_INTERACTIONS.universe.filter(row, value));
            const stats = summarize(rows);
            const years = rows.map(row => row.year).filter(Number.isFinite);
            return [
                metric('收录电影', stats.n.toLocaleString('zh-CN'), '每颗粒子代表一部电影'),
                metric('平均评分', stats.mean.toFixed(2), '当前地区等权计算'),
                metric('年份跨度', years.length ? `${Math.min(...years)}–${Math.max(...years)}` : '--', '最早至最晚上映年份'),
                metric('高分占比', `${stats.highShare.toFixed(1)}%`, '评分 ≥ 8.5')
            ];
        },
        insight: value => value === 'all'
            ? `共有 ${particleData.length.toLocaleString('zh-CN')} 部电影达到年份、评分和评价人数门槛。选择地区后可查看其电影数与评分分布。`
            : `${REGION_LABELS[Number(value)]}被单独点亮。点任意一颗粒子，可从集合回到具体电影。`
    },
    'chinese-dialect': {
        label: '第二部 · 份额下降以后的口碑',
        prompt: '按年代看，普通话和方言的平均分怎么变。',
        type: 'buttons',
        defaultValue: 'all',
        options: [
            { value: 'all', label: '全部年份' },
            { value: 'Pre-1990s', label: '1990 年前' },
            { value: '1990s', label: '1990s' },
            { value: '2000s', label: '2000s' },
            { value: '2010s', label: '2010s' },
            { value: '2020s', label: '2020s' }
        ],
        filter: (row, value) => (
            isChinaLanguagePair(row)
            && (value === 'all' || decadeOf(row.year) === value)
        ),
        metrics: value => {
            const rows = particleData.filter(row => SCENE_INTERACTIONS['chinese-dialect'].filter(row, value));
            const mandarin = summarize(rows.filter(isChinaMandarin));
            const dialect = summarize(rows.filter(isChinaDialect));
            const delta = dialect.mean - mandarin.mean;
            return [
                metric('普通话平均分', mandarin.n ? mandarin.mean.toFixed(2) : '--', `${mandarin.n.toLocaleString('zh-CN')} 部`),
                metric('方言平均分', dialect.n ? dialect.mean.toFixed(2) : '--', `${dialect.n.toLocaleString('zh-CN')} 部`),
                metric('相差', mandarin.n && dialect.n ? `${delta >= 0 ? '+' : ''}${delta.toFixed(2)}` : '--', '方言减普通话'),
                metric('两组电影数', rows.length.toLocaleString('zh-CN'), value === 'all' ? '全部年份' : value)
            ];
        },
        insight: value => {
            const rows = particleData.filter(row => SCENE_INTERACTIONS['chinese-dialect'].filter(row, value));
            const mandarin = summarize(rows.filter(isChinaMandarin));
            const dialect = summarize(rows.filter(isChinaDialect));
            const delta = dialect.mean - mandarin.mean;
            return `${value === 'all' ? '全部年份' : value}：方言比普通话 ${delta >= 0 ? '高' : '低'} ${Math.abs(delta).toFixed(2)} 分。`;
        }
    },
    'final-universe': {
        label: '星云 · 按语言看',
        prompt: '按语言缩小范围，再点开一部电影。',
        type: 'buttons',
        defaultValue: 'all',
        options: languageOptionList(true),
        filter: (row, value) => value === 'all' || row.langCode === Number(value),
        metrics: value => standardMetrics(particleData.filter(row => SCENE_INTERACTIONS['final-universe'].filter(row, value))),
        insight: () => '金黄是方言，灰蓝是普通话。点一颗核对具体作品。'
    },
    'global-layers': {
        label: '第四幕 · 欧洲、日韩也这样',
        prompt: '放到同一条 5 分线上，看谁更容易掉到 5 分以下。',
        type: 'buttons',
        defaultValue: 'mandarin-outlier',
        options: [
            { value: 'pull-back', label: '全部' },
            { value: 'axes', label: '5 分线' },
            { value: 'four-groups', label: '前四组' },
            { value: 'mandarin-outlier', label: '普通话' },
            { value: 'boundary', label: '对照' }
        ],
        filter: () => true,
        metrics: value => {
            if (!dialectAgg) return [metric('数据加载中', '--', '请稍候')];
            const byName = Object.fromEntries(dialectAgg.global_layers.map(layer => [layer.name, layer]));
            const read = (name, label, detail) => {
                const layer = byName[name];
                return metric(label, layer ? `${layer.below5}%` : '--', layer ? `${detail} n=${layer.n.toLocaleString('zh-CN')}` : '请稍候');
            };
            const fourGroupNames = ['欧洲 · 非主导语言', '欧洲 · 英语', '日韩', '华语 · 方言'];
            const fiveGroupNames = [...fourGroupNames, '华语 · 普通话'];
            if (value === 'pull-back') {
                const mandarin = summarize(particleData.filter(row => row.langCode === 2));
                const dialect = summarize(particleData.filter(row => row.langCode === 3));
                return [
                    metric('普通话电影数', mandarin.n ? mandarin.n.toLocaleString('zh-CN') : '--', '中国这些电影里'),
                    metric('方言电影数', dialect.n ? dialect.n.toLocaleString('zh-CN') : '--', '中国这些电影里'),
                    metric('普通话平均分', mandarin.n ? mandarin.mean.toFixed(2) : '--', `${mandarin.n.toLocaleString('zh-CN')} 部`),
                    metric('方言平均分', dialect.n ? dialect.mean.toFixed(2) : '--', `${dialect.n.toLocaleString('zh-CN')} 部`)
                ];
            }
            if (value === 'axes') {
                const fiveN = fiveGroupNames.reduce((sum, name) => sum + (byName[name] ? byName[name].n : 0), 0);
                return [
                    metric('5 分线', '5.0', '豆瓣评分'),
                    metric('语言组', '5', '拿来对照的几组'),
                    metric('五组合计', fiveN ? fiveN.toLocaleString('zh-CN') : '--', '部电影'),
                    metric('看什么', '不到 5 分的比例', '掉到 5 分以下的占比')
                ];
            }
            if (value === 'four-groups') {
                return [
                    read('欧洲 · 非主导语言', '欧洲本地话', '不到 5 分'),
                    read('欧洲 · 英语', '英语', '欧洲英语'),
                    read('日韩', '日韩', '不到 5 分'),
                    read('华语 · 方言', '华语方言', '不到 5 分')
                ];
            }
            if (value === 'mandarin-outlier') {
                const mandarin = byName['华语 · 普通话'];
                const fourMax = fourGroupNames.reduce((max, name) => {
                    const rate = byName[name] ? byName[name].below5 : 0;
                    return rate > max ? rate : max;
                }, 0);
                return [
                    read('华语 · 普通话', '华语普通话', '不到 5 分'),
                    read('华语 · 方言', '华语方言', '不到 5 分'),
                    metric('前四组最高', fourMax ? `${fourMax}%` : '--', '这四组里差片最多的一组'),
                    metric('普通话样本', mandarin ? mandarin.n.toLocaleString('zh-CN') : '--', '华语 · 普通话')
                ];
            }
            return [
                read('欧洲 · 非主导语言', '欧洲本地话', '不到 5 分'),
                read('欧洲 · 英语', '英语', '欧洲英语'),
                read('日韩', '日韩', '不到 5 分'),
                read('华语 · 方言', '华语方言', '不到 5 分'),
                read('华语 · 普通话', '华语普通话', '不到 5 分'),
                read('北美 · 英语', '北美英语', '对照之外')
            ];
        },
        insight: value => {
            if (value === 'pull-back') {
                return '全部语言组。点随后会按几组语言重新排。';
            }
            if (value === 'axes') {
                return '竖轴是豆瓣评分。看谁更容易掉到 5 分以下。';
            }
            if (value === 'four-groups') {
                return '欧洲本地话、英语、日韩、华语方言：不到 5 分的都比较少。';
            }
            if (value === 'mandarin-outlier') {
                return '普通话片子里，大约四部中有一部不到 5 分。';
            }
            return '别处说本地话的电影，不到 5 分的也更少。只有几部的方言组，平均分会跟着那几部跳。';
        }
    },
    'dialect-flops': {
        label: '第三部 · 高分方言片的特征',
        prompt: '看方言片里的大多数、低分那些、四部例子，或只留不到 5 分的点。',
        type: 'buttons',
        defaultValue: 'isolate',
        options: [
            { value: 'isolate', label: '大多数' },
            { value: 'tail', label: '低分那些' },
            { value: 'cases', label: '四部例子' },
            { value: 'flopsOnly', label: '只留低分' }
        ],
        filter: (row, phase) => (phase === 'flopsOnly' ? isDialectFlop(row) : isChinaDialect(row)),
        metrics: phase => {
            const current = resolveFlopPhase(phase);
            const stats = dialectFlopStats();
            const paths = computeGenreFlopRates();
            const flops = particleData.filter(isDialectFlop);
            const flopSummary = summarize(flops);
            const flopMin = flops.reduce((min, row) => {
                const rating = Number(row.rating);
                return Number.isFinite(rating) && rating < min ? rating : min;
            }, Infinity);
            if (current === 'tail') {
                const topRates = [...paths].sort((a, b) => b.rate - a.rate).slice(0, 2);
                return [
                    metric('低分片', stats.flopN ? stats.flopN.toLocaleString('zh-CN') : '--', '评分 < 5'),
                    metric('占方言', stats.n ? `${stats.rate.toFixed(1)}%` : '--', `${stats.flopN.toLocaleString('zh-CN')} / ${stats.n.toLocaleString('zh-CN')}`),
                    metric('低分平均分', flopSummary.n ? flopSummary.mean.toFixed(2) : '--', `${flopSummary.n.toLocaleString('zh-CN')} 部`),
                    metric('低分中位', flopSummary.n ? flopSummary.median.toFixed(2) : '--', '不太受极端分拉动'),
                    ...topRates.map(item => metric(item.label, item.n ? `${item.rate.toFixed(1)}%` : '--', `低分 ${item.flopN} / ${item.n}`))
                ];
            }
            if (current === 'cases') {
                return FLOP_CASE_PATHS.map(item => {
                    const movie = caseMovieById(item.movieId);
                    return metric(
                        movie ? movie.title : item.path,
                        movie && Number.isFinite(Number(movie.rating)) ? Number(movie.rating).toFixed(1) : '--',
                        item.path
                    );
                });
            }
            if (current === 'flopsOnly') {
                const topCounts = [...paths].sort((a, b) => b.flopN - a.flopN).slice(0, 2);
                return [
                    metric('低分片', stats.flopN ? stats.flopN.toLocaleString('zh-CN') : '--', '图上只留这些点'),
                    metric('平均分', flopSummary.n ? flopSummary.mean.toFixed(2) : '--', `${flopSummary.n.toLocaleString('zh-CN')} 部`),
                    metric('中位', flopSummary.n ? flopSummary.median.toFixed(2) : '--', '评分 < 5'),
                    metric('最低分', Number.isFinite(flopMin) ? flopMin.toFixed(1) : '--', `这 ${stats.flopN.toLocaleString('zh-CN')} 部里`),
                    ...topCounts.map(item => metric(item.label, item.flopN ? String(item.flopN) : '--', `低分 ${item.flopN} / ${item.n}`))
                ];
            }
            return [
                metric('方言片', stats.n ? stats.n.toLocaleString('zh-CN') : '--', '中国组'),
                metric('不到 5 分', stats.flopN ? String(stats.flopN) : '--', `${stats.rate.toFixed(1)}%`),
                ...paths.map(item => metric(item.label, item.n ? `${item.rate.toFixed(1)}%` : '--', `低分 ${item.flopN} / ${item.n}`))
            ];
        },
        insight: phase => {
            const current = resolveFlopPhase(phase);
            const stats = dialectFlopStats();
            if (current === 'tail') {
                return `${stats.flopN.toLocaleString('zh-CN')} 部不到 5 分。`;
            }
            if (current === 'cases') {
                return '四部真实的低分方言片。点开卡片或粒子，核对具体作品。';
            }
            if (current === 'flopsOnly') {
                return `图上只剩不到 5 分的 ${stats.flopN.toLocaleString('zh-CN')} 部。`;
            }
            return `${stats.n.toLocaleString('zh-CN')} 部方言片里，只有 ${stats.flopN.toLocaleString('zh-CN')} 部不到 5 分（${stats.rate.toFixed(1)}%）。`;
        }
    },
    'dual-director': {
        label: '第三部 · 高分方言片的特征',
        prompt: '同一批导演的方言片和普通话片都在图上。点开卡片看具体作品。',
        type: 'buttons',
        defaultValue: 'all',
        options: [
            { value: 'all', label: '两种语言' },
            { value: '3', label: '方言' },
            { value: '2', label: '普通话' }
        ],
        filter: (row, value) => {
            if (!isChinaLanguagePair(row)) return false;
            if (value === 'all') return true;
            if (value === '3') return isChinaDialect(row);
            if (value === '2') return isChinaMandarin(row);
            return false;
        },
        metrics: value => {
            const rows = particleData.filter(row => SCENE_INTERACTIONS['dual-director'].filter(row, value));
            const dialect = summarize(rows.filter(isChinaDialect));
            const mandarin = summarize(rows.filter(isChinaMandarin));
            const dd = dialectAgg && dialectAgg.dual_director;
            const shared = [
                metric('两种话都拍过', dd ? dd.total.toLocaleString('zh-CN') : '--', '同一批导演'),
                metric('方言更高', dd ? dd.share_positive + '%' : '--', dd ? '平均分差 +' + dd.mean_diff.toFixed(2) : '加载中')
            ];
            const flopRate = stats => metric(
                '不到 5 分',
                stats.n ? `${stats.belowFive.toFixed(1)}%` : '--',
                stats.n ? `${stats.n.toLocaleString('zh-CN')} 部里` : '差片占比'
            );
            if (value === '3') {
                return [
                    ...shared,
                    metric('方言平均分', dialect.n ? dialect.mean.toFixed(2) : '--', `${dialect.n.toLocaleString('zh-CN')} 部`),
                    flopRate(dialect)
                ];
            }
            if (value === '2') {
                return [
                    ...shared,
                    metric('普通话平均分', mandarin.n ? mandarin.mean.toFixed(2) : '--', `${mandarin.n.toLocaleString('zh-CN')} 部`),
                    flopRate(mandarin)
                ];
            }
            return [
                ...shared,
                metric('方言平均分', dialect.n ? dialect.mean.toFixed(2) : '--', `${dialect.n.toLocaleString('zh-CN')} 部`),
                metric('普通话平均分', mandarin.n ? mandarin.mean.toFixed(2) : '--', `${mandarin.n.toLocaleString('zh-CN')} 部`)
            ];
        },
        insight: () => {
            const dd = dialectAgg && dialectAgg.dual_director;
            if (!dd) return '同一人拍方言片和普通话片，分数仍可能不同。';
            return `${dd.total} 位导演两种话都拍过，其中 ${dd.share_positive}% 的方言片平均分更高，差 +${dd.mean_diff.toFixed(2)}。具体到每一部，同一人拍的几部可以差出四五分。`;
        }
    },
    'china-dialect-stars': {
        label: '引言 · 方言电影',
        prompt: '点一颗星，看这部电影。',
        type: 'buttons',
        defaultValue: 'all',
        options: [{ value: 'all', label: '中国方言片' }],
        filter: (row) => isStorySpanDialect(row),
        metrics: () => {
            const stats = summarize(particleData.filter(isStorySpanDialect));
            return [
                metric('方言片', stats.n ? stats.n.toLocaleString('zh-CN') : '--', '1985 年起，中国含港澳台'),
                metric('平均分', stats.n ? stats.mean.toFixed(2) : '--', `${stats.n.toLocaleString('zh-CN')} 部`)
            ];
        },
        insight: () => '星空是 1985 年起的中国方言片，更早的没有放进来。'
    },
    'wave-hk': {
        label: '第一部 · 方言电影的发展历程',
        prompt: '点一颗星，看这部港片。',
        type: 'buttons',
        defaultValue: 'all',
        options: [{ value: 'all', label: '港片粤语' }],
        filter: (row) => isHkDialect(row) && inYearRange(row, 1985, 2005),
        metrics: () => {
            const stats = summarize(particleData.filter(row => isHkDialect(row) && inYearRange(row, 1985, 2005)));
            return [
                metric('港片', stats.n ? stats.n.toLocaleString('zh-CN') : '--', '1985–2005 方言'),
                metric('平均分', stats.n ? stats.mean.toFixed(2) : '--', '香港')
            ];
        },
        insight: () => '1985 到 2005 年的香港方言片。每一年都有。'
    },
    'mandarin-gap': {
        label: '第一部 · 方言电影的发展历程',
        prompt: '点一颗星，看这几年里还在拍的内地方言片。',
        type: 'buttons',
        defaultValue: 'all',
        options: [{ value: 'all', label: '内地方言 2000–2010' }],
        filter: (row) => isMainlandDialect(row) && inYearRange(row, 2000, 2010),
        metrics: () => {
            const dialect = summarize(particleData.filter(row => isMainlandDialect(row) && inYearRange(row, 2000, 2010)));
            const mandarin = summarize(particleData.filter(row => isMainlandMandarin(row) && inYearRange(row, 2000, 2010)));
            return [
                metric('内地方言', dialect.n ? dialect.n.toLocaleString('zh-CN') : '--', '2000–2010'),
                metric('内地普通话', mandarin.n ? mandarin.n.toLocaleString('zh-CN') : '--', '同一时期内地')
            ];
        },
        insight: () => '星空是 2000 到 2010 年的内地方言片。部数已经很少。'
    },
    'three-waves': {
        label: '第一部 · 方言电影的发展历程',
        prompt: '点一颗星，或点下面片单。',
        type: 'buttons',
        defaultValue: 'all',
        options: [{ value: 'all', label: '2008–2020，加一部阿嬷' }],
        filter: (row) => isLaterWaveDialect(row),
        metrics: () => {
            const stats = summarize(particleData.filter(isLaterWaveDialect));
            const waves = dialectAgg && dialectAgg.wave_cases;
            const count = waves ? ['hk', 'sw', 'mn'].reduce((n, key) => n + (waves[key] || []).length, 0) : 0;
            return [
                metric('后来的方言片', stats.n ? stats.n.toLocaleString('zh-CN') : '--', '非港片，2008–2020'),
                metric('三波片单', count ? String(count) : '--', '港片／四川贵州／闽南')
            ];
        },
        insight: () => '星空是 2008 到 2020 年、产地不是香港的方言片，外加一部 2026 年的《给阿嬷的情书》。'
    },
    'china-2010s': {
        label: '第二部 · 份额下降以后的口碑',
        prompt: '金黄是方言。点一颗看 2010 到 2019 年的方言片。',
        type: 'buttons',
        defaultValue: 'all',
        options: [{ value: 'all', label: '2010–2019' }],
        filter: (row) => isChinaLanguagePair(row) && decadeOf(row.year) === '2010s',
        metrics: () => {
            const rows = particleData.filter(row => isChinaLanguagePair(row) && decadeOf(row.year) === '2010s');
            const mandarin = summarize(rows.filter(isChinaMandarin));
            const dialect = summarize(rows.filter(isChinaDialect));
            return [
                metric('方言', dialect.n ? dialect.n.toLocaleString('zh-CN') : '--', dialect.n ? `平均 ${dialect.mean.toFixed(2)}` : '2010s'),
                metric('普通话', mandarin.n ? mandarin.n.toLocaleString('zh-CN') : '--', mandarin.n ? `平均 ${mandarin.mean.toFixed(2)}` : '2010s')
            ];
        },
        insight: () => '2010 到 2019 年，方言片还在拍，占中国电影的份额更小了。'
    },
    'china-2020s': {
        label: '第二部 · 份额下降以后的口碑',
        prompt: '点一颗星。绝大多数是 2020 年，一部是《给阿嬷的情书》。',
        type: 'buttons',
        defaultValue: 'all',
        options: [{ value: 'all', label: '2020 年，加一部阿嬷' }],
        filter: (row) => isChinaDialect(row) && decadeOf(row.year) === '2020s',
        metrics: () => {
            const rows = particleData.filter(row => isChinaDialect(row) && decadeOf(row.year) === '2020s');
            const stats = summarize(rows);
            const y2020 = rows.filter(row => Number(row.year) === 2020).length;
            return [
                metric('方言片', stats.n ? stats.n.toLocaleString('zh-CN') : '--', `${y2020} 部是 2020 年`),
                metric('平均分', stats.n ? stats.mean.toFixed(2) : '--', '2021–2025 年无收录')
            ];
        },
        insight: () => '这份快照里没有 2021 到 2025 年的中国方言片。'
    },
    'china-below5': {
        label: '第二部 · 份额下降以后的口碑',
        prompt: '金黄是方言，蓝色是普通话。点一颗看这部电影。',
        type: 'buttons',
        defaultValue: 'all',
        options: [{ value: 'all', label: '中国电影' }],
        filter: (row) => isChinaLanguagePair(row),
        metrics: () => {
            const dialect = summarize(particleData.filter(isChinaDialect));
            const mandarin = summarize(particleData.filter(isChinaMandarin));
            return [
                metric('方言不到 5 分', dialect.n ? `${dialect.belowFive.toFixed(1)}%` : '--', `${dialect.n.toLocaleString('zh-CN')} 部里`),
                metric('普通话不到 5 分', mandarin.n ? `${mandarin.belowFive.toFixed(1)}%` : '--', `${mandarin.n.toLocaleString('zh-CN')} 部里`)
            ];
        },
        insight: () => '把这些年的中国电影加在一起，掉到 5 分以下的，方言片更少。'
    },
    'china-high8': {
        label: '第三部 · 高分方言片的特征',
        prompt: '点一颗八分及以上的方言片。',
        type: 'buttons',
        defaultValue: 'all',
        options: [{ value: 'all', label: '八分及以上' }],
        filter: (row) => isChinaDialect(row) && Number(row.rating) >= 8,
        metrics: () => {
            const stats = summarize(particleData.filter(row => isChinaDialect(row) && Number(row.rating) >= 8));
            return [
                metric('八分及以上', stats.n ? stats.n.toLocaleString('zh-CN') : '--', '中国方言片'),
                metric('平均分', stats.n ? stats.mean.toFixed(2) : '--', '这些高分片子')
            ];
        },
        insight: () => '八分及以上。短评里写的是具体场面。'
    },
    'scale': {
        label: '世界平均分',
        prompt: '点开一部电影，或看各地区平均分。',
        type: 'buttons',
        defaultValue: 'all',
        options: languageOptionList(true),
        filter: (row, value) => value === 'all' || row.langCode === Number(value),
        metrics: () => {
            const rungs = getWorldScaleRungs();
            if (rungs) {
                return rungs.map(rung => metric(
                    rung.name,
                    rung.score.toFixed(2),
                    `n=${Number(rung.n).toLocaleString('zh-CN')}`
                ));
            }
            const dialect = summarize(particleData.filter(isChinaDialect));
            const europe = summarize(particleData.filter(row => row.regionCode === 1));
            const northAmerica = summarize(particleData.filter(row => row.regionCode === 0));
            return [
                metric('方言平均分', dialect.n ? dialect.mean.toFixed(2) : '--', `${dialect.n.toLocaleString('zh-CN')} 部`),
                metric('欧洲平均分', europe.n ? europe.mean.toFixed(2) : '--', `${europe.n.toLocaleString('zh-CN')} 部`),
                metric('北美平均分', northAmerica.n ? northAmerica.mean.toFixed(2) : '--', `${northAmerica.n.toLocaleString('zh-CN')} 部`)
            ];
        },
        insight: () => {
            const rungs = getWorldScaleRungs();
            if (rungs) {
                const shown = Object.fromEntries(rungs.map(rung => [rung.key, Number(rung.score.toFixed(2))]));
                const premium = (shown.dia - shown.cn).toFixed(2);
                const remain = (shown.eu - shown.dia).toFixed(2);
                return `方言平均分 ${shown.dia.toFixed(2)}，仍低于欧洲 ${shown.eu.toFixed(2)}、北美 ${shown.na.toFixed(2)}。比普通话高 ${premium}，离欧洲还差 ${remain}。`;
            }
            const dialect = summarize(particleData.filter(isChinaDialect));
            const europe = summarize(particleData.filter(row => row.regionCode === 1));
            const northAmerica = summarize(particleData.filter(row => row.regionCode === 0));
            if (!dialect.n || !europe.n || !northAmerica.n) {
                return '方言片，和欧洲、北美的平均分。';
            }
            return `方言平均分 ${dialect.mean.toFixed(2)}，仍低于欧洲 ${europe.mean.toFixed(2)}、北美 ${northAmerica.mean.toFixed(2)}。`;
        }
    },
    'echo-narrative': {
        label: '第四部 · 方言电影的大众化路径',
        prompt: '',
        type: 'buttons',
        defaultValue: 'all',
        options: [],
        filter: (row) => isStorySpanDialect(row),
        metrics: () => [],
        insight: () => '',
    },
};

function initSceneInteractions() {
    const steps = [...document.querySelectorAll('.particle-step')];

    steps.forEach((step, index) => {
        const sceneId = step.dataset.scene || 'universe';
        const config = SCENE_INTERACTIONS[sceneId];
        if (!config) return;
        step.dataset.chapter = `${String(index + 1).padStart(2, '0')} / ${String(steps.length).padStart(2, '0')}`;
        // 数据卡标题跟随正文 badge，避免两套命名（badge 与 config.label）不一致。
        const badge = step.querySelector('.theory-badge');
        const labLabel = badge ? badge.textContent.trim() : config.label;
        step.dataset.sceneTitle = labLabel;
        if (sceneState[sceneId] === undefined) sceneState[sceneId] = config.defaultValue;

        // Keep the opening screen as spare as the original hero. Interactive
        // evidence begins with the first actual story act below it.
        if (index === 0) return;
        if (sceneId === 'echo-narrative') return;
        if (sceneId === 'china-dialect-stars') return;
        if (document.querySelector(`[data-scene-lab="${sceneId}"]`)) return;

        // Keep the original lightweight story surface. Per-scene analysis is
        // available on demand instead of permanently occupying the homepage.
        const lab = document.createElement('details');
        lab.className = 'scene-lab';
        lab.dataset.sceneLab = sceneId;
        lab.innerHTML = `
            <summary class="scene-lab-heading">
                <span class="scene-lab-toggle">展开数据</span>
                <b>${labLabel}</b>
                <i aria-hidden="true">＋</i>
            </summary>
            <div class="scene-lab-body">
                <p class="scene-question">${config.prompt}</p>
                <div class="scene-control" aria-label="场景筛选器"></div>
                <div class="scene-metrics" aria-live="polite"></div>
                <p class="scene-insight"></p>
                <p class="scene-guide-note">图中虚线标出比较基准；出现色带时，色带表示两条统计线之间的差距。</p>
                <div class="scene-picked" aria-live="polite"><span>尚未点选电影</span></div>
                <button class="scene-random" type="button">随机看一部</button>
            </div>
        `;
        const hook = step.querySelector('.scene-hook');
        if (hook) {
            step.insertBefore(lab, hook);
        } else {
            step.appendChild(lab);
        }
        if (sceneId === 'global-layers') {
            const dock = document.createElement('div');
            dock.className = 'global-lab-dock';
            lab.replaceWith(dock);
            dock.appendChild(lab);
            const callout = step.querySelector('.mandarin-outlier-callout');
            if (callout) dock.appendChild(callout);
        }
        buildSceneControl(sceneId, lab, config);
        lab.querySelector('.scene-random').addEventListener('click', () => pickRandomMovie(sceneId));
        // 切换 summary 文案：折叠时引导展开，展开后提示可收起。
        lab.addEventListener('toggle', () => {
            const toggleLabel = lab.querySelector('.scene-lab-toggle');
            if (toggleLabel) toggleLabel.textContent = lab.open ? '收起数据' : '展开数据';
        });
        updateSceneLab(sceneId);
    });

    if (steps[0]) {
        steps[0].classList.add('is-active');
        activateSceneInteraction('universe', steps[0]);
    }
}

function buildSceneControl(sceneId, lab, config) {
    const container = lab.querySelector('.scene-control');
    if (config.type === 'range') {
        const output = document.createElement('output');
        output.className = 'scene-range-value';
        output.textContent = config.formatValue(config.defaultValue);
        const input = document.createElement('input');
        input.type = 'range';
        input.min = config.min;
        input.max = config.max;
        input.step = config.step;
        input.value = config.defaultValue;
        input.setAttribute('aria-label', config.prompt);
        input.addEventListener('input', () => {
            sceneState[sceneId] = Number(input.value);
            output.textContent = config.formatValue(sceneState[sceneId]);
            clearTimeout(sceneSelectionTimer);
            sceneSelectionTimer = setTimeout(() => applySceneSelection(sceneId), 70);
        });
        container.append(output, input);
        return;
    }

    config.options.forEach(option => {
        const button = document.createElement('button');
        button.type = 'button';
        button.className = 'scene-option';
        button.dataset.value = option.value;
        button.textContent = option.label;
        button.setAttribute('aria-pressed', String(option.value === String(config.defaultValue)));
        button.addEventListener('click', () => {
            sceneState[sceneId] = option.value;
            applySceneSelection(sceneId);
        });
        container.appendChild(button);
    });
}

function syncGlobalLayersPhase() {
    const phase = sceneState['global-layers'] || 'mandarin-outlier';
    globalLayersPhase = phase;
    document.documentElement.dataset.globalPhase = phase;
}

function applySceneSelection(sceneId) {
    if (sceneId === 'global-layers') syncGlobalLayersPhase();
    if (sceneId === 'dialect-flops') {
        const nextPhase = resolveFlopPhase(sceneState[sceneId]);
        setFlopPhase(nextPhase, { render: false, refreshLab: true });
    }
    updateSceneLab(sceneId);
    if (sceneId !== activeSceneId) return;
    const config = SCENE_INTERACTIONS[sceneId];
    const focus = config.focus || config.filter;
    activeSceneFilter = row => focus(row, sceneState[sceneId]);
    renderParticleScene(sceneId);
}

function updateSceneLab(sceneId) {
    const config = SCENE_INTERACTIONS[sceneId];
    const lab = document.querySelector(`[data-scene-lab="${sceneId}"]`);
    if (!config || !lab) return;

    lab.querySelectorAll('.scene-option').forEach(button => {
        const active = button.dataset.value === String(sceneState[sceneId]);
        button.classList.toggle('is-selected', active);
        button.setAttribute('aria-pressed', String(active));
    });

    const metrics = config.metrics(sceneState[sceneId]);
    const metricsNode = lab.querySelector('.scene-metrics');
    metricsNode.replaceChildren(...metrics.map(item => {
        const node = document.createElement('div');
        node.className = 'scene-metric';
        const label = document.createElement('span');
        label.textContent = item.label;
        const value = document.createElement('strong');
        value.textContent = item.value;
        const detail = document.createElement('small');
        detail.textContent = item.detail;
        node.append(label, value, detail);
        return node;
    }));
    lab.querySelector('.scene-insight').textContent = config.insight(sceneState[sceneId]);
}

function activateSceneInteraction(sceneId, step) {
    const alreadyHere = activeSceneId === sceneId;
    activeSceneId = sceneId;
    if (sceneId === 'global-layers') syncGlobalLayersPhase();
    if (sceneId === 'dialect-flops') {
        if (!alreadyHere) {
            setFlopPhase(resolveFlopPhase(sceneState[sceneId] || 'isolate'), { render: false, refreshLab: true });
        }
    } else {
        cancelFlopOverlay();
        syncFlopCaseCards(false);
        unbindFlopCaseLinkSync();
        document.documentElement.removeAttribute('data-flop-phase');
    }
    const config = SCENE_INTERACTIONS[sceneId];
    const focus = config && (config.focus || config.filter);
    activeSceneFilter = focus ? row => focus(row, sceneState[sceneId]) : () => true;
}

function currentFilteredMovies(sceneId = activeSceneId) {
    const config = SCENE_INTERACTIONS[sceneId];
    return config
        ? particleData.filter(row => config.filter(row, sceneState[sceneId]))
        : particleData;
}

function pickRandomMovie(sceneId) {
    const candidates = currentFilteredMovies(sceneId);
    if (!candidates.length) return;
    const movie = candidates[Math.floor(Math.random() * candidates.length)];
    renderPickedMovie(sceneId, movie, '随机看一部');
    openMovieDetail(movie);
    if (sceneId === activeSceneId && particleChart) {
        const plottedRows = plottedSeriesData[0] || [];
        const dataIndex = plottedRows.findIndex(item => {
            const value = Array.isArray(item) ? item : item?.value;
            return value?.[3] === movie.id;
        });
        if (dataIndex >= 0) {
            particleChart.dispatchAction({ type: 'showTip', seriesIndex: 0, dataIndex });
        }
    }
}

function renderPickedMovie(sceneId, movie, source = '点选粒子') {
    const lab = document.querySelector(`[data-scene-lab="${sceneId}"]`);
    if (!lab || !movie) return;
    const picked = lab.querySelector('.scene-picked');
    picked.replaceChildren();
    const sourceNode = document.createElement('span');
    sourceNode.textContent = source;
    const title = document.createElement('strong');
    title.textContent = `《${movie.title}》`;
    const meta = document.createElement('small');
    const rating = Number(movie.rating);
    const ratingLabel = Number.isFinite(rating) ? rating.toFixed(1) : '--';
    meta.textContent = `${movie.year || '未知'} · ${ratingLabel} 分 · ${Number(movie.votes || 0).toLocaleString('zh-CN')} 人评价 · ${REGION_LABELS[movie.regionCode] || '未知地区'} · ${LANGUAGE_LABELS[movie.langCode] || '未知语言组'}`;
    picked.append(sourceNode, title, meta);
    if (source === '点选粒子' && lab instanceof HTMLDetailsElement) lab.open = true;
}

function isSceneFocused(movie) {
    try {
        return activeSceneFilter(movie) ? 1 : 0;
    } catch (error) {
        return 1;
    }
}

// =======================
// 第一卷：万级粒子引擎
// =======================
function isMobileViewport() {
    return window.innerWidth <= 768;
}

function isStarfieldScene(sceneId) {
    return sceneId === 'universe'
        || sceneId === 'final-universe'
        || sceneId === 'three-waves'
        || sceneId === 'scale'
        || sceneId === 'echo-narrative'
        || sceneId === 'china-dialect-stars'
        || sceneId === 'wave-hk'
        || sceneId === 'mandarin-gap'
        || sceneId === 'china-2020s'
        || sceneId === 'china-high8';
}

function rememberPlottedSeries(series) {
    const list = Array.isArray(series) ? series : (series ? [series] : []);
    plottedSeriesData = list.map(item => (item && Array.isArray(item.data) ? item.data : []));
}

function scatterItemValue(item) {
    if (Array.isArray(item) && item.length >= 2) return item;
    if (item && Array.isArray(item.value) && item.value.length >= 2) return item.value;
    return null;
}

function seriesPixelAffine(seriesIndex) {
    const origin = particleChart.convertToPixel({ seriesIndex }, [0, 0]);
    const xUnit = particleChart.convertToPixel({ seriesIndex }, [1, 0]);
    const yUnit = particleChart.convertToPixel({ seriesIndex }, [0, 1]);
    if (!origin || !xUnit || !yUnit) return null;
    const sx = xUnit[0] - origin[0];
    const sy = xUnit[1] - origin[1];
    const tx = yUnit[0] - origin[0];
    const ty = yUnit[1] - origin[1];
    if (![sx, sy, tx, ty].every(Number.isFinite)) return null;
    return { origin, sx, sy, tx, ty };
}

function findNearestMovieByPixel(offsetX, offsetY, radiusPx) {
    if (!particleChart || !plottedSeriesData.length) return null;
    let best = null;
    let bestDist = radiusPx * radiusPx;
    for (let seriesIndex = 0; seriesIndex < plottedSeriesData.length; seriesIndex += 1) {
        const rows = plottedSeriesData[seriesIndex];
        if (!rows.length) continue;
        const affine = seriesPixelAffine(seriesIndex);
        if (!affine) continue;
        const { origin, sx, sy, tx, ty } = affine;
        for (let i = 0; i < rows.length; i += 1) {
            const value = scatterItemValue(rows[i]);
            if (!value) continue;
            if (value.length > 4 && Number(value[4]) === 0) continue;
            const px = origin[0] + value[0] * sx + value[1] * tx;
            const py = origin[1] + value[0] * sy + value[1] * ty;
            const dx = px - offsetX;
            const dy = py - offsetY;
            const dist = dx * dx + dy * dy;
            if (dist <= bestDist) {
                bestDist = dist;
                const movieId = value[3];
                best = Number.isInteger(movieId) ? particleData[movieId] : null;
            }
        }
    }
    return best;
}

function openPickedParticle(movie) {
    if (!movie) return;
    if (window.WaveScene && window.WaveScene.handleParticleClick(movie)) return;
    renderPickedMovie(activeSceneId, movie, '点选粒子');
    openMovieDetail(movie);
}

function initPrologueMotionLayer() {
    const canvas = document.getElementById('prologue-motion-layer');
    if (!canvas || prologueMotionLayer) return;
    prologueMotionLayer = createPrologueMotionLayer(canvas);
    prologueMotionLayer.resize();
}

function initParticleEngine() {
    const container = document.getElementById('chart-container');
    particleChart = echarts.init(container, 'dark');
    runtime.particleChart = particleChart;
    runtime.renderParticleScene = renderParticleScene;
    particleChart.on('click', params => {
        if (prologueMotionBusy() || isMobileViewport() || isStarfieldScene(activeSceneId)) return;
        const movieId = params.value && params.value[3];
        const movie = particleData[movieId];
        if (movie) openPickedParticle(movie);
    });
    particleChart.getZr().on('click', event => {
        if (prologueMotionBusy()) return;
        if (!isMobileViewport() && !isStarfieldScene(activeSceneId)) return;
        const movie = findNearestMovieByPixel(event.offsetX, event.offsetY, isStarfieldScene(activeSceneId) ? 18 : 20);
        if (movie) openPickedParticle(movie);
    });
    initPrologueMotionLayer();
    setPrologueState(PROLOGUE_STATES.WORLD_MAP);
    renderParticleScene('universe');
    startUniverseLoop();
}

function universeChartAr() {
    if (prologueMotionLayer && prologueMotionLayer.isVisible()) {
        const size = prologueMotionLayer.cssSize();
        if (size.width && size.height) return Math.max(0.5, size.width / size.height);
    }
    const chartW = particleChart ? particleChart.getWidth() : window.innerWidth;
    const chartH = particleChart ? particleChart.getHeight() : window.innerHeight;
    return Math.max(0.5, chartW / Math.max(1, chartH));
}

function buildUniversePlot() {
    const ar = universeChartAr();
    const rows = prologueVisibleRows();
    const moving = prologueMotionBusy();
    if (universePlotCache.length !== rows.length) {
        universePlotCache = rows.map(() => ({
            value: [0, 0, '', 0, 0.5, 0, 1],
            id: '0',
            symbolSize: 2,
            itemStyle: { color: 'rgba(220, 220, 226, 0.16)' }
        }));
    }
    for (let i = 0; i < rows.length; i += 1) {
        const d = rows[i];
        const pose = universePose(d, ar);
        const brightness = ratingBrightness(d.rating);
        const dim = prologueState === PROLOGUE_STATES.REGION_FOCUS
            && d.visualGroup !== prologueFocusGroup;
        const item = universePlotCache[i];
        item.id = String(d.id);
        item.value[0] = pose.x;
        item.value[1] = pose.y;
        item.value[2] = d.visualGroup;
        item.value[3] = d.id;
        item.value[4] = brightness;
        item.value[5] = pose.onMap;
        item.value[6] = pose.appear;
        item.symbolSize = universeSymbolSize(d, brightness, pose.appear, dim);
        const color = visualGroupColor(
            d.visualGroup,
            brightness,
            pose.onMap === 1,
            d,
            pose.appear,
            dim
        );
        const glowing = !moving
            && pose.onMap
            && !isCoverDust(d)
            && brightness >= 0.87
            && pose.appear > 0.55;
        if (glowing) {
            const hex = prologueState === PROLOGUE_STATES.WORLD_MAP && d.visualGroup === 'china'
                ? COVER_CHINA_HEX
                : (VISUAL_GROUP_COLORS[d.visualGroup] || VISUAL_GROUP_COLORS.unknown);
            item.itemStyle = {
                color,
                shadowBlur: 6,
                shadowColor: hexToRgba(hex, 0.38)
            };
        } else {
            item.itemStyle = { color };
        }
    }
    return universePlotCache;
}

function prologueMotionKey() {
    return [
        prologueState,
        prologueMotion.reveal.toFixed(4),
        prologueMotion.fly.toFixed(4),
        prologueMotion.release.toFixed(4),
        prologueMotion.gather.toFixed(4)
    ].join('|');
}

function paintUniverseMotionFrame(reusePose = false) {
    if (!prologueMotionLayer) return;
    const size = prologueMotionLayer.cssSize();
    const width = size.width || window.innerWidth;
    const height = size.height || window.innerHeight;
    const ar = universeChartAr();
    const xScale = width / Math.max(1e-6, 100 * ar);
    const yScale = height / 100;
    const expected = prologueLandRows.length + (coverDustVisible() ? prologueDustRows.length : 0);
    const cachePose = !reusePose && !prologueMotionBusy();
    if (cachePose) ensureIdlePoseCapacity(expected);
    prologueMotionLayer.begin(expected);
    let i = 0;
    eachPrologueRow(d => {
        let x;
        let y;
        let onMap;
        let appear;
        if (reusePose && i < universeIdlePoseCount) {
            x = universeIdlePoseX[i];
            y = universeIdlePoseY[i];
            onMap = universeIdlePoseOnMap[i];
            appear = universeIdlePoseAppear[i];
        } else {
            const pose = universePose(d, ar);
            x = pose.x;
            y = pose.y;
            onMap = pose.onMap;
            appear = pose.appear;
            if (cachePose) {
                universeIdlePoseX[i] = x;
                universeIdlePoseY[i] = y;
                universeIdlePoseOnMap[i] = onMap;
                universeIdlePoseAppear[i] = appear;
            }
        }
        i += 1;
        const brightness = d.brightness || ratingBrightness(d.rating);
        const dim = prologueState === PROLOGUE_STATES.REGION_FOCUS
            && d.visualGroup !== prologueFocusGroup;
        let rgba = visualGroupRgba(
            d.visualGroup,
            brightness,
            onMap === 1,
            d,
            appear,
            dim
        );
        if (universeExitHandoff && !isCoverDust(d)) {
            const styled = dialectHandoffStyle(
                isStorySpanDialect(d),
                prologueMotion.release,
                rgba
            );
            appear *= styled.appearScale;
            rgba = styled.rgba;
        }
        if (appear < 0.02) return;
        prologueMotionLayer.push(
            x * xScale,
            (100 - y) * yScale,
            universeSymbolSize(d, brightness, appear, dim),
            rgba
        );
    });
    if (cachePose) universeIdlePoseCount = i;
    prologueMotionLayer.draw();
}

function clearUniverseEchartsData() {
    if (!particleChart) return;
    rememberPlottedSeries([{ data: [] }]);
    particleChart.setOption({
        animation: false,
        series: [{ data: [] }]
    }, { notMerge: false, lazyUpdate: false, silent: true });
}

function hidePrologueMotionLayer() {
    if (universeHandoffTimer) {
        window.clearTimeout(universeHandoffTimer);
        universeHandoffTimer = 0;
    }
    if (universeFinishedHandler && particleChart) {
        particleChart.off('finished', universeFinishedHandler);
        universeFinishedHandler = null;
    }
    universeMotionOverlay = false;
    setUniverseHitLayerHidden(false);
    if (prologueMotionLayer) {
        prologueMotionLayer.setVisible(false);
        prologueMotionLayer.clear();
    }
}

function afterUniverseEchartsPaint(token, done) {
    if (!particleChart) {
        done();
        return;
    }
    if (universeFinishedHandler) {
        particleChart.off('finished', universeFinishedHandler);
        universeFinishedHandler = null;
    }
    let finished = false;
    const finish = () => {
        if (universeFinishedHandler) {
            particleChart.off('finished', universeFinishedHandler);
            universeFinishedHandler = null;
        }
        if (finished || token !== universeHandoffToken) return;
        finished = true;
        if (universeHandoffTimer) {
            window.clearTimeout(universeHandoffTimer);
            universeHandoffTimer = 0;
        }
        done();
    };
    const onFinished = () => {
        requestAnimationFrame(() => {
            requestAnimationFrame(finish);
        });
    };
    universeFinishedHandler = onFinished;
    particleChart.on('finished', onFinished);
    universeHandoffTimer = window.setTimeout(finish, 360);
}

function paintUniverseEcharts(onPainted) {
    if (!particleChart || activeSceneId !== 'universe') return;
    const data = buildUniversePlot();
    rememberPlottedSeries([{ data }]);
    const token = universeHandoffToken;
    if (onPainted) afterUniverseEchartsPaint(token, onPainted);
    particleChart.setOption({
        animation: false,
        series: [{ data }]
    }, { notMerge: false, lazyUpdate: false, silent: true });
}

function universeCanvasActive() {
    return activeSceneId === 'universe' || universeExitHandoff;
}

function finishUniverseToDialectHandoff() {
    if (!universeExitHandoff) return;
    universeExitHandoff = false;
    if (universeRaf) {
        cancelAnimationFrame(universeRaf);
        universeRaf = 0;
    }
    renderParticleScene('china-dialect-stars', { skipHandoff: true, animate: false });
}

function paintUniverseLive(now = performance.now()) {
    if (!universeCanvasActive()) return;
    advancePrologueMotion(now);
    if (universeExitHandoff) {
        if (!universeHandoffT0) universeHandoffT0 = now;
        universeIdleSince = 0;
        universeBreathMix = 0;
        universePaintNow = now;
        const elapsed = now - universeHandoffT0;
        if (elapsed < DIALECT_HANDOFF_MS) {
            universeIdleEchartsPainted = false;
            const key = prologueMotionKey();
            if (key === lastUniverseMotionKey) return;
            lastUniverseMotionKey = key;
            if (prologueMotionLayer) {
                universeIdlePoseValid = false;
                paintUniverseMotionFrame(false);
                if (!universeMotionOverlay) {
                    universeHandoffToken += 1;
                    universeMotionOverlay = true;
                    prologueMotionLayer.setVisible(true);
                    clearUniverseEchartsData();
                    setUniverseHitLayerHidden(false);
                }
            }
            return;
        }
        finishUniverseToDialectHandoff();
        return;
    }
    const busy = prologueMotionBusy();
    const breathing = universeIdleBreathing();
    if (busy || !breathing) {
        universeIdleSince = 0;
        universeBreathMix = 0;
    } else {
        if (!universeIdleSince) universeIdleSince = now;
        universeBreathMix = smooth01((now - universeIdleSince) / 600);
    }
    universePaintNow = now;

    if (busy) {
        universeIdleEchartsPainted = false;
        const key = prologueMotionKey();
        if (key === lastUniverseMotionKey) return;
        lastUniverseMotionKey = key;
        if (prologueMotionLayer) {
            universeIdlePoseValid = false;
            paintUniverseMotionFrame(false);
            if (!universeMotionOverlay) {
                universeHandoffToken += 1;
                universeMotionOverlay = true;
                prologueMotionLayer.setVisible(true);
                clearUniverseEchartsData();
                setUniverseHitLayerHidden(false);
            }
        }
        syncCoverReveal();
        return;
    }

    if (!breathing) {
        if (universeMotionOverlay) {
            const token = universeHandoffToken;
            paintUniverseEcharts(() => {
                if (token !== universeHandoffToken || prologueMotionBusy()) return;
                hidePrologueMotionLayer();
            });
        } else if (particleChart) {
            paintUniverseEcharts();
        }
        syncCoverReveal();
        return;
    }

    const minDt = isMobileViewport() ? 50 : 42;
    if (lastUniverseIdlePaint && now - lastUniverseIdlePaint < minDt) {
        syncCoverReveal();
        return;
    }
    lastUniverseIdlePaint = now;

    if (prologueMotionLayer && !universeMotionOverlay) {
        universeMotionOverlay = true;
        prologueMotionLayer.setVisible(true);
    }
    paintUniverseMotionFrame(universeIdlePoseValid);
    universeIdlePoseValid = true;

    if (!universeIdleEchartsPainted && particleChart) {
        const mix = universeBreathMix;
        universeBreathMix = 0;
        if (prologueMotionLayer) setUniverseHitLayerHidden(true);
        paintUniverseEcharts();
        universeBreathMix = mix;
        universeIdleEchartsPainted = true;
    }
    syncCoverReveal();
}

function prologueMotionBusy() {
    if (prefersReducedMotion()) return false;
    if (prologueState === PROLOGUE_STATES.WORLD_MAP) {
        return prologueMotion.reveal < 0.999 || prologueMotion.fly < 0.999;
    }
    if (prologueState === PROLOGUE_STATES.STAR_FIELD) {
        if (universeExitHandoff) {
            return (performance.now() - universeHandoffT0) < DIALECT_HANDOFF_MS
                || prologueMotion.release < 0.999;
        }
        return prologueMotion.release < 0.999;
    }
    return prologueMotion.gather < 0.999;
}

function startUniverseLoop() {
    if (universeRaf) return;
    const tick = now => {
        universeRaf = 0;
        if (!universeCanvasActive()) return;
        if (!document.hidden) paintUniverseLive(now);
        if (universeCanvasActive() && (universeExitHandoff || prologueMotionBusy() || universeIdleBreathing())) {
            universeRaf = requestAnimationFrame(tick);
        }
    };
    universeRaf = requestAnimationFrame(tick);
}

function chinaLanguageScatter(rows, extraGuides = []) {
    const mandarin = summarize(rows.filter(isChinaMandarin));
    const dialect = summarize(rows.filter(isChinaDialect));
    const data = rows.map(d => [
        (isChinaDialect(d) ? 1 : 0) + d.jitterX * 0.55,
        d.rating,
        isChinaDialect(d) ? 3 : 2,
        d.id,
        1
    ]);
    return {
        backgroundColor: 'transparent',
        animationDurationUpdate: 2000,
        xAxis: {
            type: 'value', min: -0.6, max: 1.6, interval: 1, splitLine: { show: false },
            axisLine: { show: true, lineStyle: { color: 'rgba(255,255,255,0.3)' } },
            axisLabel: {
                formatter: val => {
                    const i = Math.round(val);
                    if (Math.abs(val - i) >= 0.1) return '';
                    return i === 0 ? '普通话' : i === 1 ? '方言' : '';
                },
                color: '#FFF', fontSize: 13, fontWeight: 'bold'
            }
        },
        yAxis: {
            type: 'value', min: sampleRatingExtent[0], max: sampleRatingExtent[1], splitLine: { show: false },
            axisLine: { show: true, lineStyle: { color: 'rgba(255,255,255,0.3)' } },
            axisLabel: { color: '#FFF' }
        },
        series: [{
            type: 'scatter',
            data,
            symbolSize: val => {
                if (val[2] !== 2 && val[2] !== 3) return 2;
                return val[4] ? 6 : 2;
            },
            itemStyle: {
                color: p => {
                    const code = p.value[2];
                    if (code === 3) return COLORS.dialect;
                    if (code === 2) return COLORS.chinaBlue;
                    return 'rgba(255, 255, 255, 0.08)';
                }
            },
            markLine: createGuideMarkLine([
                horizontalGuide(mandarin.n ? mandarin.mean : NaN, `普通话均值 ${mandarin.n ? mandarin.mean.toFixed(2) : '--'}`, GUIDE_COLORS.mandarin, 'insideEndTop'),
                horizontalGuide(dialect.n ? dialect.mean : NaN, `方言均值 ${dialect.n ? dialect.mean.toFixed(2) : '--'}`, GUIDE_COLORS.dialect, 'insideEndBottom'),
                verticalGuide(0.5, '两组分界', GUIDE_COLORS.selected),
                ...extraGuides
            ]),
            markArea: horizontalDifferenceBand(
                mandarin.n ? mandarin.mean : NaN,
                dialect.n ? dialect.mean : NaN,
                'rgba(255, 209, 102, 0.10)'
            ),
            universalTransition: true
        }]
    };
}

function languageStarfieldScene(rows) {
    const data = rows.map(d => [d.randX, d.randY, d.langCode, d.id, 1]);
    return {
        backgroundColor: 'transparent',
        animationDurationUpdate: 2000,
        xAxis: { show: false, min: 0, max: 100 },
        yAxis: { show: false, min: 0, max: 100 },
        series: [{
            type: 'scatter',
            data,
            symbolSize: 5,
            itemStyle: {
                color: p => {
                    const lang = p.value[2];
                    if (lang === 3) return 'rgba(255, 179, 0, 0.7)';
                    if (lang === 2) return 'rgba(98, 176, 255, 0.7)';
                    return 'rgba(255, 255, 255, 0.12)';
                }
            },
            universalTransition: true
        }]
    };
}

const particleScenes = {
    'universe': () => {
        const ar = universeChartAr();
        advancePrologueMotion(performance.now());
        const data = (prologueMotionBusy() || universeIdleBreathing()) ? [] : buildUniversePlot();
        return {
            backgroundColor: 'transparent',
            animation: false,
            animationDurationUpdate: 0,
            xAxis: { show: false, min: 0, max: 100 * ar },
            yAxis: { show: false, min: 0, max: 100 },
            series: [{
                _noDim: true,
                type: 'scatter',
                data,
                symbol: 'circle',
                symbolSize: 2,
                itemStyle: {},
                universalTransition: false
            }]
        };
    },
    'hollywood-entropy': () => {
        const selectedGenre = sceneState['hollywood-entropy'];
        const selectedRows = particleData.filter(row => selectedGenre === 'all' || row.genreCode === Number(selectedGenre));
        const northAmerica = summarize(selectedRows.filter(row => row.regionCode === 0));
        const otherRegions = summarize(selectedRows.filter(row => row.regionCode !== 0));
        const guides = [
            horizontalGuide(northAmerica.mean, `北美均值 ${northAmerica.mean.toFixed(2)}`, GUIDE_COLORS.northAmerica, 'insideEndTop'),
            horizontalGuide(otherRegions.mean, `其他地区均值 ${otherRegions.mean.toFixed(2)}`, GUIDE_COLORS.comparison, 'insideEndBottom')
        ];
        const focusedComparison = selectedGenre !== 'all';
        if (focusedComparison) guides.push(verticalGuide(4.5, '两组分界'));
        const spreadBands = selectedGenre === 'all' ? [] : [
            [
                {
                    xAxis: 3.6,
                    yAxis: northAmerica.mean - northAmerica.sd,
                    itemStyle: { color: 'rgba(84, 112, 198, 0.12)' }
                },
                { xAxis: 4.4, yAxis: northAmerica.mean + northAmerica.sd }
            ],
            [
                {
                    xAxis: 4.6,
                    yAxis: otherRegions.mean - otherRegions.sd,
                    itemStyle: { color: 'rgba(229, 57, 53, 0.09)' }
                },
                { xAxis: 5.4, yAxis: otherRegions.mean + otherRegions.sd }
            ]
        ];
        const data = (focusedComparison ? selectedRows : particleData).map(d => [
            focusedComparison ? (d.isHollywood ? 4 : 5) + d.jitterX : d.genreCode + d.jitterGenreX,
            d.rating,
            d.isHollywood ? 1 : 0,
            d.id,
            isSceneFocused(d)
        ]);
        return {
            backgroundColor: 'transparent',
            animationDurationUpdate: 2000,
            xAxis: { 
                type: 'value', min: -0.8, max: focusedComparison ? 5.8 : 6.8, interval: 1,
                splitLine: { show: false },
                axisLine: { show: true, lineStyle: { color: 'rgba(255,255,255,0.3)' } },
                axisLabel: { 
                    formatter: val => {
                        const i = Math.round(val);
                        if (Math.abs(val - i) >= 0.1) return '';
                        if (focusedComparison) return i === 4 ? '北美' : i === 5 ? '其他地区' : '';
                        return GENRE_AXIS_LABELS[i] || '';
                    },
                    color: '#FFF', fontSize: 13, fontWeight: 'bold'
                },
                name: '类型 (Genre)', nameTextStyle: { color: '#FFF', fontSize: 14 }
            },
            yAxis: { 
                type: 'value', min: sampleRatingExtent[0], max: sampleRatingExtent[1],
                splitLine: { show: false },
                axisLine: { show: true, lineStyle: { color: 'rgba(255,255,255,0.3)' } },
                axisLabel: { color: '#FFF' },
                name: '评分 (Rating)', nameTextStyle: { color: '#FFF', fontSize: 14 }
            },
            series: [{
                type: 'scatter',
                data: data,
                symbolSize: val => val[2] === 1 ? 5 : 3,
                itemStyle: { color: p => p.value[2] === 1 ? COLORS.hollywood : COLORS.asian },
                markLine: createGuideMarkLine(guides),
                markArea: spreadBands.length ? { silent: true, label: { show: false }, data: spreadBands } : undefined,
                universalTransition: true
            }]
        };
    },
    'asian-breakout': () => {
        const selectedRegion = Number(sceneState['asian-breakout']);
        const regionOrder = [0, 1, 2, 3, 4].filter(code => code !== selectedRegion).concat(selectedRegion);
        const regionPosition = code => regionOrder.indexOf(code);
        const selectedRows = particleData.filter(row => row.regionCode === selectedRegion);
        const regionStats = summarize(selectedRows);
        const standardized = standardizedMeanByDecadeGenre(selectedRows, particleData);
        const overallStats = summarize(particleData);
        const data = particleData.map(d => [regionPosition(d.regionCode) + d.jitterX, d.rating, d.regionCode, d.id, 1]);
        return {
            backgroundColor: 'transparent',
            animationDurationUpdate: 2000,
            xAxis: { 
                type: 'value', min: -1, max: 5, interval: 1, splitLine: { show: false },
                axisLine: { show: true, lineStyle: { color: 'rgba(255,255,255,0.3)' } },
                axisLabel: { 
                    formatter: val => {
                        const i = Math.round(val);
                        return Math.abs(val - i) < 0.1 ? REGIONS[regionOrder[i]] || '' : '';
                    },
                    color: '#FFF', fontSize: 14, fontWeight: 'bold'
                }
            },
            yAxis: { 
                type: 'value', min: sampleRatingExtent[0], max: sampleRatingExtent[1], splitLine: { show: false },
                axisLine: { show: true, lineStyle: { color: 'rgba(255,255,255,0.3)' } },
                axisLabel: { color: '#FFF' }
            },
            series: [{
                type: 'scatter',
                data: data,
                symbolSize: val => val[2] === 2 || val[2] === 3 ? 5 : 2,
                itemStyle: { 
                    color: p => {
                        const reg = p.value[2];
                        if (reg === 2 || reg === 3) return COLORS.asian; // 东亚 & 中国 (红)
                        if (reg === 0) return 'rgba(84, 112, 198, 0.35)'; // 北美 (暗蓝)
                        return 'rgba(255, 255, 255, 0.15)'; // 欧洲及其他
                    }
                },
                markLine: createGuideMarkLine([
                    horizontalGuide(regionStats.mean, `${REGION_LABELS[selectedRegion]}均值 ${regionStats.mean.toFixed(2)}`, GUIDE_COLORS.comparison, 'insideEndTop'),
                    horizontalGuide(standardized.mean, `标准化均值 ${standardized.mean.toFixed(2)}`, GUIDE_COLORS.standardized, 'insideStartBottom'),
                    horizontalGuide(overallStats.mean, `全部电影均值 ${overallStats.mean.toFixed(2)}`, GUIDE_COLORS.overall, 'insideEndBottom'),
                    verticalGuide(regionPosition(selectedRegion), `所选地区：${REGION_LABELS[selectedRegion]}`)
                ]),
                markArea: horizontalDifferenceBand(regionStats.mean, standardized.mean, 'rgba(92, 200, 161, 0.10)'),
                universalTransition: true
            }]
        };
    },
    'language-babel': () => {
        const selectedLanguage = Number(sceneState['language-babel']);
        const languageOrder = LANGUAGE_DISPLAY_ORDER.filter(code => code !== selectedLanguage).concat(selectedLanguage);
        const languagePosition = code => languageOrder.indexOf(code);
        const languageStats = summarize(particleData.filter(row => row.langCode === selectedLanguage));
        const overallStats = summarize(particleData);
        const data = particleData.map(d => [languagePosition(d.langCode) + d.jitterGenreX, d.rating, d.langCode, d.id, 1]);
        return {
            backgroundColor: 'transparent',
            animationDurationUpdate: 2000,
            xAxis: { 
                type: 'value', min: -0.8, max: 5.8, interval: 1, splitLine: { show: false },
                axisLine: { show: true, lineStyle: { color: 'rgba(255,255,255,0.3)' } },
                axisLabel: { 
                    formatter: val => {
                        const i = Math.round(val);
                        return Math.abs(val - i) < 0.1 ? LANGUAGE_LABELS[languageOrder[i]] || '' : '';
                    },
                    color: '#FFF', fontSize: 13, fontWeight: 'bold'
                }
            },
            yAxis: { 
                type: 'value', min: sampleRatingExtent[0], max: sampleRatingExtent[1], splitLine: { show: false },
                axisLine: { show: true, lineStyle: { color: 'rgba(255,255,255,0.3)' } },
                axisLabel: { color: '#FFF' }
            },
            series: [{
                type: 'scatter',
                data: data,
                symbolSize: val => val[2] === selectedLanguage ? 6 : 3,
                itemStyle: { 
                    color: p => LANGUAGE_COLORS[p.value[2]] || 'rgba(255, 255, 255, 0.15)'
                },
                markLine: createGuideMarkLine([
                    horizontalGuide(languageStats.mean, `${LANGUAGE_LABELS[selectedLanguage]}均值 ${languageStats.mean.toFixed(2)}`, GUIDE_COLORS.comparison, 'insideEndTop'),
                    horizontalGuide(overallStats.mean, `全部电影均值 ${overallStats.mean.toFixed(2)}`, GUIDE_COLORS.overall, 'insideEndBottom'),
                    verticalGuide(languagePosition(selectedLanguage), `所选组：${LANGUAGE_LABELS[selectedLanguage]}`)
                ]),
                universalTransition: true
            }]
        };
    },
    'european-slow': () => {
        const selectedRegion = Number(sceneState['european-slow']);
        const regionOrder = [0, 1, 2, 3, 4].filter(code => code !== selectedRegion).concat(selectedRegion);
        const regionPosition = code => regionOrder.indexOf(code);
        const regionStats = summarize(particleData.filter(row => row.regionCode === selectedRegion));
        const data = particleData.map(d => [regionPosition(d.regionCode) + d.jitterX, d.rating, d.regionCode, d.id, 1]);
        return {
            backgroundColor: 'transparent',
            animationDurationUpdate: 2000,
            xAxis: { 
                type: 'value', min: -1, max: 5, interval: 1, splitLine: { show: false },
                axisLine: { show: true, lineStyle: { color: 'rgba(255,255,255,0.3)' } },
                axisLabel: { 
                    formatter: val => {
                        const i = Math.round(val);
                        return Math.abs(val - i) < 0.1 ? REGIONS[regionOrder[i]] || '' : '';
                    },
                    color: '#FFF', fontSize: 14, fontWeight: 'bold'
                }
            },
            yAxis: { 
                type: 'value', min: sampleRatingExtent[0], max: sampleRatingExtent[1], splitLine: { show: false },
                axisLine: { show: true, lineStyle: { color: 'rgba(255,255,255,0.3)' } },
                axisLabel: { color: '#FFF' }
            },
            series: [{
                type: 'scatter',
                data: data,
                symbolSize: val => val[2] === selectedRegion ? 6 : 2,
                itemStyle: { 
                    color: p => p.value[2] === selectedRegion ? COLORS.selectedRegion : 'rgba(255, 255, 255, 0.12)'
                },
                markLine: createGuideMarkLine([
                    horizontalGuide(regionStats.q1, `${REGION_LABELS[selectedRegion]} Q1 ${regionStats.q1.toFixed(2)}`, GUIDE_COLORS.q1, 'insideEndBottom'),
                    horizontalGuide(regionStats.median, `${REGION_LABELS[selectedRegion]}中位数 ${regionStats.median.toFixed(2)}`, GUIDE_COLORS.median, 'insideEndTop'),
                    horizontalGuide(5, '不到 5 分', GUIDE_COLORS.threshold, 'insideEndTop'),
                    verticalGuide(regionPosition(selectedRegion), `所选地区：${REGION_LABELS[selectedRegion]}`)
                ]),
                markArea: horizontalDifferenceBand(regionStats.q1, regionStats.median, 'rgba(92, 200, 161, 0.10)'),
                universalTransition: true
            }]
        };
    },
    'chinese-dialect': () => {
        const selectedPeriod = sceneState['chinese-dialect'];
        const selectedRows = particleData.filter(row => SCENE_INTERACTIONS['chinese-dialect'].filter(row, selectedPeriod));
        return chinaLanguageScatter(selectedRows);
    },
    'china-2010s': () => chinaLanguageScatter(
        particleData.filter(row => isChinaLanguagePair(row) && decadeOf(row.year) === '2010s')
    ),
    'china-below5': () => chinaLanguageScatter(
        particleData.filter(isChinaLanguagePair),
        [{
            ...horizontalGuide(5, '不到 5 分', GUIDE_COLORS.threshold, 'insideEndTop'),
            type: 'solid',
            width: 2.2,
            opacity: 1
        }]
    ),
    'dual-director': () => {
        const selected = sceneState['dual-director'];
        const selectedRows = particleData.filter(row => SCENE_INTERACTIONS['dual-director'].filter(row, selected));
        const mandarin = summarize(selectedRows.filter(isChinaMandarin));
        const dialect = summarize(selectedRows.filter(isChinaDialect));
        const dualOrder = selected === '2' ? [3, 2] : [2, 3];
        const dualX = code => dualOrder.indexOf(code);
        const data = selectedRows.map(d => {
            const code = isChinaDialect(d) ? 3 : 2;
            return [dualX(code) + d.jitterX * 0.55, d.rating, code, d.id, 1];
        });
        const dialectGuide = selected === '2' ? NaN : (dialect.n ? dialect.mean : NaN);
        const mandarinGuide = selected === '3' ? NaN : (mandarin.n ? mandarin.mean : NaN);
        return {
            backgroundColor: 'transparent',
            animationDurationUpdate: 2000,
            xAxis: {
                type: 'value', min: -0.6, max: 1.6, interval: 1, splitLine: { show: false },
                axisLine: { show: true, lineStyle: { color: 'rgba(255,255,255,0.3)' } },
                axisLabel: {
                    formatter: val => {
                        const i = Math.round(val);
                        if (Math.abs(val - i) >= 0.1) return '';
                        return i === 0 || i === 1
                            ? (dualOrder[i] === 2 ? '普通话' : '方言')
                            : '';
                    },
                    color: '#FFF', fontSize: 13, fontWeight: 'bold'
                }
            },
            yAxis: {
                type: 'value', min: sampleRatingExtent[0], max: sampleRatingExtent[1], splitLine: { show: false },
                axisLine: { show: true, lineStyle: { color: 'rgba(255,255,255,0.3)' } },
                axisLabel: { color: '#FFF' }
            },
            series: [{
                type: 'scatter',
                data: data,
                symbolSize: val => {
                    if (val[2] !== 2 && val[2] !== 3) return 1.5;
                    return val[4] ? 6 : 2.4;
                },
                itemStyle: {
                    color: p => {
                        const code = p.value[2];
                        const focused = p.value[4];
                        if (code === 3) return focused ? COLORS.dialect : 'rgba(255, 209, 102, 0.18)';
                        if (code === 2) return focused ? COLORS.chinaBlue : 'rgba(98, 176, 255, 0.16)';
                        return 'rgba(255, 255, 255, 0.04)';
                    }
                },
                markLine: createGuideMarkLine([
                    horizontalGuide(mandarinGuide, `普通话均值 ${mandarin.n ? mandarin.mean.toFixed(2) : '--'}`, GUIDE_COLORS.mandarin, 'insideEndTop'),
                    horizontalGuide(dialectGuide, `方言均值 ${dialect.n ? dialect.mean.toFixed(2) : '--'}`, GUIDE_COLORS.dialect, 'insideEndBottom'),
                    verticalGuide(0.5, '两组分界', GUIDE_COLORS.selected)
                ]),
                markArea: horizontalDifferenceBand(mandarinGuide, dialectGuide, 'rgba(255, 209, 102, 0.10)'),
                universalTransition: true
            }]
        };
    },
    'global-layers': () => {
        const phase = globalLayersPhase || 'pull-back';
        const compact = window.innerWidth <= 700;
        const showThreshold = phase !== 'pull-back';
        const layerGroups = phase === 'boundary' ? BOUNDARY_LAYER_GROUPS : GLOBAL_LAYER_GROUPS;
        const data = particleData.flatMap(d => {
            const group = globalLayerOf(d);
            if (phase === 'four-groups' && (group === 4 || group < 0)) return [];
            return [[globalLayerX(d, group, phase), d.rating, group, d.id, 1]];
        });
        const names = compact
            ? layerGroups.map(group => group.short)
            : layerGroups.map(group => group.label);
        const rates = layerGroups.map(group => globalLayerRate(group.jsonName, group.fallback));
        const labelAt = i => {
            if (!names[i]) return '';
            if (phase === 'axes') return names[i];
            return `${names[i]}\n${rates[i]}`;
        };
        const guides = showThreshold
            ? [{
                ...horizontalGuide(5, '5 分线', GUIDE_COLORS.threshold, 'insideEndTop'),
                type: 'solid',
                width: 2,
                opacity: 1
            }]
            : [];
        return {
            backgroundColor: 'transparent',
            animationDurationUpdate: 1100,
            xAxis: {
                type: 'value',
                min: phase === 'pull-back' ? -0.8 : -0.7,
                max: globalLayerXMax(phase),
                interval: phase === 'mandarin-outlier' ? OUTLIER_COLUMN_X[1] : 1,
                splitLine: { show: false },
                axisLine: { show: true, lineStyle: { color: 'rgba(255,255,255,0.28)' } },
                axisLabel: {
                    hideOverlap: true,
                    color: '#FFF',
                    fontSize: compact ? 10 : 12,
                    fontWeight: 'bold',
                    lineHeight: 16,
                    rotate: compact ? 30 : 0,
                    formatter: val => {
                        if (phase === 'pull-back') {
                            const i = Math.round(val);
                            if (Math.abs(val - i) >= 0.1 || i < 0 || i > 5) return '';
                            return LANGUAGE_LABELS[LANGUAGE_DISPLAY_ORDER[i]] || '';
                        }
                        if (phase === 'mandarin-outlier') {
                            const idx = OUTLIER_COLUMN_X.findIndex(x => Math.abs(val - x) < 0.08);
                            return idx < 0 ? '' : labelAt(idx);
                        }
                        const i = Math.round(val);
                        if (Math.abs(val - i) >= 0.1 || i < 0) return '';
                        if (phase === 'four-groups' && i >= 4) return '';
                        if (phase === 'boundary' && i > 5) return '';
                        if (phase !== 'boundary' && i > 4) return '';
                        return labelAt(i);
                    }
                },
                name: '语言组',
                nameTextStyle: { color: 'rgba(255,255,255,0.55)', fontSize: 12 }
            },
            yAxis: {
                type: 'value',
                min: 0,
                max: 10,
                interval: 1,
                splitLine: { show: true, lineStyle: { color: 'rgba(255,255,255,0.04)', width: 1 } },
                axisLine: { show: true, lineStyle: { color: 'rgba(255,255,255,0.28)' } },
                axisLabel: { color: '#FFF' },
                name: '豆瓣评分',
                nameTextStyle: { color: '#E2E2E2', fontSize: 12 }
            },
            series: [{
                type: 'scatter',
                data,
                symbolSize: val => {
                    const group = val[2];
                    const movie = particleData[val[3]];
                    const northAmerica = movie && isNorthAmericaEnglish(movie);
                    if (phase === 'pull-back') {
                        return movie && (movie.langCode === 2 || movie.langCode === 3) ? 4 : 2;
                    }
                    if (phase === 'four-groups') {
                        return (group === 4 || group < 0) ? 0 : 2.8;
                    }
                    if (phase === 'boundary') {
                        if (group < 0 && !northAmerica) return 1.5;
                        return 2.4;
                    }
                    if (group < 0) return 1.5;
                    if (phase === 'mandarin-outlier' && group === 4) return 2.4;
                    if (phase === 'mandarin-outlier') return 2.1;
                    return 2.8;
                },
                itemStyle: {
                    color: p => {
                        const group = p.value[2];
                        const movie = particleData[p.value[3]];
                        const below = p.value[1] < 5;
                        const northAmerica = movie && isNorthAmericaEnglish(movie);
                        if (phase === 'pull-back') {
                            if (movie && movie.langCode === 3) return COLORS.dialect;
                            if (movie && movie.langCode === 2) return COLORS.chinaBlue;
                            return 'rgba(255, 255, 255, 0.08)';
                        }
                        if (phase === 'four-groups') {
                            if (group === 4 || group < 0) return 'rgba(0, 0, 0, 0)';
                            if (group === 3) return 'rgba(255, 179, 0, 0.55)';
                            return 'rgba(255, 255, 255, 0.38)';
                        }
                        if (phase === 'mandarin-outlier') {
                            if (group < 0) return 'rgba(255, 255, 255, 0.05)';
                            if (group === 4) {
                                return below ? 'rgba(98, 176, 255, 0.42)' : 'rgba(98, 176, 255, 0.26)';
                            }
                            return group === 3 ? 'rgba(255, 179, 0, 0.28)' : 'rgba(255, 255, 255, 0.14)';
                        }
                        if (phase === 'boundary') {
                            if (northAmerica) return 'rgba(132, 164, 214, 0.50)';
                            if (group < 0) return 'rgba(255, 255, 255, 0.05)';
                            if (group === 4) return 'rgba(98, 176, 255, 0.55)';
                            if (group === 3) return 'rgba(255, 179, 0, 0.55)';
                            return 'rgba(255, 255, 255, 0.38)';
                        }
                        if (group < 0) return 'rgba(255, 255, 255, 0.05)';
                        if (group === 4) return 'rgba(98, 176, 255, 0.55)';
                        if (group === 3) return 'rgba(255, 179, 0, 0.55)';
                        return 'rgba(255, 255, 255, 0.38)';
                    }
                },
                markLine: createGuideMarkLine(guides),
                universalTransition: true
            }]
        };
    },
    'final-universe': () => languageStarfieldScene(particleData),
    'china-dialect-stars': () => languageStarfieldScene(particleData.filter(isStorySpanDialect)),
    'wave-hk': () => languageStarfieldScene(particleData.filter(row => isHkDialect(row) && inYearRange(row, 1985, 2005))),
    'mandarin-gap': () => languageStarfieldScene(particleData.filter(row => isMainlandDialect(row) && inYearRange(row, 2000, 2010))),
    'three-waves': () => languageStarfieldScene(particleData.filter(isLaterWaveDialect)),
    'china-2020s': () => languageStarfieldScene(particleData.filter(row => isChinaDialect(row) && decadeOf(row.year) === '2020s')),
    'china-high8': () => languageStarfieldScene(particleData.filter(row => isChinaDialect(row) && Number(row.rating) >= 8)),
    'dialect-flops': () => {
        const phase = resolveFlopPhase(flopPhase);
        const data = particleData.filter(row => isFlopLit(row, phase)).map(row => [
            dialectFlopX(row, phase),
            row.rating,
            dialectFlopRole(row),
            row.id,
            1
        ]);
        const guides = [{
            ...horizontalGuide(5, '方言片低分线', GUIDE_COLORS.threshold, 'insideEndTop'),
            type: 'solid',
            width: 2.2,
            opacity: 1
        }];
        return {
            backgroundColor: 'transparent',
            animationDurationUpdate: 1100,
            xAxis: {
                type: 'value',
                min: -0.15,
                max: 4.2,
                interval: 1,
                splitLine: { show: false },
                axisLine: { show: true, lineStyle: { color: 'rgba(255,255,255,0.22)' } },
                axisLabel: {
                    color: '#FFF',
                    fontSize: 12,
                    fontWeight: 'bold',
                    formatter: val => (Math.abs(val - 2) < 0.08 ? '方言电影内部' : '')
                },
                name: '方言电影内部',
                nameTextStyle: { color: 'rgba(255,255,255,0.55)', fontSize: 12 }
            },
            yAxis: {
                type: 'value',
                min: 0,
                max: 10,
                interval: 1,
                splitLine: {
                    show: true,
                    lineStyle: { color: 'rgba(255,255,255,0.04)', width: 1 }
                },
                axisLine: { show: true, lineStyle: { color: 'rgba(255,255,255,0.22)' } },
                axisLabel: { color: '#FFF' },
                name: '豆瓣评分',
                nameTextStyle: { color: '#E2E2E2', fontSize: 12 }
            },
            series: [{
                type: 'scatter',
                data,
                _noDim: true,
                symbolSize: val => {
                    if (!val || val[4] === 0) return 0;
                    const role = val[2];
                    if (phase === 'cases') {
                        if (role === 3) return 9;
                        if (role === 2) return 3.4;
                        return 2.2;
                    }
                    if (phase === 'flopsOnly') return role === 3 ? 6.5 : 4.2;
                    if (phase === 'tail') return (role === 2 || role === 3) ? 4.4 : 2.1;
                    return (role === 2 || role === 3) ? 3.4 : 2.8;
                },
                itemStyle: {
                    color: p => {
                        if (!p.value || p.value[4] === 0) return 'rgba(0,0,0,0)';
                        const role = p.value[2];
                        if (phase === 'cases' && role === 3) return 'rgba(232, 176, 88, 0.95)';
                        if (phase === 'tail' || phase === 'flopsOnly') {
                            if (role === 2 || role === 3) return 'rgba(214, 98, 92, 0.86)';
                            return 'rgba(176, 132, 72, 0.2)';
                        }
                        if (role === 2 || role === 3) return 'rgba(196, 118, 86, 0.76)';
                        return 'rgba(176, 132, 72, 0.36)';
                    }
                },
                markLine: createGuideMarkLine(guides),
                universalTransition: true
            }]
        };
    }
};
particleScenes['scale'] = particleScenes['final-universe'];
particleScenes['echo-narrative'] = particleScenes['china-dialect-stars'];

function renderParticleScene(sceneId, { animate, skipHandoff } = {}) {
    const previousSceneId = runtime.activeSceneId;
    runtime.activeSceneId = sceneId;
    if (universeExitHandoff && sceneId !== 'china-dialect-stars') {
        universeExitHandoff = false;
    }
    if (universeExitHandoff && sceneId === 'china-dialect-stars') {
        lastUniverseMotionKey = '';
        paintUniverseLive();
        startUniverseLoop();
        return;
    }
    if (!skipHandoff && shouldPlayCoverToIntroHandoff({
        sceneId,
        fromSceneId: previousSceneId,
        prologueState,
        reducedMotion: prefersReducedMotion()
    })) {
        universeExitHandoff = true;
        universeHandoffT0 = performance.now();
        setPrologueState(PROLOGUE_STATES.STAR_FIELD);
        prologueMotion.t0 = universeHandoffT0;
        prologueMotion.release = 0;
        return;
    }
    if (sceneId !== 'universe') {
        setUniverseHitLayerHidden(false);
        if (universeRaf) {
            cancelAnimationFrame(universeRaf);
            universeRaf = 0;
        }
    }
    const chartDom = document.getElementById('chart-container');
    if (chartDom) {
        if (chartDom.dataset.echoLayer) delete chartDom.dataset.echoLayer;
        if (!chartDom.dataset.waveLayer) chartDom.style.opacity = '1';
    }
    if(!particleChart || !particleScenes[sceneId]) return;
    const option = particleScenes[sceneId]();
    const wantMotion = animate !== false;
    const largeDataset = particleData.length > 20000;
    const reducedMotion = window.innerWidth <= 700
        || window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    const compactMotion = reducedMotion || largeDataset;
    const isUniverse = isStarfieldScene(sceneId);
    const isGlobalLayers = sceneId === 'global-layers';
    const isDialectFlops = sceneId === 'dialect-flops';
    option.animation = !(largeDataset && !isUniverse);
    if (!isUniverse || !option.animationDurationUpdate) {
        option.animationDurationUpdate = compactMotion ? 0 : 420;
    }
    if ((isGlobalLayers || isDialectFlops) && !reducedMotion && wantMotion) {
        option.animation = true;
        option.animationDurationUpdate = 1100;
    }
    option.animationEasingUpdate = 'cubicOut';
    if (sceneId === 'universe') {
        option.animation = false;
        option.animationDurationUpdate = 0;
    }
    if (!wantMotion) {
        option.animation = false;
        option.animationDurationUpdate = 0;
    }
    const hasVisibleAxes = !isUniverse;
    option.grid = hasVisibleAxes
        ? { left: 8, right: 8, top: 8, bottom: 8, containLabel: false }
        : { left: 0, right: 0, top: 0, bottom: 0, containLabel: false };
    if (isGlobalLayers) {
        option.grid = {
            left: 28,
            right: 18,
            top: 22,
            bottom: window.innerWidth <= 700 ? 78 : 56,
            containLabel: false
        };
    }
    if (isDialectFlops) {
        option.grid = {
            left: window.innerWidth <= 700 ? 28 : '16%',
            right: window.innerWidth <= 700 ? 18 : '7%',
            top: 22,
            bottom: window.innerWidth <= 700 ? 78 : 56,
            containLabel: false
        };
    }
    if (hasVisibleAxes) {
        // Labels sit inside the viewport, so the data field itself remains
        // full-bleed and no rectangular plot island is visible.
        [option.xAxis, option.yAxis].forEach(axis => {
            if (!axis) return;
            axis.name = '';
            axis.axisTick = { show: false };
            axis.axisLabel = {
                ...(axis.axisLabel || {}),
                inside: true,
                margin: 8,
                fontSize: window.innerWidth <= 700 ? 10 : 12,
                hideOverlap: true
            };
        });
    }
    if ((isGlobalLayers || isDialectFlops) && option.xAxis && option.yAxis) {
        option.xAxis.name = isDialectFlops ? '方言电影内部' : '语言组';
        option.xAxis.nameLocation = 'middle';
        option.xAxis.nameGap = window.innerWidth <= 700 ? 30 : 20;
        option.xAxis.nameTextStyle = { color: 'rgba(255,255,255,0.5)', fontSize: 11, fontFamily: 'Noto Sans SC, sans-serif' };
        option.xAxis.axisLabel.inside = true;
        option.xAxis.axisLabel.hideOverlap = false;
        option.xAxis.axisLabel.margin = 8;
        option.xAxis.axisLabel.backgroundColor = 'rgba(5, 5, 7, 0.72)';
        option.xAxis.axisLabel.padding = [3, 5];
        option.xAxis.axisLabel.borderRadius = 3;
        option.yAxis.name = '豆瓣评分';
        option.yAxis.nameLocation = 'end';
        option.yAxis.nameGap = 8;
        option.yAxis.nameTextStyle = { color: '#E2E2E2', fontSize: 12, fontFamily: 'Noto Sans SC, sans-serif' };
    }
    const series = option.series && option.series[0];
    if (series) {
        series.universalTransition = sceneId === 'universe' || !wantMotion
            ? false
            : ((isGlobalLayers || isDialectFlops) ? !reducedMotion : !compactMotion);
        series.progressive = sceneId === 'universe' ? 0 : (largeDataset ? 6000 : 0);
        series.progressiveThreshold = largeDataset ? 5000 : 3000;
        series.progressiveChunkMode = 'mod';
        if (sceneId === 'universe') {
            series.itemStyle = series.itemStyle || {};
            series.emphasis = {
                scale: 1.35,
                itemStyle: { borderColor: '#FFFFFF', borderWidth: 1 }
            };
        } else {
            const originalColor = series.itemStyle && series.itemStyle.color;
            const originalSize = series.symbolSize;
            const unfocusedColor = series.unfocusedColor || 'rgba(255, 255, 255, 0.09)';
            const unfocusedSize = Number.isFinite(Number(series.unfocusedSize))
                ? Number(series.unfocusedSize)
                : (largeDataset ? 0.8 : 1.5);
            delete series.unfocusedColor;
            delete series.unfocusedSize;
            series.itemStyle = series.itemStyle || {};
            series.itemStyle.color = params => {
                if (!series._noDim && params.value && params.value[4] === 0) return unfocusedColor;
                return typeof originalColor === 'function' ? originalColor(params) : originalColor;
            };
            series.symbolSize = value => {
                if (value && value[4] === 0) return isDialectFlops ? 0 : unfocusedSize;
                const size = typeof originalSize === 'function' ? originalSize(value) : originalSize;
                if (series._noDim || isGlobalLayers || isDialectFlops || isUniverse) return size;
                return largeDataset ? Math.max(1.2, Math.min(3.2, Number(size) * 0.64)) : size;
            };
            series.emphasis = isDialectFlops
                ? { scale: 1.35, itemStyle: { borderColor: 'rgba(255,255,255,0.4)', borderWidth: 1, shadowBlur: 0 } }
                : {
                    scale: largeDataset ? 1.35 : 2.2,
                    itemStyle: { borderColor: '#FFFFFF', borderWidth: 1, shadowBlur: 16, shadowColor: 'rgba(255,255,255,0.65)' }
                };
        }
    }
    option.tooltip = {
        trigger: 'item',
        confine: true,
        backgroundColor: 'rgba(5, 5, 7, 0.94)',
        borderColor: 'rgba(255,255,255,0.2)',
        textStyle: { color: '#FFFFFF', fontFamily: 'Noto Sans SC, sans-serif' },
        formatter: params => {
            const raw = params.value;
            if (isDialectFlops && raw && raw[4] === 0) return '';
            const movie = particleData[raw && raw[3]];
            if (!movie) return '';
            return `<strong style="font-size:14px">${escapeHtml(movie.title)}</strong><br>`
                + `${movie.year} · ${movie.rating.toFixed(1)} 分 · ${Number(movie.votes || 0).toLocaleString('zh-CN')} 人评价<br>`
                + `${REGION_LABELS[movie.regionCode] || '未知地区'} · ${LANGUAGE_LABELS[movie.langCode] || '未知语言组'}`;
        }
    };
    particleChart.setOption(option, true);
    rememberPlottedSeries(option.series);
    runtime.renderParticleScene = renderParticleScene;
    if (sceneId === 'universe') {
        lastUniverseMotionKey = '';
        resetUniverseIdlePaint();
        paintUniverseLive();
        startUniverseLoop();
    } else {
        if (universeRaf) {
            cancelAnimationFrame(universeRaf);
            universeRaf = 0;
        }
        universeHandoffToken += 1;
        if (skipHandoff && universeMotionOverlay) {
            requestAnimationFrame(() => {
                requestAnimationFrame(() => hidePrologueMotionLayer());
            });
        } else {
            hidePrologueMotionLayer();
        }
    }
    if (isDialectFlops) {
        scheduleFlopOverlay((reducedMotion || !wantMotion) ? 0 : 1100);
    }
}

function bindMovieDetailDialog() {
    const dialog = document.getElementById('movie-detail-dialog');
    if (!dialog || dialog.dataset.bound) return;
    dialog.dataset.bound = '1';
    dialog.addEventListener('click', event => {
        if (event.target === dialog) dialog.close();
    });
}

function maybeCountSceneStats(step) {
    if (!step) return;
    if (step.id === 'step-8b') {
        const el = document.getElementById('gl-mandarin-outlier');
        const numeric = parseFloat(String(el && el.textContent).replace('%', ''));
        if (el && Number.isFinite(numeric)) window.StoryUI.animateCount(el, el.textContent, numeric);
    }
}

function setTextById(id, value) {
    const node = document.getElementById(id);
    if (!node) return;
    node.textContent = value;
    // 首屏骨架屏：数字填入后撤掉 pending 灰条，触发淡入。
    if (node.classList.contains('is-pending')) node.classList.remove('is-pending');
}

function medianOf(values) {
    if (!values.length) return null;
    const sorted = [...values].sort((a, b) => a - b);
    const mid = Math.floor(sorted.length / 2);
    return sorted.length % 2 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2;
}

function getWorldScaleRungs() {
    const regions = narrativeFacts && narrativeFacts.regions;
    const raw = dialectAgg && dialectAgg.type_controlled && dialectAgg.type_controlled.raw;
    if (!regions || !regions['中国大陆'] || !regions['其他'] || !regions['北美'] || !regions['东亚'] || !regions['欧洲'] || !raw || !raw.d) {
        return null;
    }
    const dialectMed = narrativeFacts.mandarin_dialect && narrativeFacts.mandarin_dialect.dialect_mixed
        ? narrativeFacts.mandarin_dialect.dialect_mixed.median
        : null;
    return [
        { key: 'cn', name: '中国电影整体', score: Number(regions['中国大陆'].mean), med: Number(regions['中国大陆'].median), n: regions['中国大陆'].n, color: '#837C6E', note: '含普通话量产大片。这是流水线逻辑下的基线。' },
        { key: 'dia', name: '方言片', score: Number(raw.d.mean), med: dialectMed, n: raw.d.n, color: '#d4a574', isKey: true, note: '语言层切片。这是我们最好的成绩；烂片率仅 6.4%。' },
        { key: 'oth', name: '其他地区', score: Number(regions['其他'].mean), med: Number(regions['其他'].median), n: regions['其他'].n, color: '#9A938A', note: '拉美、非洲、大洋洲等混装样本较小，仅供参考。' },
        { key: 'na', name: '北美', score: Number(regions['北美'].mean), med: Number(regions['北美'].median), n: regions['北美'].n, color: '#7A5D82', note: '英语世界的工业中心，均分并不是最高。' },
        { key: 'ea', name: '日韩', score: Number(regions['东亚'].mean), med: Number(regions['东亚'].median), n: regions['东亚'].n, color: '#4F8F86', note: '东亚近邻。高分样本多为演出实录，看中位数更稳。' },
        { key: 'eu', name: '欧洲', score: Number(regions['欧洲'].mean), med: Number(regions['欧洲'].median), n: regions['欧洲'].n, color: '#6B5F8A', note: '当前最高的一级，作者电影的另一个大本营。' }
    ];
}

function spreadScalePositions(linearYMap, keys, minGap = 9, bounds = { top: 8, bottom: 92 }) {
    const ordered = [...keys].sort((a, b) => linearYMap[a] - linearYMap[b]);
    const ys = ordered.map(key => linearYMap[key]);

    for (let i = 1; i < ys.length; i += 1) {
        if (ys[i] - ys[i - 1] < minGap) ys[i] = ys[i - 1] + minGap;
    }
    if (ys[ys.length - 1] > bounds.bottom) {
        const overflow = ys[ys.length - 1] - bounds.bottom;
        for (let i = 0; i < ys.length; i += 1) ys[i] -= overflow;
    }
    if (ys[0] < bounds.top) {
        const underflow = bounds.top - ys[0];
        for (let i = 0; i < ys.length; i += 1) ys[i] += underflow;
    }
    for (let i = ys.length - 2; i >= 0; i -= 1) {
        if (ys[i + 1] - ys[i] < minGap) ys[i] = ys[i + 1] - minGap;
    }

    return Object.fromEntries(ordered.map((key, i) => [key, ys[i]]));
}

function spreadScaleValues(values, minGap = 5, bounds = { top: 8, bottom: 92 }) {
    const ys = [...values];
    for (let i = 1; i < ys.length; i += 1) {
        if (ys[i] - ys[i - 1] < minGap) ys[i] = ys[i - 1] + minGap;
    }
    if (ys[ys.length - 1] > bounds.bottom) {
        const overflow = ys[ys.length - 1] - bounds.bottom;
        for (let i = 0; i < ys.length; i += 1) ys[i] -= overflow;
    }
    for (let i = ys.length - 2; i >= 0; i -= 1) {
        if (ys[i + 1] - ys[i] < minGap) ys[i] = ys[i + 1] - minGap;
    }
    return ys;
}

function hexRgba(hex, alpha) {
    if (!hex || hex.charAt(0) !== '#') return `rgba(200,194,180,${alpha})`;
    const n = parseInt(hex.slice(1), 16);
    if (!Number.isFinite(n)) return `rgba(200,194,180,${alpha})`;
    return `rgba(${(n >> 16) & 255},${(n >> 8) & 255},${n & 255},${alpha})`;
}

function getWorldScaleLayout() {
    const rungs = getWorldScaleRungs();
    if (!rungs) return null;
    const shown = Object.fromEntries(rungs.map(rung => [rung.key, Number(rung.score.toFixed(2))]));
    const scores = rungs.map(rung => shown[rung.key]);
    const top = Math.max(...scores) + 0.15;
    const bot = Math.min(...scores) - 0.13;
    const yPct = score => ((top - score) / (top - bot)) * 100;
    const keys = rungs.map(rung => rung.key);
    const linearY = Object.fromEntries(keys.map(key => [key, yPct(shown[key])]));
    return { rungs, shown, keys, spreadY: spreadScalePositions(linearY, keys) };
}

function fillWorldScale() {
    const layout = getWorldScaleLayout();
    const rungsEl = document.getElementById('world-scale-rungs');
    if (!layout || !rungsEl) return;

    const { rungs, shown, spreadY } = layout;
    const plus = value => `+${Math.abs(value).toFixed(2)}`;
    rungsEl.innerHTML = rungs.map(rung => {
        const score = shown[rung.key];
        const tag = rung.isKey ? '<span class="tagline">我们最好的成绩</span>' : '';
        return `<button type="button" class="world-scale-rung" style="--y:${spreadY[rung.key].toFixed(2)}%;--c:${rung.color};--c-bg:${hexRgba(rung.color, 0.16)}" data-key="${rung.key}" data-name="${escapeHtml(rung.name)}" data-score="${score.toFixed(2)}" data-med="${Number.isFinite(Number(rung.med)) ? Number(rung.med).toFixed(1) : ''}" data-n="${Number(rung.n).toLocaleString('zh-CN')}" data-note="${escapeHtml(rung.note)}" aria-label="${escapeHtml(rung.name)} 均分 ${score.toFixed(2)}">
            <span class="guide"></span><span class="bloom"></span><span class="tick"></span>
            <span class="who">${escapeHtml(rung.name)}</span>
            <span class="score">0.00</span>${tag}
        </button>`;
    }).join('');

    const premium = shown.dia - shown.cn;
    const remain = shown.eu - shown.dia;
    const step1 = shown.oth - shown.dia;
    const step2 = shown.na - shown.oth;
    const step3 = shown.ea - shown.na;
    const step4 = shown.eu - shown.ea;
    const premiumEl = document.getElementById('scale-gap-premium');
    const remainEl = document.getElementById('scale-gap-remain');
    if (premiumEl) {
        premiumEl.style.top = `${spreadY.dia.toFixed(2)}%`;
        premiumEl.style.height = `${(spreadY.cn - spreadY.dia).toFixed(2)}%`;
    }
    if (remainEl) {
        remainEl.style.top = `${spreadY.eu.toFixed(2)}%`;
        remainEl.style.height = `${(spreadY.dia - spreadY.eu).toFixed(2)}%`;
    }
    const dcPairs = [
        ['dia', 'oth', step1],
        ['oth', 'na', step2],
        ['na', 'ea', step3],
        ['ea', 'eu', step4]
    ];
    const dcYs = spreadScaleValues(dcPairs.map(([a, b]) => (spreadY[a] + spreadY[b]) / 2), 5);
    dcPairs.forEach(([, , delta], i) => {
        const dc = document.getElementById(`scale-dc-${i}`);
        if (!dc) return;
        dc.textContent = `+${Math.abs(delta).toFixed(2)}`;
        dc.style.top = `${dcYs[i].toFixed(2)}%`;
    });

    const sampleN = narrativeFacts.sample && narrativeFacts.sample.n
        ? narrativeFacts.sample.n
        : narrativeFacts.meta && narrativeFacts.meta.record_count;
    if (sampleN) setTextById('scale-n', Number(sampleN).toLocaleString('zh-CN'));
    setTextById('scale-cn', shown.cn.toFixed(2));
    setTextById('scale-premium', plus(premium));
    setTextById('scale-premium-mark', plus(premium));
    setTextById('scale-remain', Math.abs(remain).toFixed(2));
    setTextById('scale-remain-mark', `−${Math.abs(remain).toFixed(2)}`);
    setTextById('scale-step1', Math.abs(step1).toFixed(2));
    setTextById('scale-step2', Math.abs(step2).toFixed(2));
    setTextById('scale-gap-eu', Math.abs(step1).toFixed(2));
    setTextById('scale-gap-na', Math.abs(step2).toFixed(2));
    setTextById('scale-median-chain', rungs.map(rung => (
        Number.isFinite(Number(rung.med)) ? Number(rung.med).toFixed(1) : '--'
    )).join(' → '));
    if (window.ScaleScene) window.ScaleScene.refresh();
}

function fillChinaNarrativeKpis() {
    const agg = dialectAgg;
    const facts = narrativeFacts;
    const data = (window.DataService && window.DataService.dataset) || [];
    const chinaRows = data.filter(movie => movie.regionCode === 3);

    if (agg && agg.meta && agg.meta.baseline) {
        setTextById('china-n', Number(agg.meta.baseline.china_total).toLocaleString('zh-CN'));
    }
    if (facts && facts.regions && facts.regions['中国大陆']) {
        const china = facts.regions['中国大陆'];
        setTextById('china-mean', Number(china.mean).toFixed(2));
        setTextById('china-below5', `${(china.below_five_share).toFixed(1)}%`);
        const europe = facts.regions['欧洲'];
        if (europe && Number.isFinite(Number(europe.mean)) && Number.isFinite(Number(china.mean))) {
            setTextById('china-europe-mean-gap', Math.abs(Number(europe.mean) - Number(china.mean)).toFixed(2));
        }
    }
    if (facts && facts.regions) {
        const europe = facts.regions['欧洲'];
        const northAmerica = facts.regions['北美'];
        if (europe) {
            setTextById('west-eu', Number(europe.mean).toFixed(2));
        }
        if (northAmerica) {
            setTextById('west-na', Number(northAmerica.mean).toFixed(2));
        }
    }

    if (agg && agg.type_controlled && agg.type_controlled.raw) {
        const raw = agg.type_controlled.raw;
        const dialectMean = Number(raw.d.mean).toFixed(2);
        const mandarinMean = Number(raw.m.mean).toFixed(2);
        const delta = (Number(raw.d.mean) - Number(raw.m.mean)).toFixed(2);
        setTextById('china-dialect-mean', dialectMean);
        setTextById('china-mandarin-mean', mandarinMean);
        setTextById('dialect-mean', dialectMean);
        setTextById('mandarin-mean', mandarinMean);
        setTextById('dialect-count', Number(raw.d.n).toLocaleString('zh-CN'));
        setTextById('mandarin-count', Number(raw.m.n).toLocaleString('zh-CN'));
        setTextById('dialect-delta', delta);
        setTextById('finale-dialect-mean', dialectMean);
    }
    if (agg && agg.flop_overall) {
        setTextById('china-dialect-below5', `${agg.flop_overall.d}%`);
        setTextById('china-mandarin-below5', `${agg.flop_overall.m}%`);
        setTextById('overtake-flop-d', `${agg.flop_overall.d}%`);
        setTextById('overtake-flop-m', `${agg.flop_overall.m}%`);
        setTextById('finale-flop-d', `${agg.flop_overall.d}%`);
        setTextById('finale-flop-m', `${agg.flop_overall.m}%`);
        setTextById('finale-flop-d-int', String(Math.round(Number(agg.flop_overall.d))));
        setTextById('finale-flop-m-int', String(Math.round(Number(agg.flop_overall.m))));
        setTextById('scale-flop-d', `${agg.flop_overall.d}%`);
        setTextById('scale-flop-m', `${agg.flop_overall.m}%`);
        setTextById('gl-mandarin-outlier', `${agg.flop_overall.m}%`);
    }
    if (agg && agg.by_decade) {
        const d1990 = agg.by_decade['1990s'];
        const d2010 = agg.by_decade['2010s'];
        const d2020 = agg.by_decade['2020s'];
        if (d2010) {
            setTextById('delta-2010s', Math.abs(Number(d2010.delta)).toFixed(2));
            setTextById('dialect-delta-2010s', `${Number(d2010.delta) >= 0 ? '+' : ''}${Number(d2010.delta).toFixed(2)}`);
            setTextById('decade-2010s-d-n', Number(d2010.d.n).toLocaleString('zh-CN'));
            setTextById('decade-2010s-m-n', Number(d2010.m.n).toLocaleString('zh-CN'));
            const pair = Number(d2010.d.n) + Number(d2010.m.n);
            if (pair) setTextById('decade-2010s-d-share', `${((Number(d2010.d.n) / pair) * 100).toFixed(1)}%`);
        }
        if (d2020) {
            setTextById('delta-2020s', `${Number(d2020.delta) >= 0 ? '+' : ''}${Number(d2020.delta).toFixed(2)}`);
            setTextById('china-dialect-2020s-n', String(d2020.d.n));
        }
        const high8Rows = data.filter(movie => movie.region === 'China' && movie.isDialect && Number(movie.rating) >= 8);
        if (high8Rows.length) setTextById('china-high8-n', String(high8Rows.length));
        const high8Drama = high8Rows.filter(movie => Number(movie.genreCode) === 0).length;
        if (high8Drama) setTextById('china-high8-drama-n', String(high8Drama));
        const n2020 = data.filter(movie => movie.region === 'China' && movie.isDialect && Number(movie.year) === 2020).length;
        if (n2020) setTextById('china-dialect-2020-n', String(n2020));
        const hkN = data.filter(movie => (
            movie.region === 'China' && movie.isDialect && movie.country === '中国香港'
            && Number(movie.year) >= 1985 && Number(movie.year) <= 2005
        )).length;
        if (hkN) setTextById('wave-hk-n', hkN.toLocaleString('zh-CN'));
        const gapMandarin = data.filter(movie => (
            movie.region === 'China' && !movie.isDialect && movie.country === '中国'
            && Number(movie.year) >= 2000 && Number(movie.year) <= 2010
        )).length;
        const gapDialect = data.filter(movie => (
            movie.region === 'China' && movie.isDialect && movie.country === '中国'
            && Number(movie.year) >= 2000 && Number(movie.year) <= 2010
        )).length;
        if (gapMandarin) setTextById('mandarin-gap-n', gapMandarin.toLocaleString('zh-CN'));
        if (gapDialect) setTextById('mainland-d-gap-n', gapDialect.toLocaleString('zh-CN'));
    }
    if (agg && Array.isArray(agg.global_layers)) {
        const byName = Object.fromEntries(agg.global_layers.map(layer => [layer.name, layer]));
        const writeLayer = (id, name) => {
            if (byName[name]) setTextById(id, `${byName[name].below5}%`);
        };
        writeLayer('gl-europe-nondom', '欧洲 · 非主导语言');
        writeLayer('gl-europe-en', '欧洲 · 英语');
        writeLayer('gl-easia', '日韩');
        writeLayer('gl-hua-dialect', '华语 · 方言');
        writeLayer('gl-mandarin-outlier', '华语 · 普通话');
    }
    if (agg && agg.dual_director) {
        setTextById('dd-total-inline', Number(agg.dual_director.total).toLocaleString('zh-CN'));
        setTextById('dd-share-finale', `${agg.dual_director.share_positive}%`);
        setTextById('dd-diff-finale', `+${Number(agg.dual_director.mean_diff).toFixed(2)}`);
        setTextById('scale-dd-share', `${agg.dual_director.share_positive}%`);
    }
    if (agg && Array.isArray(agg.genre_avg)) {
        const byName = Object.fromEntries(agg.genre_avg.map(item => [item.name, item]));
        const writeGenre = (id, name) => {
            if (byName[name]) setTextById(id, Number(byName[name].mean).toFixed(2));
        };
        writeGenre('genre-anim', '动画');
        writeGenre('genre-doc', '纪录片');
        writeGenre('genre-hist', '历史');
        writeGenre('genre-fam', '家庭');
    }

    if (chinaRows.length) {
        const dialectRows = chinaRows.filter(movie => movie.isDialect);
        const mandarinRows = chinaRows.filter(movie => !movie.isDialect);
        const dialectHigh = dialectRows.filter(movie => Number(movie.rating) >= 8);
        const mandarinHigh = mandarinRows.filter(movie => Number(movie.rating) >= 8);
        if (dialectRows.length) {
            const high8 = `${(dialectHigh.length / dialectRows.length * 100).toFixed(1)}%`;
            setTextById('china-dialect-high8', high8);
            setTextById('china-dialect-high8-inline', high8);
        }
        if (mandarinRows.length) {
            const high8 = `${(mandarinHigh.length / mandarinRows.length * 100).toFixed(1)}%`;
            setTextById('china-mandarin-high8', high8);
            setTextById('china-mandarin-high8-inline', high8);
        }
        const dialectMedian = medianOf(dialectHigh.map(movie => Number(movie.votes)).filter(Number.isFinite));
        const mandarinMedian = medianOf(mandarinHigh.map(movie => Number(movie.votes)).filter(Number.isFinite));
        if (dialectMedian != null) {
            setTextById('dialect-high-votes-median', Math.round(dialectMedian).toLocaleString('zh-CN'));
        }
        if (mandarinMedian != null) {
            setTextById('mandarin-high-votes-median', Math.round(mandarinMedian).toLocaleString('zh-CN'));
        }
    }
    fillWorldScale();
}

// ===============================
// 数据填充函数（dialect_aggregates.json）
// ===============================
function fillDirectorCases() {
    document.querySelectorAll('.director-film[data-movie-id]').forEach(button => {
        const movie = findPublicationMovie(button.dataset.movieId);
        if (!movie) return;
        const title = button.querySelector('.director-film-title');
        const rating = button.querySelector('.director-film-rating');
        const score = Number(movie.rating);
        if (title) title.textContent = movie.title;
        if (rating && Number.isFinite(score)) rating.textContent = score.toFixed(1);
        button.classList.toggle('is-high', Number.isFinite(score) && score >= 7.5);
        button.classList.toggle('is-low', Number.isFinite(score) && score < 6);
    });
    if (directorCasesBound) return;
    const step = document.getElementById('step-8d-cases') || document.getElementById('step-8d');
    if (!step) return;
    step.addEventListener('click', event => {
        const button = event.target.closest('.director-film[data-movie-id]');
        if (!button) return;
        const movie = findPublicationMovie(button.dataset.movieId);
        if (!movie) return;
        renderPickedMovie('dual-director', movie, '对照片');
        openMovieDetail(movie);
    });
    directorCasesBound = true;
}

function fillFlopNarrative() {
    const stats = dialectFlopStats();
    const lead = document.getElementById('flop-lead-copy');
    if (lead && stats.n) {
        lead.innerHTML = `${stats.n.toLocaleString('zh-CN')} 部方言片里，只有 <strong>${stats.flopN.toLocaleString('zh-CN')}</strong> 部不到 5 分。`;
    }
    document.querySelectorAll('#step-8c .flop-case-card[data-movie-id]').forEach(card => {
        const movie = caseMovieById(card.dataset.movieId);
        if (!movie) return;
        const title = card.querySelector('strong');
        const rating = card.querySelector('.flop-rating');
        if (title) title.textContent = movie.title;
        if (rating) rating.textContent = movie.rating.toFixed(1);
    });
    if (!flopCasesBound) {
        const step = document.getElementById('step-8c');
        if (step) {
            step.addEventListener('click', event => {
                const card = event.target.closest('.flop-case-card[data-movie-id]');
                if (!card) return;
                const movie = caseMovieById(card.dataset.movieId);
                if (!movie) return;
                renderPickedMovie('dialect-flops', movie, '案例粒子');
                openMovieDetail(movie);
            });
            flopCasesBound = true;
        }
    }
    fillDirectorCases();
}

function fillDialectFlopsCards() {
    const container = document.getElementById('genre-bars');
    if (!container || !particleData.length) return;
    const paths = computeGenreFlopRates();
    const overall = dialectFlopStats().rate;
    const maxRate = Math.max(...paths.map(item => item.rate), 1);
    container.innerHTML = paths.map(item => {
        const pct = (item.rate / maxRate * 100).toFixed(1);
        const lowClass = item.rate >= overall ? ' low' : '';
        return `<div class="genre-row${lowClass}">
            <span class="genre-name">${item.label}</span>
            <div class="genre-bar-track"><div class="genre-bar" style="width:${pct}%"></div></div>
            <span class="genre-value">${item.rate.toFixed(1)}%<small> n=${item.n}</small></span>
        </div>`;
    }).join('');
}

function fillFinaleData() {
    if (!dialectAgg) return;
    if (dialectAgg.dual_director) {
        const dd = dialectAgg.dual_director;
        const ddShare = document.getElementById('dd-share');
        const ddDiff = document.getElementById('dd-diff');
        if (ddShare) { ddShare.textContent = dd.share_positive + '%'; ddShare.classList.remove('is-pending'); }
        if (ddDiff) { ddDiff.textContent = '+' + dd.mean_diff.toFixed(2); ddDiff.classList.remove('is-pending'); }
        setTextById('scale-dd-share', `${dd.share_positive}%`);
    }
    fillDirectorCases();
    // 层 3：语言多样性条。台语与闽南语同源异名，合并为一行（加权均值、n 相加）。
    const langContainer = document.getElementById('lang-bars');
    if (langContainer && dialectAgg.lang_diversity) {
        const merged = [];
        for (const item of dialectAgg.lang_diversity) {
            if (item.name === '台语') {
                const mnRow = merged.find(row => row.name.startsWith('闽南语'));
                if (mnRow) {
                    const total = mnRow.n + item.n;
                    mnRow.mean = (mnRow.mean * mnRow.n + item.mean * item.n) / total;
                    mnRow.n = total;
                    continue;
                }
            }
            merged.push({ ...item });
        }
        const mnLabel = merged.find(row => row.name.startsWith('闽南语'));
        if (mnLabel) mnLabel.name = '闽南语／台语';
        langContainer.innerHTML = merged.map(l => {
            const pct = (l.mean / 10 * 100).toFixed(1);
            return `<div class="lang-row">
                <span class="lang-name">${escapeHtml(l.name)}</span>
                <div class="lang-bar-track"><div class="lang-bar" style="width:${pct}%"></div></div>
                <span class="lang-value">${l.mean.toFixed(2)}<small> n=${l.n}</small></span>
            </div>`;
        }).join('');
    }
    fillWorldScale();
}

function findPublicationMovie(movieId) {
    const id = String(movieId);
    if (window.DataService && Array.isArray(window.DataService.dataset)) {
        const hit = window.DataService.dataset.find(movie => String(movie.movieId) === id);
        if (hit) return hit;
    }
    return particleData.find(movie => String(movie.movieId) === id);
}

function bindWaveScene() {
    if (!window.WaveScene) return;
    window.WaveScene.init({
        particleChart,
        particleData,
        getActiveSceneId: () => activeSceneId,
        getDialectAgg: () => dialectAgg,
        openMovieDetail,
        findPublicationMovie,
        setChartHidden(hidden) {
            const el = document.getElementById('chart-container');
            if (el) {
                if (hidden) {
                    el.dataset.waveLayer = 'hidden';
                    el.style.opacity = '0';
                } else {
                    delete el.dataset.waveLayer;
                    el.style.opacity = '1';
                }
            }
            if (hidden) {
                universeHandoffToken += 1;
                hidePrologueMotionLayer();
            } else if (activeSceneId === 'universe') {
                lastUniverseMotionKey = '';
                resetUniverseIdlePaint();
                startUniverseLoop();
            }
        }
    });
}

function fillWaveCases() {
    if (!dialectAgg || !dialectAgg.wave_cases) return;
    const waves = [
        ['hk', 'wave-hk'],
        ['sw', 'wave-sw'],
        ['mn', 'wave-mn']
    ];
    waves.forEach(([key, containerId]) => {
        const container = document.getElementById(containerId);
        if (!container) return;
        const films = dialectAgg.wave_cases[key] || [];
        container.replaceChildren();
        films.forEach(film => {
            const button = document.createElement('button');
            button.type = 'button';
            button.className = 'movie-chip';
            button.innerHTML = `${escapeHtml(film.title)}<span class="yr">${escapeHtml(film.year)}</span><span class="rt">★ ${Number(film.rating).toFixed(1)}</span>`;
            button.addEventListener('click', () => {
                const movie = findPublicationMovie(film.id) || {
                    movieId: String(film.id),
                    title: film.title,
                    year: film.year,
                    rating: film.rating,
                    votes: 0,
                    decade: '',
                    genres: '',
                    regionCode: 3,
                    langCode: 3
                };
                openMovieDetail(movie);
            });
            container.appendChild(button);
        });
    });
}
