import { rafThrottle, prefersReducedMotion } from './lib/schedule.js';

export function chapterLabel(step) {
    const badge = step.querySelector('.theory-badge');
    if (badge) return badge.textContent.trim();
    if (step.id === 'step-0') return '封面';
    if (step.id === 'step-intro') return '引言';
    const heading = step.querySelector('h1, h2');
    return heading ? heading.textContent.trim().slice(0, 18) : step.id;
}

function getChapterNavFill() {
    return document.querySelector('.chapter-nav-fill');
}

function updateChapterNavFill(currentStep) {
    const fill = getChapterNavFill();
    if (!fill || !currentStep) return;
    const steps = [...document.querySelectorAll('.particle-step')];
    const index = steps.indexOf(currentStep);
    if (index < 0 || steps.length <= 1) {
        fill.style.height = index >= 0 ? '100%' : '0%';
        fill.style.top = '0%';
        return;
    }
    const segment = 100 / steps.length;
    fill.style.height = `${segment}%`;
    fill.style.top = `${index * segment}%`;
}

export function updateChapterNav(currentStep) {
    if (!currentStep) return;
    document.querySelectorAll('.chapter-nav-dots a').forEach(link => {
        const isCurrent = link.dataset.step === currentStep.id;
        link.classList.toggle('is-current', isCurrent);
        if (isCurrent) link.setAttribute('aria-current', 'true');
        else link.removeAttribute('aria-current');
    });
    updateChapterNavFill(currentStep);
    const label = document.getElementById('chapter-nav-label');
    if (label) {
        const chapter = currentStep.dataset.chapter || '';
        label.textContent = chapter ? `${chapter} · ${chapterLabel(currentStep)}` : chapterLabel(currentStep);
    }
}

export function initChapterNav() {
    const list = document.getElementById('chapter-nav-dots');
    if (!list) return;
    const steps = [...document.querySelectorAll('.particle-step')];
    list.innerHTML = steps.map(step => {
        const label = chapterLabel(step);
        return `<li><a href="#${step.id}" data-step="${step.id}" aria-label="${label}"><span class="chapter-nav-marker" aria-hidden="true"></span><span class="chapter-nav-tip">${label}</span></a></li>`;
    }).join('');

    list.addEventListener('click', event => {
        const link = event.target.closest('a[data-step]');
        if (!link) return;
        event.preventDefault();
        const targetStep = document.getElementById(link.dataset.step);
        if (!targetStep) return;
        updateChapterNav(targetStep);
        targetStep.scrollIntoView({
            block: 'center',
            behavior: prefersReducedMotion() ? 'auto' : 'smooth'
        });
    });

    const nav = document.getElementById('chapter-nav');
    if (nav) {
        nav.addEventListener('keydown', event => {
            if (event.key !== 'ArrowUp' && event.key !== 'ArrowDown') return;
            const links = [...list.querySelectorAll('a[data-step]')];
            const currentIndex = links.findIndex(link => link.classList.contains('is-current'));
            if (currentIndex < 0) return;
            event.preventDefault();
            const nextIndex = event.key === 'ArrowUp'
                ? Math.max(0, currentIndex - 1)
                : Math.min(links.length - 1, currentIndex + 1);
            const nextLink = links[nextIndex];
            if (!nextLink || nextIndex === currentIndex) return;
            nextLink.focus();
            const targetStep = document.getElementById(nextLink.dataset.step);
            if (!targetStep) return;
            updateChapterNav(targetStep);
            targetStep.scrollIntoView({
                block: 'center',
                behavior: prefersReducedMotion() ? 'auto' : 'smooth'
            });
        });
    }

    const bar = document.querySelector('#story-progress i');
    const onScroll = rafThrottle(() => {
        const max = document.documentElement.scrollHeight - window.innerHeight;
        if (bar && max > 0) bar.style.width = `${Math.min(100, (window.scrollY / max) * 100)}%`;
        if (window.ScaleScene) window.ScaleScene.onScroll();
    });
    window.addEventListener('scroll', onScroll, { passive: true });
    onScroll();
    updateChapterNav(document.querySelector('.particle-step.is-active') || steps[0]);
}

export function initScrollytelling(deps) {
    const steps = [...document.querySelectorAll('.particle-step')];
    let currentStep = steps[0] || null;

    const particleObserver = new IntersectionObserver(entries => {
        entries.forEach(entry => {
            if (!entry.isIntersecting || entry.target === currentStep) return;
            currentStep = entry.target;
            steps.forEach(step => step.classList.toggle('is-active', step === currentStep));
            updateChapterNav(currentStep);
            deps.syncCoverReveal();
            deps.maybeCountSceneStats(currentStep);
            const sceneId = currentStep.getAttribute('data-scene') || 'universe';
            document.documentElement.dataset.activeScene = sceneId;
            if (sceneId === 'universe') {
                if (currentStep.id === 'step-0') deps.setPrologueState(deps.PROLOGUE_STATES.WORLD_MAP);
                else if (currentStep.id === 'step-intro') deps.setPrologueState(deps.PROLOGUE_STATES.STAR_FIELD);
            }
            deps.activateSceneInteraction(sceneId, currentStep);
            deps.renderParticleScene(sceneId);
            if (window.WaveScene) window.WaveScene.onSceneChange(sceneId);
            if (window.ScaleScene) window.ScaleScene.onSceneChange(sceneId);
        });
    }, { rootMargin: '-22% 0px -22% 0px' });
    steps.forEach(step => particleObserver.observe(step));
}
