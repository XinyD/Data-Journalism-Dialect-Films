// js/core.js
// Singleton Data Service for fetching and holding the dataset

import { escapeHtml } from './lib/dom.js';
import { populateMovieDetail } from './lib/movie-detail.js';
import { prefersReducedMotion, rafThrottle, debounce } from './lib/schedule.js';

const ANALYSIS_LANGUAGE_LABELS = ['英语', '日语', '普通话', '方言', '韩语', '其他'];
const DEFAULT_FETCH_TIMEOUT_MS = 30000;

async function fetchJson(url, timeoutMs = DEFAULT_FETCH_TIMEOUT_MS) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeoutMs);
    try {
        const response = await fetch(url, { signal: controller.signal });
        if (!response.ok) {
            throw new Error(`HTTP ${response.status} for ${url}`);
        }
        return await response.json();
    } catch (error) {
        if (error && error.name === 'AbortError') {
            throw new Error(`Timed out after ${timeoutMs}ms: ${url}`);
        }
        throw error;
    } finally {
        clearTimeout(timer);
    }
}

export const StoryUI = {
    counted: new Set(),

    showBootError(error) {
        const root = document.getElementById('boot-error');
        const message = document.getElementById('boot-error-message');
        const retry = document.getElementById('boot-error-retry');
        if (message) {
            message.textContent = '数据加载失败。请通过本地服务器打开页面，不要直接双击 HTML。';
        }
        if (retry && !retry.dataset.bound) {
            retry.dataset.bound = '1';
            retry.addEventListener('click', () => window.location.reload());
        }
        if (root) {
            root.hidden = false;
            return;
        }
        console.error('Failed to load dataset:', error);
    },

    showRuntimeError(message) {
        const root = document.getElementById('boot-error');
        const title = document.getElementById('boot-error-title');
        const detail = document.getElementById('boot-error-message');
        const retry = document.getElementById('boot-error-retry');
        if (title) title.textContent = '页面运行出错';
        if (detail) detail.textContent = String(message || '发生未知错误，请刷新页面重试。');
        if (retry && !retry.dataset.bound) {
            retry.dataset.bound = '1';
            retry.addEventListener('click', () => window.location.reload());
        }
        if (root) {
            root.hidden = false;
            return;
        }
        console.error('Runtime error:', message);
    },

    rafThrottle,

    debounce,

    prefersReducedMotion,

    ratingTier(rating) {
        const value = Number(rating);
        if (!Number.isFinite(value)) return 'is-mid';
        if (value < 5) return 'is-low';
        if (value >= 8) return 'is-high';
        return 'is-mid';
    },

    ratingBadge(rating) {
        const value = Number(rating);
        const label = Number.isFinite(value) ? value.toFixed(1) : '--';
        return `<span class="movie-rating ${this.ratingTier(value)}">${label}</span>`;
    },

    animateCount(el, formatted, numeric) {
        if (!el) return;
        if (numeric == null || this.prefersReducedMotion() || this.counted.has(el.id)) {
            el.textContent = formatted;
            if (el.id) this.counted.add(el.id);
            return;
        }
        this.counted.add(el.id);
        const start = performance.now();
        const duration = 900;
        const suffix = String(formatted).endsWith('%') ? '%' : '';
        const decimals = suffix ? 1 : (Number.isInteger(numeric) ? 0 : 2);
        const tick = now => {
            const t = Math.min(1, (now - start) / duration);
            const eased = 1 - ((1 - t) ** 3);
            const current = numeric * eased;
            el.textContent = decimals
                ? `${current.toFixed(decimals)}${suffix}`
                : Math.round(current).toLocaleString('zh-CN');
            if (t < 1) requestAnimationFrame(tick);
            else el.textContent = formatted;
        };
        requestAnimationFrame(tick);
    }
};

