import assert from 'node:assert/strict';
import test from 'node:test';
import { motifCentroid, particleSparkle, sampleFilmMotif, waveFilmMotifIds } from '../frontend/js/lib/wave-film-motifs.js';

const W = 1440;
const H = 900;

test('every curated wave film has a motif', () => {
    const ids = waveFilmMotifIds();
    assert.equal(ids.length, 17);
    for (const id of ids) {
        const points = sampleFilmMotif(id, W, H, 240);
        assert.equal(points.length, 240, id);
        for (const point of points) {
            assert.ok(point.x >= 0 && point.x <= W, `${id} x`);
            assert.ok(point.y >= 0 && point.y <= H, `${id} y`);
        }
    }
});

test('unknown movie has no motif', () => {
    assert.deepEqual(sampleFilmMotif('0', W, H, 80), []);
    assert.deepEqual(sampleFilmMotif('', W, H, 80), []);
});

test('different movies land in different places', () => {
    const a = motifCentroid(sampleFilmMotif('1307914', W, H, 400));
    const b = motifCentroid(sampleFilmMotif('26337866', W, H, 400));
    const c = motifCentroid(sampleFilmMotif('37116446', W, H, 400));
    assert.ok(Math.hypot(a.x - b.x, a.y - b.y) > 12);
    assert.ok(Math.hypot(b.x - c.x, b.y - c.y) > 12);
    assert.ok(Math.hypot(a.x - c.x, a.y - c.y) > 8);
});

test('motif sampling is deterministic', () => {
    const first = sampleFilmMotif('900089', W, H, 80);
    const second = sampleFilmMotif('900089', W, H, 80);
    assert.deepEqual(first, second);
});

test('particleSparkle marks a bright subset and stays in range', () => {
    const quiet = particleSparkle(0.2, 0.4, 1.1, false);
    const hot = particleSparkle(0.95, 0.4, 1.1, false);
    assert.equal(quiet.twinkle, false);
    assert.equal(hot.twinkle, true);
    assert.ok(quiet.flash >= 0 && quiet.flash <= 1);
    assert.ok(hot.flash >= 0 && hot.flash <= 1);
    assert.deepEqual(particleSparkle(0.95, 1.2, 0.3, false), particleSparkle(0.95, 1.2, 0.3, false));
});

test('particleSparkle holds still when motion is reduced', () => {
    const reduced = particleSparkle(0.99, 8, 2, true);
    assert.equal(reduced.twinkle, false);
    assert.equal(reduced.flash, 0.82);
});
