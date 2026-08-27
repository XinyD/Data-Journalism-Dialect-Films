/**
 * Fullscreen movie-particle layer for the cover/prologue.
 * ECharts scatter creates one graphic per point; this draws into one canvas.
 */

const FALLBACK_RGBA = [220, 220, 226, 1];

// Hover cards must not pop over the prose while reading: they only appear after
// the pointer rests on one particle for TOOLTIP_DWELL_MS, and any scroll cancels.
const TOOLTIP_DWELL_MS = 1000;
const TOOLTIP_MOVE_TOLERANCE_PX = 6;

export function dwellAnchorUpdate(anchor, index, clientX, clientY, tolerancePx) {
    if (anchor && anchor.index === index) {
        const dx = clientX - anchor.x;
        const dy = clientY - anchor.y;
        if (dx * dx + dy * dy <= tolerancePx * tolerancePx) return anchor;
    }
    return { index, x: clientX, y: clientY };
}

export function parseRgba(color) {
    if (typeof color !== 'string' || !color) return FALLBACK_RGBA.slice();
    const s = color.trim();
    if (s.charCodeAt(0) === 35) {
        const hex = s.slice(1);
        if (hex.length === 3) {
            const r = parseInt(hex[0] + hex[0], 16);
            const g = parseInt(hex[1] + hex[1], 16);
            const b = parseInt(hex[2] + hex[2], 16);
            return [r, g, b, 1];
        }
        if (hex.length >= 6) {
            return [
                parseInt(hex.slice(0, 2), 16),
                parseInt(hex.slice(2, 4), 16),
                parseInt(hex.slice(4, 6), 16),
                1
            ];
        }
        return FALLBACK_RGBA.slice();
    }
    const start = s.indexOf('(');
    const end = s.lastIndexOf(')');
    if (start < 0 || end < 0) return FALLBACK_RGBA.slice();
    const parts = s.slice(start + 1, end).split(',');
    const r = Number(parts[0]);
    const g = Number(parts[1]);
    const b = Number(parts[2]);
    const a = parts.length > 3 ? Number(parts[3]) : 1;
    if (![r, g, b, a].every(Number.isFinite)) return FALLBACK_RGBA.slice();
    return [r, g, b, a];
}

export function dataToPixel(x, y, xMax, width, height) {
    const maxX = Math.max(1e-6, Number(xMax) || 1);
    return [
        (Number(x) / maxX) * width,
        (1 - Number(y) / 100) * height
    ];
}

export function nearestIndex(px, py, xs, ys, count, radiusPx) {
    if (!count) return -1;
    let best = -1;
    let bestDist = radiusPx * radiusPx;
    for (let i = 0; i < count; i += 1) {
        const dx = xs[i] - px;
        const dy = ys[i] - py;
        const dist = dx * dx + dy * dy;
        if (dist <= bestDist) {
            bestDist = dist;
            best = i;
        }
    }
    return best;
}

function grow(typed, ctor, cap) {
    const next = new ctor(cap);
    next.set(typed);
    return next;
}

