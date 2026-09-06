import { runtime } from './runtime.js';
import { escapeHtml } from './lib/dom.js';
import { populateMovieDetail } from './lib/movie-detail.js';
import { summarizeDialectFilms } from './lib/dialect-summary.js';

// 快捷家乡话入口：手工挑选覆盖主要方言区，并保证正文提到的方言都在。
const CHIP_FAMILIES = ['粤语', '闽南语', '四川话', '重庆话', '上海话', '河南话', '陕西话', '客家话', '潮汕话'];

const REGION_LABELS = {
    North_America: '北美',
    Europe: '欧洲',
    East_Asia: '东亚',
    China: '中国大陆',
    Other: '其他'
};

const SORTERS = {
    'rating-desc': (a, b) => b.rating - a.rating,
    'rating-asc': (a, b) => a.rating - b.rating,
    'votes-desc': (a, b) => b.votes - a.votes,
    'year-desc': (a, b) => b.year - a.year,
    'year-asc': (a, b) => a.year - b.year
};

let galleryMoviesById = new Map();
let galleryFilteredMovies = [];
let galleryPage = 0;
const GALLERY_PAGE_SIZE = 50;

function regionLabel(region) {
    if (REGION_LABELS[region]) return REGION_LABELS[region];
    return String(region || '未知').replaceAll('_', ' ');
}

function primaryGenre(genres) {
    return String(genres || '').split('/')[0].trim() || '未知';
}

function scrollToGalleryTop() {
    const target = document.getElementById('global-gallery');
    if (!target) return;
    const behavior = window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth';
    target.scrollIntoView({ behavior, block: 'start' });
}

function escapeTooltip(value) {
    return escapeHtml(value);
}

let galleryBound = false;

export function initGallery() {
    if (galleryBound) return;
    galleryBound = true;
    galleryMoviesById = new Map(
        window.DataService.dataset.map(movie => [String(movie.movieId), movie])
    );
    galleryFilteredMovies = window.DataService.dataset;
    renderGalleryPage();

    const grid = document.getElementById('movie-grid');
    if (!grid) return;
    grid.addEventListener('click', event => {
        const card = event.target.closest('.movie-card[data-movie-id]');
        if (!card) return;
        const movie = galleryMoviesById.get(card.dataset.movieId);
        if (movie) runtime.openMovieDetail(movie);
    });
    const preloadMovieDetails = event => {
        const card = event.target.closest('.movie-card[data-movie-id]');
        if (card) window.DataService.loadMovieDetailShard(card.dataset.movieId).catch(() => {});
    };
    grid.addEventListener('pointerover', preloadMovieDetails);
    grid.addEventListener('focusin', preloadMovieDetails);

    runtime.bindMovieDetailDialog();
    bindFilterSheet();

    document.getElementById('gallery-prev')?.addEventListener('click', () => {
        if (galleryPage === 0) return;
        galleryPage -= 1;
        renderGalleryPage();
        scrollToGalleryTop();
    });
    document.getElementById('gallery-next')?.addEventListener('click', () => {
        const pageCount = Math.ceil(galleryFilteredMovies.length / GALLERY_PAGE_SIZE);
        if (galleryPage >= pageCount - 1) return;
        galleryPage += 1;
        renderGalleryPage();
        scrollToGalleryTop();
    });

    const jumpToPage = () => {
        const input = document.getElementById('gallery-page-jump');
        if (!input) return;
        const value = Number.parseInt(input.value, 10);
        if (!Number.isFinite(value)) return;
        const pageCount = Math.max(1, Math.ceil(galleryFilteredMovies.length / GALLERY_PAGE_SIZE));
        const target = Math.min(Math.max(value, 1), pageCount) - 1;
        if (target === galleryPage) return;
        galleryPage = target;
        renderGalleryPage();
        scrollToGalleryTop();
    };
    document.getElementById('gallery-jump')?.addEventListener('click', jumpToPage);
    document.getElementById('gallery-page-jump')?.addEventListener('keydown', event => {
        if (event.key === 'Enter') {
            event.preventDefault();
            jumpToPage();
        }
    });

    ['decade', 'region', 'language', 'dialect', 'sort'].forEach(type => {
        document.getElementById(`filter-${type}`)?.addEventListener('change', applyGalleryFilters);
    });

    document.getElementById('dialect-chips')?.addEventListener('click', event => {
        const chip = event.target.closest('.dialect-chip');
        if (!chip) return;
        const select = document.getElementById('filter-dialect');
        if (!select) return;
        // 再点一次已选中的 chip 等于取消该家乡话。
        select.value = select.value === chip.dataset.dialect ? 'All' : chip.dataset.dialect;
        applyGalleryFilters();
    });

    // 三波浪潮片单卡的「在画廊看全部」：预设家乡话后进探索舱。
    // 滚动放到下一帧，此时 explorer_scene 的同事件处理器已把探索舱展开。
    document.querySelectorAll('.wave-card-more[data-dialect]').forEach(link => {
        link.addEventListener('click', () => {
            const select = document.getElementById('filter-dialect');
            if (!select) return;
            select.value = link.dataset.dialect;
            applyGalleryFilters({ scroll: false });
            requestAnimationFrame(() => scrollToGalleryTop());
        });
    });
}

