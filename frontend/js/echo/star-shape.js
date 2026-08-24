/** Four-point sparkle star with concave curved sides (viewBox 0 0 24 24). */
export const SPARKLE_STAR_PATH = [
    'path://M12 1.5',
    'Q13.2 7.2 14.8 9.2',
    'Q17.4 10.6 20.8 12',
    'Q17.4 13.4 14.8 14.8',
    'Q13.2 16.8 12 22.5',
    'Q10.8 16.8 9.2 14.8',
    'Q6.6 13.4 3.2 12',
    'Q6.6 10.6 9.2 9.2',
    'Q10.8 7.2 12 1.5 Z',
].join(' ');

/** @deprecated Use SPARKLE_STAR_PATH */
export const DIAMOND_STAR_PATH = SPARKLE_STAR_PATH;

function hexToRgba(hex, alpha) {
    const n = parseInt(hex.replace('#', ''), 16);
    const r = (n >> 16) & 0xff;
    const g = (n >> 8) & 0xff;
    const b = n & 0xff;
    return `rgba(${r},${g},${b},${alpha})`;
}

function traceSparklePath(ctx, cx, cy, radius) {
    const r = radius;
    const ir = radius * 0.38;
    ctx.moveTo(cx, cy - r);
    ctx.quadraticCurveTo(cx + r * 0.12, cy - r * 0.42, cx + ir * 1.15, cy - ir * 1.15);
    ctx.quadraticCurveTo(cx + r * 0.42, cy - r * 0.12, cx + r, cy);
    ctx.quadraticCurveTo(cx + r * 0.42, cy + r * 0.12, cx + ir * 1.15, cy + ir * 1.15);
    ctx.quadraticCurveTo(cx + r * 0.12, cy + r * 0.42, cx, cy + r);
    ctx.quadraticCurveTo(cx - r * 0.12, cy + r * 0.42, cx - ir * 1.15, cy + ir * 1.15);
    ctx.quadraticCurveTo(cx - r * 0.42, cy + r * 0.12, cx - r, cy);
    ctx.quadraticCurveTo(cx - r * 0.42, cy - r * 0.12, cx - ir * 1.15, cy - ir * 1.15);
    ctx.quadraticCurveTo(cx - r * 0.12, cy - r * 0.42, cx, cy - r);
    ctx.closePath();
}

/**
 * Draw sparkle star on canvas with radial core + soft glow.
 */
export function drawSparkleStar(ctx, cx, cy, radius, { color = '#f0d7a8', glowColor = '#ffffff', opacity = 1 } = {}) {
    ctx.save();
    ctx.globalCompositeOperation = 'lighter';

    const haloGrad = ctx.createRadialGradient(cx, cy, 0, cx, cy, radius * 1.1);
    haloGrad.addColorStop(0, hexToRgba(glowColor, 0.45 * opacity));
    haloGrad.addColorStop(0.45, hexToRgba(color, 0.22 * opacity));
    haloGrad.addColorStop(1, hexToRgba(color, 0));
    ctx.fillStyle = haloGrad;
    ctx.beginPath();
    ctx.arc(cx, cy, radius * 1.1, 0, Math.PI * 2);
    ctx.fill();

    const bodyGrad = ctx.createRadialGradient(cx, cy, 0, cx, cy, radius * 0.85);
    bodyGrad.addColorStop(0, `rgba(255,255,255,${0.95 * opacity})`);
    bodyGrad.addColorStop(0.35, hexToRgba(color, 0.92 * opacity));
    bodyGrad.addColorStop(0.75, hexToRgba(color, 0.55 * opacity));
    bodyGrad.addColorStop(1, hexToRgba(color, 0.1 * opacity));
    ctx.fillStyle = bodyGrad;
    ctx.beginPath();
    traceSparklePath(ctx, cx, cy, radius * 0.88);
    ctx.fill();

    ctx.strokeStyle = hexToRgba(glowColor, 0.35 * opacity);
    ctx.lineWidth = Math.max(0.5, radius * 0.04);
    ctx.beginPath();
    traceSparklePath(ctx, cx, cy, radius * 0.88);
    ctx.stroke();

    ctx.restore();
}
