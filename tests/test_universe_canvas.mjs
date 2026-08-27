import assert from 'node:assert/strict';
import test from 'node:test';
import {
    dataToPixel,
    dwellAnchorUpdate,
    nearestIndex,
    parseRgba
} from '../frontend/js/scenes/universe_canvas.js';

test('parseRgba reads rgba channels', () => {
    assert.deepEqual(parseRgba('rgba(220, 220, 226, 0.16)'), [220, 220, 226, 0.16]);
    assert.deepEqual(parseRgba('rgb(212, 165, 116)'), [212, 165, 116, 1]);
    assert.deepEqual(parseRgba('#e6bc86'), [230, 188, 134, 1]);
});

test('parseRgba falls back for empty input', () => {
    assert.deepEqual(parseRgba(''), [220, 220, 226, 1]);
    assert.deepEqual(parseRgba(null), [220, 220, 226, 1]);
});

test('dataToPixel maps cartesian data to CSS pixels with y up', () => {
    const xMax = 200;
    assert.deepEqual(dataToPixel(0, 0, xMax, 1000, 800), [0, 800]);
    assert.deepEqual(dataToPixel(xMax, 100, xMax, 1000, 800), [1000, 0]);
    assert.deepEqual(dataToPixel(xMax / 2, 50, xMax, 1000, 800), [500, 400]);
});

test('nearestIndex returns the closest point within radius', () => {
    const xs = new Float32Array([10, 50, 90]);
    const ys = new Float32Array([10, 50, 90]);
    assert.equal(nearestIndex(11, 12, xs, ys, 3, 5), 0);
    assert.equal(nearestIndex(48, 52, xs, ys, 3, 8), 1);
});

test('nearestIndex returns -1 when outside radius or empty', () => {
    const xs = new Float32Array([10, 50]);
    const ys = new Float32Array([10, 50]);
    assert.equal(nearestIndex(100, 100, xs, ys, 2, 5), -1);
    assert.equal(nearestIndex(10, 10, xs, ys, 0, 20), -1);
});

test('dwellAnchorUpdate keeps the anchor within tolerance, resets beyond it', () => {
    const anchor = { index: 4, x: 100, y: 100 };
    assert.equal(dwellAnchorUpdate(anchor, 4, 103, 104, 6), anchor);
    assert.deepEqual(dwellAnchorUpdate(anchor, 4, 110, 100, 6), { index: 4, x: 110, y: 100 });
    assert.deepEqual(dwellAnchorUpdate(anchor, 5, 101, 100, 6), { index: 5, x: 101, y: 100 });
    assert.deepEqual(dwellAnchorUpdate(null, 1, 10, 10, 6), { index: 1, x: 10, y: 10 });
});
