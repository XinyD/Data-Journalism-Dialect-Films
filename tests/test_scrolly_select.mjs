import assert from 'node:assert/strict';
import test from 'node:test';
import { chapterFillFromGeometry, isFarJump, narrativeProgress, nextStoryStepIndex, pickCurrentStep, storyArrowDelta } from '../frontend/js/lib/scrolly-select.js';

const ids = ['step-0', 'step-intro', 'step-2', 'step-7', 'step-8e'];

test('pickCurrentStep chooses the highest ratio', () => {
    const ratios = new Map([['step-0', 0.2], ['step-2', 0.8], ['step-7', 0.1]]);
    assert.equal(pickCurrentStep(ids, ratios, 'step-0'), 'step-2');
});

test('pickCurrentStep keeps current when lead is within hysteresis', () => {
    const ratios = new Map([['step-0', 0.4], ['step-intro', 0.48]]);
    assert.equal(pickCurrentStep(ids, ratios, 'step-0', 0.12), 'step-0');
});

test('pickCurrentStep switches when lead exceeds hysteresis', () => {
    const ratios = new Map([['step-0', 0.2], ['step-intro', 0.4]]);
    assert.equal(pickCurrentStep(ids, ratios, 'step-0', 0.12), 'step-intro');
});

test('pickCurrentStep reselects when current has left the band', () => {
    const ratios = new Map([['step-0', 0], ['step-8e', 0.6]]);
    assert.equal(pickCurrentStep(ids, ratios, 'step-0'), 'step-8e');
});

test('pickCurrentStep keeps current when nothing is intersecting', () => {
    const ratios = new Map([['step-0', 0], ['step-2', 0]]);
    assert.equal(pickCurrentStep(ids, ratios, 'step-2'), 'step-2');
});

test('isFarJump is true across two or more steps', () => {
    assert.equal(isFarJump(0, 1), false);
    assert.equal(isFarJump(0, 2), true);
    assert.equal(isFarJump(4, 1), true);
    assert.equal(isFarJump(-1, 3), false);
});

test('narrativeProgress is clamped to the story range', () => {
    assert.equal(narrativeProgress(0, 0, 1000), 0);
    assert.equal(narrativeProgress(250, 0, 1000), 0.25);
    assert.equal(narrativeProgress(2000, 0, 1000), 1);
    assert.equal(narrativeProgress(100, 200, 1200), 0);
});

test('storyArrowDelta maps arrow keys to one step', () => {
    assert.equal(storyArrowDelta('ArrowDown'), 1);
    assert.equal(storyArrowDelta('ArrowRight'), 1);
    assert.equal(storyArrowDelta('ArrowUp'), -1);
    assert.equal(storyArrowDelta('ArrowLeft'), -1);
    assert.equal(storyArrowDelta('PageDown'), 0);
    assert.equal(storyArrowDelta('a'), 0);
});

test('nextStoryStepIndex advances and stops at the ends', () => {
    assert.equal(nextStoryStepIndex(0, 1, 10), 1);
    assert.equal(nextStoryStepIndex(9, 1, 10), 9);
    assert.equal(nextStoryStepIndex(0, -1, 10), 0);
    assert.equal(nextStoryStepIndex(3, -1, 10), 2);
    assert.equal(nextStoryStepIndex(2, 0, 10), 2);
    assert.equal(nextStoryStepIndex(0, 1, 0), 0);
});

test('chapterFillFromGeometry uses real step heights', () => {
    const steps = [
        { id: 'a', top: 0, height: 100 },
        { id: 'b', top: 100, height: 300 },
        { id: 'c', top: 400, height: 100 }
    ];
    const fill = chapterFillFromGeometry(steps, 'b');
    assert.equal(fill.top, 20);
    assert.equal(fill.height, 60);
});
