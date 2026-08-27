import { rafThrottle } from '../lib/schedule.js';
import { runtime } from '../runtime.js';

export function createFlopLinkSync(paint) {
    return rafThrottle(() => {
        if (runtime.activeSceneId !== 'dialect-flops' || runtime.flopPhase !== 'cases' || !runtime.flopLinksReady) return;
        paint();
    });
}

export function paintFlopGraphic(particleChart, elements) {
    if (!particleChart) return;
    particleChart.setOption({
        animation: false,
        graphic: elements
    }, { notMerge: false, lazyUpdate: true, silent: true });
}
