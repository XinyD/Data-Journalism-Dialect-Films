export function pickCurrentStep(stepIds, ratios, currentId, hysteresis = 0.12) {
    let bestId = null;
    let bestRatio = -1;
    const read = id => {
        if (!id) return 0;
        if (ratios && typeof ratios.get === 'function') return Number(ratios.get(id)) || 0;
        return Number(ratios && ratios[id]) || 0;
    };
    for (let i = 0; i < stepIds.length; i += 1) {
        const id = stepIds[i];
        const ratio = read(id);
        if (ratio > bestRatio) {
            bestRatio = ratio;
            bestId = id;
        }
    }
    if (bestRatio <= 0) return currentId || stepIds[0] || null;
    if (!currentId || currentId === bestId) return bestId;
    const currentRatio = read(currentId);
    if (bestRatio - currentRatio < hysteresis) return currentId;
    return bestId;
}

export function isFarJump(fromIndex, toIndex) {
    if (!Number.isInteger(fromIndex) || !Number.isInteger(toIndex)) return false;
    if (fromIndex < 0 || toIndex < 0) return false;
    return Math.abs(toIndex - fromIndex) >= 2;
}

export function narrativeProgress(scrollY, start, end) {
    const span = Math.max(1, Number(end) - Number(start));
    return Math.max(0, Math.min(1, (Number(scrollY) - Number(start)) / span));
}

export function storyArrowDelta(key) {
    if (key === 'ArrowDown' || key === 'ArrowRight') return 1;
    if (key === 'ArrowUp' || key === 'ArrowLeft') return -1;
    return 0;
}

export function nextStoryStepIndex(currentIndex, delta, length) {
    if (!Number.isInteger(currentIndex) || !Number.isInteger(delta) || !Number.isInteger(length)) {
        return currentIndex;
    }
    if (length <= 0 || delta === 0) return currentIndex;
    const next = currentIndex + delta;
    if (next < 0 || next >= length) return currentIndex;
    return next;
}

export function chapterFillFromGeometry(steps, currentId) {
    if (!steps.length) return { top: 0, height: 0 };
    const first = steps[0].top;
    const last = steps[steps.length - 1];
    const total = Math.max(1, last.top + last.height - first);
    const current = steps.find(step => step.id === currentId) || steps[0];
    return {
        top: (current.top - first) / total * 100,
        height: current.height / total * 100
    };
}
