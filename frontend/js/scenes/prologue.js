import { prefersReducedMotion } from '../lib/schedule.js';
import { runtime } from '../runtime.js';

export function syncCoverReveal(forceReady = false) {
    const root = document.documentElement;
    if (root.dataset.coverSkipped) return;
    const cover = document.getElementById('step-0');
    const onCover = Boolean(cover && cover.classList.contains('is-active'));
    if (!onCover) {
        if (!root.dataset.coverReady) root.dataset.coverSkipped = 'true';
        return;
    }
    const reveal = runtime.prologueMotion ? runtime.prologueMotion.reveal : 0;
    if (forceReady || prefersReducedMotion() || reveal >= 0.85) {
        root.dataset.coverReady = 'true';
    }
}

export function parseRgba(color) {
    if (Array.isArray(color)) {
        return [
            Number(color[0]) || 0,
            Number(color[1]) || 0,
            Number(color[2]) || 0,
            color[3] == null ? 1 : Number(color[3])
        ];
    }
    const match = String(color || '').match(/rgba?\(([\d.]+),\s*([\d.]+),\s*([\d.]+)(?:,\s*([\d.]+))?\)/i);
    if (!match) return [220, 220, 226, 0.16];
    return [
        Number(match[1]),
        Number(match[2]),
        Number(match[3]),
        match[4] == null ? 1 : Number(match[4])
    ];
}

function growChannel(prev, size) {
    const next = new Float32Array(size);
    if (prev) next.set(prev);
    return next;
}

function growIndex(prev, size) {
    const next = new Uint32Array(size);
    if (prev) next.set(prev);
    return next;
}

function makeCircleSprite(ri, gi, bi, px) {
    const canvas = document.createElement('canvas');
    const dim = px + 2;
    canvas.width = dim;
    canvas.height = dim;
    const sctx = canvas.getContext('2d');
    if (!sctx) return canvas;
    sctx.fillStyle = `rgb(${ri},${gi},${bi})`;
    sctx.beginPath();
    sctx.arc(dim / 2, dim / 2, px / 2, 0, Math.PI * 2);
    sctx.fill();
    return canvas;
}

