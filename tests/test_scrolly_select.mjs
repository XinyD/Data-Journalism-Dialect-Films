import assert from 'node:assert/strict';
import test from 'node:test';
import { isFarJump, pickCurrentStep } from '../frontend/js/lib/scrolly-select.js';

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
