/* 第十幕 · 刻度：按钮换拍，点亮尺子与换句 */
(function (global) {
    const MAX_BEAT = 9;
    const ROLL_MS = 750;
    const PLAY_MS = 700;

    const clamp = (value, min, max) => Math.max(min, Math.min(max, value));
    const lerp = (a, b, t) => a + (b - a) * t;

    const reducedMotion = () => window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    const state = {
        bound: false,
        raf: 0,
        beat: 0,
        playTimer: 0,
        staggerTimers: [],
        activeKey: null,
        litPrev: [],
        roll: []
    };

    function $(id) {
        return document.getElementById(id);
    }

    function stepEl() {
        return $('step-10');
    }

    function rungs() {
        return [...document.querySelectorAll('#world-scale-rungs .world-scale-rung')];
    }

    function clearStagger() {
        state.staggerTimers.forEach(id => clearTimeout(id));
        state.staggerTimers = [];
    }

    function stopPlay() {
        if (state.playTimer) {
            clearTimeout(state.playTimer);
            state.playTimer = 0;
        }
        clearStagger();
    }

    function closeDetail() {
        state.activeKey = null;
        const detail = $('scale-detail');
        if (detail) detail.hidden = true;
        rungs().forEach(el => el.classList.toggle('is-key', el.dataset.key === 'dia' && el.classList.contains('is-lit')));
    }

    function openDetail(key) {
        const btn = rungs().find(el => el.dataset.key === key);
        const detail = $('scale-detail');
        if (!btn || !detail || !btn.classList.contains('is-lit')) return;
        state.activeKey = key;
        $('scale-d-name').textContent = btn.dataset.name || '';
        $('scale-d-meta').textContent = `均分 ${Number(btn.dataset.score).toFixed(2)} · 中位数 ${btn.dataset.med || '--'} · n=${btn.dataset.n || '--'}`;
        $('scale-d-note').textContent = btn.dataset.note || '';
        detail.hidden = false;
        rungs().forEach(el => el.classList.toggle('is-key', el.dataset.key === key));
    }

    function toggleDetail(key) {
        if (state.activeKey === key) closeDetail();
        else openDetail(key);
    }

    function syncControls() {
        const prev = document.querySelector('#scale-controls [data-scale-step="-1"]');
        const next = document.querySelector('#scale-controls [data-scale-step="1"]');
        if (prev) prev.disabled = state.beat <= 0;
        if (next) next.disabled = state.beat >= MAX_BEAT;
        document.querySelectorAll('#scale-controls [data-scale-beat]').forEach(btn => {
            const target = Number(btn.dataset.scaleBeat);
            const on = target === 6
                ? state.beat >= 1 && state.beat <= 6
                : state.beat === target;
            btn.classList.toggle('is-on', on);
        });
    }

    function applyUi() {
        const beat = state.beat;
        const hint = $('scale-hint');
        const core = $('scale-core');
        const diag = $('scale-diag');
        const mani = $('scale-mani');
        const board = $('scale-board');
        const ga = $('scale-gap-premium');
        const gb = $('scale-gap-remain');
        const buttons = rungs();
        const litCount = beat <= 0 ? 0 : Math.min(6, beat);
        const now = performance.now();
        const rm = reducedMotion();

        if (hint) hint.classList.toggle('is-on', beat === 0);

        buttons.forEach((el, i) => {
            const on = i < litCount;
            if (on && !state.litPrev[i]) {
                const score = Number(el.dataset.score);
                state.roll[i] = {
                    active: !rm,
                    from: Math.max(score - 0.55, 6.05),
                    t0: now
                };
                const scoreEl = el.querySelector('.score');
                if (scoreEl && rm) scoreEl.textContent = score.toFixed(2);
            }
            if (!on && state.litPrev[i]) {
                if (state.roll[i]) state.roll[i].active = false;
                const scoreEl = el.querySelector('.score');
                if (scoreEl) scoreEl.textContent = Number(el.dataset.score).toFixed(2);
                if (el.dataset.key === state.activeKey) closeDetail();
            }
            state.litPrev[i] = on;
            el.classList.toggle('is-lit', on);
            if (el.dataset.key === 'dia') el.classList.toggle('is-key', on && !state.activeKey);
            if (state.activeKey) el.classList.toggle('is-key', el.dataset.key === state.activeKey);
        });

        if (ga) ga.classList.toggle('is-on', beat >= 7);
        if (gb) gb.classList.toggle('is-on', beat >= 7);

        if (core) {
            core.style.opacity = beat === 7 ? '1' : '0';
            core.classList.toggle('on', beat === 7);
        }
        if (diag) {
            diag.style.opacity = beat === 8 ? '1' : '0';
            diag.classList.toggle('on', beat === 8);
            [...diag.querySelectorAll('li')].forEach((li, i) => {
                li.classList.toggle('is-on', beat === 8 && (rm || i === 0 || li.dataset.ready === '1'));
            });
        }
        if (mani) {
            mani.style.opacity = beat === 9 ? '1' : '0';
            mani.classList.toggle('on', beat === 9);
            [...mani.querySelectorAll('p')].forEach((el, i) => {
                el.classList.toggle('is-on', beat === 9 && (rm || i === 0 || el.dataset.ready === '1'));
            });
        }
        if (board) board.classList.toggle('is-diag', beat === 8);
        syncControls();
    }

    function staggerIn(selector, reset) {
        clearStagger();
        const items = [...document.querySelectorAll(selector)];
        items.forEach(el => {
            if (reset) el.dataset.ready = '';
        });
        if (reducedMotion()) {
            items.forEach(el => {
                el.dataset.ready = '1';
                el.classList.add('is-on');
            });
            return;
        }
        items.forEach((el, i) => {
            const timer = setTimeout(() => {
                el.dataset.ready = '1';
                el.classList.add('is-on');
            }, i * 140);
            state.staggerTimers.push(timer);
        });
    }

    function setBeat(next) {
        const beat = clamp(Number(next) || 0, 0, MAX_BEAT);
        const prev = state.beat;
        state.beat = beat;
        if (beat !== 8 && beat !== 9) clearStagger();
        if (beat < 8) {
            document.querySelectorAll('#scale-diag li').forEach(el => {
                el.dataset.ready = '';
            });
        }
        if (beat < 9) {
            document.querySelectorAll('#scale-mani p').forEach(el => {
                el.dataset.ready = '';
            });
        }
        applyUi();
        if (beat === 8 && prev !== 8) staggerIn('#scale-diag li', true);
        if (beat === 9 && prev !== 9) staggerIn('#scale-mani p', true);
        startLoop();
    }

    function snapStand() {
        const items = rungs();
        state.litPrev = items.map(() => true);
        state.roll = items.map(() => ({ active: false, from: 0, t0: 0 }));
        items.forEach(el => {
            const scoreEl = el.querySelector('.score');
            if (scoreEl) scoreEl.textContent = Number(el.dataset.score).toFixed(2);
            el.classList.add('is-lit');
        });
    }

    function playStand() {
        setBeat(0);
        state.litPrev = rungs().map(() => false);
        state.roll = rungs().map(() => ({ active: false, from: 0, t0: 0 }));
        let next = 0;
        const step = () => {
            next += 1;
            setBeat(next);
            if (next >= 6) {
                state.playTimer = 0;
                return;
            }
            state.playTimer = setTimeout(step, PLAY_MS);
        };
        state.playTimer = setTimeout(step, PLAY_MS);
    }

    function playTo(target) {
        stopPlay();
        const dest = clamp(Number(target) || 0, 0, MAX_BEAT);
        if (reducedMotion()) {
            if (dest >= 7) snapStand();
            setBeat(dest);
            return;
        }
        if (dest <= 6) {
            playStand();
            return;
        }
        snapStand();
        const replay = state.beat === dest;
        if (dest === 7 || replay) {
            setBeat(6);
            state.playTimer = setTimeout(() => {
                setBeat(dest);
                state.playTimer = 0;
            }, 80);
            return;
        }
        setBeat(dest);
    }

    function tickRolls(now) {
        rungs().forEach((el, i) => {
            const roll = state.roll[i];
            if (!roll || !roll.active) return;
            const k = Math.min(1, (now - roll.t0) / ROLL_MS);
            const ease = 1 - Math.pow(1 - k, 3);
            const scoreEl = el.querySelector('.score');
            const target = Number(el.dataset.score);
            if (scoreEl) scoreEl.textContent = lerp(roll.from, target, ease).toFixed(2);
            if (k >= 1) roll.active = false;
        });
    }

    function frame(now) {
        tickRolls(now);
        const rolling = state.roll.some(item => item && item.active);
        if (rolling) state.raf = requestAnimationFrame(frame);
        else state.raf = 0;
    }

    function startLoop() {
        if (!state.raf) state.raf = requestAnimationFrame(frame);
    }

    function bind() {
        if (state.bound) return;
        const step = stepEl();
        if (!step) return;
        step.addEventListener('click', event => {
            const close = event.target.closest('#scale-detail-x');
            if (close) {
                closeDetail();
                return;
            }
            const stepBtn = event.target.closest('[data-scale-step]');
            if (stepBtn) {
                stopPlay();
                setBeat(state.beat + Number(stepBtn.dataset.scaleStep));
                return;
            }
            const jump = event.target.closest('[data-scale-beat]');
            if (jump) {
                playTo(Number(jump.dataset.scaleBeat));
                return;
            }
            const rung = event.target.closest('.world-scale-rung');
            if (rung && rung.dataset.key) toggleDetail(rung.dataset.key);
        });
        state.bound = true;
    }

    function refresh() {
        stopPlay();
        state.litPrev = rungs().map(() => false);
        state.roll = rungs().map(() => ({ active: false, from: 0, t0: 0 }));
        closeDetail();
        applyUi();
        startLoop();
    }

    function init() {
        bind();
        refresh();
    }

    function onScroll() {}

    function onSceneChange(sceneId) {
        if (sceneId === 'scale') applyUi();
    }

    global.ScaleScene = {
        init,
        refresh,
        setBeat,
        onScroll,
        onSceneChange
    };
})(window);
