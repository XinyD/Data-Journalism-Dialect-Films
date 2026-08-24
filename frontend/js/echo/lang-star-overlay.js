const DEFAULT_ZOOM = 1.28;
const MIN_ZOOM = 0.7;
const MAX_ZOOM = 6;
const MARGIN_PX = 28;
const OFFSCREEN_PAD = 40;

function clamp(value, min, max) {
    return Math.min(max, Math.max(min, value));
}

function lerp(a, b, t) {
    return a + (b - a) * t;
}

function perimeterOnEllipse(mapRect, angle, marginPx) {
    const hw = mapRect.width / 2 + marginPx;
    const hh = mapRect.height / 2 + marginPx;
    return {
        x: mapRect.cx + Math.cos(angle) * hw,
        y: mapRect.cy + Math.sin(angle) * hh,
    };
}

function computeStarPosition(marker, mapRect, zoom, vw, vh) {
    const perim = perimeterOnEllipse(mapRect, marker.angle, MARGIN_PX);
    const fill = { x: marker.fillX * vw, y: marker.fillY * vh };

    const shrinkT = clamp((DEFAULT_ZOOM - zoom) / (DEFAULT_ZOOM - MIN_ZOOM), 0, 1);
    const expandT = clamp((zoom - DEFAULT_ZOOM) / (MAX_ZOOM - DEFAULT_ZOOM), 0, 1);
    const attach = marker.followFactor * (1 - shrinkT * (1 - marker.followFactor));
    const attachWeight = clamp(attach + expandT * (1 - attach), 0, 1);

    const x = lerp(fill.x, perim.x, attachWeight);
    const y = lerp(fill.y, perim.y, attachWeight);

    let edgeFade = 1;
    if (x < -OFFSCREEN_PAD || x > vw + OFFSCREEN_PAD || y < -OFFSCREEN_PAD || y > vh + OFFSCREEN_PAD) {
        edgeFade = 0;
    } else if (x < 0 || x > vw || y < 0 || y > vh) {
        const dx = x < 0 ? -x : x > vw ? x - vw : 0;
        const dy = y < 0 ? -y : y > vh ? y - vh : 0;
        edgeFade = clamp(1 - Math.max(dx, dy) / OFFSCREEN_PAD, 0, 1);
    }

    return { x, y, edgeFade };
}

/**
 * Screen-space language star overlay — positions relative to map bbox, syncs on georoam.
 */
export function createLangStarOverlay(anchorEl, markers, hooks, { reducedMotion = false } = {}) {
    const layer = document.createElement('div');
    layer.className = 'echo-lang-stars-layer';
    layer.setAttribute('aria-hidden', 'true');
    if (reducedMotion) layer.hidden = true;
    anchorEl.appendChild(layer);

    const entries = markers.map((marker) => {
        const el = document.createElement('button');
        el.type = 'button';
        el.className = 'echo-lang-star';
        el.setAttribute('aria-label', marker.lang.name || marker.lang.id);
        el.style.width = `${marker.symbolSize}px`;
        el.style.height = `${marker.symbolSize}px`;
        el.style.backgroundImage = `url(${marker.symbolUrl})`;
        el.dataset.langId = marker.langId;
        el.style.setProperty('--star-bright', String(marker.brightMul));

        el.addEventListener('click', (e) => {
            e.stopPropagation();
            hooks.onLangStar?.(marker.lang, { event: e });
        });
        el.addEventListener('mouseenter', () => {
            hooks.onLangStarHover?.(marker.lang, screenPosFromEl(el));
        });
        el.addEventListener('mouseleave', () => {
            hooks.onLangStarLeave?.();
        });

        layer.appendChild(el);
        return { el, marker };
    });

    let raf = 0;
    let active = false;
    let mapRect = null;
    let zoom = DEFAULT_ZOOM;

    function getViewportSize() {
        return {
            vw: anchorEl.clientWidth || layer.clientWidth,
            vh: anchorEl.clientHeight || layer.clientHeight,
        };
    }

    function screenPosFromEl(el) {
        const r = el.getBoundingClientRect();
        return {
            x: r.left + r.width / 2,
            y: r.top + r.height / 2,
            visible: r.width > 0 && r.height > 0 && (el.style.opacity === '' || parseFloat(el.style.opacity) > 0),
        };
    }

    function applyVisual(entry, pos, { driftX = 0, driftY = 0, scale = 1, opacity = 1, edgeFade = 1, brightness = 1 } = {}) {
        const { el, marker } = entry;
        el.style.left = `${pos.x}px`;
        el.style.top = `${pos.y}px`;
        el.style.opacity = String(opacity * edgeFade);
        el.style.pointerEvents = edgeFade < 0.05 ? 'none' : 'auto';
        el.style.transform = `translate(calc(-50% + ${driftX}px), calc(-50% + ${driftY}px)) scale(${scale})`;
        el.style.filter = `brightness(${brightness * (0.75 + marker.brightMul * 0.5)})`;
    }

    function layoutAll(t = 0, animate = false) {
        if (!mapRect) return;
        const { vw, vh } = getViewportSize();
        if (!vw || !vh) return;

        entries.forEach((entry) => {
            const { marker } = entry;
            const pos = computeStarPosition(marker, mapRect, zoom, vw, vh);

            if (!animate) {
                applyVisual(entry, pos, {
                    opacity: marker.brightMul,
                    edgeFade: pos.edgeFade,
                });
                return;
            }

            const phase = marker.breathePhase;
            const hopY = -3.5 * (0.5 + 0.5 * Math.sin(t * 0.0022 + phase));
            const scale = 0.92 + 0.14 * (0.5 + 0.5 * Math.sin(t * 0.0022 + phase + Math.PI / 2));
            const breath = 0.72 + 0.28 * Math.sin(t * 0.0012 + phase);
            const brightness = 0.85 + 0.15 * (0.5 + 0.5 * Math.sin(t * 0.0018 + phase * 1.1));
            applyVisual(entry, pos, {
                driftY: hopY,
                scale,
                opacity: marker.brightMul * breath,
                brightness,
                edgeFade: pos.edgeFade,
            });
        });
    }

    function syncToMap(nextMapRect, nextZoom) {
        mapRect = nextMapRect;
        zoom = nextZoom ?? DEFAULT_ZOOM;
        layoutAll(0, active);
    }

    function tick(t) {
        if (!active) return;
        layoutAll(t, true);
        raf = requestAnimationFrame(tick);
    }

    function start() {
        if (reducedMotion || active) return;
        layer.hidden = false;
        active = true;
        cancelAnimationFrame(raf);
        raf = requestAnimationFrame(tick);
    }

    function stop() {
        active = false;
        cancelAnimationFrame(raf);
        raf = 0;
        layoutAll(0, false);
        if (reducedMotion) layer.hidden = true;
    }

    function dispose() {
        stop();
        layer.remove();
    }

    function resize() {
        layoutAll(0, active);
    }

    function getScreenPos(langId) {
        const entry = entries.find((e) => e.marker.langId === langId);
        if (!entry || entry.el.style.pointerEvents === 'none') return null;
        return screenPosFromEl(entry.el);
    }

    return { start, stop, dispose, resize, getScreenPos, syncToMap };
}
