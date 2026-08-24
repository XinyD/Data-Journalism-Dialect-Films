import { runtime } from './runtime.js';
import { escapeHtml } from './lib/dom.js';
import { populateMovieDetail } from './lib/movie-detail.js';

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

    ['decade', 'region', 'language', 'sort'].forEach(type => {
        document.getElementById(`filter-${type}`)?.addEventListener('change', applyGalleryFilters);
    });
}

export function applyGalleryFilters() {
    const dec = document.getElementById('filter-decade').value;
    const reg = document.getElementById('filter-region').value;
    const lang = document.getElementById('filter-language').value;
    const sorter = SORTERS[document.getElementById('filter-sort')?.value] || null;
    const matches = window.DataService.filter(dec, reg, lang);
    galleryFilteredMovies = sorter ? [...matches].sort(sorter) : matches;
    galleryPage = 0;
    renderGalleryPage();
    scrollToGalleryTop();
}

export function clearGalleryFilters() {
    ['decade', 'region', 'language'].forEach(type => {
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