export function applyGalleryFilters({ scroll = true } = {}) {
    const dec = document.getElementById('filter-decade').value;
    const reg = document.getElementById('filter-region').value;
    const lang = document.getElementById('filter-language').value;
    const dial = document.getElementById('filter-dialect')?.value || 'All';
    const sorter = SORTERS[document.getElementById('filter-sort')?.value] || null;
    const matches = window.DataService.filter(dec, reg, lang, dial);
    galleryFilteredMovies = sorter ? [...matches].sort(sorter) : matches;
    galleryPage = 0;
    renderGalleryPage();
    updateDialectSummary(dial);
    if (scroll) scrollToGalleryTop();
}

function updateDialectSummary(dialect) {
    const summary = document.getElementById('gallery-dialect-summary');
    if (!summary) return;
    document.querySelectorAll('.dialect-chip').forEach(chip => {
        chip.classList.toggle('is-active', chip.dataset.dialect === dialect && dialect !== 'All');
    });
    if (!dialect || dialect === 'All' || galleryFilteredMovies.length === 0) {
        summary.hidden = true;
        return;
    }
    const stats = summarizeDialectFilms(galleryFilteredMovies);
    if (!stats) {
        summary.hidden = true;
        return;
    }
    const parts = [
        `<strong>${escapeHtml(dialect)}</strong> ${stats.n.toLocaleString('zh-CN')} 部`,
        `平均 ${stats.mean.toFixed(2)} 分`
    ];
    if (stats.yearMin !== null) parts.push(`${stats.yearMin}–${stats.yearMax} 年`);
    if (stats.earliest) {
        parts.push(`最早的一部是《${escapeHtml(stats.earliest.title)}》（${stats.earliest.year}）`);
    }
    summary.innerHTML = parts.join(' · ');
    summary.hidden = false;
}

export function populateDialectFilter(families) {
    const select = document.getElementById('filter-dialect');
    if (!select) return;
    // 家乡话选项取 n>=2 的方言族；只有一部的零星标签仍可经「方言」语言组浏览。
    families.filter(family => family.n >= 2).forEach(family => {
        const option = document.createElement('option');
        option.value = family.name;
        option.textContent = `${family.name}（${family.n.toLocaleString('zh-CN')} 部）`;
        select.appendChild(option);
    });
    select.closest('.filter-group')?.removeAttribute('hidden');

    renderDialectChips(families);
    document.querySelectorAll('.wave-card-more[data-dialect]').forEach(link => {
        link.removeAttribute('hidden');
    });
}

function renderDialectChips(families) {
    const host = document.getElementById('dialect-chips');
    if (!host) return;
    const known = new Set(families.map(family => family.name));
    const names = CHIP_FAMILIES.filter(name => known.has(name));
    if (!names.length) return;
    host.innerHTML = names
        .map(name => `<button type="button" class="dialect-chip" data-dialect="${escapeHtml(name)}">${escapeHtml(name)}</button>`)
        .join('');
    host.removeAttribute('hidden');
}

