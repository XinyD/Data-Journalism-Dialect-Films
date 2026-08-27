export function easeCubicOut(t) {
    const clamped = Math.max(0, Math.min(1, t));
    const inv = 1 - clamped;
    return 1 - inv * inv * inv;
}

export function orderedRegions(selected) {
    const code = Number(selected);
    return [0, 1, 2, 3, 4].filter(item => item !== code).concat(code);
}

export function orderedLanguages(selected, displayOrder) {
    const code = Number(selected);
    const order = displayOrder.filter(item => item !== code);
    order.push(code);
    return order;
}

export function plotToPixel(x, y, axes, box) {
    const dx = Math.max(1e-6, axes.xMax - axes.xMin);
    const dy = Math.max(1e-6, axes.yMax - axes.yMin);
    return [
        box.left + (Number(x) - axes.xMin) / dx * box.width,
        box.top + (1 - (Number(y) - axes.yMin) / dy) * box.height
    ];
}

export function layoutAxes(sceneId, env) {
    const yMin = env.yMin;
    const yMax = env.yMax;
    switch (sceneId) {
        case 'asian-breakout':
        case 'european-slow':
            return { xMin: -1, xMax: 5, yMin, yMax };
        case 'language-babel':
        case 'chinese-dialect':
            return { xMin: -0.8, xMax: 5.8, yMin, yMax };
        case 'decade-bubble':
        case 'century-decline':
            return { xMin: env.yearMin, xMax: env.yearMax, yMin, yMax };
        case 'dual-director':
            return { xMin: -0.6, xMax: 1.6, yMin, yMax };
        case 'global-layers':
            return env.globalPhase === 'pull-back'
                ? { xMin: -0.8, xMax: 5.8, yMin: 0, yMax: 10 }
                : { xMin: -0.7, xMax: 4.7, yMin: 0, yMax: 10 };
        case 'dialect-flops':
            return { xMin: -0.15, xMax: 4.2, yMin: 0, yMax: 10 };
        default:
            return { xMin: 0, xMax: 100, yMin: 0, yMax: 100 };
    }
}

export function layoutXY(sceneId, movie, env) {
    switch (sceneId) {
        case 'asian-breakout': {
            const order = orderedRegions(env.selectedRegion);
            return { x: order.indexOf(movie.regionCode) + movie.jitterX, y: movie.rating };
        }
        case 'european-slow': {
            const order = orderedRegions(env.selectedRegion);
            return { x: order.indexOf(movie.regionCode) + movie.jitterX, y: movie.rating };
        }
        case 'language-babel': {
            const order = orderedLanguages(env.selectedLanguage, env.languageOrder);
            return { x: order.indexOf(movie.langCode) + movie.jitterGenreX, y: movie.rating };
        }
        case 'decade-bubble':
            return { x: movie.year, y: movie.rating };
        case 'century-decline':
            return { x: movie.year, y: movie.rating };
        case 'chinese-dialect':
            return { x: env.languageIndex(movie.langCode) + movie.jitterGenreX, y: movie.rating };
        case 'dual-director': {
            const inPair = (movie.langCode === 2 || movie.langCode === 3) && movie.regionCode === 3;
            const x = inPair
                ? (movie.langCode === 2 ? 0 : 1) + movie.jitterX * 0.55
                : -1.2 + movie.jitterX * 0.2;
            return { x, y: movie.rating };
        }
        case 'global-layers': {
            const group = env.layerOf(movie);
            return { x: env.layerX(movie, group, env.globalPhase), y: movie.rating };
        }
        case 'dialect-flops': {
            const lit = env.flopLit(movie, env.flopPhase);
            const group = env.layerOf(movie);
            const x = lit
                ? env.flopX(movie, env.flopPhase)
                : env.layerX(movie, group, env.globalPhase);
            return { x, y: movie.rating };
        }
        default:
            return { x: movie.randX, y: movie.randY };
    }
}

export function usesPlotAxes(sceneId) {
    return sceneId !== 'universe'
        && sceneId !== 'final-universe'
        && sceneId !== 'three-waves'
        && sceneId !== 'scale'
        && sceneId !== 'echo-narrative';
}