export function createPrologueMotionLayer(canvas) {
    const ctx = canvas
        ? (canvas.getContext('2d', { alpha: true, desynchronized: true })
            || canvas.getContext('2d', { alpha: true }))
        : null;
    const buffer = typeof document !== 'undefined' ? document.createElement('canvas') : null;
    const bctx = buffer ? buffer.getContext('2d', { alpha: true }) : null;
    let cssW = 0;
    let cssH = 0;
    let dpr = 1;
    let visible = false;
    let count = 0;
    let xs = new Float32Array(0);
    let ys = new Float32Array(0);
    const sprites = new Map();
    const buckets = new Map();

    function ensureCapacity(next) {
        if (next <= xs.length) return;
        const size = Math.max(next, Math.ceil((xs.length || 1024) * 1.5));
        xs = growChannel(xs, size);
        ys = growChannel(ys, size);
    }

    function resetBuckets() {
        buckets.forEach(bucket => {
            bucket.n = 0;
        });
    }

    function addToBucket(key, rgb, aQuant, stamp, index) {
        let bucket = buckets.get(key);
        if (!bucket) {
            bucket = { rgb, aQuant, stamp, n: 0, idx: new Uint32Array(64) };
            buckets.set(key, bucket);
        }
        if (bucket.n === bucket.idx.length) {
            bucket.idx = growIndex(bucket.idx, bucket.idx.length * 2);
        }
        bucket.idx[bucket.n] = index;
        bucket.n += 1;
    }

    function spriteFor(rgb, stamp, ri, gi, bi) {
        const key = rgb * 8 + stamp;
        const cached = sprites.get(key);
        if (cached) return cached;
        const sprite = makeCircleSprite(ri, gi, bi, stamp);
        sprites.set(key, sprite);
        return sprite;
    }

    function resize() {
        if (!canvas || !ctx || !buffer || !bctx) return;
        dpr = Math.min(1.25, window.devicePixelRatio || 1);
        cssW = window.innerWidth;
        cssH = window.innerHeight;
        canvas.width = Math.max(1, Math.round(cssW * dpr));
        canvas.height = Math.max(1, Math.round(cssH * dpr));
        canvas.style.width = `${cssW}px`;
        canvas.style.height = `${cssH}px`;
        buffer.width = Math.max(1, cssW);
        buffer.height = Math.max(1, cssH);
        ctx.setTransform(1, 0, 0, 1, 0, 0);
        ctx.imageSmoothingEnabled = true;
        ctx.imageSmoothingQuality = 'low';
        bctx.imageSmoothingEnabled = false;
    }

    function setVisible(next) {
        visible = Boolean(next);
        if (canvas) canvas.classList.toggle('is-active', visible);
        if (!visible && ctx) ctx.clearRect(0, 0, canvas.width, canvas.height);
        if (!visible && bctx && buffer) bctx.clearRect(0, 0, buffer.width, buffer.height);
    }

    function begin(expected = 0) {
        count = 0;
        resetBuckets();
        if (expected) ensureCapacity(expected);
        if (!cssW || !cssH) resize();
    }

    function push(x, y, size, color) {
        if (size <= 0.2) return;
        const rgba = Array.isArray(color) ? color : parseRgba(color);
        if (rgba[3] <= 0.01) return;
        ensureCapacity(count + 1);
        const ri = rgba[0] | 0;
        const gi = rgba[1] | 0;
        const bi = rgba[2] | 0;
        const q = (rgba[3] * 32) | 0;
        const stamp = Math.max(2, Math.min(6, Math.round(size)));
        xs[count] = x;
        ys[count] = y;
        const rgb = (ri << 16) | (gi << 8) | bi;
        addToBucket(rgb * 264 + q * 8 + stamp, rgb, q, stamp, count);
        count += 1;
    }

    function draw() {
        if (!ctx || !bctx || !buffer || !canvas) return;
        bctx.clearRect(0, 0, buffer.width, buffer.height);
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        if (!count) {
            bctx.globalAlpha = 1;
            ctx.globalAlpha = 1;
            return;
        }
        let lastRgb = -1;
        let lastQ = -1;
        let lastStamp = -1;
        let sprite = null;
        buckets.forEach(bucket => {
            if (!bucket.n) return;
            if (bucket.aQuant !== lastQ) {
                bctx.globalAlpha = bucket.aQuant / 32;
                lastQ = bucket.aQuant;
            }
            const idx = bucket.idx;
            const stamp = bucket.stamp;
            if (stamp <= 3) {
                if (bucket.rgb !== lastRgb) {
                    bctx.fillStyle = `rgb(${(bucket.rgb >> 16) & 255},${(bucket.rgb >> 8) & 255},${bucket.rgb & 255})`;
                    lastRgb = bucket.rgb;
                    lastStamp = -1;
                }
                const half = stamp / 2;
                for (let n = 0; n < bucket.n; n += 1) {
                    const i = idx[n];
                    bctx.fillRect(
                        Math.round(xs[i] - half),
                        Math.round(ys[i] - half),
                        stamp,
                        stamp
                    );
                }
                return;
            }
            if (bucket.rgb !== lastRgb || stamp !== lastStamp) {
                sprite = spriteFor(
                    bucket.rgb,
                    stamp,
                    (bucket.rgb >> 16) & 255,
                    (bucket.rgb >> 8) & 255,
                    bucket.rgb & 255
                );
                lastRgb = bucket.rgb;
                lastStamp = stamp;
            }
            const ox = sprite.width / 2;
            const oy = sprite.height / 2;
            for (let n = 0; n < bucket.n; n += 1) {
                const i = idx[n];
                bctx.drawImage(sprite, Math.round(xs[i] - ox), Math.round(ys[i] - oy));
            }
        });
        bctx.globalAlpha = 1;
        ctx.drawImage(buffer, 0, 0, canvas.width, canvas.height);
        ctx.globalAlpha = 1;
    }

    return {
        resize,
        setVisible,
        isVisible: () => visible,
        cssSize: () => ({
            width: cssW || window.innerWidth,
            height: cssH || window.innerHeight
        }),
        begin,
        push,
        draw,
        clear() {
            count = 0;
            resetBuckets();
            if (ctx && canvas) ctx.clearRect(0, 0, canvas.width, canvas.height);
            if (bctx && buffer) bctx.clearRect(0, 0, buffer.width, buffer.height);
        }
    };
}
