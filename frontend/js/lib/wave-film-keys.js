export function filmStripArrowDelta(key) {
    if (key === 'ArrowRight') return 1;
    if (key === 'ArrowLeft') return -1;
    return 0;
}

export function filmStripKeyAction(key) {
    if (key === 'Escape') return { type: 'leave' };
    const delta = filmStripArrowDelta(key);
    if (delta) return { type: 'move', delta };
    if (key === 'Enter' || key === ' ') return { type: 'open' };
    return null;
}

export function firstIndexOfWave(deck, wave) {
    if (!Array.isArray(deck) || !deck.length) return 0;
    const index = deck.findIndex(film => Number(film && film.wave) === Number(wave));
    return index < 0 ? 0 : index;
}
