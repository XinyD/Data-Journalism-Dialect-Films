import { escapeHtml } from '../lib/dom.js';

/* Part 3h · 展：从方言星云进入三波电影胶片空间 */
(function (global) {
    const AMA_ID = '37116446';
    const LAST_NIGHT_ID = '26633257';
    const INFERNAL_ID = '1307914';
    const PICNIC_ID = '26337866';
    const WAVE2_FEATURED = [PICNIC_ID, LAST_NIGHT_ID, '27110296'];
    const FOCUS_IDS = {
        [INFERNAL_ID]: 'city',
        [PICNIC_ID]: 'mountain',
        [AMA_ID]: 'letter'
    };
    const FIELD_SETTLE = 0.55;
    const FIELD_SETTLE_TRANS = 0.16;
    const WAVE_TRANS_MS = 1000;
    const TRANSITION_MS = 1200;
    const OVERLAY_FADE_MS = 350;
    const FILM_REVEAL_VMAX = 150;
    const MODE_BY_WAVE = { 1: 'city', 2: 'mountain', 3: 'letter' };

    const waveScene = {
        layer: 'galaxy',
        wave: 1,
        targetWave: 1,
        focusIndex: 0,
        filmScrollProgress: 0,
        particleSceneMode: 'city',
        backgroundFocus: 0,
        focusId: '',
        transitionProgress: 0,
        transitionKind: '',
        leavePull: 0
    };

    let ctx = null;
    let bound = false;
    let portalMovie = null;
    let portalRaf = 0;
    let fieldParticles = [];
    let fieldRaf = 0;
    let nebulaGradient = null;
    let nebulaGradientKey = '';
    let vigGradient = null;
    let vigGradientKey = '';
    let fieldReady = false;
    let fieldLastT = 0;
    let axisBound = false;
    let deckFilms = [];
    let waveTransRaf = 0;
    let enterOrigin = { x: 0, y: 0 };
    let transitionBox = { width: 0, height: 0 };
    let prefetchScheduled = false;

    const COPY_SPECS = {
        1: {
            kicker: 'WAVE 01 · 第一波 · 港片粤语',
            title: '城市有自己的声音。',
            body: '一座城市的街道、餐桌与人情，也可以成为电影最动人的部分。'
        },
        2: {
            kicker: 'WAVE 02 · 第二波 · 西南方言',
            title: '有些电影，不需要替土地说话。',
            body: '山路、小镇、沉默的人，本身就是故事的一部分。',
            aside: '作者表达 · 边缘叙事 · 土地的力量'
        },
        3: {
            kicker: 'WAVE 03 · 第三波 · 闽南语新浪潮',
            title: '故事最后，总要回到某个人身上。',
            body: '一封信、一间旧屋、一家人的记忆，从一个地方出发，也可以抵达很远的人心里。'
        }
    };

    const FILM_BLURBS = {
        '1307914': '卧底与警察，走在同一条街上',
        '1303913': '戏台散了，人还在说粤语',
        '900054': '一桌菜，把一家人留在饭桌上',
        '1305690': '无根的人，在城市里流浪',
        '900089': '过期的罐头，和擦肩而过的人',
        '900072': '县太爷的戏，也是土地的戏',
        '27110296': '小城的人，也有自己的江湖',
        '26337866': '山路把时间绕成一个圈',
        '26657126': '沉默的人把话说完',
        '27668250': '雨夜里，有人还在跑',
        '26633257': '记忆在雾里走回去',
        '1292434': '一个家庭，把一生慢慢说完',
        '27059130': '夜里骑车的人，看见了自己',
        '3993559': '名字被喊出来，土地才还在',
        '30292777': '父亲的沉默，比阳光更重',
        '34805873': '一碗汤，把离家的人喊回来',
        '37116446': '一封信，写给还没离开的人'
    };

    const dom = {
        portal: null,
        hint: null,
        transition: null,
        film: null,
        scroll: null,
        stage: null,
        field: null
    };

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

    function cubicOut(t) {
        const x = 1 - clamp01(t);
        return 1 - x * x * x;
    }

    function prefersReduced() {
        return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    }

    function isMobile() {
        return window.innerWidth <= 768;
    }

    function hash01(value, salt = 0) {
        let hash = (2166136261 ^ salt) >>> 0;
        const text = String(value);
        for (let i = 0; i < text.length; i += 1) {
            hash ^= text.charCodeAt(i);
            hash = Math.imul(hash, 16777619);
        }
        return (hash >>> 0) / 4294967295;
    }

    function animate(duration, onFrame) {
        return new Promise(resolve => {
            if (prefersReduced()) {
                onFrame(1);
                resolve();
                return;
            }
            const start = performance.now();
            const tick = now => {
                const t = clamp01((now - start) / duration);
                onFrame(t);
                if (t < 1) requestAnimationFrame(tick);
                else resolve();
            };
            requestAnimationFrame(tick);
        });
    }

    function resizeCanvas(canvas) {
        if (!canvas) return { width: window.innerWidth, height: window.innerHeight, context: null };
        const dpr = Math.min(window.devicePixelRatio || 1, 2);
        const width = window.innerWidth;
        const height = window.innerHeight;
        canvas.width = Math.max(1, Math.floor(width * dpr));
        canvas.height = Math.max(1, Math.floor(height * dpr));
        canvas.style.width = `${width}px`;
        canvas.style.height = `${height}px`;
        const context = canvas.getContext('2d');
        if (context) context.setTransform(dpr, 0, 0, dpr, 0, 0);
        return { width, height, context };
    }

    function movieToPixel(movie) {
        const chart = ctx && ctx.particleChart;
        if (chart && movie) {
            const tries = [
                () => chart.convertToPixel({ seriesIndex: 0 }, [movie.randX, movie.randY]),
                () => chart.convertToPixel('grid', [movie.randX, movie.randY])
            ];
            for (let i = 0; i < tries.length; i += 1) {
                try {
                    const pix = tries[i]();
                    if (Array.isArray(pix) && Number.isFinite(pix[0]) && Number.isFinite(pix[1])) {
                        return { x: pix[0], y: pix[1] };
                    }
                } catch (error) {
                    // Try the next converter, then fall back to data-space mapping.
                }
            }
        }
        return {
            x: ((movie && movie.randX) || 70) / 100 * window.innerWidth,
            y: (1 - ((movie && movie.randY) || 50) / 100) * window.innerHeight
        };
    }

    function pickPortalMovie() {
        const rows = (ctx && ctx.particleData) || [];
        const dialect = rows.filter(row => row.langCode === 3);
        if (!dialect.length) return null;
        const safe = dialect.filter(row => row.randX >= 56 && row.randX <= 90 && row.randY >= 30 && row.randY <= 70);
        const pool = (safe.length ? safe : dialect).slice().sort((a, b) => String(a.movieId).localeCompare(String(b.movieId)));
        return pool[Math.floor(hash01('wave-portal-pick', 11) * pool.length)] || pool[0];
    }

    function cacheDom() {
        dom.portal = document.getElementById('wave-portal-particle');
        dom.hint = document.querySelector('#step-8e .wave-portal-hint');
        dom.transition = document.getElementById('wave-transition-canvas');
        dom.film = document.getElementById('wave-film-space');
        dom.scroll = document.getElementById('wave-film-scroll');
        dom.stage = document.getElementById('wave-film-stage');
        dom.field = document.getElementById('wave-field-canvas');
    }

    function getStage() {
        return dom.stage || (dom.scroll && dom.scroll.querySelector('.wave-film-stage'));
    }

    function setHintSeeking(on) {
        if (dom.hint) dom.hint.classList.toggle('is-seeking', on);
    }

    function syncPortalPosition() {
        const visible = ctx
            && ctx.getActiveSceneId() === 'three-waves'
            && waveScene.layer === 'galaxy';
        if (!dom.portal) return;
        if (!visible) {
            dom.portal.hidden = true;
            setHintSeeking(false);
            return;
        }
        if (!portalMovie) portalMovie = pickPortalMovie();
        if (!portalMovie) {
            dom.portal.hidden = true;
            return;
        }
        const pix = movieToPixel(portalMovie);
        if (!Number.isFinite(pix.x) || pix.x < 8 || pix.y < 8) {
            dom.portal.hidden = true;
            return;
        }
        dom.portal.style.left = `${pix.x}px`;
        dom.portal.style.top = `${pix.y}px`;
        dom.portal.hidden = false;
    }

    function startPortalTracking() {
        stopPortalTracking();
        let frames = 0;
        const tick = () => {
            syncPortalPosition();
            frames += 1;
            if (waveScene.layer === 'galaxy' && frames < 180) {
                portalRaf = requestAnimationFrame(tick);
            } else {
                portalRaf = 0;
            }
        };
        portalRaf = requestAnimationFrame(tick);
    }

    function stopPortalTracking() {
        if (portalRaf) cancelAnimationFrame(portalRaf);
        portalRaf = 0;
    }

    function lookupFilm(id, fallback) {
        const movie = ctx && ctx.findPublicationMovie ? ctx.findPublicationMovie(id) : null;
        if (movie) {
            return {
                id: String(movie.movieId || id),
                title: movie.title,
                year: movie.year,
                rating: movie.rating,
                movie
            };
        }
        return {
            id: String(id),
            title: fallback && fallback.title || '未知电影',
            year: fallback && fallback.year || '',
            rating: fallback && fallback.rating,
            movie: fallback || { movieId: String(id), title: fallback && fallback.title, year: fallback && fallback.year, rating: fallback && fallback.rating || 0 }
        };
    }

    function uniqueFilms(list) {
        const seen = new Set();
        return list.filter(film => {
            const id = String(film.id);
            if (seen.has(id)) return false;
            seen.add(id);
            return true;
        });
    }

    function waveFilms() {
        const waves = ctx && ctx.getDialectAgg && ctx.getDialectAgg() && ctx.getDialectAgg().wave_cases;
        const hk = ((waves && waves.hk) || []).map(film => lookupFilm(film.id, film));
        const sw = ((waves && waves.sw) || []).map(film => lookupFilm(film.id, film));
        const mn = ((waves && waves.mn) || []).map(film => lookupFilm(film.id, film));

        const featuredSw = WAVE2_FEATURED.map(id => {
            const fromCases = sw.find(film => String(film.id) === id);
            return fromCases || lookupFilm(id, id === LAST_NIGHT_ID ? { title: '地球最后的夜晚', year: 2018, rating: 6.9 } : null);
        });
        const restSw = sw.filter(film => !WAVE2_FEATURED.includes(String(film.id)));

        const ama = lookupFilm(AMA_ID, { title: '给阿嬷的情书', year: 2026, rating: 9.3 });
        const mid = Math.max(1, Math.floor(mn.length / 2));
        const mnWithHero = mn.slice();
        mnWithHero.splice(mid, 0, Object.assign({}, ama, { hero: true }));

        return {
            1: uniqueFilms(hk),
            2: uniqueFilms(featuredSw.concat(restSw)),
            3: uniqueFilms(mnWithHero)
        };
    }

    function rafThrottle(fn) {
        let frame = 0;
        return (...args) => {
            if (frame) return;
            frame = requestAnimationFrame(() => {
                frame = 0;
                fn(...args);
            });
        };
    }

    function buildDeck() {
        const waves = waveFilms();
        const deck = [];
        [1, 2, 3].forEach(wave => {
            (waves[wave] || []).forEach(film => {
                deck.push(Object.assign({}, film, { wave }));
            });
        });
        return deck;
    }

    function filmBlurb(film) {
        const keyed = FILM_BLURBS[String(film.id)];
        if (keyed) return keyed;
        const rating = Number.isFinite(Number(film.rating)) ? Number(film.rating).toFixed(1) : '';
        const year = film.year || '';
        return [year, rating].filter(Boolean).join(' · ') || '—';
    }

    function cardHtml(film, index) {
        const rating = Number.isFinite(Number(film.rating)) ? Number(film.rating).toFixed(1) : '--';
        const year = film.year || '';
        const tip = `${film.title || ''}${year ? ` · ${year}` : ''} · ${rating}`;
        const motif = MODE_BY_WAVE[film.wave] || 'city';
        const frameNo = String(index + 1).padStart(2, '0');
        const waveNo = String(film.wave || 1).padStart(2, '0');
        return `
            <button type="button" class="wave-film-card${film.hero ? ' is-hero' : ''}" data-movie-id="${escapeHtml(film.id)}" data-index="${index}" data-wave="${film.wave}" title="${escapeHtml(tip)}">
                <span class="wave-film-stock">
                    <span class="wave-film-sprocket" aria-hidden="true"></span>
                    <span class="wave-film-gate">
                        <span class="wave-film-still wave-film-still--${motif} wave-film-still--id-${escapeHtml(film.id)}" aria-hidden="true"><i></i></span>
                        <span class="wave-film-caption">
                            <span class="wave-film-frame-no">${frameNo}</span>
                            <strong>${escapeHtml(film.title)}</strong>
                            <small>${escapeHtml(filmBlurb(film))}</small>
                        </span>
                    </span>
                    <span class="wave-film-sprocket" aria-hidden="true"></span>
                    <span class="wave-film-edge">W${waveNo} · ${frameNo}</span>
                </span>
            </button>
        `;
    }

    function copyHtml(wave, spec) {
        const active = wave === 1 ? ' is-active' : '';
        const hidden = wave === 1 ? 'false' : 'true';
        return `
            <div class="wave-film-copy${active}" data-wave="${wave}" aria-hidden="${hidden}">
                <span class="wave-film-kicker">${spec.kicker}</span>
                <h3>${spec.title}</h3>
                <p>${spec.body}</p>
                ${spec.aside ? `<small class="wave-film-aside">${spec.aside}</small>` : ''}
            </div>
        `;
    }

    function ensureFilmPages() {
        if (!dom.scroll || dom.scroll.dataset.ready === '1') return;
        deckFilms = buildDeck();
        dom.scroll.innerHTML = `
            <div class="wave-film-copy-stack">
                ${copyHtml(1, COPY_SPECS[1])}
                ${copyHtml(2, COPY_SPECS[2])}
                ${copyHtml(3, COPY_SPECS[3])}
            </div>
            <div class="wave-film-strip-wrap">
                <div class="wave-film-stage" id="wave-film-stage" tabindex="0" aria-label="三波浪潮电影胶片">
                    <div class="wave-film-ribbon" aria-hidden="true"></div>
                    ${deckFilms.map((film, index) => cardHtml(film, index)).join('')}
                </div>
                <button type="button" class="wave-return" id="wave-return">
                    <span class="wave-return-arrow">↑</span>
                    <span>回到星云</span>
                </button>
                <p class="wave-film-browse-hint"><span class="wave-browse-arrows">↔</span>滚动 / 拖动浏览胶片</p>
            </div>
        `;
        dom.scroll.dataset.ready = '1';
        dom.stage = document.getElementById('wave-film-stage');
        bindFilmInteractions();
        layoutShuffle(true);
        updateCopy();
        updateBackgroundFocus();
    }

    function refreshFilmCards() {
        if (!dom.scroll) return;
        if (dom.scroll.dataset.ready !== '1' || !getStage()) {
            if (dom.scroll) dom.scroll.dataset.ready = '';
            ensureFilmPages();
            return;
        }
        deckFilms = buildDeck();
        const stage = getStage();
        stage.innerHTML = `<div class="wave-film-ribbon" aria-hidden="true"></div>${deckFilms.map((film, index) => cardHtml(film, index)).join('')}`;
        layoutShuffle(true);
        updateCopy();
        updateBackgroundFocus();
    }

    function fadeBrowseHint() {
        const hint = dom.scroll && dom.scroll.querySelector('.wave-film-browse-hint');
        if (hint) hint.classList.add('is-faded');
    }

    function updateCopy() {
        if (!dom.scroll) return;
        const from = waveScene.wave;
        const to = waveScene.targetWave;
        const crossing = Boolean(waveScene.transitionKind) && from !== to;
        dom.scroll.querySelectorAll('.wave-film-copy').forEach(node => {
            const wave = Number(node.dataset.wave);
            const incoming = crossing && wave === to;
            const outgoing = crossing && wave === from;
            const idleActive = !crossing && wave === from;
            node.style.opacity = '';
            node.style.transform = '';
            node.classList.toggle('is-active', incoming || idleActive);
            node.classList.toggle('is-leaving', outgoing);
            node.setAttribute('aria-hidden', incoming || idleActive ? 'false' : 'true');
        });
    }

    function cancelWaveTransition() {
        if (waveTransRaf) cancelAnimationFrame(waveTransRaf);
        waveTransRaf = 0;
        waveScene.transitionKind = '';
        waveScene.transitionProgress = 0;
    }

    function kindFromWaves(from, to) {
        if (from === to) return '';
        if (from === 1 && to === 2) return 'city-mountain';
        if (from === 2 && to === 1) return 'mountain-city';
        if (from === 2 && to === 3) return 'mountain-letter';
        if (from === 3 && to === 2) return 'letter-mountain';
        if (from === 1 && to === 3) return 'city-letter';
        if (from === 3 && to === 1) return 'letter-city';
        return '';
    }

    function finishWaveTransition(wave) {
        cancelWaveTransition();
        waveScene.wave = wave;
        waveScene.targetWave = wave;
        waveScene.particleSceneMode = MODE_BY_WAVE[wave] || 'city';
        updateCopy();
    }

    function startWaveTransition(nextWave) {
        if (nextWave === waveScene.targetWave && waveScene.transitionKind) return;
        if (waveScene.transitionKind && waveScene.transitionProgress > 0.35) {
            waveScene.wave = waveScene.targetWave;
        }
        if (nextWave === waveScene.wave) {
            finishWaveTransition(nextWave);
            return;
        }
        const kind = kindFromWaves(waveScene.wave, nextWave);
        waveScene.targetWave = nextWave;
        if (!kind || prefersReduced()) {
            finishWaveTransition(nextWave);
            return;
        }
        if (waveTransRaf) cancelAnimationFrame(waveTransRaf);
        waveScene.transitionKind = kind;
        waveScene.transitionProgress = 0;
        const started = performance.now();
        const tick = now => {
            waveScene.transitionProgress = clamp01((now - started) / WAVE_TRANS_MS);
            updateCopy();
            if (waveScene.transitionProgress >= 1) {
                finishWaveTransition(nextWave);
                return;
            }
            waveTransRaf = requestAnimationFrame(tick);
        };
        waveTransRaf = requestAnimationFrame(tick);
    }

    function shuffleSlot(offset) {
        const mobile = isMobile();
        const reach = mobile ? 3 : 4;
        const abs = Math.abs(offset);
        if (abs > reach) {
            return { x: offset * 48, y: 0, scale: 0.5, rotate: 0, opacity: 0, depth: 0, visible: false };
        }
        const side = Math.sign(offset) || 0;
        const pitch = mobile ? 188 : 248;
        const scales = [1.04, 0.86, 0.72, 0.6, 0.5];
        const opacities = [1, 0.82, 0.5, 0.32, 0.18];
        return {
            x: side * abs * pitch,
            y: abs === 0 ? -8 : 0,
            scale: scales[abs] || 0.5,
            rotate: 0,
            opacity: opacities[abs] || 0.18,
            depth: 24 - abs,
            visible: true
        };
    }

    function layoutShuffle(instant) {
        const stage = getStage();
        if (!stage) return;
        const reduced = prefersReduced() || instant;
        stage.querySelectorAll('.wave-film-card').forEach((card, index) => {
            const pose = shuffleSlot(index - waveScene.focusIndex);
            card.style.transition = reduced ? 'none' : '';
            card.style.zIndex = String(10 + pose.depth);
            card.style.opacity = String(pose.opacity);
            card.style.pointerEvents = pose.visible && pose.opacity > 0.12 ? 'auto' : 'none';
            card.style.transform = `translate(-50%, -50%) translate(${pose.x}px, ${pose.y}px) rotate(${pose.rotate}deg) scale(${pose.scale})`;
            card.classList.toggle('is-focus', index === waveScene.focusIndex);
            card.classList.toggle('is-away', !pose.visible);
        });
    }

    function setFocusIndex(next) {
        const count = deckFilms.length;
        if (!count) return;
        const index = Math.max(0, Math.min(count - 1, next));
        waveScene.focusIndex = index;
        waveScene.filmScrollProgress = count > 1 ? index / (count - 1) : 0;
        const film = deckFilms[index];
        const nextWave = film && film.wave ? film.wave : 1;
        layoutShuffle(false);
        updateCopy();
        updateBackgroundFocus();
        if (nextWave !== waveScene.targetWave || (nextWave !== waveScene.wave && !waveScene.transitionKind)) {
            startWaveTransition(nextWave);
        }
    }

    function updateBackgroundFocus() {
        const film = deckFilms[waveScene.focusIndex];
        const id = film ? String(film.id) : '';
        const featured = Boolean(FOCUS_IDS[id]);
        waveScene.focusId = featured ? id : '';
        const raw = featured ? 1 : 0;
        waveScene.backgroundFocus += (raw - waveScene.backgroundFocus) * 0.12;
    }

    function bindFilmInteractions() {
        const stage = getStage();
        if (!stage || !dom.film || axisBound) return;
        axisBound = true;
        bindFieldHits();

        let wheelAcc = 0;
        let dragging = false;
        let moved = false;
        let startX = 0;
        let dragSteps = 0;

        const onWheel = event => {
            if (waveScene.layer !== 'film' && waveScene.layer !== 'transitioning') return;
            const dialog = document.getElementById('movie-detail-dialog');
            if (dialog && dialog.open) return;
            event.preventDefault();
            wheelAcc += event.deltaY + event.deltaX;
            const step = isMobile() ? 88 : 64;
            if (Math.abs(wheelAcc) < step) return;
            const dir = Math.sign(wheelAcc);
            wheelAcc = 0;
            setFocusIndex(waveScene.focusIndex + dir);
            fadeBrowseHint();
        };

        dom.film.addEventListener('wheel', onWheel, { passive: false });

        const back = document.getElementById('wave-return');
        if (back) back.addEventListener('click', () => leaveFilm());

        stage.addEventListener('mousedown', event => {
            if (event.button !== 0) return;
            dragging = true;
            moved = false;
            startX = event.clientX;
            dragSteps = 0;
            stage.classList.add('is-dragging');
        });

        window.addEventListener('mousemove', event => {
            if (!dragging) return;
            const dx = event.clientX - startX;
            if (Math.abs(dx) > 8) moved = true;
            const unit = isMobile() ? 80 : 108;
            const steps = Math.trunc(-dx / unit);
            if (steps !== dragSteps) {
                setFocusIndex(waveScene.focusIndex + (steps - dragSteps));
                dragSteps = steps;
                fadeBrowseHint();
            }
        });

        const endDrag = () => {
            if (!dragging) return;
            dragging = false;
            const next = getStage();
            if (next) next.classList.remove('is-dragging');
            if (moved && next) {
                next.dataset.suppressClick = '1';
                setTimeout(() => { if (next) delete next.dataset.suppressClick; }, 40);
            }
        };

        window.addEventListener('mouseup', endDrag);

        stage.addEventListener('touchstart', event => {
            if (!event.touches[0]) return;
            dragging = true;
            moved = false;
            startX = event.touches[0].clientX;
            dragSteps = 0;
            stage.classList.add('is-dragging');
        }, { passive: true });

        window.addEventListener('touchmove', event => {
            if (!dragging || !event.touches[0]) return;
            const dx = event.touches[0].clientX - startX;
            if (Math.abs(dx) > 8) moved = true;
            const unit = isMobile() ? 80 : 108;
            const steps = Math.trunc(-dx / unit);
            if (steps !== dragSteps) {
                setFocusIndex(waveScene.focusIndex + (steps - dragSteps));
                dragSteps = steps;
                fadeBrowseHint();
            }
        }, { passive: true });

        window.addEventListener('touchend', endDrag);

        stage.addEventListener('click', event => {
            const next = getStage();
            if (next && next.dataset.suppressClick) {
                event.preventDefault();
                event.stopPropagation();
                return;
            }
            const card = event.target.closest('.wave-film-card');
            if (!card) return;
            const film = lookupFilm(card.dataset.movieId);
            const movie = film.movie || {
                movieId: film.id,
                title: film.title,
                year: film.year,
                rating: Number(film.rating) || 0,
                votes: 0,
                decade: '',
                genres: '',
                regionCode: 3,
                langCode: 3
            };
            if (!Number.isFinite(Number(movie.rating))) movie.rating = Number(film.rating) || 0;
            if (ctx && ctx.openMovieDetail) ctx.openMovieDetail(movie);
        });
    }

    function linePoints(x1, y1, x2, y2, count) {
        const points = [];
        for (let i = 0; i < count; i += 1) {
            const t = count === 1 ? 0 : i / (count - 1);
            points.push({ x: lerp(x1, x2, t), y: lerp(y1, y2, t) });
        }
        return points;
    }

    function takeScattered(points, count, salt) {
        if (points.length <= count) return points.slice();
        return points
            .map((point, index) => ({ point, score: hash01(index, salt) }))
            .sort((a, b) => a.score - b.score)
            .slice(0, count)
            .map(item => item.point);
    }

    function fillPoints(points, count, salt) {
        if (!count) return [];
        if (!points.length) return [];
        if (points.length >= count) return takeScattered(points, count, salt);
        const out = points.slice();
        while (out.length < count) {
            const src = points[out.length % points.length];
            const key = out.length + salt;
            out.push({
                x: src.x + (hash01(key, 1) - 0.5) * 5,
                y: src.y + (hash01(key, 2) - 0.5) * 5,
                openX: (src.openX == null ? src.x : src.openX) + (hash01(key, 3) - 0.5) * 5,
                openY: (src.openY == null ? src.y : src.openY) + (hash01(key, 4) - 0.5) * 5,
                role: src.role
            });
        }
        return out;
    }

    function collectFieldSample(budget) {
        const rows = (ctx && ctx.particleData) || [];
        const dialect = rows.filter(row => row.langCode === 3);
        const sample = dialect.slice();
        if (sample.length < budget) {
            const extras = rows.filter(row => row.langCode !== 3 && Number(row.rating) >= 8);
            for (let i = 0; i < extras.length && sample.length < budget; i += 1) {
                sample.push(extras[i]);
            }
        }
        let clone = 1;
        while (sample.length < budget && dialect.length) {
            for (let i = 0; i < dialect.length && sample.length < budget; i += 1) {
                sample.push(Object.assign({}, dialect[i], { _clone: clone }));
            }
            clone += 1;
        }
        return sample.slice(0, budget);
    }

    function buildCity(width, height) {
        const skyline = [];
        const street = [];
        const lights = [];
        const layers = [
            { cols: 34, baseY: 0.5, peak: 0.34, tall: 0.26, mid: 0.16, short: 0.08, winMin: 2, winSpan: 2, skipFloor: 0.12, skipWin: 0.18 },
            { cols: 38, baseY: 0.6, peak: 0.48, tall: 0.36, mid: 0.22, short: 0.12, winMin: 3, winSpan: 2, skipFloor: 0.06, skipWin: 0.1 },
            { cols: 40, baseY: 0.72, peak: 0.58, tall: 0.44, mid: 0.28, short: 0.14, winMin: 4, winSpan: 3, skipFloor: 0.04, skipWin: 0.05 }
        ];
        layers.forEach((layer, layerIndex) => {
            for (let i = 0; i < layer.cols; i += 1) {
                if (hash01(i + layerIndex * 17, 3) < 0.04) continue;
                const roll = hash01(i + layerIndex * 31, 6);
                let bh;
                if (roll > 0.8) bh = height * (layer.peak + hash01(i, 7) * 0.08);
                else if (roll > 0.5) bh = height * (layer.tall + hash01(i, 7) * 0.08);
                else if (roll > 0.22) bh = height * (layer.mid + hash01(i, 7) * 0.07);
                else bh = height * (layer.short + hash01(i, 7) * 0.05);
                const x0 = width * (0.01 + (i + hash01(i, 4) * 0.35) / layer.cols) * 0.98;
                const lean = (hash01(i, 14) - 0.5) * (8 + layerIndex * 3);
                const bw = 4 + hash01(i, 5) * (roll > 0.5 ? 14 : 20);
                const floors = 7 + Math.floor(bh / (height * 0.016));
                const windows = layer.winMin + Math.floor(hash01(i, 8) * layer.winSpan);
                const missingTop = Math.floor(hash01(i, 15) * 2);
                const baseY = height * layer.baseY + (hash01(i, 23) - 0.5) * 14;
                const tallFacade = layerIndex === 2 && roll > 0.5;
                for (let floor = 0; floor < floors - missingTop; floor += 1) {
                    if (hash01(i * 13 + floor, 16) < layer.skipFloor) continue;
                    const py = baseY - (floor / Math.max(1, floors)) * bh + (hash01(floor, 18) - 0.5) * 2;
                    for (let w = 0; w < windows; w += 1) {
                        if (hash01(i * 29 + floor * 7 + w, 19) < layer.skipWin) continue;
                        const px = x0 + lean * (floor / Math.max(1, floors))
                            + (w / Math.max(1, windows - 1) - 0.5) * bw
                            + (hash01(floor + w, 20) - 0.5) * 1.4;
                        skyline.push({ x: px, y: py, role: 'skyline' });
                        if (hash01(i * 17 + floor * 5 + w, 11) > 0.46) {
                            lights.push({
                                x: px + (hash01(floor + w, 12) - 0.5) * 2,
                                y: py,
                                role: 'light'
                            });
                        }
                    }
                    if (tallFacade) {
                        const fillCols = 2 + Math.floor(hash01(i + floor, 24) * 2);
                        for (let f = 0; f < fillCols; f += 1) {
                            skyline.push({
                                x: x0 + lean * (floor / Math.max(1, floors))
                                    + (f / Math.max(1, fillCols - 1) - 0.5) * bw * 0.92
                                    + (hash01(floor + f, 25) - 0.5) * 1.2,
                                y: py + (hash01(floor + f, 26) - 0.5) * 3,
                                role: 'skyline'
                            });
                        }
                    }
                }
                skyline.push({
                    x: x0 + lean + (hash01(i, 21) - 0.5) * 5,
                    y: baseY - bh + missingTop * 3,
                    role: 'skyline'
                });
            }
        });
        for (let lane = 0; lane < 6; lane += 1) {
            const y = height * (0.72 + lane * 0.022);
            for (let i = 0; i < 420; i += 1) {
                street.push({
                    x: width * (0.01 + hash01(i + lane * 90, 21) * 0.98),
                    y: y + (hash01(i, 22 + lane) - 0.5) * 9,
                    role: 'street'
                });
            }
        }
        return { skyline, street, lights };
    }

    function quadCurvePts(x1, y1, cx, cy, x2, y2, count) {
        const pts = [];
        for (let i = 0; i < count; i += 1) {
            const t = count === 1 ? 0.5 : i / (count - 1);
            const mt = 1 - t;
            pts.push({
                x: mt * mt * x1 + 2 * mt * t * cx + t * t * x2,
                y: mt * mt * y1 + 2 * mt * t * cy + t * t * y2
            });
        }
        return pts;
    }

    function addCurvedMountain(list, width, height, spec, role, edgeCount, fillCount, salt, layer) {
        const px = width * spec.peakX;
        const py = height * spec.peakY;
        const lx = width * (spec.peakX - spec.halfW);
        const rx = width * (spec.peakX + spec.halfW);
        const by = height * spec.baseY;
        const curveBend = (by - py) * 0.15;
        const leftCtrlX = px - spec.halfW * width * 0.55;
        const leftCtrlY = (py + by) * 0.5 + curveBend * 0.3;
        const rightCtrlX = px + spec.halfW * width * 0.55;
        const rightCtrlY = (py + by) * 0.5 + curveBend * 0.3;
        quadCurvePts(px, py, leftCtrlX, leftCtrlY, lx, by, edgeCount).forEach(point => {
            list.push({ x: point.x, y: point.y, role, layer });
        });
        quadCurvePts(px, py, rightCtrlX, rightCtrlY, rx, by, edgeCount).forEach(point => {
            list.push({ x: point.x, y: point.y, role, layer });
        });
        const baseJitter = 2.5;
        const basePts = linePoints(lx, by, rx, by, Math.floor(edgeCount * 0.7));
        basePts.forEach(point => {
            list.push({
                x: point.x + (hash01(point.x + salt, 91) - 0.5) * baseJitter,
                y: point.y + (hash01(point.y + salt, 92) - 0.5) * baseJitter,
                role, layer
            });
        });
        const ridgeCount = Math.max(3, Math.floor(fillCount / 12));
        const ptsPerRidge = Math.floor(fillCount / ridgeCount);
        for (let r = 0; r < ridgeCount; r += 1) {
            const frac = (r + 0.5) / ridgeCount;
            const baseX = lx + (rx - lx) * frac;
            const ridgeSalt = salt + r * 137;
            for (let j = 0; j < ptsPerRidge; j += 1) {
                const t = (j + 1) / (ptsPerRidge + 1);
                const ridgeX = px + (baseX - px) * t;
                const ridgeY = py + (by - py) * t;
                const spread = t * spec.halfW * width * 0.12;
                list.push({
                    x: ridgeX + (hash01(j + ridgeSalt, 6) - 0.5) * spread,
                    y: ridgeY + (hash01(j + ridgeSalt, 7) - 0.5) * spread * 0.4,
                    role, layer
                });
            }
        }
    }

    function buildMountain(width, height) {
        const layers = [];
        const layerSpecs = [
            { peaks: [
                { peakX: 0.12, peakY: 0.2, halfW: 0.14, baseY: 0.42 },
                { peakX: 0.38, peakY: 0.17, halfW: 0.16, baseY: 0.4 },
                { peakX: 0.62, peakY: 0.19, halfW: 0.15, baseY: 0.41 },
                { peakX: 0.88, peakY: 0.22, halfW: 0.13, baseY: 0.43 }
            ], edge: 48, fill: 40 },
            { peaks: [
                { peakX: 0.08, peakY: 0.25, halfW: 0.13, baseY: 0.48 },
                { peakX: 0.3, peakY: 0.22, halfW: 0.16, baseY: 0.47 },
                { peakX: 0.52, peakY: 0.2, halfW: 0.18, baseY: 0.46 },
                { peakX: 0.75, peakY: 0.24, halfW: 0.14, baseY: 0.48 },
                { peakX: 0.94, peakY: 0.27, halfW: 0.11, baseY: 0.49 }
            ], edge: 56, fill: 50 },
            { peaks: [
                { peakX: 0.1, peakY: 0.3, halfW: 0.15, baseY: 0.55 },
                { peakX: 0.32, peakY: 0.26, halfW: 0.18, baseY: 0.54 },
                { peakX: 0.55, peakY: 0.24, halfW: 0.2, baseY: 0.53 },
                { peakX: 0.78, peakY: 0.28, halfW: 0.16, baseY: 0.55 },
                { peakX: 0.95, peakY: 0.32, halfW: 0.12, baseY: 0.56 }
            ], edge: 64, fill: 65 },
            { peaks: [
                { peakX: 0.06, peakY: 0.36, halfW: 0.16, baseY: 0.64 },
                { peakX: 0.24, peakY: 0.3, halfW: 0.2, baseY: 0.65 },
                { peakX: 0.44, peakY: 0.27, halfW: 0.22, baseY: 0.66 },
                { peakX: 0.64, peakY: 0.32, halfW: 0.18, baseY: 0.64 },
                { peakX: 0.82, peakY: 0.35, halfW: 0.17, baseY: 0.63 }
            ], edge: 80, fill: 90 },
            { peaks: [
                { peakX: 0.08, peakY: 0.42, halfW: 0.15, baseY: 0.74 },
                { peakX: 0.26, peakY: 0.36, halfW: 0.19, baseY: 0.76 },
                { peakX: 0.46, peakY: 0.32, halfW: 0.22, baseY: 0.77 },
                { peakX: 0.66, peakY: 0.38, halfW: 0.17, baseY: 0.75 },
                { peakX: 0.84, peakY: 0.43, halfW: 0.14, baseY: 0.73 }
            ], edge: 90, fill: 110 }
        ];
        layerSpecs.forEach((layerSpec, layerIndex) => {
            const layerList = [];
            layerSpec.peaks.forEach((spec, peakIndex) => {
                addCurvedMountain(
                    layerList, width, height, spec, 'nearRidge',
                    layerSpec.edge, layerSpec.fill,
                    40 + layerIndex * 100 + peakIndex * 17,
                    layerIndex
                );
            });
            layers.push(layerList);
        });
        const sky = [];
        for (let i = 0; i < 500; i += 1) {
            const x = hash01(i, 301) * width;
            const rawY = hash01(i, 302);
            const y = rawY * rawY * height * 0.38;
            const isStar = hash01(i, 303) > 0.35;
            sky.push({
                x, y, role: 'mtnSky',
                skyType: isStar ? 'star' : 'fog',
                skySize: isStar ? 0.5 + hash01(i, 304) * 0.8 : 3 + hash01(i, 305) * 3.5,
                skyAlpha: isStar ? 0.04 + hash01(i, 306) * 0.07 : 0.012 + hash01(i, 307) * 0.02
            });
        }
        return { layers, sky };
    }

    function buildLetter(width, height) {
        const envelope = [];
        const paper = [];
        const cx = width * 0.5;
        const cy = height * 0.47;
        const lw = width * 0.36;
        const lh = height * 0.28;
        const left = cx - lw / 2;
        const right = cx + lw / 2;
        const top = cy - lh / 2;
        const bottom = cy + lh / 2;
        const flapY = top - lh * 0.38;
        const frame = [
            ...linePoints(left, top, right, top, 320),
            ...linePoints(right, top, right, bottom, 200),
            ...linePoints(right, bottom, left, bottom, 320),
            ...linePoints(left, bottom, left, top, 200),
            ...linePoints(left, top, cx, flapY, 160),
            ...linePoints(cx, flapY, right, top, 160)
        ];
        const inset = 3;
        const innerFrame = [
            ...linePoints(left + inset, top + inset, right - inset, top + inset, 280),
            ...linePoints(right - inset, top + inset, right - inset, bottom - inset, 170),
            ...linePoints(right - inset, bottom - inset, left + inset, bottom - inset, 280),
            ...linePoints(left + inset, bottom - inset, left + inset, top + inset, 170)
        ];
        frame.forEach((point, index) => {
            if (hash01(index, 51) < 0.02) return;
            const x = point.x + (hash01(index, 52) - 0.5) * 0.8;
            const y = point.y + (hash01(index, 53) - 0.5) * 0.8;
            envelope.push({ x, y, role: 'envelope' });
        });
        innerFrame.forEach((point, index) => {
            if (hash01(index + 5000, 51) < 0.02) return;
            const x = point.x + (hash01(index + 5000, 52) - 0.5) * 0.6;
            const y = point.y + (hash01(index + 5000, 53) - 0.5) * 0.6;
            envelope.push({ x, y, role: 'envelope' });
        });
        const fold = [
            ...linePoints(left, top, cx, cy, 160),
            ...linePoints(right, top, cx, cy, 160)
        ];
        fold.forEach((point, index) => {
            if (hash01(index, 61) < 0.02) return;
            const x = point.x + (hash01(index, 62) - 0.5) * 0.8;
            const y = point.y + (hash01(index, 63) - 0.5) * 0.8;
            envelope.push({ x, y, role: 'crease' });
        });
        const lineCount = 7;
        const lineMarginX = 24;
        const lineMarginY = 18;
        const innerLeft = left + lineMarginX;
        const innerRight = right - lineMarginX;
        const innerTop = top + lineMarginY;
        const innerBottom = bottom - lineMarginY;
        for (let line = 0; line < lineCount; line += 1) {
            const ly = innerTop + (line / (lineCount - 1)) * (innerBottom - innerTop);
            const isShort = hash01(line, 101) > 0.65;
            const lineEnd = isShort ? innerLeft + (innerRight - innerLeft) * (0.45 + hash01(line, 102) * 0.3) : innerRight;
            const ptsInLine = 70 + Math.floor(hash01(line, 103) * 35);
            for (let p = 0; p < ptsInLine; p += 1) {
                const t = p / (ptsInLine - 1);
                const baseX = innerLeft + (lineEnd - innerLeft) * t;
                const gapNoise = hash01(p + line * 200, 104);
                if (gapNoise < 0.06) continue;
                const wordGap = hash01(p + line * 200, 105) > 0.82 ? 3 + hash01(p, 106) * 4 : 0;
                const px = baseX + wordGap + (hash01(p + line * 200, 107) - 0.5) * 1.5;
                const py = ly + (hash01(p + line * 200, 108) - 0.5) * 1.2;
                paper.push({ x: px, y: py, role: 'paper' });
            }
        }
        return { envelope, paper };
    }

    function assignPoint(list, index, home, role) {
        const point = list[index];
        if (!point) {
            return {
                x: home.x,
                y: home.y,
                openX: home.x,
                openY: home.y,
                role: role || 'floater'
            };
        }
        return {
            x: point.x,
            y: point.y,
            openX: point.openX == null ? point.x : point.openX,
            openY: point.openY == null ? point.y : point.openY,
            role: point.role || role || 'floater'
        };
    }

    function floaterPoint(home, key, amount) {
        return {
            x: home.x + (hash01(key, 3) - 0.5) * amount,
            y: home.y + (hash01(key, 4) - 0.5) * amount,
            openX: home.x + (hash01(key, 5) - 0.5) * amount,
            openY: home.y + (hash01(key, 6) - 0.5) * amount,
            role: 'floater'
        };
    }

    function rebuildField() {
        if (!dom.field || !ctx || !ctx.particleData) return;
        const { width, height } = resizeCanvas(dom.field);
        const budget = isMobile() ? 2400 : 9000;
        const sample = collectFieldSample(budget);
        const n = sample.length;
        const city = buildCity(width, height);
        const mountain = buildMountain(width, height);
        const letter = buildLetter(width, height);
        const citySky = fillPoints(city.skyline, Math.floor(n * 0.52), 17);
        const cityStreet = fillPoints(city.street, Math.floor(n * 0.12), 18);
        const cityLight = fillPoints(city.lights, Math.floor(n * 0.12), 19);
        const mtnLayers = mountain.layers.map((layer, i) =>
            fillPoints(layer, Math.floor(n * [0.04, 0.06, 0.1, 0.16, 0.22][i]), 27 + i * 5)
        );
        const mtnSky = fillPoints(mountain.sky, Math.floor(n * 0.06), 37);
        const letEnv = fillPoints(letter.envelope, Math.floor(n * 0.4), 61);
        const letPaper = fillPoints(letter.paper, Math.floor(n * 0.28), 64);
        const c1 = citySky.length;
        const c2 = c1 + cityStreet.length;
        const c3 = c2 + cityLight.length;
        const mtnOffsets = [];
        let mtnAcc = 0;
        mtnLayers.forEach(layer => { mtnOffsets.push(mtnAcc); mtnAcc += layer.length; });
        const mtnTotal = mtnAcc;
        const mtnSkyStart = mtnTotal;
        const mtnSkyEnd = mtnSkyStart + mtnSky.length;
        const l1 = letEnv.length;
        const l2 = l1 + letPaper.length;

        fieldParticles = sample.map((row, index) => {
            const seed = `${row.movieId}|${row._clone || 0}`;
            const home = {
                x: hash01(seed, 1) * width,
                y: hash01(seed, 2) * height
            };
            const sizeVar = 0.6 + hash01(seed, 91) * 0.8;
            const cityPt = index < c1
                ? assignPoint(citySky, index, home, 'skyline')
                : index < c2
                    ? assignPoint(cityStreet, index - c1, home, 'street')
                    : index < c3
                        ? assignPoint(cityLight, index - c2, home, 'light')
                        : floaterPoint(home, `${seed}-c`, 40);
            let mountainPt;
            let mtnLayerIdx = -1;
            if (index < mtnTotal) {
                for (let li = mtnLayers.length - 1; li >= 0; li -= 1) {
                    if (index >= mtnOffsets[li]) {
                        mountainPt = assignPoint(mtnLayers[li], index - mtnOffsets[li], home, 'nearRidge');
                        mtnLayerIdx = li;
                        break;
                    }
                }
            } else if (index < mtnSkyEnd) {
                mountainPt = assignPoint(mtnSky, index - mtnSkyStart, home, 'mtnSky');
            } else {
                mountainPt = floaterPoint(home, `${seed}-m`, 45);
            }
            if (!mountainPt) mountainPt = floaterPoint(home, `${seed}-m`, 45);
            const letterClosed = index < l1
                ? assignPoint(letEnv, index, home, 'envelope')
                : index < l2
                    ? assignPoint(letPaper, index - l1, home, 'paper')
                    : floaterPoint(home, `${seed}-l`, 38);
            return {
                seed,
                home,
                movieId: String(row.movieId || ''),
                title: row.title || '',
                year: row.year || '',
                rating: Number(row.rating) || 0,
                city: cityPt,
                mountain: mountainPt,
                letter: letterClosed,
                cityRole: cityPt.role,
                mountainRole: mountainPt.role,
                letterRole: letterClosed.role,
                mtnLayer: mtnLayerIdx,
                x: cityPt.x,
                y: cityPt.y,
                phase: hash01(seed, 13) * Math.PI * 2,
                freq: 0.1 + hash01(seed, 19) * 0.08,
                size: (cityPt.role === 'floater' ? 0.85 : 1.35) * sizeVar
            };
        });
        fieldLastT = 0;
        fieldReady = true;
        bindFieldHits();
    }

    function hitFieldParticle(clientX, clientY) {
        if (!dom.field || !fieldParticles.length) return null;
        const rect = dom.field.getBoundingClientRect();
        const x = clientX - rect.left;
        const y = clientY - rect.top;
        const mode = MODE_BY_WAVE[waveScene.targetWave] || MODE_BY_WAVE[waveScene.wave] || 'city';
        let best = null;
        let bestDist = (mode === 'mountain' || mode === 'letter') ? 28 : 16;
        for (let i = 0; i < fieldParticles.length; i += 1) {
            const particle = fieldParticles[i];
            const dist = Math.hypot(particle.x - x, particle.y - y);
            if (dist < bestDist) {
                bestDist = dist;
                best = particle;
            }
        }
        return best;
    }

    function openFieldMovie(particle) {
        if (!particle || !particle.movieId || !ctx || !ctx.openMovieDetail) return;
        const film = lookupFilm(particle.movieId, {
            title: particle.title,
            year: particle.year,
            rating: particle.rating
        });
        const movie = film.movie || {
            movieId: particle.movieId,
            title: particle.title,
            year: particle.year,
            rating: Number(particle.rating) || 0,
            votes: 0,
            decade: '',
            genres: '',
            regionCode: 3,
            langCode: 3
        };
        if (!Number.isFinite(Number(movie.rating))) movie.rating = Number(particle.rating) || 0;
        ctx.openMovieDetail(movie);
    }

    function bindFieldHits() {
        if (!dom.field || dom.field.dataset.hitBound === '1') return;
        dom.field.dataset.hitBound = '1';
        dom.field.addEventListener('mousemove', rafThrottle(event => {
            if (waveScene.layer !== 'film') return;
            const hit = hitFieldParticle(event.clientX, event.clientY);
            dom.field.style.cursor = hit ? 'pointer' : 'default';
            const tip = hit
                ? `${hit.title || '电影'}${hit.year ? ` · ${hit.year}` : ''}${Number.isFinite(Number(hit.rating)) ? ` · ${Number(hit.rating).toFixed(1)}` : ''}`
                : '';
            dom.field.title = tip;
        }));
        dom.field.addEventListener('click', event => {
            if (waveScene.layer !== 'film') return;
            const dialog = document.getElementById('movie-detail-dialog');
            if (dialog && dialog.open) return;
            const hit = hitFieldParticle(event.clientX, event.clientY);
            if (hit) openFieldMovie(hit);
        });
    }

    function mixPts(a, b, t) {
        return {
            x: lerp(a.x, b.x, t),
            y: lerp(a.y, b.y, t),
            role: t < 0.5 ? a.role : b.role
        };
    }

    function worldPoint(particle, mode, unfold) {
        if (mode === 'city') {
            return { x: particle.city.x, y: particle.city.y, role: particle.cityRole };
        }
        if (mode === 'mountain') {
            return { x: particle.mountain.x, y: particle.mountain.y, role: particle.mountainRole };
        }
        const closed = particle.letter;
        return {
            x: lerp(closed.x, closed.openX, unfold),
            y: lerp(closed.y, closed.openY, unfold),
            role: particle.letterRole
        };
    }

    function dustPoint(particle, height) {
        const home = particle.home || { x: particle.x, y: particle.y };
        return {
            x: home.x,
            y: height * (0.18 + hash01(particle.seed || 0, 21) * 0.3),
            role: 'floater'
        };
    }

    function gatherPoint(particle, width, height) {
        return {
            x: width * 0.5 + (hash01(particle.seed || 0, 31) - 0.5) * 90,
            y: height * 0.47 + (hash01(particle.seed || 0, 32) - 0.5) * 56,
            role: 'floater'
        };
    }

    function letterUnfoldAmount() {
        return 0;
    }

    function stagedGoal(from, via, to, t, a, b) {
        if (t < a) return from;
        if (t < b) return mixPts(from, via, smooth01((t - a) / Math.max(0.001, b - a)));
        return mixPts(via, to, smooth01((t - b) / Math.max(0.001, 1 - b)));
    }

    function mixFieldGoal(particle, width, height, unfold) {
        const kind = waveScene.transitionKind;
        const t = waveScene.transitionProgress;
        const city = worldPoint(particle, 'city', 0);
        const mountain = worldPoint(particle, 'mountain', 0);
        const letter = worldPoint(particle, 'letter', unfold);
        const dust = dustPoint(particle, height);
        const gather = gatherPoint(particle, width, height);
        if (!kind) {
            const mode = MODE_BY_WAVE[waveScene.wave] || 'city';
            return worldPoint(particle, mode, mode === 'letter' ? unfold : 0);
        }
        if (kind === 'city-mountain') return stagedGoal(city, dust, mountain, t, 0.16, 0.52);
        if (kind === 'mountain-city') return stagedGoal(mountain, dust, city, t, 0.14, 0.50);
        if (kind === 'mountain-letter') {
            if (t < 0.22) return mixPts(mountain, dust, smooth01(t / 0.22));
            if (t < 0.52) return mixPts(dust, worldPoint(particle, 'letter', 0), smooth01((t - 0.22) / 0.3));
            return letter;
        }
        if (kind === 'letter-mountain') {
            if (t < 0.22) return mixPts(letter, dust, smooth01(t / 0.22));
            if (t < 0.52) return mixPts(dust, mountain, smooth01((t - 0.22) / 0.3));
            return mountain;
        }
        if (kind === 'city-letter') return stagedGoal(city, gather, letter, t, 0.18, 0.52);
        if (kind === 'letter-city') return stagedGoal(letter, gather, city, t, 0.18, 0.52);
        return city;
    }

    function drawField(now) {
        if (!dom.field || !fieldReady) return;
        const context = dom.field.getContext('2d');
        if (!context) return;
        const width = window.innerWidth;
        const height = window.innerHeight;
        context.clearRect(0, 0, width, height);
        /* Nebula background glow */
        const nebulaMode = MODE_BY_WAVE[waveScene.targetWave] || MODE_BY_WAVE[waveScene.wave] || 'city';
        const nc = nebulaMode === 'mountain' ? [50, 110, 130]
            : nebulaMode === 'letter' ? [130, 80, 40]
            : [100, 70, 30];
        const nebulaKey = `${width}|${height}|${nc.join(',')}`;
        if (!nebulaGradient || nebulaGradientKey !== nebulaKey) {
            nebulaGradientKey = nebulaKey;
            nebulaGradient = context.createRadialGradient(
                width * 0.5, height * 0.45, 0,
                width * 0.5, height * 0.45, Math.max(width, height) * 0.65
            );
            nebulaGradient.addColorStop(0, `rgba(${nc[0]}, ${nc[1]}, ${nc[2]}, 0.07)`);
            nebulaGradient.addColorStop(0.4, `rgba(${nc[0]}, ${nc[1]}, ${nc[2]}, 0.025)`);
            nebulaGradient.addColorStop(1, 'rgba(5, 5, 7, 0)');
        }
        context.fillStyle = nebulaGradient;
        context.fillRect(0, 0, width, height);
        updateBackgroundFocus();
        const dt = fieldLastT ? Math.min(0.05, (now - fieldLastT) / 1000) : 0.016;
        fieldLastT = now;
        const settleTau = waveScene.transitionKind ? FIELD_SETTLE_TRANS : FIELD_SETTLE;
        const settle = 1 - Math.exp(-dt / settleTau);
        const focus = waveScene.backgroundFocus;
        const focusKind = FOCUS_IDS[waveScene.focusId] || '';
        const unfold = letterUnfoldAmount(focusKind, focus);
        const time = now * 0.001;
        const cityBoost = focusKind === 'city' ? focus : 0;
        const mountainBoost = focusKind === 'mountain' ? focus : 0;
        const letterBoost = focusKind === 'letter' ? focus : 0;
        const kind = waveScene.transitionKind;
        const tp = waveScene.transitionProgress;
        const lightMul = kind === 'city-mountain'
            ? 1 - clamp01(tp / 0.16)
            : kind === 'mountain-city'
                ? clamp01((tp - 0.52) / 0.48)
                : 1;
        fieldParticles.forEach(particle => {
            const goal = mixFieldGoal(particle, width, height, unfold);
            if (waveScene.leavePull > 0.001) {
                goal.x = lerp(goal.x, enterOrigin.x, waveScene.leavePull);
                goal.y = lerp(goal.y, enterOrigin.y, waveScene.leavePull);
            }
            const role = goal.role || 'floater';
            let drift = role === 'floater' ? 2.4 : 0.55;
            let speed = 1;
            if (role === 'street') {
                goal.x += Math.sin(time * (0.16 + cityBoost * 0.22) + particle.phase) * (14 + cityBoost * 10);
                drift = 0.28;
            } else if (role === 'skyline') {
                drift = 0.42;
            } else if (role === 'nearRidge' || role === 'mtnSky') {
                const layerDrift = role === 'mtnSky' ? 0.15 : (0.12 + (particle.mtnLayer >= 0 ? particle.mtnLayer : 2) * 0.07);
                drift *= layerDrift + mountainBoost * 0.2;
                speed = role === 'mtnSky' ? 0.18 : 0.42;
                if (role === 'nearRidge' && (particle.mtnLayer >= 3)) {
                    goal.x += Math.sin(time * 0.08 + particle.phase) * 3;
                }
            } else if (role === 'envelope' || role === 'crease' || role === 'paper') {
                drift *= 0.46;
                if (letterBoost) {
                    goal.x = lerp(goal.x, width * 0.5, letterBoost * 0.1);
                    goal.y = lerp(goal.y, height * 0.47, letterBoost * 0.1);
                    speed = 0.36;
                }
            }
            if (mountainBoost) speed *= 1 - mountainBoost * 0.48;
            if (letterBoost && role === 'floater') speed *= 1 - letterBoost * 0.55;
            if (kind === 'city-mountain' && tp > 0.12 && tp < 0.55) drift += 1.4;
            if (kind === 'mountain-letter' && tp > 0.08 && tp < 0.4) drift += 1.8;
            if (waveScene.leavePull > 0.001) drift *= 1 - waveScene.leavePull * 0.75;
            particle.x += (goal.x - particle.x) * settle;
            particle.y += (goal.y - particle.y) * settle;
            const wobbleX = Math.sin(time * particle.freq * speed + particle.phase) * drift;
            const wobbleY = Math.cos(time * particle.freq * 0.8 * speed + particle.phase) * drift * 0.5;
            const x = particle.x + wobbleX;
            const y = particle.y + wobbleY;
            let alpha = 0.06;
            let size = particle.size;
            const breath = 0.82 + 0.18 * (0.5 + 0.5 * Math.sin(time * 0.55 + particle.phase));
            if (role === 'skyline') {
                alpha = (0.14 + cityBoost * 0.08) * breath;
                size = 1.7;
            } else if (role === 'street') {
                alpha = 0.16;
                size = 1.15;
            } else if (role === 'light') {
                const flicker = 0.4 + 0.6 * (0.5 + 0.5 * Math.sin(time * 3.1 + particle.phase));
                alpha = (0.26 + cityBoost * 0.34) * flicker * lightMul;
                size = 2.1 + cityBoost * 0.9;
            } else if (role === 'nearRidge') {
                const ml = particle.mtnLayer >= 0 ? particle.mtnLayer : 2;
                const layerAlphas = [0.04, 0.06, 0.1, 0.18, 0.24];
                const layerSizes = [1.8, 2.2, 2.8, 3.4, 3.8];
                const ba = layerAlphas[ml] + mountainBoost * 0.08;
                alpha = ba * (0.5 + 0.5 * (0.45 + 0.55 * Math.sin(time * (0.22 + ml * 0.03) + particle.phase)));
                size = layerSizes[ml];
            } else if (role === 'mtnSky') {
                alpha = particle.skyAlpha || 0.04;
                if (particle.skyType === 'star') {
                    alpha *= 0.5 + 0.5 * Math.sin(time * 1.2 + particle.phase);
                }
                size = particle.skySize || 1;
            } else if (role === 'envelope') {
                alpha = 0.32 + letterBoost * 0.12;
                size = 3.2;
            } else if (role === 'paper') {
                alpha = 0.12 + letterBoost * 0.06;
                size = 1.4 + (hash01(particle.seed || 0, 71) > 0.5 ? 0.4 : 0);
            } else if (role === 'crease') {
                alpha = 0.28 + letterBoost * 0.1;
                size = 2.8;
            }
            size *= particle.size;
            /* Per-wave emotional color palette */
            const cm = MODE_BY_WAVE[waveScene.targetWave] || MODE_BY_WAVE[waveScene.wave] || 'city';
            let cr, cg, cb;
            if (role === 'light' || role === 'street') {
                cr = 255; cg = 200; cb = 110;
            } else if (role === 'mtnSky') {
                cr = 180; cg = 200; cb = 220;
            } else if (cm === 'mountain' && (role === 'nearRidge' || role === 'farRidge')) {
                const ml = particle.mtnLayer >= 0 ? particle.mtnLayer : 2;
                const mtnColors = [[80, 130, 155], [95, 150, 170], [105, 160, 180], [115, 170, 190], [120, 175, 195]];
                cr = mtnColors[ml][0]; cg = mtnColors[ml][1]; cb = mtnColors[ml][2];
            } else if (cm === 'letter') {
                if (role === 'envelope') { cr = 185; cg = 130; cb = 75; }
                else if (role === 'crease') { cr = 200; cg = 150; cb = 95; }
                else if (role === 'paper') { cr = 235; cg = 215; cb = 185; }
                else { cr = 215; cg = 165; cb = 115; }
            } else {
                cr = 210; cg = 160; cb = 70;
            }
            /* Glow halo for larger particles */
            if (size > 2.0 && alpha > 0.06) {
                const glowAlphaMul = cm === 'mountain' ? 0.25 : cm === 'letter' ? 0.15 : 0.20;
                const glowSizeMul = cm === 'mountain' ? 3.8 : cm === 'letter' ? 2.8 : 3.2;
                const gs = size * glowSizeMul;
                const ga = alpha * glowAlphaMul;
                context.fillStyle = `rgba(${cr}, ${cg}, ${cb}, ${ga})`;
                context.fillRect(x - (gs - size) * 0.5, y - (gs - size) * 0.5, gs, gs);
            }
            /* Core particle */
            const neon = role === 'light' && hash01(particle.seed || 0, 41) > 0.72;
            context.fillStyle = neon
                ? `rgba(255, 168, 92, ${alpha})`
                : role === 'light'
                    ? `rgba(255, 214, 128, ${alpha})`
                    : `rgba(${cr}, ${cg}, ${cb}, ${alpha})`;
            context.fillRect(x, y, size, size);
        });
        /* Vignette overlay */
        const vigKey = `${width}|${height}`;
        if (!vigGradient || vigGradientKey !== vigKey) {
            vigGradientKey = vigKey;
            vigGradient = context.createRadialGradient(
                width * 0.5, height * 0.5, Math.min(width, height) * 0.22,
                width * 0.5, height * 0.5, Math.max(width, height) * 0.72
            );
            vigGradient.addColorStop(0, 'rgba(0, 0, 0, 0)');
            vigGradient.addColorStop(1, 'rgba(0, 0, 0, 0.22)');
        }
        context.fillStyle = vigGradient;
        context.fillRect(0, 0, width, height);
    }

    function startFieldLoop() {
        stopFieldLoop();
        if (!fieldReady) rebuildField();
        const tick = now => {
            drawField(now);
            if (waveScene.layer === 'film' || waveScene.layer === 'returning' || waveScene.layer === 'transitioning') {
                fieldRaf = requestAnimationFrame(tick);
            } else {
                fieldRaf = 0;
            }
        };
        fieldRaf = requestAnimationFrame(tick);
    }

    function stopFieldLoop() {
        if (fieldRaf) cancelAnimationFrame(fieldRaf);
        fieldRaf = 0;
    }

    function phaseRange(t, start, end) {
        if (end <= start) return t >= end ? 1 : 0;
        return smooth01(clamp01((t - start) / (end - start)));
    }

    function transitionPhases(direction, progress) {
        const t = clamp01(progress);
        if (direction === 'enter') {
            return {
                reveal: phaseRange(t, 0, 0.35),
                content: phaseRange(t, 0.35, 0.75),
                canvas: 1 - phaseRange(t, 0.75, 1),
                pull: 0
            };
        }
        return {
            reveal: 1 - phaseRange(t, 0.35, 0.65),
            content: 1 - phaseRange(t, 0, 0.35),
            canvas: t < 0.75 ? 1 : 1 - phaseRange(t, 0.75, 1),
            pull: smooth01(phaseRange(t, 0.35, 0.65))
        };
    }

    function drawTransition(origin, canvasAlpha, reveal) {
        const { width, height, context } = getTransitionSurface();
        if (!context) return;
        context.clearRect(0, 0, width, height);
        const alpha = canvasAlpha == null ? 1 : clamp01(canvasAlpha);
        if (alpha <= 0.001) return;

        context.globalAlpha = alpha;
        context.fillStyle = '#050507';
        context.fillRect(0, 0, width, height);

        const revealAmount = reveal == null ? 0 : clamp01(reveal);
        if (revealAmount > 0.001) {
            const holeR = lerp(0, Math.hypot(width, height) * 0.72, revealAmount);
            context.save();
            context.globalCompositeOperation = 'destination-out';
            context.beginPath();
            context.arc(origin.x, origin.y, holeR, 0, Math.PI * 2);
            context.fill();
            context.restore();
        }
        context.globalAlpha = 1;
    }

    function setTransitionOrigin(origin) {
        if (!dom.film || !origin) return;
        dom.film.style.setProperty('--wave-origin-x', `${origin.x}px`);
        dom.film.style.setProperty('--wave-origin-y', `${origin.y}px`);
    }

    function setFilmReveal(amount, origin) {
        if (!dom.film || !origin) return;
        const reveal = clamp01(amount);
        const radius = lerp(0, FILM_REVEAL_VMAX, reveal);
        dom.film.style.clipPath = `circle(${radius}vmax at ${origin.x}px ${origin.y}px)`;
    }

    function clearFilmReveal() {
        if (!dom.film) return;
        dom.film.style.clipPath = 'none';
        dom.film.style.removeProperty('--wave-origin-x');
        dom.film.style.removeProperty('--wave-origin-y');
    }

    function fadeScrollyOverlay(hide) {
        const root = document.documentElement;
        if (hide) {
            requestAnimationFrame(() => root.classList.add('wave-overlay-hidden'));
            return animate(OVERLAY_FADE_MS, () => {});
        }
        root.classList.remove('wave-overlay-hidden');
        return Promise.resolve();
    }

    function prefetchField() {
        if (fieldReady || prefetchScheduled) return;
        prefetchScheduled = true;
        const run = () => {
            prefetchScheduled = false;
            if (!fieldReady && dom.field && ctx && ctx.particleData) rebuildField();
        };
        if (typeof requestIdleCallback === 'function') {
            requestIdleCallback(run, { timeout: 2000 });
        } else {
            window.setTimeout(run, 0);
        }
    }

    async function ensureFieldReady() {
        if (fieldReady) return;
        await new Promise(resolve => requestAnimationFrame(resolve));
        if (!fieldReady) rebuildField();
    }

    async function prepareFilmUnderMask(origin) {
        if (!dom.film) return;
        ensureFilmPages();
        await ensureFieldReady();
        dom.film.hidden = false;
        dom.film.classList.add('is-on');
        dom.film.setAttribute('aria-hidden', 'false');
        dom.film.style.opacity = '1';
        setTransitionOrigin(origin);
        setFilmReveal(0, origin);
        setFilmChrome(0);
        startFieldLoop();
    }

    function clearTransitionCanvas() {
        const { width, height, context } = getTransitionSurface();
        if (context) context.clearRect(0, 0, width, height);
    }

    function getTransitionSurface() {
        const width = window.innerWidth;
        const height = window.innerHeight;
        if (transitionBox.width !== width || transitionBox.height !== height) {
            resizeCanvas(dom.transition);
            transitionBox = { width, height };
        }
        return {
            width,
            height,
            context: dom.transition ? dom.transition.getContext('2d') : null
        };
    }

    function setFilmChrome(opacity) {
        const amount = clamp01(opacity);
        if (dom.scroll) {
            dom.scroll.style.opacity = String(amount);
            dom.scroll.style.transform = `translateY(${(1 - amount) * 16}px)`;
        }
    }

    function resetFilmChrome() {
        if (dom.scroll) {
            dom.scroll.style.opacity = '';
            dom.scroll.style.transform = '';
        }
        if (dom.field) dom.field.style.opacity = '';
        if (dom.film) dom.film.style.opacity = '';
        if (dom.transition) dom.transition.style.opacity = '';
        clearFilmReveal();
    }

    function showTransitionCanvas() {
        if (!dom.transition) return;
        dom.transition.style.opacity = '1';
        dom.transition.hidden = false;
    }

    async function hideTransitionCanvas() {
        if (!dom.transition) return;
        if (!prefersReduced() && !dom.transition.hidden) {
            const start = Number(dom.transition.style.opacity || 1);
            if (start > 0.02) {
                await animate(240, t => {
                    dom.transition.style.opacity = String(start * (1 - t));
                });
            }
        }
        clearTransitionCanvas();
        dom.transition.hidden = true;
        dom.transition.style.opacity = '';
    }

    function applyTransitionFrame(direction, origin, phase) {
        setFilmReveal(phase.reveal, origin);
        setFilmChrome(phase.content);
        waveScene.leavePull = phase.pull;
        if (direction === 'leave' && dom.field) {
            dom.field.style.opacity = String(0.85 * phase.content);
        }
        drawTransition(origin, phase.canvas, phase.reveal);
    }

    async function runTransition(direction, origin, onLeaveClose) {
        if (prefersReduced()) {
            clearTransitionCanvas();
            if (direction === 'enter') {
                setFilmReveal(1, origin);
                setFilmChrome(1);
            } else {
                setFilmChrome(0);
                waveScene.leavePull = 0;
            }
            return;
        }
        await animate(TRANSITION_MS, t => {
            const phase = transitionPhases(direction, t);
            applyTransitionFrame(direction, origin, phase);
            if (direction === 'leave' && onLeaveClose && t >= 0.65 && phase.reveal <= 0.02) {
                onLeaveClose();
            }
        });
        if (direction === 'leave') {
            waveScene.leavePull = 0;
            if (dom.field) dom.field.style.opacity = '';
        }
    }

    function openFilmChrome() {
        ensureFilmPages();
        cancelWaveTransition();
        waveScene.wave = 1;
        waveScene.targetWave = 1;
        waveScene.focusIndex = 0;
        waveScene.filmScrollProgress = 0;
        waveScene.particleSceneMode = 'city';
        waveScene.backgroundFocus = 0;
        waveScene.focusId = '';
        const hint = dom.scroll && dom.scroll.querySelector('.wave-film-browse-hint');
        if (hint) hint.classList.remove('is-faded');
        if (dom.film) {
            dom.film.hidden = false;
            dom.film.classList.add('is-on');
            dom.film.setAttribute('aria-hidden', 'false');
            dom.film.style.opacity = '1';
        }
        setFilmChrome(1);
        document.documentElement.classList.add('wave-film-open');
        layoutShuffle(true);
        updateCopy();
        updateBackgroundFocus();
        if (ctx && ctx.setChartHidden) ctx.setChartHidden(true);
        if (!fieldRaf) startFieldLoop();
    }

    function closeFilmChrome() {
        cancelWaveTransition();
        waveScene.leavePull = 0;
        document.documentElement.classList.remove('wave-film-open');
        resetFilmChrome();
        if (dom.film) {
            dom.film.classList.remove('is-on');
            dom.film.hidden = true;
            dom.film.setAttribute('aria-hidden', 'true');
        }
        if (ctx && ctx.setChartHidden) ctx.setChartHidden(false);
        stopFieldLoop();
    }

    async function enterFilm(origin) {
        if (waveScene.layer !== 'galaxy') return;
        waveScene.layer = 'transitioning';
        enterOrigin = origin || movieToPixel(portalMovie) || { x: window.innerWidth * 0.62, y: window.innerHeight * 0.5 };
        setTransitionOrigin(enterOrigin);
        document.documentElement.classList.add('wave-scene-busy');
        if (dom.portal) dom.portal.hidden = true;
        setHintSeeking(false);
        stopPortalTracking();
        if (ctx && ctx.setChartHidden) ctx.setChartHidden(true);
        try {
            showTransitionCanvas();
            await prepareFilmUnderMask(enterOrigin);
            await Promise.all([
                fadeScrollyOverlay(true),
                runTransition('enter', enterOrigin)
            ]);
            openFilmChrome();
            waveScene.layer = 'film';
        } catch (error) {
            closeFilmChrome();
            waveScene.layer = 'galaxy';
            fadeScrollyOverlay(false);
            if (dom.portal) dom.portal.hidden = false;
            startPortalTracking();
            syncPortalPosition();
            console.warn('enterFilm failed', error);
        } finally {
            await hideTransitionCanvas();
            clearFilmReveal();
            document.documentElement.classList.remove('wave-scene-busy');
        }
    }

    async function leaveFilm() {
        if (waveScene.layer !== 'film') return;
        waveScene.layer = 'returning';
        document.documentElement.classList.add('wave-scene-busy');
        document.documentElement.classList.remove('wave-film-open');
        setTransitionOrigin(enterOrigin);
        setFilmReveal(1, enterOrigin);
        let filmClosed = false;
        const closeFilmWhenMasked = () => {
            if (filmClosed) return;
            filmClosed = true;
            closeFilmChrome();
        };
        try {
            showTransitionCanvas();
            await runTransition('leave', enterOrigin, closeFilmWhenMasked);
            if (!filmClosed) closeFilmWhenMasked();
        } finally {
            await hideTransitionCanvas();
            document.documentElement.classList.remove('wave-scene-busy');
            waveScene.layer = 'galaxy';
            fadeScrollyOverlay(false);
            syncPortalPosition();
            if (dom.portal) {
                dom.portal.classList.add('is-returned');
                window.setTimeout(() => {
                    if (dom.portal) dom.portal.classList.remove('is-returned');
                }, 1700);
            }
        }
    }

    function bindOnce() {
        if (bound) return;
        bound = true;
        cacheDom();
        if (dom.portal) {
            dom.portal.addEventListener('mouseenter', () => setHintSeeking(true));
            dom.portal.addEventListener('mouseleave', () => setHintSeeking(false));
            dom.portal.addEventListener('focus', () => setHintSeeking(true));
            dom.portal.addEventListener('blur', () => setHintSeeking(false));
            dom.portal.addEventListener('click', event => {
                event.preventDefault();
                event.stopPropagation();
                const rect = dom.portal.getBoundingClientRect();
                enterFilm({ x: rect.left + rect.width / 2, y: rect.top + rect.height / 2 });
            });
        }
        document.addEventListener('keydown', event => {
            if (event.key !== 'Escape' || waveScene.layer !== 'film') return;
            const dialog = document.getElementById('movie-detail-dialog');
            if (dialog && dialog.open) return;
            leaveFilm();
        });
    }

    function init(nextCtx) {
        ctx = Object.assign(ctx || {}, nextCtx || {});
        bindOnce();
        cacheDom();
        if (ctx.getDialectAgg && ctx.getDialectAgg()) {
            if (dom.scroll && dom.scroll.dataset.ready === '1') refreshFilmCards();
            else ensureFilmPages();
        }
        if (ctx.getActiveSceneId && ctx.getActiveSceneId() === 'three-waves') {
            startPortalTracking();
        } else {
            syncPortalPosition();
        }
    }

    function onSceneChange(sceneId) {
        if (sceneId === 'three-waves') {
            prefetchField();
            if (waveScene.layer === 'galaxy') startPortalTracking();
        } else if (waveScene.layer === 'galaxy') {
            stopPortalTracking();
            syncPortalPosition();
        }
    }

    function onResize() {
        if (waveScene.layer === 'galaxy') syncPortalPosition();
        if (waveScene.layer === 'film') {
            rebuildField();
            layoutShuffle(true);
            updateCopy();
            updateBackgroundFocus();
        }
    }

    function handleParticleClick(movie) {
        if (!movie || !ctx || ctx.getActiveSceneId() !== 'three-waves') return false;
        if (waveScene.layer !== 'galaxy') return false;
        if (!portalMovie) portalMovie = pickPortalMovie();
        if (!portalMovie) return false;
        const same = movie.id === portalMovie.id || String(movie.movieId) === String(portalMovie.movieId);
        if (!same) return false;
        enterFilm(movieToPixel(portalMovie));
        return true;
    }

    global.WaveScene = {
        init,
        onSceneChange,
        onResize,
        handleParticleClick,
        getState: () => waveScene
    };
})(window);
