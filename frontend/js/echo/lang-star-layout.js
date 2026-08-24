import { getLangStarSizes, getLangStarSymbol, getLangStarTier } from './star-symbols.js';

const GOLDEN_ANGLE = (137.508 * Math.PI) / 180;

function seededJitter(seed) {
    const x = Math.sin(seed * 12.9898) * 43758.5453;
    return x - Math.floor(x);
}

function clamp(value, min, max) {
    return Math.min(max, Math.max(min, value));
}

function computeFillPosition(i, n) {
    const fillAngle = ((2 * Math.PI * i) / n) + (seededJitter(i * 9.1) - 0.5) * 0.6;
    const fillRadius = 0.36 + seededJitter(i * 4.3) * 0.14;
    let fillX = 0.5 + Math.cos(fillAngle) * fillRadius;
    let fillY = 0.5 + Math.sin(fillAngle) * fillRadius;
    fillX += (seededJitter(i * 11.7) - 0.5) * 0.1;
    fillY += (seededJitter(i * 13.2) - 0.5) * 0.1;

    if (fillX > 0.24 && fillX < 0.76 && fillY > 0.24 && fillY < 0.76) {
        const dx = fillX - 0.5;
        const dy = fillY - 0.5;
        const len = Math.hypot(dx, dy) || 1;
        fillX = 0.5 + (dx / len) * 0.42;
        fillY = 0.5 + (dy / len) * 0.42;
    }

    return {
        fillX: clamp(fillX, 0.06, 0.94),
        fillY: clamp(fillY, 0.08, 0.92),
    };
}

/**
 * Build screen-space language star markers with perimeter slots and viewport fill anchors.
 */
export function buildScreenLangStars(languages) {
    const n = languages.length || 1;

    return languages.map((lang, i) => {
        const angleJitter = (seededJitter(i * 3.1 + 1) - 0.5) * 0.35;
        const angle = (2 * Math.PI * i) / n - Math.PI / 2 + angleJitter;
        const { fillX, fillY } = computeFillPosition(i, n);

        const followFactor = 0.35 + seededJitter(i * 5.7 + 2) * 0.65;
        const sizeMul = 0.7 + seededJitter(i * 2.1 + 3) * 0.55;
        let brightMul = 0.55 + seededJitter(i * 3.3 + 4) * 0.45;

        const tier = getLangStarTier(lang);
        const sizes = getLangStarSizes(tier);
        const pending = lang.status === 'pending' || !(lang.films && lang.films.length);
        if (pending) brightMul *= 0.65;

        const symbolUrl = getLangStarSymbol(lang, i);

        return {
            lang,
            langId: lang.id,
            tier,
            angle,
            fillX,
            fillY,
            followFactor,
            sizeMul,
            brightMul,
            breathePhase: i * 1.7,
            driftPhase: i * 2.3 + i * GOLDEN_ANGLE * 0.01,
            symbolUrl,
            symbolSize: Math.round(sizes.body * sizeMul),
        };
    });
}
