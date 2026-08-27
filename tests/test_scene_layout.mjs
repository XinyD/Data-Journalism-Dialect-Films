import assert from 'node:assert/strict';
import test from 'node:test';
import {
    easeCubicOut,
    layoutAxes,
    layoutXY,
    orderedRegions,
    plotToPixel,
    usesPlotAxes
} from '../frontend/js/scenes/scene_layout.js';

test('orderedRegions puts the selected region last', () => {
    assert.deepEqual(orderedRegions(3), [0, 1, 2, 4, 3]);
});

test('layoutXY puts China on the selected column for asian-breakout', () => {
    const movie = { regionCode: 3, rating: 6.6, jitterX: 0 };
    const { x, y } = layoutXY('asian-breakout', movie, { selectedRegion: 3 });
    assert.equal(x, 4);
    assert.equal(y, 6.6);
});

test('plotToPixel maps rating-axis cartesian onto the plot box', () => {
    const axes = { xMin: -1, xMax: 5, yMin: 0, yMax: 10 };
    const box = { left: 10, top: 20, width: 600, height: 400 };
    assert.deepEqual(plotToPixel(-1, 0, axes, box), [10, 420]);
    assert.deepEqual(plotToPixel(5, 10, axes, box), [610, 20]);
});

test('easeCubicOut starts fast then settles', () => {
    assert.equal(easeCubicOut(0), 0);
    assert.equal(easeCubicOut(1), 1);
    assert.ok(easeCubicOut(0.5) > 0.5);
});

test('starfield scenes do not use comparison axes', () => {
    assert.equal(usesPlotAxes('asian-breakout'), true);
    assert.equal(usesPlotAxes('final-universe'), false);
    const axes = layoutAxes('final-universe', { yMin: 0, yMax: 10, yearMin: 1888, yearMax: 2026 });
    assert.deepEqual(axes, { xMin: 0, xMax: 100, yMin: 0, yMax: 100 });
});
