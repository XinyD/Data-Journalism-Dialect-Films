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