export const DataService = {
    dataset: [],
    meta: {},
    visualMasks: null,
    movieDetails: new Map(),
    detailShardPromises: new Map(),
    loaded: false,
    fetchJson,

    async init(options = {}) {
        if (this.loaded) return;
        const slim = Boolean(options.slim);
        try {
            const payload = await fetchJson('../data/frontend_dataset.json');
            if (Array.isArray(payload)) {
                // Backward compatibility with the first publication payload.
                this.dataset = payload;
                this.meta = { recordCount: payload.length };
            } else {
                if (!Array.isArray(payload.columns) || !Array.isArray(payload.records)) {
                    throw new Error('Publication payload has an invalid schema');
                }
                const columns = Object.fromEntries(payload.columns.map((name, index) => [name, index]));
                this.dataset = payload.records.map(row => ({
                    movieId: String(row[columns.movieId]),
                    title: row[columns.title],
                    year: Number(row[columns.year]),
                    rating: Number(row[columns.rating]),
                    votes: Number(row[columns.votes]),
                    decade: row[columns.decade],
                    region: row[columns.region],
                    language: row[columns.language],
                    genres: row[columns.genres],
                    regionCode: Number(row[columns.regionCode]),
                    genreCode: Number(row[columns.genreCode]),
                    langCode: Number(row[columns.langCode]),
                    languageGroup: ANALYSIS_LANGUAGE_LABELS[Number(row[columns.langCode])] || '未分类',
                    isDialect: Number(row[columns.isDialect]) === 1
                }));
                this.meta = payload.meta || { recordCount: this.dataset.length };
                if (Number(this.meta.recordCount) !== this.dataset.length) {
                    throw new Error('Publication payload record count does not match its metadata');
                }
            }
            if (!slim) {
            // Load geographic enrichment data (lat/lng/geoRegion per movie)
            try {
                const geoPayload = await fetchJson('../data/frontend/geo_enrichment.json');
                const geoFingerprint = geoPayload.meta && geoPayload.meta.sampleFingerprint;
                const expectedFingerprint = this.meta.sampleFingerprint;
                if (expectedFingerprint && geoFingerprint && geoFingerprint !== expectedFingerprint) {
                    console.warn(
                        'Geo enrichment belongs to a different publication sample; skipping lat/lng merge.',
                        { geo: geoFingerprint, expected: expectedFingerprint }
                    );
                } else if (Array.isArray(geoPayload.columns) && Array.isArray(geoPayload.records)
                    && geoPayload.records.length === this.dataset.length) {
                    const gc = Object.fromEntries(geoPayload.columns.map((name, index) => [name, index]));
                    this.geoRegionLabels = (geoPayload.meta && geoPayload.meta.geoRegionLabels) || {};
                    this.dataset.forEach((movie, i) => {
                        const row = geoPayload.records[i];
                        movie.lat = Number(row[gc.lat]);
                        movie.lng = Number(row[gc.lng]);
                        movie.geoRegion = Number(row[gc.geoRegion]);
                        movie.country = row[gc.country] || '';
                        movie.dlng = Number(row[gc.dlng]) || 1.5;
                        movie.dlat = Number(row[gc.dlat]) || 1.5;
                    });
                }
            } catch (geoError) {
                console.warn("Geo enrichment not loaded (optional):", geoError.message);
            }

            // Visual land masks: layout only, does not change frozen geography.
            try {
                this.visualMasks = await fetchJson('../data/frontend/visual_land_masks.json');
            } catch (maskError) {
                console.warn("Visual land masks not loaded (optional):", maskError.message);
            }
            }

            document.querySelectorAll('[data-publication-count]').forEach(node => {
                node.textContent = this.dataset.length.toLocaleString('zh-CN');
            });
            this.loaded = true;
        } catch (error) {
            console.error("Failed to load dataset:", error);
            StoryUI.showBootError(error);
        }
    },

    detailShard(movieId) {
        let hash = 0;
        const value = String(movieId);
        for (let index = 0; index < value.length; index += 1) {
            hash = (Math.imul(hash, 31) + value.charCodeAt(index)) >>> 0;
        }
        return hash % 64;
    },

    async loadMovieDetailShard(movieId) {
        const shard = this.detailShard(movieId);
        if (!this.detailShardPromises.has(shard)) {
            const shardName = shard.toString(16).padStart(2, '0');
            const promise = (async () => {
                const response = await fetch(`../data/frontend/details/${shardName}.json`);
                if (!response.ok) throw new Error('Movie detail payload could not be loaded');
                const payload = await response.json();
                if (!Array.isArray(payload.columns) || !Array.isArray(payload.records)) {
                    throw new Error('Movie detail payload has an invalid schema');
                }
                if (Number(payload.meta && payload.meta.recordCount) !== payload.records.length) {
                    throw new Error('Movie detail payload record count does not match its metadata');
                }
                if (Number(payload.meta.shard) !== shard || Number(payload.meta.shardCount) !== 64) {
                    throw new Error('Movie detail payload has invalid shard metadata');
                }
                if (
                    this.meta.sampleFingerprint
                    && payload.meta.sampleFingerprint !== this.meta.sampleFingerprint
                ) {
                    throw new Error('Movie detail payload belongs to a different publication sample');
                }
                const columns = Object.fromEntries(payload.columns.map((name, index) => [name, index]));
                payload.records.forEach(row => {
                    this.movieDetails.set(String(row[columns.movieId]), {
                        director: row[columns.director] || '',
                        productionCountries: row[columns.productionCountries] || '',
                        originalLanguages: row[columns.originalLanguages] || '',
                        source: row[columns.source] || '',
                        sourceUrl: row[columns.sourceUrl] || '',
                        summaryKind: Number(row[columns.summaryKind]),
                        summary: row[columns.summary] || ''
                    });
                });
                return shard;
            })();
            this.detailShardPromises.set(shard, promise);
        }
        try {
            return await this.detailShardPromises.get(shard);
        } catch (error) {
            this.detailShardPromises.delete(shard);
            throw error;
        }
    },

    async getMovieDetails(movieId) {
        await this.loadMovieDetailShard(movieId);
        return this.movieDetails.get(String(movieId)) || null;
    },

    doubanUrlFor(movieId) {
        const id = String(movieId || '').trim();
        return /^\d+$/.test(id) ? `https://movie.douban.com/subject/${id}/` : '';
    },

    resolveSourceUrl(movie, details) {
        const raw = details && details.sourceUrl;
        try {
            const url = new URL(raw);
            if (url.protocol === 'http:' || url.protocol === 'https:') return url.href;
        } catch (error) {
            // Fall back to the Douban subject URL derived from movieId.
        }
        return this.doubanUrlFor(movie && movie.movieId);
    },

    applySourceLink(linkEl, url) {
        if (!linkEl) return;
        if (!url) {
            linkEl.hidden = true;
            linkEl.removeAttribute('href');
            return;
        }
        linkEl.hidden = false;
        linkEl.href = url;
        linkEl.textContent = url.includes('douban.com') ? '在豆瓣查看' : '查看来源记录';
    },

    getMoviesByDecade(decade) {
        return this.dataset.filter(m => m.decade === decade);
    },

    getMoviesByRegion(region) {
        return this.dataset.filter(m => m.region === region);
    },

    getMoviesByLanguage(languageCode) {
        return this.dataset.filter(m => m.langCode === Number(languageCode));
    },

    filter(decade, region, language) {
        return this.dataset.filter(m => {
            if (decade && decade !== 'All' && m.decade !== decade) return false;
            if (region && region !== 'All' && m.region !== region) return false;
            if (language && language !== 'All' && m.langCode !== Number(language)) return false;
            return true;
        });
    }
};

