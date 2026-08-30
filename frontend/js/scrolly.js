import { rafThrottle, prefersReducedMotion } from './lib/schedule.js';
import { chapterFillFromGeometry, isFarJump, narrativeProgress, pickCurrentStep } from './lib/scrolly-select.js';

const STEP_HYSTERESIS = 0.12;
const RATIO_THRESHOLDS = [0, 0.08, 0.16, 0.28, 0.4, 0.55, 0.7, 0.85, 1];

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

function pageTop(el) {
    return el.getBoundingClientRect().top + window.scrollY;
}

function stepGeometry() {
    return [...document.querySelectorAll('.particle-step')].map(step => ({
        id: step.id,
        top: pageTop(step),
        height: step.offsetHeight
    }));
}

function updateChapterNavFill(currentStep) {
    const fill = getChapterNavFill();
    if (!fill || !currentStep) return;
    const geometry = stepGeometry();
    if (geometry.length <= 1) {
        fill.style.height = geometry.length ? '100%' : '0%';
        fill.style.top = '0%';
        return;
    }
    const rect = chapterFillFromGeometry(geometry, currentStep.id);
    fill.style.top = `${rect.top}%`;
    fill.style.height = `${rect.height}%`;
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
}

function whenScrollSettles(done) {
    let finished = false;
    const finish = () => {
        if (finished) return;
        finished = true;
        window.removeEventListener('scrollend', onScrollEnd);
        window.clearTimeout(timer);
        done();
    };
    const onScrollEnd = () => finish();
    if ('onscrollend' in window) {
        window.addEventListener('scrollend', onScrollEnd, { once: true });
    }
    const timer = window.setTimeout(finish, 480);
    let last = window.scrollY;
    let still = 0;
    const tick = () => {
        if (finished) return;
        if (Math.abs(window.scrollY - last) < 1) still += 1;
        else still = 0;
        last = window.scrollY;
        if (still >= 3) {
            finish();
            return;
        }
        requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);
}

export function initScrollytelling(deps) {
    const steps = [...document.querySelectorAll('.particle-step')];
    const stepIds = steps.map(step => step.id);
    const ratios = new Map(stepIds.map(id => [id, 0]));
    let currentStep = steps[0] || null;
    let pendingPinId = null;
    let selectRaf = 0;
    const bar = document.querySelector('#story-progress i');

    function refreshRatiosFromView() {
        const top = window.innerHeight * 0.22;
        const bottom = window.innerHeight * 0.78;
        const band = Math.max(1, bottom - top);
        for (let i = 0; i < steps.length; i += 1) {
            const step = steps[i];
            const rect = step.getBoundingClientRect();
            const visible = Math.max(0, Math.min(rect.bottom, bottom) - Math.max(rect.top, top));
            ratios.set(step.id, visible / band);
        }
    }

    function updateProgress() {
        if (bar && steps.length) {
            const first = steps[0];
            const last = steps[steps.length - 1];
            const start = pageTop(first);
            const end = pageTop(last) + last.offsetHeight - window.innerHeight;
            bar.style.width = `${narrativeProgress(window.scrollY, start, end) * 100}%`;
        }
        if (currentStep) updateChapterNavFill(currentStep);
    }

    function sceneIdOf(step) {
        return (step && step.getAttribute('data-scene')) || 'universe';
    }

    function applyStep(nextStep) {
        if (!nextStep) return;
        const prevStep = currentStep;
        const prevScene = sceneIdOf(prevStep);
        const sceneId = sceneIdOf(nextStep);
        const sameStep = nextStep === currentStep;
        currentStep = nextStep;
        steps.forEach(step => step.classList.toggle('is-active', step === currentStep));
        updateChapterNav(currentStep);
        deps.syncCoverReveal();
        deps.maybeCountSceneStats(currentStep);
        document.documentElement.dataset.activeScene = sceneId;
        let prologueChanged = false;
        if (sceneId === 'universe') {
            const nextState = nextStep.id === 'step-0'
                ? deps.PROLOGUE_STATES.WORLD_MAP
                : nextStep.id === 'step-intro'
                    ? deps.PROLOGUE_STATES.STAR_FIELD
                    : null;
            if (nextState && document.documentElement.dataset.prologueState !== nextState) {
                deps.setPrologueState(nextState);
                prologueChanged = true;
            }
        }
        if (sameStep && !prologueChanged) {
            updateProgress();
            return;
        }
        deps.activateSceneInteraction(sceneId, currentStep);
        const sameScene = prevScene === sceneId && !prologueChanged;
        if (!sameScene || prologueChanged) {
            deps.renderParticleScene(sceneId);
        }
        if (window.WaveScene) window.WaveScene.onSceneChange(sceneId);
        updateProgress();
    }

    function commitStep() {
        if (pendingPinId) return;
        const nextId = pickCurrentStep(stepIds, ratios, currentStep && currentStep.id, STEP_HYSTERESIS);
        const nextStep = nextId ? document.getElementById(nextId) : null;
        if (!nextStep || nextStep === currentStep) return;
        applyStep(nextStep);
    }

    function scheduleSelect() {
        if (selectRaf) return;
        selectRaf = requestAnimationFrame(() => {
            selectRaf = 0;
            commitStep();
        });
    }

    function jumpTo(targetStep) {
        if (!targetStep) return;
        pendingPinId = targetStep.id;
        const fromIndex = steps.indexOf(currentStep);
        const toIndex = steps.indexOf(targetStep);
        const far = isFarJump(fromIndex, toIndex);
        const reduce = prefersReducedMotion();
        const behavior = far || reduce ? 'auto' : 'smooth';
        targetStep.scrollIntoView({
            block: 'center',
            behavior
        });
        const settle = () => {
            if (pendingPinId !== targetStep.id) return;
            pendingPinId = null;
            applyStep(targetStep);
        };
        if (behavior === 'auto') {
            requestAnimationFrame(() => requestAnimationFrame(settle));
            return;
        }
        whenScrollSettles(settle);
    }

    const particleObserver = new IntersectionObserver(() => {
        if (pendingPinId) return;
        refreshRatiosFromView();
        scheduleSelect();
    }, {
        rootMargin: '-22% 0px -22% 0px',
        threshold: RATIO_THRESHOLDS
    });
    steps.forEach(step => particleObserver.observe(step));

    const list = document.getElementById('chapter-nav-dots');
    if (list) {
        list.addEventListener('click', event => {
            const link = event.target.closest('a[data-step]');
            if (!link) return;
            event.preventDefault();
            jumpTo(document.getElementById(link.dataset.step));
        });
    }
    const nav = document.getElementById('chapter-nav');
    if (nav && list) {
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
            jumpTo(document.getElementById(nextLink.dataset.step));
        });
    }

    const onScroll = rafThrottle(() => {
        updateProgress();
        if (!pendingPinId) {
            refreshRatiosFromView();
            scheduleSelect();
        }
    });
    window.addEventListener('scroll', onScroll, { passive: true });
    refreshRatiosFromView();
    updateProgress();
    updateChapterNav(document.querySelector('.particle-step.is-active') || steps[0]);
    scheduleSelect();
}