// 深链支持：#粤语 这类 hash（与章节锚点不冲突，因为方言族不是任何元素 id）。
export function applyDialectHashPreset() {
    let wanted = '';
    try {
        wanted = decodeURIComponent(window.location.hash.slice(1));
    } catch {
        return false;
    }
    const select = document.getElementById('filter-dialect');
    if (!wanted || !select) return false;
    const has = [...select.options].some(option => option.value === wanted);
    if (!has) return false;
    select.value = wanted;
    applyGalleryFilters({ scroll: false });
    return true;
}

export function clearGalleryFilters() {
    ['decade', 'region', 'language', 'dialect'].forEach(type => {
        const select = document.getElementById(`filter-${type}`);
        if (select) select.value = 'All';
    });
    applyGalleryFilters();
}

function bindFilterSheet() {
    const bar = document.querySelector('.filter-bar');
    const toggle = document.getElementById('filter-toggle');
    const done = document.getElementById('filter-done');
    const setOpen = open => {
        if (!bar || !toggle) return;
        bar.classList.toggle('is-open', open);
        toggle.setAttribute('aria-expanded', String(open));
    };
    toggle?.addEventListener('click', () => setOpen(!bar.classList.contains('is-open')));
    done?.addEventListener('click', () => setOpen(false));
}

export function renderGalleryPage() {
    const start = galleryPage * GALLERY_PAGE_SIZE;
    const movies = galleryFilteredMovies.slice(start, start + GALLERY_PAGE_SIZE);
    renderGallery(movies, galleryFilteredMovies.length, start);

    const pageCount = Math.max(1, Math.ceil(galleryFilteredMovies.length / GALLERY_PAGE_SIZE));
    const previous = document.getElementById('gallery-prev');
    const next = document.getElementById('gallery-next');
    if (previous) previous.disabled = galleryPage === 0;
    if (next) next.disabled = galleryFilteredMovies.length === 0 || galleryPage >= pageCount - 1;
    const status = document.getElementById('gallery-page-status');
    if (status) status.textContent = `${galleryPage + 1} / ${pageCount}`;
    const jumpInput = document.getElementById('gallery-page-jump');
    if (jumpInput) {
        jumpInput.value = galleryPage + 1;
        jumpInput.max = String(pageCount);
    }
}

function renderGallery(movies, totalCount, start) {
    const grid = document.getElementById('movie-grid');
    const subtitle = document.getElementById('gallery-subtitle');
    if (!grid) return;

    if (movies.length === 0) {
        if (subtitle) subtitle.textContent = '没有符合这些条件的电影。';
        grid.innerHTML = '<div class="gallery-empty"><p>没有符合这些条件的电影。</p><button type="button" class="gallery-clear" id="gallery-clear">清除筛选</button></div>';
        document.getElementById('gallery-clear')?.addEventListener('click', clearGalleryFilters);
        return;
    }
    const first = start + 1;
    const last = start + movies.length;
    if (subtitle) {
        subtitle.textContent = `当前筛选 ${totalCount.toLocaleString('zh-CN')} 部，显示第 ${first.toLocaleString('zh-CN')}–${last.toLocaleString('zh-CN')} 部`;
    }

    grid.innerHTML = movies.map(m => `
        <button class="movie-card" type="button" data-movie-id="${escapeTooltip(m.movieId)}" aria-label="查看《${escapeTooltip(m.title)}》详情">
            <span class="movie-card-top">
                <span class="movie-title">${escapeTooltip(m.title)} <small>(${m.year})</small></span>
                ${window.StoryUI.ratingBadge(m.rating)}
            </span>
            <span class="movie-tags">
                <span class="genre-badge">${escapeTooltip(regionLabel(m.region))}</span>
                <span class="genre-badge">${escapeTooltip(primaryGenre(m.genres))}</span>
            </span>
            <span class="movie-card-action">查看详情</span>
        </button>
    `).join('');
}