// ECharts Cinematic Theme Tokens
export const TOKENS = {
    bg: 'transparent',
    primary: '#8FB2FF',
    secondary: '#5CC8A1',
    accent: '#FF7A73',
    textMain: '#F4F4F5',
    textMuted: '#B4B4BC',
    gridLine: 'rgba(255, 255, 255, 0.14)',
    fontFamily: 'Noto Sans SC, PingFang SC, sans-serif'
};

export function getBaseChartOption() {
    return {
        backgroundColor: TOKENS.bg,
        textStyle: { fontFamily: TOKENS.fontFamily, color: TOKENS.textMain },
        tooltip: {
            backgroundColor: 'rgba(15, 15, 18, 0.96)',
            borderColor: 'rgba(255, 255, 255, 0.2)',
            borderWidth: 1,
            textStyle: { color: TOKENS.textMain },
            padding: 12,
            borderRadius: 4,
            extraCssText: 'box-shadow: 0 12px 36px rgba(0, 0, 0, 0.42);'
        }
    };
}

function escapeMarkup(value) {
    return escapeHtml(value);
}

function createSharedDetailView(dialog) {
    const field = name => dialog.querySelector(`[data-detail-field="${name}"]`);
    return {
        setField(name, value) {
            const node = field(name);
            if (node) node.textContent = value || '未知';
        },
        formatGroups(movie) {
            const regionLabel = String(movie.region || '未知').replaceAll('_', ' ');
            return `${regionLabel} · ${movie.languageGroup || movie.language || '其他'}`;
        },
        setSynopsisVisible(visible) {
            const section = dialog.querySelector('[data-detail-section="synopsis"]');
            if (section) section.hidden = !visible;
        },
        setGeminiVisible(visible) {
            const section = dialog.querySelector('[data-detail-section="gemini"]');
            if (section) section.hidden = !visible;
        },
        getSourceLink() {
            return field('source-link');
        },
        resolveSourceUrl(movie, details) {
            return DataService.resolveSourceUrl(movie, details);
        },
        applySourceLink(linkEl, url) {
            DataService.applySourceLink(linkEl, url);
        },
        getMovieDetails(movieId) {
            return DataService.getMovieDetails(movieId);
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

function ensureSharedMovieDetailDialog() {
    let dialog = document.getElementById('shared-movie-detail-dialog');
    if (dialog) return dialog;

    dialog = document.createElement('dialog');
    dialog.id = 'shared-movie-detail-dialog';
    dialog.className = 'movie-detail-dialog';
    dialog.setAttribute('aria-labelledby', 'shared-movie-detail-title');
    dialog.innerHTML = `
        <article class="movie-detail-panel">
            <header class="movie-detail-header">
                <span>电影详情</span>
                <form method="dialog">
                    <button class="movie-detail-close" type="submit" aria-label="关闭电影详情" title="关闭">×</button>
                </form>
            </header>
            <div class="movie-detail-heading">
                <div>
                    <p data-detail-field="year"></p>
                    <h2 id="shared-movie-detail-title" data-detail-field="title"></h2>
                </div>
                <strong data-detail-field="rating"></strong>
            </div>
            <div class="movie-detail-copy">
                <section data-detail-section="synopsis">
                    <h3>剧情简介</h3>
                    <p data-detail-field="synopsis"></p>
                </section>
                <section data-detail-section="gemini" hidden>
                    <h3>Gemini 生成短评 <span>AI 生成</span></h3>
                    <p data-detail-field="gemini"></p>
                </section>
            </div>
            <dl class="movie-detail-list">
                <div><dt>导演</dt><dd data-detail-field="director"></dd></div>
                <div><dt>类型</dt><dd data-detail-field="genres"></dd></div>
                <div><dt>制片国家／地区</dt><dd data-detail-field="countries"></dd></div>
                <div><dt>语言</dt><dd data-detail-field="languages"></dd></div>
                <div><dt>评价人数</dt><dd data-detail-field="votes"></dd></div>
                <div><dt>分析分类</dt><dd data-detail-field="groups"></dd></div>
                <div><dt>数据来源</dt><dd data-detail-field="source"></dd></div>
                <div><dt>数据集 ID</dt><dd data-detail-field="id"></dd></div>
            </dl>
            <a class="movie-detail-source" data-detail-field="source-link" target="_blank" rel="noopener noreferrer" hidden>在豆瓣查看</a>
        </article>
    `;
    dialog.addEventListener('click', event => {
        if (event.target === dialog) dialog.close();
    });
    document.body.appendChild(dialog);
    return dialog;
}

async function openSharedMovieDetail(movie) {
    if (!movie) return;
    const dialog = ensureSharedMovieDetailDialog();
    dialog.dataset.movieId = String(movie.movieId);
    await populateMovieDetail(movie, createSharedDetailView(dialog));
}

// Shared Gallery Renderer
export function renderLocalGallery(movies, title, containerId = 'movie-grid', limit = 12) {
    const gridEl = document.getElementById(containerId);
    const subtitleEl = document.getElementById('gallery-subtitle');
    
    if (subtitleEl) subtitleEl.innerText = title;
    gridEl.innerHTML = '';

    if (!movies || movies.length === 0) {
        gridEl.innerHTML = `<div class="empty-gallery">当前筛选下没有电影记录。</div>`;
        return;
    }

    // Show a compact, consistently ordered selection below each comparison chart.
    const topMovies = [...movies].sort((a,b) => b.rating - a.rating).slice(0, limit);

    topMovies.forEach(movie => {
        const card = document.createElement('button');
        card.type = 'button';
        card.className = 'movie-card';
        card.dataset.movieId = movie.movieId;
        card.setAttribute('aria-label', `查看《${movie.title}》详情`);
        const genres = (movie.genres || '').split('/').map(g => g.trim()).filter(g => g);
        const genresHtml = genres.map(g => `<span class="genre-badge">${escapeMarkup(g)}</span>`).join('');
        card.innerHTML = `
            <span class="movie-card-top">
                <span class="movie-title">${escapeMarkup(movie.title)} <small>(${escapeMarkup(movie.year || movie.decade || '')})</small></span>
                ${StoryUI.ratingBadge(movie.rating)}
            </span>
            <div class="movie-genres" style="margin-bottom:8px;">${genresHtml}</div>
            <div style="font-size:0.8rem;color:var(--color-text-muted)">
                ${escapeMarkup(movie.decade || '未知年代')} | ${escapeMarkup(String(movie.region || '未知').replaceAll('_', ' '))} | ${escapeMarkup(movie.languageGroup || movie.language || '其他')}
            </div>
            <span class="movie-card-action">查看详情</span>
        `;
        card.addEventListener('click', () => openSharedMovieDetail(movie));
        card.addEventListener('pointerenter', () => {
            DataService.loadMovieDetailShard(movie.movieId).catch(() => {});
        }, { once: true });
        gridEl.appendChild(card);
    });
}

document.addEventListener('DOMContentLoaded', () => {
    const nav = document.querySelector('.volume-page .nav-menu');
    const active = nav && nav.querySelector('.nav-item.active');
    if (!nav || !active || window.innerWidth > 900) return;
    nav.scrollLeft = Math.max(0, active.offsetLeft - (nav.clientWidth - active.clientWidth) / 2);
});

// Expose to window explicitly
window.DataService = DataService;
window.StoryUI = StoryUI;
window.fetchJson = fetchJson;
window.ANALYSIS_LANGUAGE_LABELS = ANALYSIS_LANGUAGE_LABELS;
window.openSharedMovieDetail = openSharedMovieDetail;
window.renderLocalGallery = renderLocalGallery;
window.getBaseChartOption = getBaseChartOption;
window.TOKENS = TOKENS;

function installGlobalErrorHandlers() {
    window.addEventListener('error', event => {
        if (event.defaultPrevented) return;
        const message = event.error?.message || event.message || '页面运行时发生错误';
        StoryUI.showRuntimeError(message);
    });
    window.addEventListener('unhandledrejection', event => {
        const reason = event.reason;
        const message = reason instanceof Error ? reason.message : String(reason || '未处理的异步错误');
        StoryUI.showRuntimeError(message);
    });
}

installGlobalErrorHandlers();
