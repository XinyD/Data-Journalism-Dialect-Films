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

export function createPrologueMotionLayer(canvas) {
    const ctx = canvas ? canvas.getContext('2d', { alpha: true }) : null;
    let cssW = 0;
    let cssH = 0;
    let dpr = 1;
    let visible = false;
    let count = 0;
    let xs = new Float32Array(0);
    let ys = new Float32Array(0);
    let sizes = new Float32Array(0);
    let rCh = new Float32Array(0);
    let gCh = new Float32Array(0);
    let bCh = new Float32Array(0);
    let aCh = new Float32Array(0);

    function ensureCapacity(next) {
        if (next <= xs.length) return;
        const size = Math.max(next, Math.ceil((xs.length || 1024) * 1.5));
        xs = growChannel(xs, size);
        ys = growChannel(ys, size);
        sizes = growChannel(sizes, size);
        rCh = growChannel(rCh, size);
        gCh = growChannel(gCh, size);
        bCh = growChannel(bCh, size);
        aCh = growChannel(aCh, size);
    }

    function resize() {
        if (!canvas || !ctx) return;
        dpr = Math.min(2, window.devicePixelRatio || 1);
        cssW = window.innerWidth;
        cssH = window.innerHeight;
        canvas.width = Math.max(1, Math.round(cssW * dpr));
        canvas.height = Math.max(1, Math.round(cssH * dpr));
        canvas.style.width = `${cssW}px`;
        canvas.style.height = `${cssH}px`;
        ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    }

    function setVisible(next) {
        visible = Boolean(next);
        if (canvas) canvas.classList.toggle('is-active', visible);
        if (!visible && ctx) ctx.clearRect(0, 0, cssW, cssH);
    }

    function begin(expected = 0) {
        count = 0;
        if (expected) ensureCapacity(expected);
        if (!cssW || !cssH) resize();
    }

    function push(x, y, size, color) {
        if (size <= 0.2) return;
        const rgba = Array.isArray(color) ? color : parseRgba(color);
        if (rgba[3] <= 0.01) return;
        ensureCapacity(count + 1);
        xs[count] = x;
        ys[count] = y;
        sizes[count] = size;
        rCh[count] = rgba[0];
        gCh[count] = rgba[1];
        bCh[count] = rgba[2];
        aCh[count] = rgba[3];
        count += 1;
    }

    function draw() {
        if (!ctx) return;
        ctx.clearRect(0, 0, cssW, cssH);
        let lastRgb = -1;
        let lastA = -1;
        for (let i = 0; i < count; i += 1) {
            const size = sizes[i];
            const alpha = aCh[i];
            if (size <= 0.2 || alpha <= 0.01) continue;
            const ri = rCh[i] | 0;
            const gi = gCh[i] | 0;
            const bi = bCh[i] | 0;
            const rgb = (ri << 16) | (gi << 8) | bi;
            if (rgb !== lastRgb) {
                ctx.fillStyle = `rgb(${ri},${gi},${bi})`;
                lastRgb = rgb;
            }
            const quantized = ((alpha * 32) | 0) / 32;
            if (quantized !== lastA) {
                ctx.globalAlpha = quantized;
                lastA = quantized;
            }
            const radius = size / 2;
            const x = xs[i];
            const y = ys[i];
            if (radius <= 1.55) {
                const span = Math.max(0.8, size);
                ctx.fillRect(x - span / 2, y - span / 2, span, span);
                continue;
            }
            ctx.beginPath();
            ctx.arc(x, y, radius, 0, Math.PI * 2);
            ctx.fill();
        }
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
            if (ctx) ctx.clearRect(0, 0, cssW, cssH);
        }
    };
}