export function createUniverseLayer({ canvas, onPick, formatTooltip }) {
    const tooltip = document.createElement('div');
    tooltip.className = 'universe-tooltip';
    tooltip.hidden = true;
    tooltip.setAttribute('role', 'tooltip');
    document.body.appendChild(tooltip);

    let ctx = canvas.getContext('2d', { alpha: true });
    let visible = true;
    let count = 0;
    let xMax = 100;
    let cssW = 1;
    let cssH = 1;
    let cap = 0;
    let xs = new Float32Array(0);
    let ys = new Float32Array(0);
    let sizes = new Float32Array(0);
    let rCh = new Float32Array(0);
    let gCh = new Float32Array(0);
    let bCh = new Float32Array(0);
    let aCh = new Float32Array(0);
    let glow = new Uint8Array(0);
    let ids = new Int32Array(0);
    let hoverIndex = -1;
    let tooltipIndex = -1;
    let dwellTimer = 0;
    let dwellAnchor = null;

    function ensure(n) {
        if (cap >= n) return;
        cap = Math.max(n, Math.ceil((cap || 2048) * 1.5));
        xs = grow(xs, Float32Array, cap);
        ys = grow(ys, Float32Array, cap);
        sizes = grow(sizes, Float32Array, cap);
        rCh = grow(rCh, Float32Array, cap);
        gCh = grow(gCh, Float32Array, cap);
        bCh = grow(bCh, Float32Array, cap);
        aCh = grow(aCh, Float32Array, cap);
        glow = grow(glow, Uint8Array, cap);
        ids = grow(ids, Int32Array, cap);
    }

    function resize() {
        const dpr = Math.min(window.devicePixelRatio || 1, 2);
        cssW = Math.max(1, canvas.clientWidth || window.innerWidth);
        cssH = Math.max(1, canvas.clientHeight || window.innerHeight);
        canvas.width = Math.max(1, Math.floor(cssW * dpr));
        canvas.height = Math.max(1, Math.floor(cssH * dpr));
        ctx = canvas.getContext('2d', { alpha: true });
        if (ctx) ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
        if (count) draw();
    }

    function hideTooltip() {
        tooltip.hidden = true;
        tooltip.innerHTML = '';
        tooltipIndex = -1;
    }

    function showTooltip(index, clientX, clientY) {
        if (index < 0 || !formatTooltip) {
            hideTooltip();
            return;
        }
        const html = formatTooltip(ids[index]);
        if (!html) {
            hideTooltip();
            return;
        }
        tooltip.innerHTML = html;
        tooltip.hidden = false;
        tooltipIndex = index;
        const pad = 14;
        const tw = tooltip.offsetWidth || 220;
        const th = tooltip.offsetHeight || 72;
        let left = clientX + pad;
        let top = clientY + pad;
        if (left + tw > window.innerWidth - 8) left = clientX - tw - pad;
        if (top + th > window.innerHeight - 8) top = clientY - th - pad;
        tooltip.style.left = `${Math.max(8, left)}px`;
        tooltip.style.top = `${Math.max(8, top)}px`;
    }

    function draw() {
        if (!ctx || !visible) return;
        ctx.clearRect(0, 0, cssW, cssH);
        let lastRgb = -1;
        let lastA = -1;
        for (let i = 0; i < count; i += 1) {
            const size = sizes[i];
            if (size <= 0 || aCh[i] <= 0.01) continue;
            const x = xs[i];
            const y = ys[i];
            const ri = rCh[i] | 0;
            const gi = gCh[i] | 0;
            const bi = bCh[i] | 0;
            const rgb = (ri << 16) | (gi << 8) | bi;
            if (glow[i]) {
                ctx.globalAlpha = Math.min(0.28, aCh[i] * 0.45);
                ctx.fillStyle = `rgb(${ri},${gi},${bi})`;
                const glowSize = size * 2.3;
                ctx.fillRect(x - glowSize / 2, y - glowSize / 2, glowSize, glowSize);
                lastRgb = rgb;
                lastA = -1;
            }
            if (rgb !== lastRgb) {
                ctx.fillStyle = `rgb(${ri},${gi},${bi})`;
                lastRgb = rgb;
            }
            const aq = ((aCh[i] * 32) | 0) / 32;
            if (aq !== lastA) {
                ctx.globalAlpha = aq;
                lastA = aq;
            }
            ctx.fillRect(x - size / 2, y - size / 2, size, size);
        }
        ctx.globalAlpha = 1;
        if (hoverIndex >= 0 && hoverIndex < count) {
            const size = Math.max(4, sizes[hoverIndex] + 2);
            ctx.strokeStyle = 'rgba(255,255,255,0.85)';
            ctx.lineWidth = 1;
            ctx.strokeRect(
                xs[hoverIndex] - size / 2,
                ys[hoverIndex] - size / 2,
                size,
                size
            );
        }
    }

    function hitIndex(offsetX, offsetY, radiusPx = 18) {
        return nearestIndex(offsetX, offsetY, xs, ys, count, radiusPx);
    }

    function cancelDwell() {
        if (dwellTimer) {
            window.clearTimeout(dwellTimer);
            dwellTimer = 0;
        }
    }

    function cancelDwellAndHide() {
        cancelDwell();
        dwellAnchor = null;
        hideTooltip();
    }

    function onWindowScroll() {
        if (dwellTimer || !tooltip.hidden) cancelDwellAndHide();
    }

    // 立即路径：点击与程序化高亮（随机打捞/片单）
    function setHover(index, clientX, clientY) {
        cancelDwell();
        dwellAnchor = null;
        if (index === hoverIndex) {
            if (index >= 0) showTooltip(index, clientX, clientY);
            return;
        }
        hoverIndex = index;
        draw();
        if (index >= 0) showTooltip(index, clientX, clientY);
        else hideTooltip();
    }

    function onPointerMove(event) {
        if (!visible) return;
        const rect = canvas.getBoundingClientRect();
        const index = hitIndex(event.clientX - rect.left, event.clientY - rect.top, 16);
        if (index !== hoverIndex) {
            hoverIndex = index;
            draw();
        }
        if (index < 0) {
            cancelDwellAndHide();
            return;
        }
        if (tooltipIndex === index) {
            showTooltip(index, event.clientX, event.clientY);
            return;
        }
        hideTooltip();
        const nextAnchor = dwellAnchorUpdate(dwellAnchor, index, event.clientX, event.clientY, TOOLTIP_MOVE_TOLERANCE_PX);
        const anchorMoved = nextAnchor !== dwellAnchor;
        dwellAnchor = nextAnchor;
        if (anchorMoved) {
            cancelDwell();
            dwellTimer = window.setTimeout(() => {
                dwellTimer = 0;
                if (visible && hoverIndex === index && dwellAnchor && dwellAnchor.index === index) {
                    showTooltip(index, dwellAnchor.x, dwellAnchor.y);
                }
            }, TOOLTIP_DWELL_MS);
        }
    }

    function onPointerLeave() {
        hoverIndex = -1;
        cancelDwellAndHide();
        draw();
    }

    function onClick(event) {
        if (!visible) return;
        const rect = canvas.getBoundingClientRect();
        const index = hitIndex(event.clientX - rect.left, event.clientY - rect.top, 18);
        if (index < 0) return;
        setHover(index, event.clientX, event.clientY);
        if (typeof onPick === 'function') onPick(ids[index]);
    }

    canvas.addEventListener('pointermove', onPointerMove, { passive: true });
    canvas.addEventListener('pointerleave', onPointerLeave);
    canvas.addEventListener('click', onClick);
    window.addEventListener('scroll', onWindowScroll, { passive: true });

    resize();

    return {
        begin(n, nextXMax) {
            ensure(n);
            count = 0;
            xMax = nextXMax;
        },
        push(x, y, size, color, isGlow, movieId) {
            const i = count;
            count += 1;
            ensure(count);
            const [px, py] = dataToPixel(x, y, xMax, cssW, cssH);
            const rgba = Array.isArray(color) ? color : parseRgba(color);
            xs[i] = px;
            ys[i] = py;
            sizes[i] = size;
            rCh[i] = rgba[0];
            gCh[i] = rgba[1];
            bCh[i] = rgba[2];
            aCh[i] = rgba[3];
            glow[i] = isGlow ? 1 : 0;
            ids[i] = movieId;
        },
        pushPixelRGBA(px, py, size, r, g, b, a, isGlow, movieId) {
            const i = count;
            count += 1;
            ensure(count);
            xs[i] = px;
            ys[i] = py;
            sizes[i] = size;
            rCh[i] = r;
            gCh[i] = g;
            bCh[i] = b;
            aCh[i] = a;
            glow[i] = isGlow ? 1 : 0;
            ids[i] = movieId;
        },
        pushPixel(px, py, size, color, isGlow, movieId) {
            const i = count;
            count += 1;
            ensure(count);
            const rgba = Array.isArray(color) ? color : parseRgba(color);
            xs[i] = px;
            ys[i] = py;
            sizes[i] = size;
            rCh[i] = rgba[0];
            gCh[i] = rgba[1];
            bCh[i] = rgba[2];
            aCh[i] = rgba[3];
            glow[i] = isGlow ? 1 : 0;
            ids[i] = movieId;
        },
        snapshot() {
            return {
                n: count,
                xs: xs.slice(0, count),
                ys: ys.slice(0, count),
                sizes: sizes.slice(0, count),
                rCh: rCh.slice(0, count),
                gCh: gCh.slice(0, count),
                bCh: bCh.slice(0, count),
                aCh: aCh.slice(0, count),
                glow: glow.slice(0, count),
                ids: ids.slice(0, count)
            };
        },
        draw,
        resize,
        hitTest(offsetX, offsetY, radiusPx) {
            const index = hitIndex(offsetX, offsetY, radiusPx);
            return index < 0 ? null : ids[index];
        },
        highlight(movieId, clientX, clientY) {
            let index = -1;
            for (let i = 0; i < count; i += 1) {
                if (ids[i] === movieId) {
                    index = i;
                    break;
                }
            }
            const x = index >= 0 ? xs[index] : cssW / 2;
            const y = index >= 0 ? ys[index] : cssH / 2;
            const rect = canvas.getBoundingClientRect();
            setHover(
                index,
                clientX == null ? rect.left + x : clientX,
                clientY == null ? rect.top + y : clientY
            );
        },
        setVisible(next) {
            visible = Boolean(next);
            canvas.classList.toggle('is-hidden', !visible);
            canvas.setAttribute('aria-hidden', visible ? 'false' : 'true');
            if (!visible) {
                cancelDwellAndHide();
                hoverIndex = -1;
            }
        },
        isVisible() {
            return visible;
        },
        cssSize() {
            return { width: cssW, height: cssH };
        },
        count() {
            return count;
        }
    };
}
