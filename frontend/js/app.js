import { runtime } from './runtime.js';
import { escapeHtml } from './lib/dom.js';
import { populateMovieDetail } from './lib/movie-detail.js';
import { prefersReducedMotion, rafThrottle, debounce } from './lib/schedule.js';
import { initGallery } from './gallery.js';
import { initChapterNav, initScrollytelling } from './scrolly.js';
import { initExplorerScene, exitExplorer, isExplorerOpen } from './scenes/explorer_scene.js';
import { createFlopLinkSync } from './scenes/flop-overlay.js';
import { syncCoverReveal } from './scenes/prologue.js';
import { createUniverseLayer, parseRgba } from './scenes/universe_canvas.js';
import {
    easeCubicOut,
    layoutAxes,
    layoutXY,
    plotToPixel,
    usesPlotAxes
} from './scenes/scene_layout.js';

let particleChart = null;
let particleData = [];
let plottedSeriesData = [];
let visualKeepIsMobile = false;
let universeLayer = null;
let lastVisualKey = '';
let lastLayoutWidth = 0;
const STARFIELD_SCENES = new Set(['final-universe', 'three-waves', 'scale', 'echo-narrative']);

const CANVAS_SCENES = new Set([
    'universe',
    'asian-breakout',
    'european-slow',
    'language-babel',
    'decade-bubble',
    'century-decline',
    'chinese-dialect',
    'global-layers',
    'dialect-flops',
    'dual-director',
    'final-universe',
    'three-waves',
    'scale',
    'echo-narrative'
]);
const TWEEN_MS = 920;
const TWEEN_BUDGET = 14000;
let plotTweenRaf = 0;

function isCanvasParticleScene(sceneId) {
    return CANVAS_SCENES.has(sceneId);
}

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
    afterCutoff: '#FF6B45',
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

const REGION_LABELS = ['北美', '欧洲', '东亚', '中国大陆', '其他'];
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
let flopCaseLinkBound = false;
let flopStatsCache = null;
let flopGenreCache = null;
let flopCaseMovies = null;
let flopRevealToken = 0;
let flopOverlayTimer = 0;
let flopCardTimer = 0;
let flopLinksReady = false;

