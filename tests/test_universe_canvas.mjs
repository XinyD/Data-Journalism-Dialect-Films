import assert from 'node:assert/strict';
import test from 'node:test';
import {
    dataToPixel,
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
