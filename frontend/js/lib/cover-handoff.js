export function shouldPlayCoverToIntroHandoff({
    sceneId,
    fromSceneId,
    prologueState,
    reducedMotion
}) {
    return sceneId === 'china-dialect-stars'
        && fromSceneId === 'universe'
        && prologueState === 'WORLD_MAP'
        && !reducedMotion;
}

export function dialectHandoffStyle(keep, release, rgba) {
    const t = Math.max(0, Math.min(1, Number(release) || 0));
    const src = Array.isArray(rgba) ? rgba : [220, 220, 226, 0.16];
    const r = Number(src[0]) || 0;
    const g = Number(src[1]) || 0;
    const b = Number(src[2]) || 0;
    const a = src[3] == null ? 0.16 : Number(src[3]);
    if (!keep) {
        return {
            appearScale: 1 - t,
            rgba: [r, g, b, a * (1 - t)]
        };
    }
    return {
        appearScale: 1,
        rgba: [
            r + (255 - r) * t,
            g + (179 - g) * t,
            b + (0 - b) * t,
            a + (0.7 - a) * t
        ]
    };
}
