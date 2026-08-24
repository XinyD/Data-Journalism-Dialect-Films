/** Curated per-language star colors (hex strings).
 *  Hue bands: Yue gold / Min cyan-teal / Wu steel / Mandarin warm / Tibeto-Burman plum /
 *  Turkic lapis / Mongolic steppe / sign indigo. Same branch may sit nearby; RGB distance ≥ ~30.
 */
export const LANG_STAR_COLORS = {
    '粤语': { core: '#e4b15a', glow: '#f0d7a8' },
    '闽南语': { core: '#2bb8b8', glow: '#7ee8e8' },
    '台语': { core: '#2a9b6e', glow: '#7ed9a8' },
    '潮汕话': { core: '#1aa894', glow: '#6ee0d0' },
    '上海话': { core: '#d08a62', glow: '#e8c4a8' },
    '吴语': { core: '#4a8fa3', glow: '#8cc4d4' },
    '藏语': { core: '#6b4c9a', glow: '#b89ee8' },
    '四川话': { core: '#e24a32', glow: '#f09878' },
    '重庆话': { core: '#ef9a3a', glow: '#ffc070' },
    '哈萨克语': { core: '#3d9ad0', glow: '#88c4f0' },
    '晋语': { core: '#8b6a38', glow: '#d0b088' },
    '武汉话': { core: '#d94a7a', glow: '#f088a8' },
    '维吾尔语': { core: '#3a6fd4', glow: '#78b4f0' },
    '客家话': { core: '#8fbc4a', glow: '#c0e090' },
    '河南话': { core: '#d9a44a', glow: '#ecc070' },
    '陕西话': { core: '#c46a32', glow: '#e0a070' },
    '东北话': { core: '#7a9bb8', glow: '#b0c8e0' },
    '南京话': { core: '#6e7fd0', glow: '#a8b4e8' },
    '蒙语': { core: '#2f9a72', glow: '#88d0a0' },
    '天津话': { core: '#e07048', glow: '#ffb088' },
    '山东话': { core: '#d4892a', glow: '#f0b060' },
    '唐山话': { core: '#c45a72', glow: '#e090a0' },
    '湖南话': { core: '#d63b4a', glow: '#ff7090' },
    '贵州话': { core: '#6cb83a', glow: '#a0e070' },
    '云南话': { core: '#c4a03a', glow: '#e0c070' },
    '手语': { core: '#6a7cc0', glow: '#a0b0e8' },
    '彝语': { core: '#c45c2a', glow: '#e09060' },
    '壮语': { core: '#4a9a6a', glow: '#88d0a0' },
    '苗语': { core: '#9a7ab8', glow: '#c8b0e0' },
};

const GOLDEN_ANGLE = 137.508;
const symbolCache = new Map();

function hslToHex(h, s, l) {
    const c = (1 - Math.abs(2 * l - 1)) * s;
    const x = c * (1 - Math.abs(((h / 60) % 2) - 1));
    const m = l - c / 2;
    let r = 0;
    let g = 0;
    let b = 0;
    if (h < 60) { r = c; g = x; }
    else if (h < 120) { r = x; g = c; }
    else if (h < 180) { g = c; b = x; }
    else if (h < 240) { g = x; b = c; }
    else if (h < 300) { r = x; b = c; }
    else { r = c; b = x; }
    const toHex = (v) => Math.round((v + m) * 255).toString(16).padStart(2, '0');
    return `#${toHex(r)}${toHex(g)}${toHex(b)}`;
}

function fallbackColor(langId, index) {
    const hue = (index * GOLDEN_ANGLE) % 360;
    return { core: hslToHex(hue, 0.55, 0.52), glow: hslToHex(hue, 0.45, 0.68) };
}

export function getLangStarColors(lang, index = 0) {
    const key = lang.name || lang.id;
    const base = LANG_STAR_COLORS[key] || LANG_STAR_COLORS[lang.id] || fallbackColor(lang.id, index);
    const pending = lang.status === 'pending' || !(lang.films && lang.films.length);
    if (!pending) return { ...base, pending: false };
    const dim = (hex, factor) => {
        const n = parseInt(hex.slice(1), 16);
        const r = Math.floor(((n >> 16) & 0xff) * factor);
        const g = Math.floor(((n >> 8) & 0xff) * factor);
        const b = Math.floor((n & 0xff) * factor);
        return `#${((r << 16) | (g << 8) | b).toString(16).padStart(6, '0')}`;
    };
    return { core: dim(base.core, 0.4), glow: dim(base.glow, 0.35), pending: true };
}

