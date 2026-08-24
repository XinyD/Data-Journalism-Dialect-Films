/* 终章 · 故事宇宙（地图 + 语言星合一） */
(function (global) {
    const HINT = '拖拽缩放地图；点击外围语言星看叙事资源；点击省份或地图光点看地方电影。';

    function escapeHtml(value) {
        return String(value == null ? '' : value)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    }

    let loadPromise = null;

    const state = {
        bound: false,
        visible: false,
        ready: false,
        loading: false,
        mapApi: null,
        mapData: null,
        currentProvince: null,
        hoveredLang: null,
        selectedLang: null,
        activeTab: null,
        landIndex: new Map(),
        languages: [],
        modules: null,
        deps: null,
        observer: null,
        blendRaf: 0,
        reducedMotion: false,
        mapPanelSide: null,
    };

    let dismissLayer = null;

    function $(id) {
        return document.getElementById(id);
    }

    function ensureDismissLayer() {
        const composite = $('echo-composite-layer');
        if (!composite || dismissLayer) return;
        dismissLayer = document.createElement('div');
        dismissLayer.className = 'echo-panel-dismiss';
        dismissLayer.setAttribute('aria-hidden', 'true');
        dismissLayer.addEventListener('click', () => closeAllPanels());
        composite.appendChild(dismissLayer);
    }

    function updateDismissLayer() {
        ensureDismissLayer();
        const storyOpen = $('echo-story-panel')?.classList.contains('is-on');
        const mapOpen = !!state.currentProvince;
        const anyOpen = storyOpen || mapOpen;
        dismissLayer?.classList.toggle('is-on', anyOpen);
        dismissLayer?.setAttribute('aria-hidden', anyOpen ? 'false' : 'true');
    }

    function closeMapPanels() {
        const assetCard = $('echo-asset-card');
        assetCard?.classList.remove('is-on', 'slide-from-left', 'slide-from-right', 'is-anchor-left', 'is-anchor-right');
        $('echo-film-card')?.classList.remove('is-on', 'slide-from-left', 'slide-from-right', 'is-following');
        resetFilmCardPosition();
        state.currentProvince = null;
        state.mapPanelSide = null;
        state.mapApi?.clearHighlight();
        updateDismissLayer();
    }

    function closeStoryPanel() {
        const panel = $('echo-story-panel');
        panel?.classList.remove('is-on', 'is-anchor-left', 'is-anchor-right');
        panel?.setAttribute('aria-hidden', 'true');
        const tip = $('echo-planet-tip');
        tip?.classList.remove('is-on', 'is-positioned', 'is-hover');
        if (tip) {
            tip.style.left = '';
            tip.style.top = '';
        }
        state.hoveredLang = null;
        state.selectedLang = null;
        updateDismissLayer();
    }

    function showPlanetHover(lang, screenPos) {
        const panel = $('echo-story-panel');
        if (panel?.classList.contains('is-on')) return;
        const tip = $('echo-planet-tip');
        if (!tip || !lang) return;
        state.hoveredLang = lang.id;
        tip.innerHTML = `
            <div class="name">${escapeHtml(lang.name)}</div>
            <div class="row">${escapeHtml(countLabel(lang))}</div>`;
        tip.classList.add('is-on', 'is-hover');
        positionPlanetTip(screenPos || state.mapApi?.getLangStarScreenPos?.(lang.id));
    }

    function hidePlanetHover() {
        const panel = $('echo-story-panel');
        if (panel?.classList.contains('is-on')) return;
        const tip = $('echo-planet-tip');
        if (!tip || !tip.classList.contains('is-hover')) return;
        tip.classList.remove('is-on', 'is-hover', 'is-positioned');
        tip.style.left = '';
        tip.style.top = '';
        state.hoveredLang = null;
    }

    function refreshHoveredTip() {
        if (!state.hoveredLang) return;
        const lang = state.languages.find((l) => l.id === state.hoveredLang);
        if (!lang) return;
        const panel = $('echo-story-panel');
        if (panel?.classList.contains('is-on')) return;
        positionPlanetTip(state.mapApi?.getLangStarScreenPos?.(lang.id));
    }

    function closeAllPanels() {
        closeMapPanels();
        closeStoryPanel();
    }

    function syncEchoChrome() {
        const hint = $('echo-hint');
        if (hint) hint.textContent = HINT;
        $('echo-lang-fallback')?.classList.toggle('is-on', state.visible && state.reducedMotion);
    }

    function applyEchoEngines() {
        if (!state.visible) {
            $('echo-lang-fallback')?.classList.remove('is-on');
            state.mapApi?.stopMotion?.();
            return;
        }
        $('echo-lang-fallback')?.classList.toggle('is-on', state.reducedMotion);
        requestAnimationFrame(() => {
            state.mapApi?.resize();
            if (state.reducedMotion) {
                state.mapApi?.stopMotion?.();
            } else {
                state.mapApi?.startMotion?.();
            }
        });
    }

    function openFilmFromUniverse(film) {
        if (!state.deps || !film) return;
        const movie = state.deps.findPublicationMovie(film.id) || {
            movieId: film.id,
            title: film.title,
            year: film.year,
            rating: film.rating,
            director: film.director,
            languageGroup: film.lang,
        };
        state.deps.openMovieDetail(movie);
    }

    function countLabel(lang) {
        const n = Number(lang.n) || 0;
        if (!n) return '叙事资源待开发 · 尚无收录影片';
        if (!lang.films || !lang.films.length) return `已有电影：${n} 部 · 待开发`;
        return `已有电影约 ${n} 部`;
    }

    function ratingBadgeClass(rating) {
        if (rating == null) return '';
        if (rating >= 8) return 'rating-high';
        if (rating < 6.5) return 'rating-low';
        return '';
    }

    function positionPlanetTip(screenPos) {
        const tip = $('echo-planet-tip');
        const root = $('echo-universe');
        if (!tip || !root) return;
        if (!screenPos || screenPos.visible === false) {
            tip.classList.remove('is-positioned');
            tip.style.left = '';
            tip.style.top = '';
            return;
        }
        const rootRect = root.getBoundingClientRect();
        const x = screenPos.x - rootRect.left;
        const y = screenPos.y - rootRect.top;
        tip.style.left = `${Math.min(Math.max(x, 24), rootRect.width - 24)}px`;
        tip.style.top = `${Math.max(y - 16, 72)}px`;
        tip.classList.add('is-positioned');
    }

    function applyPanelSlide(card, side) {
        if (!card) return;
        card.classList.remove('slide-from-left', 'slide-from-right');
        if (side) card.classList.add(side);
    }

    function resetFilmCardPosition() {
        const filmCard = $('echo-film-card');
        if (!filmCard) return;
        filmCard.classList.remove('is-following');
        filmCard.style.left = '';
        filmCard.style.top = '';
        filmCard.style.removeProperty('--echo-film-transform');
    }

    function resolveMapAnchor(anchor, prov) {
        if (anchor && typeof anchor === 'object' && anchor.x != null && anchor.y != null) {
            return { x: anchor.x, y: anchor.y };
        }
        if (typeof anchor === 'number') {
            return { x: anchor, y: null };
        }
        const screen = state.mapApi?.getProvinceScreenPos?.(prov.id);
        if (screen) {
            const root = $('echo-universe')?.getBoundingClientRect();
            if (root) {
                return { x: screen.x - root.left, y: screen.y - root.top };
            }
        }
        return { x: null, y: null };
    }

    function pickOppositeSide(anchorX, viewportW) {
        if (anchorX == null) return 'right';
        return anchorX > viewportW * 0.52 ? 'left' : 'right';
    }

    function positionAssetCard(anchor, prov, { animate = true } = {}) {
        const assetCard = $('echo-asset-card');
        const panels = document.querySelector('.echo-map-panels');
        if (!assetCard || !panels) return;

        const { x: rawX } = resolveMapAnchor(anchor, prov);
        const w = panels.clientWidth || 1;
        let side = state.mapPanelSide;
        if (!side) {
            side = pickOppositeSide(rawX, w);
            if (animate) state.mapPanelSide = side;
        }

        assetCard.classList.remove('is-anchor-left', 'is-anchor-right');
        assetCard.classList.add(side === 'left' ? 'is-anchor-left' : 'is-anchor-right');
        if (animate) {
            applyPanelSlide(assetCard, side === 'left' ? 'slide-from-left' : 'slide-from-right');
        }
    }

    function positionStoryPanel(screenPos) {
        const panel = $('echo-story-panel');
        const root = $('echo-universe');
        if (!panel || !root) return;

        const rootRect = root.getBoundingClientRect();
        const rootW = rootRect.width || 1;
        let anchorX = rootW * 0.5;
        if (screenPos && screenPos.x != null) {
            anchorX = screenPos.x - rootRect.left;
        }
        const side = pickOppositeSide(anchorX, rootW);
        panel.classList.remove('is-anchor-left', 'is-anchor-right');
        panel.classList.add(side === 'left' ? 'is-anchor-left' : 'is-anchor-right');
    }

    function layoutMapPanels(anchor, prov, { animate = true } = {}) {
        positionFilmCard(anchor, prov, { animate });
        positionAssetCard(anchor, prov, { animate });
    }

    function positionFilmCard(anchor, prov, { animate = true } = {}) {
        const filmCard = $('echo-film-card');
        const panels = document.querySelector('.echo-map-panels');
        if (!filmCard || !panels) return;

        filmCard.classList.toggle('is-following', !animate);

        const { x: rawX, y: rawY } = resolveMapAnchor(anchor, prov);
        const w = panels.clientWidth || 1;
        const h = panels.clientHeight || 1;
        const cardW = Math.min(300, w * 0.42);
        let x = rawX != null ? rawX : w * 0.38;
        let y = rawY != null ? rawY : h * 0.52;

        x = Math.min(Math.max(x, cardW * 0.5 + 10), w - cardW * 0.5 - 10);
        y = Math.min(Math.max(y, 28), h - 20);

        const maxCardH = Math.min(h * 0.46, 380);
        let transform = 'translate(-50%, calc(-100% - 14px))';
        if (y - maxCardH < 36) {
            transform = 'translate(-50%, 14px)';
        }

        filmCard.style.left = `${x}px`;
        filmCard.style.top = `${y}px`;
        filmCard.style.setProperty('--echo-film-transform', transform);
    }

    function refreshMapPanelPositions() {
        if (!state.currentProvince) return;
        layoutMapPanels(null, state.currentProvince, { animate: false });
    }

    function showPlanet(lang, helpers, screenPos) {
        const lands = helpers.findLandsForLanguage(lang, state.landIndex);
        const tipPos = screenPos || state.mapApi?.getLangStarScreenPos?.(lang.id);
        positionStoryPanel(tipPos);
        const tip = $('echo-planet-tip');
        if (tip) {
            tip.innerHTML = `
                <div class="name">${escapeHtml(lang.name)}</div>
                <div class="row">${escapeHtml(countLabel(lang))}</div>
                <div class="row">代表题材：${escapeHtml((lang.themes || []).join(' / '))}</div>
                <div class="row">还有：民俗 · 历史 · 人物故事等待挖掘</div>
                <div class="hint">${lang.films && lang.films.length ? '点击地图上的省份光点可看代表电影' : '该语言的故事资源仍待开发'}</div>`;
            tip.classList.add('is-on');
            tip.classList.remove('is-hover');
            positionPlanetTip(tipPos);
        }
        const identity = [lang.academicName, lang.family].filter(Boolean).join(' · ');
        const also = (lang.aliases || []).filter(Boolean).join('、');
        const body = $('echo-story-panel-body');
        if (body) {
            body.innerHTML = `
                <h3>${escapeHtml(lang.name)}</h3>
                ${identity ? `<p class="lang-identity">${escapeHtml(identity)}</p>` : ''}
                ${also ? `<p class="lang-aliases">也称 ${escapeHtml(also)}</p>` : ''}
                <p class="sub">语言是入口。真正可开采的，是它连接的生活方式。</p>
                <div class="tree-branch"><div class="label">语言</div><ul><li>${escapeHtml(lang.language || lang.name)}</li></ul></div>
                <div class="tree-branch"><div class="label">民俗</div><ul>${(lang.folk || []).map((x) => `<li>${escapeHtml(x)}</li>`).join('')}</ul></div>
                <div class="tree-branch"><div class="label">历史</div><ul>${(lang.history || []).map((x) => `<li>${escapeHtml(x)}</li>`).join('')}</ul></div>
                <div class="tree-branch"><div class="label">可讲故事</div><p class="stories">${escapeHtml(lang.stories || '')}</p></div>
                ${helpers.landLinkMarkup(lands)}`;
        }
        const panel = $('echo-story-panel');
        panel?.classList.add('is-on');
        panel?.setAttribute('aria-hidden', 'false');
        state.hoveredLang = null;
        state.selectedLang = lang.id;
        updateDismissLayer();
    }

    function goToLand(provinceId) {
        if (!state.mapApi?.getProvince(provinceId)) return;
        closeStoryPanel();
        closeMapPanels();
        state.mapApi.flyToProvince(provinceId);
    }

    function showProvince(prov, anchor) {
        closeStoryPanel();
        state.currentProvince = prov;
        state.mapPanelSide = null;
        state.activeTab = null;
        const assetCard = $('echo-asset-card');
        const filmCard = $('echo-film-card');
        layoutMapPanels(anchor, prov);
        assetCard?.classList.add('is-on');
        filmCard?.classList.add('is-on');
        $('echo-asset-title').textContent = `${prov.name} · 故事资源`;
        $('echo-asset-intro').textContent = prov.intro || '';
        $('echo-film-title').textContent = `${prov.name} · 已有电影`;
        const filmCount = (prov.films || []).length;
        $('echo-film-count').textContent = filmCount
            ? `共 ${filmCount} 部代表影片`
            : '暂无收录影片';
        renderAssetPanel();

        const chips = $('echo-film-chips');
        if (chips) {
            chips.innerHTML = (prov.themes || [])
                .map((t) => `<span class="echo-chip">${escapeHtml(t)}</span>`).join('');
        }

        const list = $('echo-film-list');
        if (list) {
            if (prov.films && prov.films.length) {
                list.innerHTML = prov.films.map((f) => {
                    const badgeClass = ratingBadgeClass(f.rating);
                    return `
                    <button type="button" class="echo-film-card" data-id="${escapeHtml(f.id)}">
                        <span class="title">《${escapeHtml(f.title)}》</span>
                        <span class="badge ${badgeClass}">${f.rating != null ? f.rating.toFixed(1) : '--'}</span>
                        <span class="sub">${escapeHtml(f.director || '未知导演')} · ${escapeHtml(f.year || '—')} · ${escapeHtml(f.lang || '方言')}</span>
                    </button>`;
                }).join('');
                list.querySelectorAll('.echo-film-card').forEach((btn) => {
                    btn.addEventListener('click', (e) => {
                        e.stopPropagation();
                        const film = prov.films.find((f) => f.id === btn.dataset.id);
                        if (film) openFilmFromUniverse(film);
                    });
                });
            } else {
                list.innerHTML = '<p class="echo-empty-state">待开发——这片土地的方言电影样本尚少，但叙事资源已相当丰富。</p>';
            }
        }

        const hooksBlock = $('echo-story-hooks-block');
        const hooks = prov.storyHooks || [];
        if (hooksBlock) {
            if (hooks.length) {
                hooksBlock.hidden = false;
                $('echo-story-hooks').innerHTML = hooks.map((h) => `<li>${escapeHtml(h)}</li>`).join('');
            } else {
                hooksBlock.hidden = true;
            }
        }

        const pending = prov.pending || [];
        $('echo-film-pending').textContent = pending.length
            ? pending.join('；')
            : (filmCount ? '还有更多地方故事等待挖掘。' : '');
        updateDismissLayer();
    }

    function renderAssetPanel() {
        if (!state.currentProvince || !state.mapHelpers) return;
        const { tabs, key, items } = state.mapHelpers.renderAssetTabs(
            state.currentProvince,
            state.activeTab,
            state.languages,
        );
        state.activeTab = key;
        const tabRow = $('echo-asset-tabs');
        if (!tabRow) return;
        tabRow.innerHTML = tabs.map((t) => `
            <button type="button" class="${t.key === key ? 'is-on' : ''}" data-key="${escapeHtml(t.key)}">${escapeHtml(t.label)}</button>`).join('');
        tabRow.querySelectorAll('button').forEach((btn) => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                state.activeTab = btn.dataset.key;
                renderAssetPanel();
            });
        });
        const listEl = $('echo-asset-list');
        if (!listEl) return;
        if (!items || !items.length) {
            listEl.innerHTML = '<li class="echo-empty-state">待补充</li>';
            return;
        }
        listEl.innerHTML = items.map((x) => {
            const title = typeof x === 'string' ? x : x.title;
            const desc = typeof x === 'string' ? '' : (x.desc || '');
            const langName = typeof x === 'object' ? x.langName : '';
            const langAttr = langName ? ` data-lang-name="${escapeHtml(langName)}"` : '';
            return `<li class="echo-asset-item${langName ? ' is-lang' : ''}"${langAttr}><strong>${escapeHtml(title)}</strong>${desc ? `<span>${escapeHtml(desc)}</span>` : ''}</li>`;
        }).join('');
        listEl.querySelectorAll('[data-lang-name]').forEach((el) => {
            el.addEventListener('click', (e) => {
                e.stopPropagation();
                const lang = (state.languages || []).find((item) => item.name === el.dataset.langName);
                if (lang && state.echoHelpers) showPlanet(lang, state.echoHelpers);
            });
        });
    }

    function buildFallback(langs) {
        const fallback = $('echo-lang-fallback');
        if (!fallback) return;
        fallback.innerHTML = langs.map((lang) => `
            <button type="button" data-id="${escapeHtml(lang.id)}">
                <span>${escapeHtml(lang.name)}</span>
                <small>${escapeHtml(countLabel(lang))}</small>
            </button>`).join('');
        fallback.querySelectorAll('button').forEach((btn) => {
            btn.addEventListener('click', () => {
                const lang = langs.find((l) => l.id === btn.dataset.id);
                if (lang && state.echoHelpers) showPlanet(lang, state.echoHelpers);
            });
        });
    }

    function bindUi() {
        ensureDismissLayer();
        $('echo-panel-close')?.addEventListener('click', (e) => {
            e.stopPropagation();
            closeStoryPanel();
        });
        $('echo-story-panel')?.addEventListener('click', (e) => e.stopPropagation());
        $('echo-story-panel-body')?.addEventListener('click', (e) => {
            const btn = e.target.closest('.land-link');
            if (!btn) return;
            e.stopPropagation();
            goToLand(btn.dataset.provinceId);
        });
        ['echo-asset-card', 'echo-film-card'].forEach((id) => {
            const card = $(id);
            if (!card) return;
            card.addEventListener('click', (e) => e.stopPropagation());
            card.querySelectorAll('[data-close]').forEach((btn) => {
                btn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    closeMapPanels();
                });
            });
        });
        document.addEventListener('keydown', (e) => {
            if (!state.visible) return;
            if (e.key !== 'Escape') return;
            closeAllPanels();
        });
        window.addEventListener('resize', () => {
            if (!state.visible) return;
            state.mapApi?.resize();
            refreshMapPanelPositions();
            refreshHoveredTip();
        });
    }

    async function loadModules() {
        if (state.modules) return state.modules;
        const manifestRes = await fetch('./build/manifest.json');
        if (!manifestRes.ok) throw new Error(`manifest.json ${manifestRes.status}`);
        const manifest = await manifestRes.json();
        if (!manifest.echoChunk) throw new Error('manifest missing echoChunk — run npm run build');
        const url = new URL(`./${manifest.echoChunk}`, document.baseURI).href;
        state.modules = await import(url);
        return state.modules;
    }

    async function doEnsureReady() {
        const mapWrap = $('echo-map-wrap');
        if (!mapWrap) return false;

        state.loading = true;
        try {
            const {
                loadMapData,
                createChinaMap,
                renderAssetTabs,
                buildLangLandIndex,
                findLandsForLanguage,
                landLinkMarkup,
            } = await loadModules();

            state.mapHelpers = { renderAssetTabs };
            state.echoHelpers = { findLandsForLanguage, landLinkMarkup };

            state.mapData = await loadMapData();
            state.landIndex = buildLangLandIndex(state.mapData.provinces);
            state.languages = state.mapData.languages || [];

            state.mapApi = createChinaMap(mapWrap, state.mapData, {
                onProvince: (prov, _geoName, params) => {
                    const evt = params?.event?.event || params?.event;
                    let anchor = null;
                    if (evt) {
                        const root = $('echo-universe')?.getBoundingClientRect();
                        anchor = root
                            ? { x: evt.clientX - root.left, y: evt.clientY - root.top }
                            : { x: evt.offsetX, y: evt.offsetY };
                    }
                    showProvince(prov, anchor);
                },
                onFilm: (film) => openFilmFromUniverse(film),
                onLangStar(lang, params) {
                    const evt = params?.event?.event || params?.event;
                    let screenPos = null;
                    if (evt) {
                        screenPos = { x: evt.clientX, y: evt.clientY, visible: true };
                    }
                    showPlanet(lang, state.echoHelpers, screenPos);
                },
                onLangStarHover(lang, screenPos) {
                    showPlanetHover(lang, screenPos);
                },
                onLangStarLeave() {
                    hidePlanetHover();
                },
                onGeoRoam() {
                    refreshMapPanelPositions();
                },
                onMapBlankClick() {
                    if (!state.currentProvince
                        && !$('echo-story-panel')?.classList.contains('is-on')) {
                        return;
                    }
                    closeAllPanels();
                },
            }, {
                landIndex: state.landIndex,
                reducedMotion: state.reducedMotion,
                overlayAnchor: $('echo-composite-layer'),
            });

            buildFallback(state.languages);

            state.ready = true;
            if (state.visible) {
                syncEchoChrome();
                applyEchoEngines();
            }
            return true;
        } catch (err) {
            console.error('EchoUniverseScene init failed:', err);
            if (mapWrap) {
                const detail = err && err.message ? `（${err.message}）` : '';
                mapWrap.innerHTML = `<p style="padding:2rem;color:#d4a574;line-height:1.7;">故事宇宙数据加载失败${detail}。请确认已执行 <code style="color:#E8E4DC;">npm run build</code>，并通过 <code style="color:#E8E4DC;">python serve.py</code> 打开 <code style="color:#E8E4DC;">/frontend/index.html</code>。</p>`;
            }
            return false;
        } finally {
            state.loading = false;
        }
    }

    async function ensureReady() {
        if (state.ready) return true;
        if (!loadPromise) loadPromise = doEnsureReady();
        return loadPromise;
    }

    function smoothstep(t) {
        const x = Math.min(1, Math.max(0, t));
        return x * x * (3 - 2 * x);
    }

    function clamp(value, min, max) {
        return Math.min(max, Math.max(min, value));
    }

    function updateBlend() {
        const step = document.getElementById('step-12');
        const root = $('echo-universe');
        if (!step || !root) return;

        const vh = window.innerHeight || 1;
        const stepRect = step.getBoundingClientRect();
        const uniRect = root.getBoundingClientRect();

        const edgeIn = smoothstep(clamp((vh - uniRect.top) / (vh * 0.3), 0, 1));
        const exitUp = smoothstep(clamp((vh * 0.22 - stepRect.bottom) / (vh * 0.22), 0, 1));
        const exitDown = smoothstep(clamp((stepRect.top - vh * 0.78) / (vh * 0.22), 0, 1));
        const edgeOut = (1 - exitUp) * (1 - exitDown);

        const inFinaleZone =
            uniRect.top < vh &&
            uniRect.bottom > 0 &&
            stepRect.top < vh * 0.88 &&
            stepRect.bottom > vh * 0.12;

        let reveal = 0;
        if (inFinaleZone) {
            reveal = edgeIn > 0.02 ? edgeOut : edgeIn * edgeOut;
        }

        const headOpacity = smoothstep(clamp(reveal, 0, 1));
        const layerOpacity = smoothstep(clamp((reveal - 0.15) / 0.65, 0, 1));

        const outroEl = step.querySelector('.finale-outro');
        const outroRect = outroEl?.getBoundingClientRect();
        const outroNear = outroRect
            ? outroRect.top < vh * 0.72 && outroRect.top > -vh * 0.1
            : false;
        const outroActive = outroNear && inFinaleZone;

        root.style.setProperty('--echo-head-opacity', String(headOpacity));
        root.style.setProperty('--echo-layer-opacity', String(layerOpacity));
        root.toggleAttribute('data-layer-revealed', layerOpacity >= 0.08);
        root.toggleAttribute('data-outro-near', outroActive);
        if (headOpacity >= 0.85) {
            root.setAttribute('data-head-entered', '');
        } else if (reveal < 0.2) {
            root.removeAttribute('data-head-entered');
        }

        const pinStage = inFinaleZone && layerOpacity >= 0.5 && !outroNear;
        if (pinStage) {
            root.setAttribute('data-stage-pinned', '');
        } else {
            root.removeAttribute('data-stage-pinned');
        }

        const immersive = inFinaleZone && layerOpacity > 0.25;
        document.documentElement.toggleAttribute('data-echo-immersive', immersive);
        document.documentElement.toggleAttribute('data-echo-outro', outroActive);

        if (state.mapApi && (pinStage || layerOpacity >= 0.08)) {
            requestAnimationFrame(() => state.mapApi.resize());
        }
    }

    function scheduleBlendUpdate() {
        if (state.blendRaf) return;
        state.blendRaf = requestAnimationFrame(() => {
            state.blendRaf = 0;
            updateBlend();
        });
    }

    function handlePreload(entry) {
        const ratio = entry.isIntersecting ? entry.intersectionRatio : 0;
        if (!state.ready && ratio >= 0.12) {
            ensureReady();
        }
    }

    global.EchoUniverseScene = {
        init(deps) {
            if (state.bound) return;
            state.deps = deps || {};
            state.reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
            bindUi();
            syncEchoChrome();

            const root = $('echo-universe');
            if (!root || state.observer) return;
            state.observer = new IntersectionObserver((entries) => {
                const entry = entries[0];
                if (!entry) return;
                handlePreload(entry);
            }, { threshold: [0, 0.12, 0.25] });
            state.observer.observe(root);
            window.addEventListener('scroll', scheduleBlendUpdate, { passive: true });
            window.addEventListener('resize', scheduleBlendUpdate);
            updateBlend();
            state.bound = true;
        },

        async onVisible(isVisible) {
            if (isVisible) {
                state.visible = true;
                const ok = await ensureReady();
                if (ok) {
                    syncEchoChrome();
                    applyEchoEngines();
                }
                updateBlend();
            } else {
                state.visible = false;
                closeAllPanels();
                state.mapApi?.stopMotion?.();
                $('echo-lang-fallback')?.classList.remove('is-on');
                $('echo-universe')?.removeAttribute('data-head-entered');
                document.documentElement.removeAttribute('data-echo-immersive');
                document.documentElement.removeAttribute('data-echo-outro');
                syncEchoChrome();
                updateBlend();
            }
        },
    };
})(window);
