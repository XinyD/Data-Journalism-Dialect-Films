import assert from 'node:assert/strict';
import test from 'node:test';
import {
    dialectHandoffStyle,
    shouldPlayCoverToIntroHandoff
} from '../frontend/js/lib/cover-handoff.js';

test('cover to intro handoff plays from the world map', () => {
    assert.equal(shouldPlayCoverToIntroHandoff({
        sceneId: 'china-dialect-stars',
        fromSceneId: 'universe',
        prologueState: 'WORLD_MAP',
        reducedMotion: false
    }), true);
});

test('cover to intro handoff skips reduced motion and other scenes', () => {
    assert.equal(shouldPlayCoverToIntroHandoff({
        sceneId: 'china-dialect-stars',
        fromSceneId: 'universe',
        prologueState: 'WORLD_MAP',
        reducedMotion: true
    }), false);
    assert.equal(shouldPlayCoverToIntroHandoff({
        sceneId: 'wave-hk',
        fromSceneId: 'universe',
        prologueState: 'WORLD_MAP',
        reducedMotion: false
    }), false);
    assert.equal(shouldPlayCoverToIntroHandoff({
        sceneId: 'china-dialect-stars',
        fromSceneId: 'universe',
        prologueState: 'STAR_FIELD',
        reducedMotion: false
    }), false);
});

test('dialect handoff fades other films and turns keepers gold', () => {
    const fade = dialectHandoffStyle(false, 1, [220, 220, 226, 0.4]);
    assert.equal(fade.appearScale, 0);
    assert.equal(fade.rgba[3], 0);
    const gold = dialectHandoffStyle(true, 1, [10, 80, 200, 0.2]);
    assert.equal(gold.appearScale, 1);
    assert.equal(gold.rgba[0], 255);
    assert.equal(gold.rgba[1], 179);
    assert.equal(gold.rgba[2], 0);
    assert.equal(gold.rgba[3], 0.7);
});
