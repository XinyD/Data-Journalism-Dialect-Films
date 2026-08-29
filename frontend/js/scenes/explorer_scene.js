const state = {
    bound: false,
    open: false,
    storyScrollY: 0,
    touchStartY: 0,
};

function isWaveBusy() {
    const root = document.documentElement;
    return root.classList.contains('wave-film-open')
        || root.classList.contains('wave-scene-busy');
}

function setChapterLabel(text) {
    const label = document.getElementById('chapter-nav-label');
    if (label) label.textContent = text;
}

export function isExplorerOpen() {
    return state.open;
}

export function enterExplorer() {
    if (state.open || isWaveBusy()) return;

    const explorerSpace = document.getElementById('explorer-space');
    if (!explorerSpace) return;

    state.open = true;
    state.storyScrollY = window.scrollY;

    document.documentElement.classList.add('explorer-open');
    explorerSpace.hidden = false;
    explorerSpace.setAttribute('aria-hidden', 'false');
    explorerSpace.classList.add('is-on');
    explorerSpace.scrollTop = 0;

    setChapterLabel('筛选电影');
}

export function exitExplorer() {
    if (!state.open) return;

    const explorerSpace = document.getElementById('explorer-space');
    state.open = false;

    document.documentElement.classList.remove('explorer-open');
    if (explorerSpace) {
        explorerSpace.classList.remove('is-on');
        explorerSpace.hidden = true;
        explorerSpace.setAttribute('aria-hidden', 'true');
    }

    const restoreY = Math.max(0, state.storyScrollY);
    window.scrollTo({
        top: restoreY,
        behavior: 'auto',
    });

    const activeStep = document.querySelector('.particle-step.is-active');
    if (activeStep) {
        const chapter = activeStep.dataset.chapter || '';
        const badge = activeStep.querySelector('.theory-badge, h2, .intro-kicker');
        const name = badge ? badge.textContent.trim().slice(0, 18) : activeStep.id;
        setChapterLabel(chapter ? `${chapter} · ${name}` : name);
    }
}

function onExplorerWheel(event) {
    if (!state.open) return;

    const explorerSpace = document.getElementById('explorer-space');
    if (!explorerSpace) return;

    if (explorerSpace.scrollTop <= 0 && event.deltaY < 0) {
        event.preventDefault();
        exitExplorer();
    }
}

function onExplorerTouchStart(event) {
    if (!state.open) return;
    state.touchStartY = event.touches[0]?.clientY ?? 0;
}

function onExplorerTouchMove(event) {
    if (!state.open) return;

    const explorerSpace = document.getElementById('explorer-space');
    if (!explorerSpace || explorerSpace.scrollTop > 0) return;

    const currentY = event.touches[0]?.clientY ?? 0;
    if (currentY - state.touchStartY > 48) {
        exitExplorer();
    }
}

function scrollExplorerToTop() {
    const explorerSpace = document.getElementById('explorer-space');
    if (!explorerSpace) return;
    const behavior = window.matchMedia('(prefers-reduced-motion: reduce)').matches
        ? 'auto' : 'smooth';
    explorerSpace.scrollTo({ top: 0, behavior });
}

function onEnterExplorerClick(event) {
    const link = event.target.closest('#enter-explorer, a[href="#glass-section"]');
    if (!link) return;
    event.preventDefault();
    event.stopPropagation();

    if (state.open) {
        scrollExplorerToTop();
        return;
    }

    state.storyScrollY = window.scrollY;
    enterExplorer();
}

export function initExplorerScene() {
    if (state.bound) return;
    state.bound = true;

    const explorerSpace = document.getElementById('explorer-space');

    explorerSpace?.addEventListener('wheel', onExplorerWheel, { passive: false });
    explorerSpace?.addEventListener('touchstart', onExplorerTouchStart, { passive: true });
    explorerSpace?.addEventListener('touchmove', onExplorerTouchMove, { passive: true });
    document.getElementById('enter-explorer')?.addEventListener('click', onEnterExplorerClick, { capture: true });
    document.addEventListener('click', onEnterExplorerClick);
}
