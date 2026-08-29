import assert from 'node:assert/strict';
import test from 'node:test';
import { filmStripArrowDelta, filmStripKeyAction, firstIndexOfWave } from '../frontend/js/lib/wave-film-keys.js';

test('filmStripArrowDelta uses left and right only', () => {
    assert.equal(filmStripArrowDelta('ArrowRight'), 1);
    assert.equal(filmStripArrowDelta('ArrowLeft'), -1);
    assert.equal(filmStripArrowDelta('ArrowDown'), 0);
    assert.equal(filmStripArrowDelta('ArrowUp'), 0);
    assert.equal(filmStripArrowDelta('Escape'), 0);
});

test('filmStripKeyAction maps film overlay keys', () => {
    assert.deepEqual(filmStripKeyAction('ArrowRight'), { type: 'move', delta: 1 });
    assert.deepEqual(filmStripKeyAction('ArrowLeft'), { type: 'move', delta: -1 });
    assert.deepEqual(filmStripKeyAction('Enter'), { type: 'open' });
    assert.deepEqual(filmStripKeyAction(' '), { type: 'open' });
    assert.deepEqual(filmStripKeyAction('Escape'), { type: 'leave' });
    assert.equal(filmStripKeyAction('ArrowDown'), null);
});

test('firstIndexOfWave finds the start of each wave', () => {
    const deck = [
        { id: 'a', wave: 1 },
        { id: 'b', wave: 1 },
        { id: 'c', wave: 2 },
        { id: 'd', wave: 3 }
    ];
    assert.equal(firstIndexOfWave(deck, 1), 0);
    assert.equal(firstIndexOfWave(deck, 2), 2);
    assert.equal(firstIndexOfWave(deck, 3), 3);
    assert.equal(firstIndexOfWave(deck, 9), 0);
    assert.equal(firstIndexOfWave([], 2), 0);
});