const FLOP_CASE_PATHS = [
    { movieId: '26796665', path: '杂糅动作' },
    { movieId: '22557335', path: '特效堆砌' },
    { movieId: '6068516', path: '合家欢拼贴' },
    { movieId: '3874981', path: '工业化特效' }
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

function globalLayerOf(row) {
    const region = row.region || (row.detail && row.detail.region);
    const language = row.language || (row.detail && row.detail.language);
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

function globalLayerX(row, group, phase) {
    if (phase === 'pull-back') {
        return languageDisplayIndex(row.langCode) + row.jitterGenreX * 2.2 + row.jitterX * 1.6;
    }
    if (group < 0) {
        return -0.55 + row.jitterGenreX * 0.2;
    }
    return group + row.jitterGenreX;
}

function isChinaDialect(row) {
    return row.region === 'China' && row.isDialect;
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
    flopPhase = resolveFlopPhase(phase);
    runtime.flopPhase = flopPhase;
    runtime.activeSceneId = activeSceneId;
    runtime.flopLinksReady = flopLinksReady;
    document.documentElement.dataset.flopPhase = flopPhase;
    sceneState['dialect-flops'] = flopPhase;
    syncFlopCaseCards(false);
    if (flopPhase === 'cases') bindFlopCaseLinkSync();
    else unbindFlopCaseLinkSync();
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
            children: [
                {
                    type: 'text',
                    style: {
                        text: `${stats.flopN.toLocaleString('zh-CN')} 部`,
                        fill: '#FF7A73',
                        font: '800 22px Noto Sans SC, PingFang SC, sans-serif'
                    }
                },
                {
                    type: 'text',
                    y: 26,
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
const VISUAL_BUDGET_DESKTOP = 10800;
const VISUAL_BUDGET_MOBILE = 7200;
const DUST_BUDGET_DESKTOP = 4000;
const DUST_BUDGET_MOBILE = 2800;
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
            rating: movie.rating,
            votes: movie.votes,
            regionCode: movie.regionCode,
            region: movie.region,
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
        cancelFlopOverlay();
        if (particleChart) particleChart.resize();
        if (universeLayer) universeLayer.resize();
        if (activeSceneId === 'universe') {
            lastUniverseMotionKey = '';
            paintUniverseLive();
        } else if (isCanvasParticleScene(activeSceneId)) {
            paintStoryParticles(activeSceneId, false);
        }
        if (window.WaveScene) window.WaveScene.onResize();
    });
    lastLayoutWidth = window.innerWidth;
    const onParticleResizeDebounced = debounce(() => {
        if (isMobileViewport() !== visualKeepIsMobile) assignVisualKeep();
        const widthChanged = window.innerWidth !== lastLayoutWidth;
        lastLayoutWidth = window.innerWidth;
        if (widthChanged && particleChart) renderParticleScene(activeSceneId, true);
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

function coverDustCenters() {
    const centers = [];
    for (let i = 0; i < 126; i += 1) {
        let x;
        let y;
        let sx;
        let sy;
        if (i < 22) {
            x = 68 + hash2(i, 2, 401) * 30;
            y = 4 + hash2(i, 4, 409) * 34;
            sx = 1.05 + hash2(i, 6, 419) * 4.1;
            sy = 0.9 + hash2(i, 8, 421) * 3.8;
        } else if (i < 38) {
            x = 3 + hash2(i, 2, 401) * 36;
            y = 4 + hash2(i, 4, 409) * 32;
            sx = 1 + hash2(i, 6, 419) * 3.9;
            sy = 0.85 + hash2(i, 8, 421) * 3.6;
        } else {
            x = 4 + hash2(i, 2, 401) * 92;
            y = 4 + hash2(i, 4, 409) * 92;
            x += (fbm2(x / 38, y / 38, 51) - 0.5) * 14;
            y += (fbm2(x / 38 + 3, y / 38, 53) - 0.5) * 12;
            sx = 1.15 + hash2(i, 6, 419) * 4.6;
            sy = 1 + hash2(i, 8, 421) * 4.2;
        }
        const stretch = hash2(i, 9, 439);
        if (stretch < 0.3) {
            sx *= 2.2;
            sy *= 0.42;
        } else if (stretch < 0.52) {
            sx *= 0.46;
            sy *= 2.1;
        }
        centers.push({ x, y, sx, sy });
    }
    return centers;
}

function placeCoverDust() {
    const centers = coverDustCenters();
    const nC = centers.length;
    const southN = 38;
    particleData.forEach(movie => {
        if (!movie.dustKeep) return;
        const id = movie.movieId;
        const mode = stableUnit(id, 241);
        const stray = mode < 0.09;
        const [nx, ny] = gaussianPair(
            Math.max(1e-6, stableUnit(id, 251)),
            stableUnit(id, 271)
        );
        let x;
        let y;
        if (stray) {
            x = 3 + stableUnit(id, 201) * 94 + nx * 2.4;
            y = 36 + stableUnit(id, 223) * 60 + ny * 2.2;
        } else if (mode < 0.31) {
            const ci = Math.min(southN - 1, Math.floor(stableUnit(id, 201) * southN));
            const c = centers[ci];
            const tight = 0.22 + stableUnit(id, 293) * 0.95;
            x = c.x + nx * c.sx * tight;
            y = c.y + ny * c.sy * tight;
        } else {
            const ci = southN + Math.min(
                nC - southN - 1,
                Math.floor(stableUnit(id, 201) * (nC - southN))
            );
            const c = centers[ci];
            const tight = 0.24 + stableUnit(id, 293) * 1.05;
            x = c.x + nx * c.sx * tight;
            y = c.y + ny * c.sy * tight;
        }
        movie.dustX = clampCover(x);
        movie.dustY = clampCover(y);
        movie.dustDepth = stableUnit(id, 277);
        movie.dustSpeck = Math.pow(stableUnit(id, 311), 2.2);
        movie.dustStray = stray;
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
}

function coverDustVisible() {
    return prologueState === PROLOGUE_STATES.WORLD_MAP;
}

function isCoverDust(movie) {
    return Boolean(movie && movie.dustKeep && !movie.mobileKeep);
}

function prologueVisibleRows() {
    const land = [];
    const dust = [];
    particleData.forEach(movie => {
        if (movie.mobileKeep) land.push(movie);
        else if (movie.dustKeep && coverDustVisible()) dust.push(movie);
    });
    return dust.concat(land);
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

function visualGroupColor(group, brightness, mapped, movie, appear, dim) {
    if (isCoverDust(movie)) {
        const depth = Number.isFinite(movie.dustDepth) ? movie.dustDepth : 0.45;
        const tone = depth * 0.7 + brightness * 0.3;
        const alpha = (0.10 + tone * 0.52) * Math.max(0, appear);
        const rgb = Math.round(198 + tone * 38);
        return [rgb, Math.min(255, rgb + 2), Math.min(255, rgb + 8), Math.max(0.08, Math.min(0.62, alpha))];
    }
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
            return [220, 220, 226, Math.max(0.08, Math.min(0.36, alpha))];
        }
        if (prologueState === PROLOGUE_STATES.REGION_FOCUS && dim) {
            const alpha = (0.06 + brightness * 0.08 + depth * 0.06) * Math.max(0, appear);
            return [220, 220, 226, Math.max(0.06, Math.min(0.20, alpha))];
        }
        const alpha = (0.22 + brightness * 0.33) * air * shown * (dim ? 0.62 : 1);
        return [220, 220, 226, Math.max(0.16, Math.min(0.55, alpha))];
    }
    let hex = VISUAL_GROUP_COLORS[group] || VISUAL_GROUP_COLORS.unknown;
    if (onCover && group === 'china') hex = COVER_CHINA_HEX;
    const coverBoost = onCover ? (group === 'china' ? 1.10 : 1) : 1;
    const alpha = (0.38 + brightness * 0.47) * falloff * air * shown * coverBoost;
    const focused = prologueState === PROLOGUE_STATES.REGION_FOCUS && !dim;
    const minA = onCover ? (group === 'china' ? 0.46 : 0.42) : focused ? 0.42 : 0.28;
    const maxA = onCover ? (group === 'china' ? 0.92 : 0.86) : focused ? 0.88 : 0.85;
    const rgb = hexToRgb(hex);
    return [rgb[0], rgb[1], rgb[2], Math.max(minA, Math.min(maxA, alpha))];
}

function universeSymbolSize(movie, brightness, appear, dim) {
    const size = movie ? movie.visualSize : 0.4;
    const shown = Math.max(0.55, appear);
    const glow = brightness >= 0.85 ? 0.3 : brightness >= 0.72 ? 0.1 : 0;
    if (isCoverDust(movie)) {
        const speck = Number.isFinite(movie.dustSpeck) ? movie.dustSpeck : 0.3;
        const depth = Number.isFinite(movie.dustDepth) ? movie.dustDepth : 0.45;
        const y = movie && Number.isFinite(movie.dustY) ? movie.dustY : 50;
        const floorTaper = 0.7 + 0.3 * Math.min(1, Math.max(0, y / 40));
        const base = movie.dustStray ? 0.92 : 1;
        const dust = base + speck * 0.68 + depth * 0.08;
        return Math.max(0.92, Math.min(1.72, dust * floorTaper * Math.max(0.45, appear)));
    }
    if (prologueState === PROLOGUE_STATES.WORLD_MAP) {
        const base = 2 + size * 0.55;
        return Math.max(2, Math.min(2.8, (base + glow * 0.5) * shown));
    }
    if (prologueState === PROLOGUE_STATES.STAR_FIELD) {
        const depth = 1.1 + size * 1.05 + glow * 0.15;
        return Math.max(1.1, Math.min(2.3, depth * Math.max(0.45, appear)));
    }
    if (dim) {
        const depth = 1.1 + size * 0.7;
        return Math.max(1.1, Math.min(1.9, depth * Math.max(0.45, appear)));
    }
    const base = 2.3 + size * 1.05 + glow * 0.2;
    return Math.max(2.3, Math.min(3.5, base * shown));
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
        prologueMotion.release = smooth01(elapsed / 1.15);
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
    const year1994 = summarize(data.filter(movie => movie.year === 1994));
    const other1990s = summarize(data.filter(movie => movie.year >= 1990 && movie.year <= 1999 && movie.year !== 1994));
    const english = summarize(data.filter(movie => movie.langCode === 0));
    const before2010 = summarize(data.filter(movie => movie.year < 2010));
    const from2010 = summarize(data.filter(movie => movie.year >= 2010));
    const pre1990 = summarize(data.filter(movie => movie.year < 1990));
    const decade2010s = summarize(data.filter(movie => movie.year >= 2010 && movie.year <= 2019));
    const cutoffGaps = [];
    for (let cutoff = 1990; cutoff <= 2020; cutoff += 1) {
        const before = summarize(data.filter(movie => movie.year < cutoff));
        const after = summarize(data.filter(movie => movie.year >= cutoff));
        cutoffGaps.push(before.mean - after.mean);
    }
    const europeRows = data.filter(movie => movie.regionCode === 1);
    const nonEuropeRows = data.filter(movie => movie.regionCode !== 1);
    const europe = summarize(europeRows);
    const nonEurope = summarize(nonEuropeRows);
    const europeStandardized = standardizedMeanByDecadeGenre(europeRows, data);
    const nonEuropeStandardized = standardizedMeanByDecadeGenre(nonEuropeRows, data);
    const europeRawGap = europe.mean - nonEurope.mean;
    const europeStandardizedGap = europeStandardized.mean - nonEuropeStandardized.mean;
    const values = {
        'hero-sample-count': formattedCount,
        'particle-sample-count': formattedCount,
        'methodology-sample-count': formattedCount,
        'minimum-vote-count': minimumVotes.toLocaleString('zh-CN'),
        'methodology-minimum-vote-count': minimumVotes.toLocaleString('zh-CN'),
        'sample-year-range': formattedYearRange,
        'methodology-year-range': formattedYearRange,
        'source-record-count': Number(meta.sourceRecordCount || 0).toLocaleString('zh-CN'),
        'europe-count': regionStats[1].n.toLocaleString('zh-CN'),
        'china-count': regionStats[3].n.toLocaleString('zh-CN'),
        'europe-mean': regionStats[1].mean.toFixed(2),
        'non-europe-count': nonEurope.n.toLocaleString('zh-CN'),
        'non-europe-mean': nonEurope.mean.toFixed(2),
        'europe-raw-gap': europeRawGap.toFixed(2),
        'europe-standardized-gap': europeStandardizedGap.toFixed(2),
        'europe-gap-reduction': (europeRawGap - europeStandardizedGap).toFixed(2),
        'year-1994-count': year1994.n.toLocaleString('zh-CN'),
        'year-1994-mean': year1994.mean.toFixed(2),
        'year-1994-high-share': `${year1994.highShare.toFixed(1)}%`,
        'other-1990s-high-share': `${other1990s.highShare.toFixed(1)}%`,
        'year-1994-high-delta': `${Math.abs(year1994.highShare - other1990s.highShare).toFixed(1)} 个百分点`,
        'english-count': english.n.toLocaleString('zh-CN'),
        'english-share': `${(english.n / data.length * 100).toFixed(1)}%`,
        'pre-2010-count': before2010.n.toLocaleString('zh-CN'),
        'pre-2010-mean': before2010.mean.toFixed(2),
        'post-2010-count': from2010.n.toLocaleString('zh-CN'),
        'post-2010-mean': from2010.mean.toFixed(2),
        'cutoff-gap-min': Math.min(...cutoffGaps).toFixed(2),
        'cutoff-gap-max': Math.max(...cutoffGaps).toFixed(2),
        'pre-1990-below-five': `${pre1990.belowFive.toFixed(1)}%`,
        'decade-2010s-below-five': `${decade2010s.belowFive.toFixed(1)}%`,
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
        'intro-sample-count': formattedCount,
        'methodology-year-range-repeat': formattedYearRange,
        'overall-unweighted-mean': average.toFixed(2),
        'overall-vote-weighted-mean': voteWeightedAverage.toFixed(2)
    };
    Object.entries(values).forEach(([id, value]) => {
        if (id === 'hero-sample-count') return;
        const node = document.getElementById(id);
        if (!node) return;
        node.innerText = value;
        if (node.classList.contains('is-pending')) node.classList.remove('is-pending');
    });
    window.StoryUI.animateCount(document.getElementById('hero-sample-count'), formattedCount, count);
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
        label: '序章 · 电影星图',
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
            : `${REGION_LABELS[Number(value)]}被单独点亮。点击右侧任意粒子，可从集合回到具体电影。`
    },
    'hollywood-entropy': {
        label: '第一幕 · 类型与离散度',
        prompt: '选择类型，比较北美与其他地区的评分离散程度。',
        type: 'buttons',
        defaultValue: 'all',
        options: [{ value: 'all', label: '全部类型' }, ...GENRES.map((label, index) => ({ value: String(index), label }))],
        filter: (row, value) => value === 'all' || row.genreCode === Number(value),
        metrics: value => {
            const rows = particleData.filter(row => SCENE_INTERACTIONS['hollywood-entropy'].filter(row, value));
            const northAmerica = summarize(rows.filter(row => row.regionCode === 0));
            const others = summarize(rows.filter(row => row.regionCode !== 0));
            return [
                metric('北美均分', northAmerica.n ? northAmerica.mean.toFixed(2) : '--', `n=${northAmerica.n}`),
                metric('其他地区均分', others.n ? others.mean.toFixed(2) : '--', `n=${others.n}`),
                metric('北美标准差', northAmerica.n ? northAmerica.sd.toFixed(2) : '--', '越小越集中'),
                metric('其他地区标准差', others.n ? others.sd.toFixed(2) : '--', value === 'all' ? '全部类型' : GENRES[Number(value)])
            ];
        },
        insight: value => {
            const rows = particleData.filter(row => SCENE_INTERACTIONS['hollywood-entropy'].filter(row, value));
            const northAmerica = summarize(rows.filter(row => row.regionCode === 0));
            const others = summarize(rows.filter(row => row.regionCode !== 0));
            const genre = value === 'all' ? '全部类型合计' : GENRES[Number(value)];
            if (!northAmerica.n || !others.n) return `${genre}缺少其中一个地区组，暂时无法计算两组标准差。`;
            const direction = northAmerica.sd < others.sd ? '更集中' : '更分散';
            return `${genre}：北美评分标准差 ${northAmerica.sd.toFixed(2)}，其他地区 ${others.sd.toFixed(2)}；北美电影的评分${direction}。`;
        }
    },
    'asian-breakout': {
        label: '第一幕 · 地区分布',
        prompt: '逐个地区查看原始均分与年代×主类型标准化均分。',
        type: 'buttons',
        defaultValue: '3',
        options: REGION_LABELS.map((label, index) => ({ value: String(index), label })),
        filter: (row, value) => row.regionCode === Number(value),
        metrics: value => {
            const rows = particleData.filter(row => row.regionCode === Number(value));
            const selected = summarize(rows);
            const overall = summarize(particleData);
            const standardized = standardizedMeanByDecadeGenre(rows, particleData);
            return [
                metric('地区电影', selected.n.toLocaleString('zh-CN'), REGION_LABELS[Number(value)]),
                metric('原始均分', selected.mean.toFixed(2), `中位数 ${selected.median.toFixed(2)}`),
                metric('标准化均分', standardized.mean.toFixed(2), '统一年代×主类型构成'),
                metric('总体均分', overall.mean.toFixed(2), `n=${overall.n.toLocaleString('zh-CN')}`),
            ];
        },
        insight: value => {
            const rows = particleData.filter(row => row.regionCode === Number(value));
            const stats = summarize(rows);
            const standardized = standardizedMeanByDecadeGenre(rows, particleData);
            return `${REGION_LABELS[Number(value)]}收录 ${stats.n.toLocaleString('zh-CN')} 部：原始均分 ${stats.mean.toFixed(2)}，统一年代×主类型构成后为 ${standardized.mean.toFixed(2)}。`;
        }
    },
    'decade-bubble': {
        label: '第四幕 · 时间的坡度（上）',
        prompt: '选择年代，一起查看电影数与高分占比。',
        type: 'buttons',
        defaultValue: '1990s',
        options: ['Pre-1990s', '1990s', '2000s', '2010s', '2020s'].map(value => ({ value, label: value })),
        filter: (row, value) => decadeOf(row.year) === value,
        metrics: value => standardMetrics(particleData.filter(row => decadeOf(row.year) === value)),
        insight: value => {
            const rows = particleData.filter(row => decadeOf(row.year) === value);
            const year1994 = rows.filter(row => row.year === 1994);
            const year1994Stats = summarize(year1994);
            const other1990s = summarize(rows.filter(row => row.year !== 1994));
            return value === '1990s'
                ? `1994 年高分占比 ${year1994Stats.highShare.toFixed(1)}%，九十年代其余年份为 ${other1990s.highShare.toFixed(1)}%。`
                : `${value} 收录 ${rows.length.toLocaleString('zh-CN')} 部，均分 ${summarize(rows).mean.toFixed(2)}，高分占比 ${summarize(rows).highShare.toFixed(1)}%。`;
        }
    },
    'language-babel': {
        label: '第三幕 · 分析语言组',
        prompt: '切换分析语言组，同时读取占比、均值和高分占比。此处语言均指主要语言；混合语种按片单首位归组。',
        type: 'buttons',
        defaultValue: '3',
        options: languageOptionList(false),
        filter: (row, value) => row.langCode === Number(value),
        metrics: value => {
            const rows = particleData.filter(row => row.langCode === Number(value));
            const stats = summarize(rows);
            return [
                metric('语言组电影', stats.n.toLocaleString('zh-CN'), LANGUAGE_LABELS[Number(value)]),
                metric('占全部电影', `${(stats.n / particleData.length * 100).toFixed(1)}%`, `共 ${particleData.length.toLocaleString('zh-CN')} 部`),
                metric('平均评分', stats.mean.toFixed(2), '当前组等权均值'),
                metric('高分占比', `${stats.highShare.toFixed(1)}%`, '评分 ≥ 8.5')
            ];
        },
        insight: value => {
            const rows = particleData.filter(row => row.langCode === Number(value));
            const stats = summarize(rows);
            return `${LANGUAGE_LABELS[Number(value)]}组收录 ${stats.n.toLocaleString('zh-CN')} 部，占全部电影 ${(stats.n / particleData.length * 100).toFixed(1)}%，均分 ${stats.mean.toFixed(2)}。`;
        }
    },
    'century-decline': {
        label: '第五幕 · 分界线实验',
        prompt: '移动分界年份，观察“此前／此后”差异是否稳定。',
        type: 'range',
        defaultValue: 2010,
        min: 1990,
        max: 2020,
        step: 1,
        formatValue: value => `${value} 年`,
        filter: () => true,
        metrics: value => {
            const cutoff = Number(value);
            const before = summarize(particleData.filter(row => row.year < cutoff));
            const after = summarize(particleData.filter(row => row.year >= cutoff));
            return [
                metric('此前均分', before.mean.toFixed(2), `n=${before.n.toLocaleString('zh-CN')}`),
                metric('此后均分', after.mean.toFixed(2), `n=${after.n.toLocaleString('zh-CN')}`),
                metric('此前高分占比', `${before.highShare.toFixed(1)}%`, '评分 ≥ 8.5'),
                metric('此后高分占比', `${after.highShare.toFixed(1)}%`, '评分 ≥ 8.5')
            ];
        },
        insight: value => {
            const cutoff = Number(value);
            const before = summarize(particleData.filter(row => row.year < cutoff));
            const after = summarize(particleData.filter(row => row.year >= cutoff));
            return `以 ${value} 年切分，较早一组比此后高 ${(before.mean - after.mean).toFixed(2)} 分；移动切点可检验差距是否稳定。`;
        }
    },
    'european-slow': {
        label: '第二幕 · 下限检验',
        prompt: '切换地区，对比第一四分位数、中位数和低分占比。',
        type: 'buttons',
        defaultValue: '3',
        options: REGION_LABELS.map((label, index) => ({ value: String(index), label })),
        filter: (row, value) => row.regionCode === Number(value),
        metrics: value => {
            const stats = summarize(particleData.filter(row => row.regionCode === Number(value)));
            return [
                metric('电影数 n', stats.n.toLocaleString('zh-CN'), REGION_LABELS[Number(value)]),
                metric('第一四分位数', stats.n ? stats.q1.toFixed(2) : '--', '25% 电影低于此值'),
                metric('中位数', stats.n ? stats.median.toFixed(2) : '--', '分布中心'),
                metric('低于 5 分', stats.n ? `${stats.belowFive.toFixed(1)}%` : '--', '低分电影占比')
            ];
        },
        insight: value => {
            const stats = summarize(particleData.filter(row => row.regionCode === Number(value)));
            return `${REGION_LABELS[Number(value)]}收录 ${stats.n.toLocaleString('zh-CN')} 部。四分位数和低分占比补充了均值看不到的分布差异。`;
        }
    },
    'chinese-dialect': {
        label: '第六幕 · 分差随年代变化',
        prompt: '切换年代，比较普通话与方言电影的均分。',
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
            (row.langCode === 2 || row.langCode === 3)
            && (value === 'all' || decadeOf(row.year) === value)
        ),
        metrics: value => {
            const rows = particleData.filter(row => SCENE_INTERACTIONS['chinese-dialect'].filter(row, value));
            const mandarin = summarize(rows.filter(row => row.langCode === 2));
            const dialect = summarize(rows.filter(row => row.langCode === 3));
            const delta = dialect.mean - mandarin.mean;
            return [
                metric('普通话均分', mandarin.n ? mandarin.mean.toFixed(2) : '--', `n=${mandarin.n.toLocaleString('zh-CN')}`),
                metric('方言均分', dialect.n ? dialect.mean.toFixed(2) : '--', `n=${dialect.n.toLocaleString('zh-CN')}`),
                metric('均分差', mandarin.n && dialect.n ? `${delta >= 0 ? '+' : ''}${delta.toFixed(2)}` : '--', '方言组 − 普通话组'),
                metric('两组电影数', rows.length.toLocaleString('zh-CN'), value === 'all' ? '全部年份' : value)
            ];
        },
        insight: value => {
            const rows = particleData.filter(row => SCENE_INTERACTIONS['chinese-dialect'].filter(row, value));
            const mandarin = summarize(rows.filter(row => row.langCode === 2));
            const dialect = summarize(rows.filter(row => row.langCode === 3));
            const delta = dialect.mean - mandarin.mean;
            return `${value === 'all' ? '全部年份' : value}：方言减普通话为 ${delta >= 0 ? '+' : ''}${delta.toFixed(2)} 分。`;
        }
    },
    'final-universe': {
        label: '第十一幕 · 语言组星云',
        prompt: '按语言组缩小星云，再随机或直接点选一部电影。',
        type: 'buttons',
        defaultValue: 'all',
        options: languageOptionList(true),
        filter: (row, value) => value === 'all' || row.langCode === Number(value),
        metrics: value => standardMetrics(particleData.filter(row => SCENE_INTERACTIONS['final-universe'].filter(row, value))),
        insight: () => '方言（琥珀色）与普通话（灰蓝色）在星云中并列。点击任意粒子核对具体作品。'
    },
    'global-layers': {
        label: '第七幕 · 全球参照',
        prompt: '把电影按语言组放回同一条 5 分线，观察谁更容易跌穿下限。点选不同观察，粒子会重新排列。',
        type: 'buttons',
        defaultValue: 'mandarin-outlier',
        options: [
            { value: 'pull-back', label: '把镜头拉远' },
            { value: 'axes', label: '5 分线' },
            { value: 'four-groups', label: '前四组' },
            { value: 'mandarin-outlier', label: '普通话异常' },
            { value: 'boundary', label: '共性边界' }
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
                    metric('普通话电影数', mandarin.n ? mandarin.n.toLocaleString('zh-CN') : '--', '华语内部 · 上一幕口径'),
                    metric('方言电影数', dialect.n ? dialect.n.toLocaleString('zh-CN') : '--', '华语内部 · 上一幕口径'),
                    metric('普通话均分', mandarin.n ? mandarin.mean.toFixed(2) : '--', `n=${mandarin.n.toLocaleString('zh-CN')}`),
                    metric('方言均分', dialect.n ? dialect.mean.toFixed(2) : '--', `n=${dialect.n.toLocaleString('zh-CN')}`)
                ];
            }
            if (value === 'axes') {
                const fiveN = fiveGroupNames.reduce((sum, name) => sum + (byName[name] ? byName[name].n : 0), 0);
                return [
                    metric('低分下限', '5.0', '豆瓣评分'),
                    metric('语言组', '5', '全球参照组'),
                    metric('五组合计', fiveN ? fiveN.toLocaleString('zh-CN') : '--', '部电影'),
                    metric('观察指标', '低于 5 分占比', '不看均分谁更高')
                ];
            }
            if (value === 'four-groups') {
                return [
                    read('欧洲 · 非主导语言', '欧洲非主导', '低于 5 分'),
                    read('欧洲 · 英语', '英语', '欧洲英语'),
                    read('日韩', '日韩', '低于 5 分'),
                    read('华语 · 方言', '华语方言', '低于 5 分')
                ];
            }
            if (value === 'mandarin-outlier') {
                const mandarin = byName['华语 · 普通话'];
                const fourMax = fourGroupNames.reduce((max, name) => {
                    const rate = byName[name] ? byName[name].below5 : 0;
                    return rate > max ? rate : max;
                }, 0);
                return [
                    read('华语 · 普通话', '华语普通话', '低于 5 分'),
                    read('华语 · 方言', '华语方言', '低于 5 分'),
                    metric('前四组最高', fourMax ? `${fourMax}%` : '--', '短尾组里最低分占比最高的一组'),
                    metric('普通话样本', mandarin ? mandarin.n.toLocaleString('zh-CN') : '--', '华语 · 普通话')
                ];
            }
            return [
                read('欧洲 · 非主导语言', '欧洲非主导', '低于 5 分'),
                read('欧洲 · 英语', '英语', '欧洲英语'),
                read('日韩', '日韩', '低于 5 分'),
                read('华语 · 方言', '华语方言', '低于 5 分'),
                read('华语 · 普通话', '华语普通话', '低于 5 分'),
                read('北美 · 英语', '北美英语', '参照组外')
            ];
        },
        insight: value => {
            if (value === 'pull-back') {
                return '先把镜头从华语内部拉开。粒子仍靠近上一幕的语言组位置，随后会按全球参照组重新排列。';
            }
            if (value === 'axes') {
                return 'Y 轴是豆瓣评分。我们不看谁平均分最高，只看谁更容易跌穿 5 分下限。';
            }
            if (value === 'four-groups') {
                return '欧洲非主导语言 1.5%、英语 3.6%、日韩 5.8%、华语方言 6.4%——这四组低分尾部都比较短。';
            }
            if (value === 'mandarin-outlier') {
                return '华语普通话低于 5 分的比例是 24.4%。约每 4 部就有 1 部落到 5 分线以下。';
            }
            return '欧洲非主导语言 1.5%、英语 3.6%、日韩 5.8%、华语方言 6.4%——低分尾部都短于华语普通话 24.4%。这只说明下限更稳的共性，不能证明语言本身造成评分差异。';
        }
    },
    'dialect-flops': {
        label: '第八幕 · 烂片也有',
        prompt: '切开方言内部。按钮只改右侧粒子：看主体、失败尾部、四部案例，或只留低分点。',
        type: 'buttons',
        defaultValue: 'isolate',
        options: [
            { value: 'isolate', label: '主体' },
            { value: 'tail', label: '失败尾部' },
            { value: 'cases', label: '案例' },
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
                    metric('低分均分', flopSummary.n ? flopSummary.mean.toFixed(2) : '--', `n=${flopSummary.n.toLocaleString('zh-CN')}`),
                    metric('低分中位', flopSummary.n ? flopSummary.median.toFixed(2) : '--', '对极端值更稳健'),
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
                    metric('均分', flopSummary.n ? flopSummary.mean.toFixed(2) : '--', `n=${flopSummary.n.toLocaleString('zh-CN')}`),
                    metric('中位', flopSummary.n ? flopSummary.median.toFixed(2) : '--', '评分 < 5'),
                    metric('最低分', Number.isFinite(flopMin) ? flopMin.toFixed(1) : '--', `这 ${stats.flopN.toLocaleString('zh-CN')} 部里`),
                    ...topCounts.map(item => metric(item.label, item.flopN ? String(item.flopN) : '--', `低分 ${item.flopN} / ${item.n}`))
                ];
            }
            return [
                metric('方言片', stats.n ? stats.n.toLocaleString('zh-CN') : '--', 'Region=China'),
                metric('低于 5 分', stats.flopN ? String(stats.flopN) : '--', `${stats.rate.toFixed(1)}%`),
                ...paths.map(item => metric(item.label, item.n ? `${item.rate.toFixed(1)}%` : '--', `低分 ${item.flopN} / ${item.n}`))
            ];
        },
        insight: phase => {
            const current = resolveFlopPhase(phase);
            const stats = dialectFlopStats();
            if (current === 'tail') {
                return `${stats.flopN.toLocaleString('zh-CN')} 部被拉到失败束。它们仍是方言片，失败的是创作路径，不是语言本身。`;
            }
            if (current === 'cases') {
                return '四部真实低分方言片，对应四条失败路径。点开卡片或粒子，核对具体作品。';
            }
            if (current === 'flopsOnly') {
                return `图上只剩低于 5 分的 ${stats.flopN.toLocaleString('zh-CN')} 部。这不是语言的失败，是路径的失败。`;
            }
            return `方言内部也会失败：${stats.n.toLocaleString('zh-CN')} 部里有 ${stats.flopN.toLocaleString('zh-CN')} 部低于 5 分（${stats.rate.toFixed(1)}%）。问题不在语言，而在创作路径。`;
        }
    },
    'dual-director': {
        label: '第九幕 · 寻 · 同导演对比',
        prompt: '同一批导演的方言片与普通话片都在图中。点开一部，核对具体作品。',
        type: 'buttons',
        defaultValue: 'all',
        options: [
            { value: 'all', label: '两种语言' },
            { value: '3', label: '方言' },
            { value: '2', label: '普通话' }
        ],
        filter: (row, value) => (
            (row.langCode === 2 || row.langCode === 3)
            && (value === 'all' || row.langCode === Number(value))
        ),
        metrics: value => {
            const rows = particleData.filter(row => SCENE_INTERACTIONS['dual-director'].filter(row, value));
            const dialect = summarize(rows.filter(row => row.langCode === 3));
            const mandarin = summarize(rows.filter(row => row.langCode === 2));
            const dd = dialectAgg && dialectAgg.dual_director;
            const shared = [
                metric('双栖导演', dd ? dd.total.toLocaleString('zh-CN') : '--', '两种语言都拍过'),
                metric('方言更高', dd ? dd.share_positive + '%' : '--', dd ? '平均分差 +' + dd.mean_diff.toFixed(2) : '加载中')
            ];
            const flopRate = stats => metric(
                '烂片率',
                stats.n ? `${stats.belowFive.toFixed(1)}%` : '--',
                stats.n ? `低于 5 分 · n=${stats.n.toLocaleString('zh-CN')}` : '低于 5 分'
            );
            if (value === '3') {
                return [
                    ...shared,
                    metric('方言均分', dialect.n ? dialect.mean.toFixed(2) : '--', `n=${dialect.n.toLocaleString('zh-CN')}`),
                    flopRate(dialect)
                ];
            }
            if (value === '2') {
                return [
                    ...shared,
                    metric('普通话均分', mandarin.n ? mandarin.mean.toFixed(2) : '--', `n=${mandarin.n.toLocaleString('zh-CN')}`),
                    flopRate(mandarin)
                ];
            }
            return [
                ...shared,
                metric('方言均分', dialect.n ? dialect.mean.toFixed(2) : '--', `n=${dialect.n.toLocaleString('zh-CN')}`),
                metric('普通话均分', mandarin.n ? mandarin.mean.toFixed(2) : '--', `n=${mandarin.n.toLocaleString('zh-CN')}`)
            ];
        },
        insight: () => {
            const dd = dialectAgg && dialectAgg.dual_director;
            if (!dd) return '把导演变量锁住：同一人拍方言片和普通话片，评分仍可能不同。';
            return `${dd.total} 位双栖导演中，${dd.share_positive}% 的方言片评分更高，平均分差 +${dd.mean_diff.toFixed(2)}。质量差异来自项目本身的投入度和创作态度。`;
        }
    },
    'three-waves': {
        label: '第十幕 · 展 · 三波浪潮',
        prompt: '点击浪潮片单中的电影，回到具体作品。',
        type: 'buttons',
        defaultValue: 'all',
        options: [{ value: 'all', label: '方言片' }],
        filter: (row) => row.langCode === 3,
        metrics: () => {
            const waves = dialectAgg && dialectAgg.wave_cases;
            const count = waves ? ['hk', 'sw', 'mn'].reduce((n, key) => n + (waves[key] || []).length, 0) : 0;
            return [
                metric('三波片单', count ? String(count) : '--', '港／西南／闽南'),
                metric('第一波', '港片粤语', '1985–2005'),
                metric('第二波', '西南方言', '2010–今'),
                metric('第三波', '闽南语新浪潮', '2008–今')
            ];
        },
        insight: () => '三波浪潮，三种方言，同一个逻辑：用更少的产量，守住更稳的下限。点击片单核对具体电影。'
    },
    'scale': {
        label: '第十二幕 · 刻度',
        prompt: '对照六级世界均分刻度，再随机或直接点选一部电影。',
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
                metric('方言均分', dialect.n ? dialect.mean.toFixed(2) : '--', `n=${dialect.n.toLocaleString('zh-CN')}`),
                metric('欧洲均分', europe.n ? europe.mean.toFixed(2) : '--', `n=${europe.n.toLocaleString('zh-CN')}`),
                metric('北美均分', northAmerica.n ? northAmerica.mean.toFixed(2) : '--', `n=${northAmerica.n.toLocaleString('zh-CN')}`)
            ];
        },
        insight: () => {
            const rungs = getWorldScaleRungs();
            if (rungs) {
                const shown = Object.fromEntries(rungs.map(rung => [rung.key, Number(rung.score.toFixed(2))]));
                const premium = (shown.dia - shown.cn).toFixed(2);
                const remain = (shown.eu - shown.dia).toFixed(2);
                return `方言均分 ${shown.dia.toFixed(2)}，仍落后于欧洲 ${shown.eu.toFixed(2)}、北美 ${shown.na.toFixed(2)}。态度溢价 +${premium}，往上还有 ${remain}。鸿沟是质量的鸿沟，不是文化的鸿沟。`;
            }
            const dialect = summarize(particleData.filter(isChinaDialect));
            const europe = summarize(particleData.filter(row => row.regionCode === 1));
            const northAmerica = summarize(particleData.filter(row => row.regionCode === 0));
            if (!dialect.n || !europe.n || !northAmerica.n) {
                return '对照方言与世界主要电影产区的均分。那道鸿沟是质量的鸿沟，不是文化的鸿沟。';
            }
            return `方言均分 ${dialect.mean.toFixed(2)}，仍落后于世界主要电影产区：欧洲 ${europe.mean.toFixed(2)}、北美 ${northAmerica.mean.toFixed(2)}。鸿沟是质量的鸿沟，不是文化的鸿沟。`;
        }
    },
    'echo-narrative': {
        label: '第十三幕 · 回响',
        prompt: '',
        type: 'buttons',
        defaultValue: 'all',
        options: [],
        filter: () => true,
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
        step.dataset.sceneTitle = config.label;
        if (sceneState[sceneId] === undefined) sceneState[sceneId] = config.defaultValue;

        // Keep the opening screen as spare as the original hero. Interactive
        // evidence begins with the first actual story act below it.
        if (index === 0) return;
        if (sceneId === 'echo-narrative') return;
        if (document.querySelector(`[data-scene-lab="${sceneId}"]`)) return;

        // Keep the original lightweight story surface. Per-scene analysis is
        // available on demand instead of permanently occupying the homepage.
        const lab = document.createElement('details');
        lab.className = 'scene-lab';
        lab.dataset.sceneLab = sceneId;
        lab.innerHTML = `
            <summary class="scene-lab-heading">
                <span class="scene-lab-toggle">展开本幕数据</span>
                <b>${config.label}</b>
                <i aria-hidden="true">＋</i>
            </summary>
            <div class="scene-lab-body">
                <p class="scene-question">${config.prompt}</p>
                <div class="scene-control" aria-label="场景筛选器"></div>
                <div class="scene-metrics" aria-live="polite"></div>
                <p class="scene-insight"></p>
                <p class="scene-guide-note">图中虚线标出比较基准；出现色带时，色带表示两条统计线之间的差距。</p>
                <div class="scene-picked" aria-live="polite"><span>尚未点选电影</span></div>
                <button class="scene-random" type="button">随机打捞一部</button>
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
            if (toggleLabel) toggleLabel.textContent = lab.open ? '收起数据' : '展开本幕数据';
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
    activeSceneId = sceneId;
    if (sceneId === 'global-layers') syncGlobalLayersPhase();
    if (sceneId === 'dialect-flops') {
        setFlopPhase(resolveFlopPhase(sceneState[sceneId] || 'isolate'), { render: false, refreshLab: true });
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
    renderPickedMovie(sceneId, movie, '随机打捞');
    openMovieDetail(movie);
    if (isCanvasParticleScene(sceneId) && universeLayer) {
        universeLayer.highlight(movie.id);
        return;
    }
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

function movieTooltipHtml(movie) {
    if (!movie) return '';
    const visualLabel = VISUAL_GROUP_LABELS[movie.visualGroup] || '';
    return `<strong style="font-size:14px">${escapeHtml(movie.title)}</strong><br>`
        + `${movie.year} · ${movie.rating.toFixed(1)} 分 · ${Number(movie.votes || 0).toLocaleString('zh-CN')} 人评价<br>`
        + `${REGION_LABELS[movie.regionCode] || '未知地区'} · ${LANGUAGE_LABELS[movie.langCode] || '未知语言组'}`
        + (visualLabel ? `<br>视觉地区 ${escapeHtml(visualLabel)}` : '');
}

function initUniverseLayer() {
    const canvas = document.getElementById('universe-layer');
    if (!canvas || universeLayer) return;
    universeLayer = createUniverseLayer({
        canvas,
        onPick(movieId) {
            const movie = Number.isInteger(movieId) ? particleData[movieId] : null;
            if (movie) openPickedParticle(movie);
        },
        formatTooltip(movieId) {
            const movie = Number.isInteger(movieId) ? particleData[movieId] : null;
            return movieTooltipHtml(movie);
        }
    });
}

function initParticleEngine() {
    const container = document.getElementById('chart-container');
    particleChart = echarts.init(container, 'dark');
    particleChart.getZr().on('click', event => {
        if (isCanvasParticleScene(activeSceneId)) return;
        const movie = findNearestMovieByPixel(event.offsetX, event.offsetY, 20);
        if (movie) openPickedParticle(movie);
    });
    initUniverseLayer();
    document.addEventListener('visibilitychange', () => {
        if (!document.hidden && activeSceneId === 'universe') startUniverseLoop();
    });
    setPrologueState(PROLOGUE_STATES.WORLD_MAP);
    renderParticleScene('universe');
    startUniverseLoop();
}

function universeChartAr() {
    if (universeLayer && universeLayer.isVisible()) {
        const size = universeLayer.cssSize();
        return Math.max(0.5, size.width / Math.max(1, size.height));
    }
    const chartW = particleChart ? particleChart.getWidth() : window.innerWidth;
    const chartH = particleChart ? particleChart.getHeight() : window.innerHeight;
    return Math.max(0.5, chartW / Math.max(1, chartH));
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

function paintUniverseLive() {
    if (!universeLayer || activeSceneId !== 'universe') return;
    advancePrologueMotion(performance.now());
    const key = prologueMotionKey();
    if (key === lastUniverseMotionKey) return;
    lastUniverseMotionKey = key;
    const ar = universeChartAr();
    const rows = prologueVisibleRows();
    const moving = prologueMotionBusy();
    universeLayer.begin(rows.length, 100 * ar);
    for (let i = 0; i < rows.length; i += 1) {
        const d = rows[i];
        const pose = universePose(d, ar);
        const brightness = ratingBrightness(d.rating);
        const dim = prologueState === PROLOGUE_STATES.REGION_FOCUS
            && d.visualGroup !== prologueFocusGroup;
        if (moving && isCoverDust(d)) continue;
        if (pose.appear < 0.02) continue;
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
        universeLayer.push(
            pose.x,
            pose.y,
            universeSymbolSize(d, brightness, pose.appear, dim),
            color,
            glowing,
            d.id
        );
    }
    universeLayer.draw();
    syncCoverReveal();
}

function languageStarColor(langCode, focused) {
    if (langCode === 3) return focused ? [255, 179, 0, 0.78] : [255, 179, 0, 0.16];
    if (langCode === 2) return focused ? [98, 176, 255, 0.72] : [98, 176, 255, 0.12];
    return focused ? [220, 220, 226, 0.18] : [220, 220, 226, 0.07];
}

function stopPlotTween() {
    if (plotTweenRaf) cancelAnimationFrame(plotTweenRaf);
    plotTweenRaf = 0;
}

function scenePlotBox(sceneId) {
    const size = universeLayer ? universeLayer.cssSize() : { width: window.innerWidth, height: window.innerHeight };
    const compact = window.innerWidth <= 700;
    if (!usesPlotAxes(sceneId)) {
        return { left: 0, top: 0, width: size.width, height: size.height };
    }
    if (sceneId === 'global-layers') {
        const bottom = compact ? 78 : 56;
        return { left: 28, top: 22, width: size.width - 46, height: size.height - 22 - bottom };
    }
    if (sceneId === 'dialect-flops') {
        const left = compact ? 28 : size.width * 0.16;
        const right = compact ? 18 : size.width * 0.07;
        const bottom = compact ? 78 : 56;
        return { left, top: 22, width: size.width - left - right, height: size.height - 22 - bottom };
    }
    return { left: 8, top: 8, width: size.width - 16, height: size.height - 16 };
}

function layoutEnv(sceneId) {
    const selected = sceneState[sceneId];
    return {
        selectedRegion: Number(selected ?? 3),
        selectedLanguage: Number(selected ?? 3),
        selectedDecade: selected,
        cutoff: Number(selected ?? 2010),
        globalPhase: globalLayersPhase || 'mandarin-outlier',
        flopPhase: resolveFlopPhase(flopPhase),
        yMin: sampleRatingExtent[0],
        yMax: sampleRatingExtent[1],
        yearMin: sampleYearExtent[0],
        yearMax: sampleYearExtent[1],
        languageOrder: LANGUAGE_DISPLAY_ORDER,
        languageIndex: languageDisplayIndex,
        layerOf: globalLayerOf,
        layerX: globalLayerX,
        flopX: dialectFlopX,
        flopLit: isFlopLit
    };
}

function particleLook(sceneId, d) {
    const focused = isSceneFocused(d) === 1;
    if (STARFIELD_SCENES.has(sceneId) || sceneId === 'echo-narrative') {
        const dialectOrMandarin = d.langCode === 3 || d.langCode === 2;
        return {
            size: focused ? (d.langCode === 3 ? 2.6 : dialectOrMandarin ? 2.3 : 1.7) : 1.15,
            color: languageStarColor(d.langCode, focused),
            glow: focused && dialectOrMandarin && d.rating >= 8.7
        };
    }
    if (sceneId === 'asian-breakout') {
        let color = [255, 255, 255, 0.14];
        if (focused) {
            if (d.regionCode === 2 || d.regionCode === 3) color = [...hexToRgb(COLORS.asian), 0.86];
            else if (d.regionCode === 0) color = [84, 112, 198, 0.55];
            else color = [236, 232, 224, 0.5];
        }
        return { size: focused ? 3.2 : 1.2, color, glow: false };
    }
    if (sceneId === 'european-slow') {
        if (!focused) return { size: 1.2, color: [255, 255, 255, 0.14], glow: false };
        if (d.rating < 5) return { size: 3.4, color: [...hexToRgb(GUIDE_COLORS.threshold), 0.9], glow: false };
        return { size: 3.1, color: [236, 232, 224, 0.84], glow: false };
    }
    if (sceneId === 'language-babel') {
        const parsed = parseRgba(LANGUAGE_COLORS[d.langCode] || 'rgba(255,255,255,0.15)');
        if (!focused) parsed[3] = Math.min(parsed[3], 0.14);
        return { size: focused ? 3.4 : 1.3, color: parsed, glow: false };
    }
    if (sceneId === 'decade-bubble') {
        const on = decadeOf(d.year) === sceneState['decade-bubble'];
        return {
            size: on ? 3.2 : 1.2,
            color: on ? [185, 196, 206, 0.86] : [255, 255, 255, 0.12],
            glow: false
        };
    }
    if (sceneId === 'century-decline') {
        const after = d.year >= Number(sceneState['century-decline']);
        return {
            size: 2.4,
            color: after ? [...hexToRgb(COLORS.afterCutoff), 0.82] : [132, 182, 244, 0.48],
            glow: false
        };
    }
    if (sceneId === 'chinese-dialect' || sceneId === 'dual-director') {
        if (d.langCode === 3) {
            return { size: focused ? 3.4 : 1.4, color: [...hexToRgb(COLORS.dialect), focused ? 0.86 : 0.18], glow: false };
        }
        if (d.langCode === 2) {
            return { size: focused ? 3.2 : 1.4, color: [...hexToRgb(COLORS.chinaBlue), focused ? 0.82 : 0.16], glow: false };
        }
        return { size: 1.15, color: [255, 255, 255, 0.08], glow: false };
    }
    if (sceneId === 'global-layers') {
        const group = globalLayerOf(d);
        let color = [255, 255, 255, 0.14];
        if (group === 3) color = [...hexToRgb(COLORS.dialect), 0.8];
        else if (group === 4) color = [...hexToRgb(COLORS.chinaBlue), 0.7];
        else if (group >= 0) color = [255, 255, 255, 0.38];
        return { size: group === 3 || group === 4 ? 2.8 : 1.6, color, glow: false };
    }
    if (sceneId === 'dialect-flops') {
        const lit = isFlopLit(d, resolveFlopPhase(flopPhase));
        const role = dialectFlopRole(d);
        if (!lit) return { size: 1.2, color: [220, 220, 226, 0.1], glow: false };
        if (role === 3) return { size: 6.5, color: [...hexToRgb(COLORS.dialect), 0.95], glow: true };
        if (role === 2 || role === 1) return { size: 3.2, color: [...hexToRgb(COLORS.dialect), 0.8], glow: false };
        return { size: 1.4, color: [255, 209, 102, 0.28], glow: false };
    }
    return { size: 1.6, color: [220, 220, 226, 0.16], glow: false };
}

function selectDrawRows(budget) {
    if (particleData.length <= budget) return particleData;
    const focused = [];
    const keep = [];
    const rest = [];
    for (let i = 0; i < particleData.length; i += 1) {
        const row = particleData[i];
        if (isSceneFocused(row)) focused.push(row);
        else if (row.mobileKeep || row.dustKeep) keep.push(row);
        else rest.push(row);
    }
    if (focused.length >= budget) return focused;
    const fill = keep.concat(rest);
    return focused.concat(fill.slice(0, budget - focused.length));
}

function projectDataPoint(x, y, axes, box) {
    const affine = particleChart ? seriesPixelAffine(0) : null;
    if (affine) {
        return [
            affine.origin[0] + x * affine.sx + y * affine.tx,
            affine.origin[1] + x * affine.sy + y * affine.ty
        ];
    }
    return plotToPixel(x, y, axes, box);
}

function buildPixelPlot(sceneId, rows) {
    const env = layoutEnv(sceneId);
    const axes = layoutAxes(sceneId, env);
    const box = scenePlotBox(sceneId);
    const items = [];
    for (let i = 0; i < rows.length; i += 1) {
        const d = rows[i];
        const point = layoutXY(sceneId, d, env);
        const pixel = projectDataPoint(point.x, point.y, axes, box);
        const look = particleLook(sceneId, d);
        items.push({
            id: d.id,
            x: pixel[0],
            y: pixel[1],
            size: look.size,
            color: look.color,
            glow: look.glow
        });
    }
    return items;
}

function blitPixelItems(items) {
    if (!universeLayer) return;
    universeLayer.begin(items.length, 1);
    for (let i = 0; i < items.length; i += 1) {
        const item = items[i];
        universeLayer.pushPixel(item.x, item.y, item.size, item.color, item.glow, item.id);
    }
    universeLayer.draw();
}

function startPlotTween(snap, toItems) {
    stopPlotTween();
    const n = toItems.length;
    const fromX = new Float32Array(n);
    const fromY = new Float32Array(n);
    const fromS = new Float32Array(n);
    const fromR = new Float32Array(n);
    const fromG = new Float32Array(n);
    const fromB = new Float32Array(n);
    const fromA = new Float32Array(n);
    const toX = new Float32Array(n);
    const toY = new Float32Array(n);
    const toS = new Float32Array(n);
    const toR = new Float32Array(n);
    const toG = new Float32Array(n);
    const toB = new Float32Array(n);
    const toA = new Float32Array(n);
    const glow = new Uint8Array(n);
    const ids = new Int32Array(n);
    const index = new Map();
    for (let i = 0; i < snap.n; i += 1) index.set(snap.ids[i], i);
    for (let i = 0; i < n; i += 1) {
        const item = toItems[i];
        const prev = index.get(item.id);
        toX[i] = item.x;
        toY[i] = item.y;
        toS[i] = item.size;
        toR[i] = item.color[0];
        toG[i] = item.color[1];
        toB[i] = item.color[2];
        toA[i] = item.color[3];
        glow[i] = item.glow ? 1 : 0;
        ids[i] = item.id;
        if (prev == null) {
            fromX[i] = item.x;
            fromY[i] = item.y;
            fromS[i] = item.size;
            fromR[i] = item.color[0];
            fromG[i] = item.color[1];
            fromB[i] = item.color[2];
            fromA[i] = 0;
        } else {
            fromX[i] = snap.xs[prev];
            fromY[i] = snap.ys[prev];
            fromS[i] = snap.sizes[prev];
            fromR[i] = snap.rCh[prev];
            fromG[i] = snap.gCh[prev];
            fromB[i] = snap.bCh[prev];
            fromA[i] = snap.aCh[prev];
        }
    }
    const t0 = performance.now();
    const tick = now => {
        const t = easeCubicOut((now - t0) / TWEEN_MS);
        universeLayer.begin(n, 1);
        for (let i = 0; i < n; i += 1) {
            universeLayer.pushPixel(
                fromX[i] + (toX[i] - fromX[i]) * t,
                fromY[i] + (toY[i] - fromY[i]) * t,
                fromS[i] + (toS[i] - fromS[i]) * t,
                [
                    fromR[i] + (toR[i] - fromR[i]) * t,
                    fromG[i] + (toG[i] - fromG[i]) * t,
                    fromB[i] + (toB[i] - fromB[i]) * t,
                    fromA[i] + (toA[i] - fromA[i]) * t
                ],
                glow[i] === 1 && t > 0.7,
                ids[i]
            );
        }
        universeLayer.draw();
        if (t < 1 && activeSceneId !== 'universe') {
            plotTweenRaf = requestAnimationFrame(tick);
            return;
        }
        plotTweenRaf = 0;
    };
    plotTweenRaf = requestAnimationFrame(tick);
}

function paintStoryParticles(sceneId, allowTween = true) {
    if (!universeLayer) return;
    if (sceneId === 'universe') {
        stopPlotTween();
        paintUniverseLive();
        return;
    }
    const items = buildPixelPlot(sceneId, selectDrawRows(TWEEN_BUDGET));
    const canTween = allowTween
        && !prefersReducedMotion()
        && universeLayer.count() > 0;
    if (!canTween) {
        blitPixelItems(items);
        return;
    }
    startPlotTween(universeLayer.snapshot(), items);
}

function paintLanguageStarfield() {
    paintStoryParticles(activeSceneId, true);
}

function prologueMotionBusy() {
    if (prefersReducedMotion()) return false;
    if (prologueState === PROLOGUE_STATES.WORLD_MAP) {
        return prologueMotion.reveal < 0.999 || prologueMotion.fly < 0.999;
    }
    if (prologueState === PROLOGUE_STATES.STAR_FIELD) {
        return prologueMotion.release < 0.999;
    }
    return prologueMotion.gather < 0.999;
}

function startUniverseLoop() {
    if (universeRaf) return;
    stopPlotTween();
    const tick = () => {
        universeRaf = 0;
        if (activeSceneId !== 'universe' || document.hidden) return;
        paintUniverseLive();
        if (prologueMotionBusy()) {
            universeRaf = requestAnimationFrame(tick);
        } else {
            lastUniverseMotionKey = '';
            paintUniverseLive();
        }
    };
    universeRaf = requestAnimationFrame(tick);
}

const particleScenes = {
    'universe': () => {
        const ar = universeChartAr();
        return {
            backgroundColor: 'transparent',
            animation: false,
            animationDurationUpdate: 0,
            xAxis: { show: false, min: 0, max: 100 * ar },
            yAxis: { show: false, min: 0, max: 100 },
            series: [{
                _noDim: true,
                type: 'scatter',
                data: [],
                silent: true,
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
                data: [],
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
                data: [],
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
    'decade-bubble': () => {
        const selectedDecade = sceneState['decade-bubble'];
        const decadeStats = summarize(particleData.filter(row => decadeOf(row.year) === selectedDecade));
        return {
            backgroundColor: 'transparent',
            animationDurationUpdate: 2000,
            xAxis: { 
                type: 'value', min: sampleYearExtent[0], max: sampleYearExtent[1],
                splitLine: { show: false },
                axisLine: { show: true, lineStyle: { color: 'rgba(255,255,255,0.3)' } },
                axisLabel: {
                    color: '#FFF',
                    formatter: value => String(Math.round(value)),
                    showMinLabel: false,
                    showMaxLabel: false
                },
                name: '年份 (Year)', nameTextStyle: { color: '#FFF', fontSize: 14 }
            },
            yAxis: { 
                type: 'value', min: sampleRatingExtent[0], max: sampleRatingExtent[1],
                splitLine: { show: false },
                axisLine: { show: true, lineStyle: { color: 'rgba(255,255,255,0.3)' } },
                axisLabel: { color: '#FFF' }
            },
            series: [{
                type: 'scatter',
                data: [],
                symbolSize: val => val[2] === 1 ? 5 : 2,
                itemStyle: { 
                    color: p => p.value[2] === 1 ? 'rgba(185, 196, 206, 0.86)' : 'rgba(255, 255, 255, 0.12)'
                },
                markLine: createGuideMarkLine([
                    horizontalGuide(decadeStats.mean, `${selectedDecade} 均值 ${decadeStats.mean.toFixed(2)}`, GUIDE_COLORS.selected, 'insideEndBottom'),
                    horizontalGuide(8.5, '编辑高分阈值 8.5', GUIDE_COLORS.threshold, 'insideEndTop'),
                    verticalGuide(1994, '1994 年', GUIDE_COLORS.selected)
                ]),
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
                data: [],
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
    'century-decline': () => {
        const cutoff = Number(sceneState['century-decline']);
        const before = summarize(particleData.filter(row => row.year < cutoff));
        const after = summarize(particleData.filter(row => row.year >= cutoff));
        return {
            backgroundColor: 'transparent',
            animationDurationUpdate: 2000,
            xAxis: { 
                type: 'value', min: sampleYearExtent[0], max: sampleYearExtent[1], splitLine: { show: false },
                axisLine: { show: true, lineStyle: { color: 'rgba(255,255,255,0.3)' } },
                axisLabel: {
                    color: '#FFF',
                    formatter: value => String(Math.round(value)),
                    showMinLabel: false,
                    showMaxLabel: false
                },
                name: '年份 (Year)', nameTextStyle: { color: '#FFF', fontSize: 14 }
            },
            yAxis: { 
                type: 'value', min: sampleRatingExtent[0], max: sampleRatingExtent[1], splitLine: { show: false },
                axisLine: { show: true, lineStyle: { color: 'rgba(255,255,255,0.3)' } },
                axisLabel: { color: '#FFF' }
            },
            series: [{
                type: 'scatter',
                data: [],
                symbolSize: 4,
                itemStyle: { 
                    color: p => p.value[2] === 1 ? COLORS.afterCutoff : 'rgba(132, 182, 244, 0.48)'
                },
                markLine: createGuideMarkLine([
                    horizontalGuide(before.mean, `此前均值 ${before.mean.toFixed(2)}`, GUIDE_COLORS.before, 'insideEndTop'),
                    horizontalGuide(after.mean, `此后均值 ${after.mean.toFixed(2)}`, GUIDE_COLORS.after, 'insideEndBottom'),
                    horizontalGuide(8.5, '编辑高分阈值 8.5', GUIDE_COLORS.threshold, 'insideEndTop'),
                    verticalGuide(cutoff, `分界 ${cutoff}`)
                ]),
                markArea: horizontalDifferenceBand(before.mean, after.mean, 'rgba(255, 138, 101, 0.10)'),
                universalTransition: true
            }]
        };
    },
    'european-slow': () => {
        const selectedRegion = Number(sceneState['european-slow']);
        const regionOrder = [0, 1, 2, 3, 4].filter(code => code !== selectedRegion).concat(selectedRegion);
        const regionPosition = code => regionOrder.indexOf(code);
        const regionStats = summarize(particleData.filter(row => row.regionCode === selectedRegion));
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
                data: [],
                symbolSize: val => val[2] === selectedRegion ? 6 : 2,
                itemStyle: { 
                    color: p => {
                        if (p.value[2] !== selectedRegion) return 'rgba(255, 255, 255, 0.14)';
                        const row = particleData[p.value[3]];
                        if (row && row.rating < 5) return GUIDE_COLORS.threshold;
                        return 'rgba(236, 232, 224, 0.84)';
                    }
                },
                markLine: createGuideMarkLine([
                    horizontalGuide(regionStats.q1, `${REGION_LABELS[selectedRegion]} Q1 ${regionStats.q1.toFixed(2)}`, GUIDE_COLORS.q1, 'insideEndBottom'),
                    horizontalGuide(regionStats.median, `${REGION_LABELS[selectedRegion]}中位数 ${regionStats.median.toFixed(2)}`, GUIDE_COLORS.median, 'insideEndTop'),
                    horizontalGuide(5, '低分界线 5.0', GUIDE_COLORS.threshold, 'insideEndTop'),
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
        const mandarin = summarize(selectedRows.filter(row => row.langCode === 2));
        const dialect = summarize(selectedRows.filter(row => row.langCode === 3));
        return {
            backgroundColor: 'transparent',
            animationDurationUpdate: 2000,
            xAxis: { 
                type: 'value', min: -0.8, max: 5.8, interval: 1, splitLine: { show: false },
                axisLine: { show: true, lineStyle: { color: 'rgba(255,255,255,0.3)' } },
                axisLabel: { 
                    formatter: val => {
                        const i = Math.round(val);
                        return Math.abs(val - i) < 0.1 ? LANGUAGE_LABELS[LANGUAGE_DISPLAY_ORDER[i]] || '' : '';
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
                data: [],
                symbolSize: val => {
                    if (val[2] !== 2 && val[2] !== 3) return 2;
                    return val[4] ? 6 : 2;
                },
                itemStyle: { 
                    color: p => {
                        const code = p.value[2];
                        if (code === 3) return COLORS.dialect; // 方言混血 (黄)
                        if (code === 2) return COLORS.chinaBlue; // 普通话 (蓝)
                        return 'rgba(255, 255, 255, 0.08)'; // 其他 (暗)
                    }
                },
                markLine: createGuideMarkLine([
                    horizontalGuide(mandarin.n ? mandarin.mean : NaN, `普通话均值 ${mandarin.n ? mandarin.mean.toFixed(2) : '--'}`, GUIDE_COLORS.mandarin, 'insideEndTop'),
                    horizontalGuide(dialect.n ? dialect.mean : NaN, `方言均值 ${dialect.n ? dialect.mean.toFixed(2) : '--'}`, GUIDE_COLORS.dialect, 'insideEndBottom'),
                    verticalGuide(3.5, '两组分界', GUIDE_COLORS.selected)
                ]),
                markArea: horizontalDifferenceBand(
                    mandarin.n ? mandarin.mean : NaN,
                    dialect.n ? dialect.mean : NaN,
                    'rgba(255, 209, 102, 0.10)'
                ),
                universalTransition: true
            }]
        };
    },
    'dual-director': () => {
        const selected = sceneState['dual-director'];
        const selectedRows = particleData.filter(row => SCENE_INTERACTIONS['dual-director'].filter(row, selected));
        const mandarin = summarize(selectedRows.filter(row => row.langCode === 2));
        const dialect = summarize(selectedRows.filter(row => row.langCode === 3));
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
                data: [],
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
        const names = compact
            ? GLOBAL_LAYER_GROUPS.map(group => group.short)
            : GLOBAL_LAYER_GROUPS.map(group => group.label);
        const rates = GLOBAL_LAYER_GROUPS.map(group => globalLayerRate(group.jsonName, group.fallback));
        const guides = showThreshold
            ? [{
                ...horizontalGuide(5, '5.0｜低分下限', GUIDE_COLORS.threshold, 'insideEndTop'),
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
                max: phase === 'pull-back' ? 5.8 : 4.7,
                interval: 1,
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
                        const i = Math.round(val);
                        if (Math.abs(val - i) >= 0.1 || i < 0) return '';
                        if (phase === 'pull-back') {
                            return i <= 5 ? (LANGUAGE_LABELS[LANGUAGE_DISPLAY_ORDER[i]] || '') : '';
                        }
                        if (i > 4) return '';
                        if (phase === 'four-groups' && i === 4) return '';
                        if (phase === 'axes') return names[i] || '';
                        return `${names[i]}\n${rates[i]}`;
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
                data: [],
                symbolSize: val => {
                    const group = val[2];
                    const movie = particleData[val[3]];
                    if (phase === 'pull-back') {
                        return movie && (movie.langCode === 2 || movie.langCode === 3) ? 4 : 2;
                    }
                    if (group < 0) return 1.5;
                    if (phase === 'four-groups' && group === 4) return 2;
                    if (phase === 'mandarin-outlier' && group === 4) return 2.4;
                    if (phase === 'mandarin-outlier') return 2.1;
                    if (phase === 'boundary') return 2.4;
                    return 2.8;
                },
                itemStyle: {
                    color: p => {
                        const group = p.value[2];
                        const movie = particleData[p.value[3]];
                        const below = p.value[1] < 5;
                        if (phase === 'pull-back') {
                            if (movie && movie.langCode === 3) return COLORS.dialect;
                            if (movie && movie.langCode === 2) return COLORS.chinaBlue;
                            return 'rgba(255, 255, 255, 0.08)';
                        }
                        if (group < 0) return 'rgba(255, 255, 255, 0.05)';
                        if (phase === 'four-groups' && group === 4) {
                            return 'rgba(98, 176, 255, 0.16)';
                        }
                        if (phase === 'mandarin-outlier') {
                            if (group === 4) {
                                return below ? 'rgba(98, 176, 255, 0.42)' : 'rgba(98, 176, 255, 0.26)';
                            }
                            return group === 3 ? 'rgba(255, 179, 0, 0.28)' : 'rgba(255, 255, 255, 0.14)';
                        }
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
    'final-universe': () => ({
        backgroundColor: 'transparent',
        animation: false,
        animationDurationUpdate: 0,
        xAxis: { show: false, min: 0, max: 100 },
        yAxis: { show: false, min: 0, max: 100 },
        series: [{
            type: 'scatter',
            data: [],
            silent: true,
            universalTransition: false
        }]
    }),
    'dialect-flops': () => {
        const phase = resolveFlopPhase(flopPhase);
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
                data: [],
                _noDim: true,
                symbolSize: val => {
                    if (!val || val[4] === 0) return 1.2;
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
                        if (!p.value || p.value[4] === 0) return 'rgba(220, 220, 226, 0.10)';
                        const role = p.value[2];
                        if (phase === 'cases' && role === 3) return COLORS.dialect;
                        if (role === 2 || role === 3) return COLORS.dialect;
                        return 'rgba(255, 209, 102, 0.28)';
                    }
                },
                markLine: createGuideMarkLine(guides),
                universalTransition: true
            }]
        };
    }
};
particleScenes['three-waves'] = particleScenes['final-universe'];
particleScenes['scale'] = particleScenes['final-universe'];
particleScenes['echo-narrative'] = particleScenes['final-universe'];

function sceneVisualKey(sceneId) {
    if (sceneId === 'universe') return `universe:${prologueState}:${prologueFocusGroup || ''}`;
    if (STARFIELD_SCENES.has(sceneId)) return `starfield:${sceneId}:${String(sceneState[sceneId] ?? '')}`;
    return `chart:${sceneId}:${String(sceneState[sceneId] ?? '')}:${globalLayersPhase}:${flopPhase}`;
}

function renderParticleScene(sceneId, force = false) {
    runtime.activeSceneId = sceneId;
    document.documentElement.dataset.activeScene = sceneId;
    const isCoverUniverse = sceneId === 'universe';
    const isStarfield = STARFIELD_SCENES.has(sceneId);
    const chartDom = document.getElementById('chart-container');
    if (chartDom) {
        if (chartDom.dataset.echoLayer) delete chartDom.dataset.echoLayer;
        if (!chartDom.dataset.waveLayer) {
            chartDom.classList.toggle('is-behind', isCoverUniverse || isStarfield);
        }
    }
    if (universeLayer) universeLayer.setVisible(isCanvasParticleScene(sceneId));
    const visualKey = sceneVisualKey(sceneId);
    if (!force && visualKey === lastVisualKey) {
        if (isCoverUniverse) startUniverseLoop();
        return;
    }
    lastVisualKey = visualKey;
    if(!particleChart || !particleScenes[sceneId]) return;
    const option = particleScenes[sceneId]();
    const largeDataset = particleData.length > 20000;
    const reducedMotion = prefersReducedMotion();
    const compactMotion = reducedMotion || largeDataset;
    const isUniverse = sceneId === 'universe' || sceneId === 'final-universe' || sceneId === 'three-waves' || sceneId === 'scale' || sceneId === 'echo-narrative';
    const isGlobalLayers = sceneId === 'global-layers';
    const isDialectFlops = sceneId === 'dialect-flops';
    option.animation = !(largeDataset || compactMotion);
    option.animationDurationUpdate = option.animation ? (isUniverse ? 0 : 420) : 0;
    option.animationEasingUpdate = 'cubicOut';
    if (isCoverUniverse || isStarfield) {
        option.animation = false;
        option.animationDurationUpdate = 0;
    }
    const hasVisibleAxes = sceneId !== 'universe' && sceneId !== 'final-universe' && sceneId !== 'three-waves' && sceneId !== 'scale' && sceneId !== 'echo-narrative';
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
        series.universalTransition = false;
        series.progressiveChunkMode = 'mod';
        if (isCoverUniverse || isStarfield || isCanvasParticleScene(sceneId)) {
            series.data = [];
            series.progressive = 0;
            series.silent = true;
            series.itemStyle = series.itemStyle || {};
            series.large = false;
        } else {
            if (largeDataset) {
                series.large = true;
                series.largeThreshold = 500;
                series.progressive = 0;
                series.progressiveThreshold = 1e9;
            } else {
                series.large = false;
                series.progressive = 0;
                series.progressiveThreshold = 3000;
            }
            const originalColor = series.itemStyle && series.itemStyle.color;
            const originalSize = series.symbolSize;
            const unfocusedColor = series.unfocusedColor || 'rgba(255, 255, 255, 0.12)';
            const unfocusedSize = Number.isFinite(Number(series.unfocusedSize))
                ? Number(series.unfocusedSize)
                : (largeDataset ? 1.2 : 1.5);
            delete series.unfocusedColor;
            delete series.unfocusedSize;
            series.itemStyle = series.itemStyle || {};
            series.itemStyle.color = params => {
                if (!series._noDim && params.value && params.value[4] === 0) return unfocusedColor;
                return typeof originalColor === 'function' ? originalColor(params) : originalColor;
            };
            series.symbolSize = value => {
                if (value && value[4] === 0) return unfocusedSize;
                const size = typeof originalSize === 'function' ? originalSize(value) : originalSize;
                if (series._noDim || isGlobalLayers || isDialectFlops) return size;
                return largeDataset ? Math.max(1.2, Math.min(3.2, Number(size) * 0.64)) : size;
            };
            series.emphasis = isDialectFlops
                ? { scale: 1.35, itemStyle: { borderColor: 'rgba(255,255,255,0.4)', borderWidth: 1, shadowBlur: 0 } }
                : {
                    scale: largeDataset ? 1.35 : 2.2,
                    itemStyle: { borderColor: '#FFFFFF', borderWidth: 1, shadowBlur: 0 }
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
            return movieTooltipHtml(particleData[raw && raw[3]]);
        }
    };
    particleChart.setOption(option, true);
    rememberPlottedSeries(option.series);
    if (isCoverUniverse) {
        stopPlotTween();
        startUniverseLoop();
    } else if (isCanvasParticleScene(sceneId)) {
        paintStoryParticles(sceneId, !force);
    }
    if (isDialectFlops) {
        scheduleFlopOverlay(0);
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

function fillWorldScale() {
    const rungs = getWorldScaleRungs();
    const rungsEl = document.getElementById('world-scale-rungs');
    if (!rungs || !rungsEl) return;

    const shown = Object.fromEntries(rungs.map(rung => [rung.key, Number(rung.score.toFixed(2))]));
    const scores = rungs.map(rung => shown[rung.key]);
    const top = Math.max(...scores) + 0.15;
    const bot = Math.min(...scores) - 0.13;
    const yPct = score => ((top - score) / (top - bot)) * 100;
    const plus = value => `+${Math.abs(value).toFixed(2)}`;
    const keys = rungs.map(rung => rung.key);
    const linearY = Object.fromEntries(keys.map(key => [key, yPct(shown[key])]));
    const spreadY = spreadScalePositions(linearY, keys);

    const glow = hex => {
        const n = parseInt(hex.slice(1), 16);
        return `rgba(${(n >> 16) & 255},${(n >> 8) & 255},${n & 255},0.16)`;
    };
    rungsEl.innerHTML = rungs.map(rung => {
        const score = shown[rung.key];
        const tag = rung.isKey ? '<span class="tagline">我们最好的成绩</span>' : '';
        return `<button type="button" class="world-scale-rung" style="--y:${spreadY[rung.key].toFixed(2)}%;--c:${rung.color};--c-bg:${glow(rung.color)}" data-key="${rung.key}" data-name="${escapeHtml(rung.name)}" data-score="${score.toFixed(2)}" data-med="${Number.isFinite(Number(rung.med)) ? Number(rung.med).toFixed(1) : ''}" data-n="${Number(rung.n).toLocaleString('zh-CN')}" data-note="${escapeHtml(rung.note)}" aria-label="${escapeHtml(rung.name)} 均分 ${score.toFixed(2)}">
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
        setTextById('china-count', Number(agg.meta.baseline.china_total).toLocaleString('zh-CN'));
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
    if (facts && facts.decades) {
        const pre = facts.decades['Pre-1990s'];
        const recent = facts.decades['2020s'];
        if (pre) setTextById('decade-pre-mean', Number(pre.mean).toFixed(2));
        if (recent) setTextById('decade-2020s-mean', Number(recent.mean).toFixed(2));
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
        if (d1990) {
            setTextById('delta-1990s', Math.abs(Number(d1990.delta)).toFixed(2));
            setTextById('dialect-delta-1990s', `${Number(d1990.delta) >= 0 ? '+' : ''}${Number(d1990.delta).toFixed(2)}`);
        }
        if (d2010) {
            setTextById('delta-2010s', Math.abs(Number(d2010.delta)).toFixed(2));
            setTextById('dialect-delta-2010s', `${Number(d2010.delta) >= 0 ? '+' : ''}${Number(d2010.delta).toFixed(2)}`);
        }
        if (d2020) {
            setTextById('delta-2020s', `${Number(d2020.delta) >= 0 ? '+' : ''}${Number(d2020.delta).toFixed(2)}`);
            setTextById('china-dialect-2020s-n', String(d2020.d.n));
        }
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
function fillFlopNarrative() {
    const stats = dialectFlopStats();
    const lead = document.getElementById('flop-lead-copy');
    if (lead && stats.n) {
        lead.innerHTML = `${stats.n.toLocaleString('zh-CN')} 部方言片中仍有 <strong>${stats.flopN.toLocaleString('zh-CN')}</strong> 部低于 5 分。`;
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
    // 层 1：同导演对比直方图
    const histContainer = document.getElementById('director-hist');
    if (histContainer && dialectAgg.dual_director) {
        const dd = dialectAgg.dual_director;
        const hist = dd.hist;
        const buckets = Object.keys(hist);
        const maxCount = Math.max(...Object.values(hist));
        histContainer.innerHTML = buckets.map(b => {
            const pct = (hist[b] / maxCount * 100).toFixed(1);
            const positive = b.startsWith('+') || b.startsWith('≥');
            const cls = positive ? ' positive' : (b === '0' ? '' : ' negative');
            return `<div class="hist-row${cls}">
                <span class="hist-label">${escapeHtml(b)}</span>
                <div class="hist-bar-track"><div class="hist-bar" style="width:${pct}%"></div></div>
                <span class="hist-count">${hist[b]}</span>
            </div>`;
        }).join('');
        const ddShare = document.getElementById('dd-share');
        const ddDiff = document.getElementById('dd-diff');
        if (ddShare) { ddShare.textContent = dd.share_positive + '%'; ddShare.classList.remove('is-pending'); }
        if (ddDiff) { ddDiff.textContent = '+' + dd.mean_diff.toFixed(2); ddDiff.classList.remove('is-pending'); }
        setTextById('scale-dd-share', `${dd.share_positive}%`);
    }
    // 层 3：语言多样性条
    const langContainer = document.getElementById('lang-bars');
    if (langContainer && dialectAgg.lang_diversity) {
        const langs = dialectAgg.lang_diversity;
        langContainer.innerHTML = langs.map(l => {
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
                    el.style.opacity = '';
                    el.classList.toggle('is-behind', isCanvasParticleScene(activeSceneId));
                }
            }
            if (universeLayer) {
                universeLayer.setVisible(!hidden && isCanvasParticleScene(activeSceneId));
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