export function getLangStarTier(lang) {
    // Fixed Zipf-aware sizes: 粤语 (~2750) is the only ≥500 primary;
    // 闽南语 (~143) is the only ≥80 secondary. Not percentiles — that would flatten the industry fact.
    const pending = lang.status === 'pending' || !(lang.films && lang.films.length);
    if (pending) return 'dim';
    const n = lang.n || 0;
    if (n >= 500) return 'primary';
    if (n >= 80) return 'secondary';
    return 'tertiary';
}

const TIER_SIZES = {
    primary: { body: 48, glow: 55, shadow: 62 },
    secondary: { body: 38, glow: 44, shadow: 50 },
    tertiary: { body: 32, glow: 37, shadow: 42 },
    dim: { body: 18, glow: 21, shadow: 24 },
};

export function getLangStarSizes(tier) {
    return TIER_SIZES[tier] || TIER_SIZES.tertiary;
}

function hexToRgba(hex, alpha) {
    const n = parseInt(hex.replace('#', ''), 16);
    const r = (n >> 16) & 0xff;
    const g = (n >> 8) & 0xff;
    const b = n & 0xff;
    return `rgba(${r},${g},${b},${alpha})`;
}

/**
 * Canvas cross-flare texture → data URL for language star overlay.
 */
export function createCrossFlareDataUrl({ color = '#f0d7a8', glowColor = '#ffffff', size = 64, rays = 4, opacity = 1 }) {
    const key = `${color}|${glowColor}|${size}|${rays}|${opacity}`;
    if (symbolCache.has(key)) return symbolCache.get(key);

    const canvas = document.createElement('canvas');
    const pad = Math.ceil(size * 0.15);
    const dim = size + pad * 2;
    canvas.width = dim;
    canvas.height = dim;
    const ctx = canvas.getContext('2d');
    const cx = dim / 2;
    const cy = dim / 2;
    const half = size / 2;
    const rayReach = half * 1.35;

    ctx.globalCompositeOperation = 'lighter';

    const coreGrad = ctx.createRadialGradient(cx, cy, 0, cx, cy, half * 0.35);
    coreGrad.addColorStop(0, `rgba(255,255,255,${opacity})`);
    coreGrad.addColorStop(0.35, hexToRgba(color, 0.9 * opacity));
    ctx.fillStyle = coreGrad;
    ctx.beginPath();
    ctx.arc(cx, cy, half * 0.22, 0, Math.PI * 2);
    ctx.fill();

    const haloGrad = ctx.createRadialGradient(cx, cy, 0, cx, cy, half * 0.7);
    haloGrad.addColorStop(0, hexToRgba(glowColor, 0.4 * opacity));
    haloGrad.addColorStop(0.5, hexToRgba(color, 0.18 * opacity));
    haloGrad.addColorStop(1, hexToRgba(color, 0));
    ctx.fillStyle = haloGrad;
    ctx.beginPath();
    ctx.arc(cx, cy, half * 0.7, 0, Math.PI * 2);
    ctx.fill();

    for (let i = 0; i < rays; i++) {
        const angle = (i / rays) * Math.PI;
        ctx.save();
        ctx.translate(cx, cy);
        ctx.rotate(angle);
        const rayGrad = ctx.createLinearGradient(0, -rayReach, 0, rayReach);
        rayGrad.addColorStop(0, hexToRgba(glowColor, 0));
        rayGrad.addColorStop(0.42, hexToRgba(glowColor, 0.12 * opacity));
        rayGrad.addColorStop(0.5, hexToRgba('#ffffff', 0.85 * opacity));
        rayGrad.addColorStop(0.58, hexToRgba(glowColor, 0.12 * opacity));
        rayGrad.addColorStop(1, hexToRgba(glowColor, 0));
        ctx.fillStyle = rayGrad;
        const rayW = half * 0.07;
        ctx.fillRect(-rayW / 2, -rayReach, rayW, rayReach * 2);
        ctx.restore();
    }

    const url = canvas.toDataURL('image/png');
    symbolCache.set(key, url);
    return url;
}

export function getLangStarSymbol(lang, index = 0) {
    const colors = getLangStarColors(lang, index);
    const tier = getLangStarTier(lang);
    const opacity = colors.pending ? 0.32 : 1;
    const texSize = tier === 'primary' ? 96 : tier === 'secondary' ? 80 : tier === 'tertiary' ? 72 : 56;
    return createCrossFlareDataUrl({
        color: colors.core,
        glowColor: colors.glow,
        size: texSize,
        rays: 4,
        opacity,
    });
}
