import assert from 'node:assert/strict';
import test from 'node:test';
import {
    TOOLTIP_DWELL_MS,
    TOOLTIP_MOVE_TOLERANCE_PX,
    createTooltipDwell,
    dwellAnchorUpdate
} from '../frontend/js/scenes/prologue.js';

// The controller schedules with setTimeout; drive it from a fake clock so the
// tests never depend on wall time.
function installFakeTimers() {
    const originalSetTimeout = globalThis.setTimeout;
    const originalClearTimeout = globalThis.clearTimeout;
    let nextId = 1;
    const pending = new Map();
    globalThis.setTimeout = (fn, delay) => {
        const id = nextId++;
        pending.set(id, { fn, delay });
        return id;
    };
    globalThis.clearTimeout = id => {
        pending.delete(id);
    };
    return {
        pending,
        // Run every timer whose delay has been reached, oldest first.
        flush() {
            const due = [...pending.entries()].sort((a, b) => a[1].delay - b[1].delay);
            pending.clear();
            for (const [, timer] of due) timer.fn();
        },
        restore() {
            globalThis.setTimeout = originalSetTimeout;
            globalThis.clearTimeout = originalClearTimeout;
        }
    };
}

function makeRecorder() {
    const events = [];
    return {
        events,
        onShow: (key, x, y) => events.push(['show', key, x, y]),
        onHide: () => events.push(['hide'])
    };
}

test('dwell anchor holds while the pointer stays inside the tolerance', () => {
    const anchor = { index: 7, x: 100, y: 100 };
    assert.equal(dwellAnchorUpdate(anchor, 7, 103, 103, 6), anchor);
    assert.equal(dwellAnchorUpdate(anchor, 7, 100, 100, 6), anchor);
});

test('dwell anchor moves once the pointer leaves the tolerance', () => {
    const anchor = { index: 7, x: 100, y: 100 };
    const moved = dwellAnchorUpdate(anchor, 7, 110, 100, 6);
    assert.notEqual(moved, anchor);
    assert.deepEqual(moved, { index: 7, x: 110, y: 100 });
});

test('dwell anchor always moves when the particle changes', () => {
    const anchor = { index: 7, x: 100, y: 100 };
    const moved = dwellAnchorUpdate(anchor, 8, 100, 100, 6);
    assert.deepEqual(moved, { index: 8, x: 100, y: 100 });
});

test('no tooltip before the dwell elapses', () => {
    const timers = installFakeTimers();
    try {
        const rec = makeRecorder();
        const dwell = createTooltipDwell({ onShow: rec.onShow, onHide: rec.onHide });
        dwell.pointerMove('a', 10, 10);
        assert.deepEqual(rec.events, []);
        assert.equal(dwell.isShowing(), false);
    } finally {
        timers.restore();
    }
});

test('tooltip appears after one dwell period of stillness', () => {
    const timers = installFakeTimers();
    try {
        const rec = makeRecorder();
        const dwell = createTooltipDwell({ onShow: rec.onShow, onHide: rec.onHide });
        dwell.pointerMove('a', 10, 10);
        timers.flush();
        assert.deepEqual(rec.events, [['show', 'a', 10, 10]]);
        assert.equal(dwell.isShowing(), true);
    } finally {
        timers.restore();
    }
});

test('tremor inside the tolerance does not restart the dwell timer', () => {
    const timers = installFakeTimers();
    try {
        const rec = makeRecorder();
        const dwell = createTooltipDwell({ onShow: rec.onShow, onHide: rec.onHide });
        dwell.pointerMove('a', 10, 10);
        // A resting hand keeps emitting moves; these must not cancel the timer.
        for (let i = 0; i < 20; i += 1) dwell.pointerMove('a', 10 + (i % 3), 10 + (i % 2));
        assert.equal(timers.pending.size, 1);
        timers.flush();
        assert.deepEqual(rec.events, [['show', 'a', 10, 10]]);
    } finally {
        timers.restore();
    }
});

test('moving beyond the tolerance restarts the dwell timer', () => {
    const timers = installFakeTimers();
    try {
        const rec = makeRecorder();
        const dwell = createTooltipDwell({ onShow: rec.onShow, onHide: rec.onHide });
        dwell.pointerMove('a', 10, 10);
        dwell.pointerMove('a', 40, 40);
        // Only the second anchor may fire, and only once.
        timers.flush();
        assert.deepEqual(rec.events, [['show', 'a', 40, 40]]);
    } finally {
        timers.restore();
    }
});

test('leaving the particle cancels a pending tooltip', () => {
    const timers = installFakeTimers();
    try {
        const rec = makeRecorder();
        const dwell = createTooltipDwell({ onShow: rec.onShow, onHide: rec.onHide });
        dwell.pointerMove('a', 10, 10);
        dwell.pointerMove(null, 10, 10);
        timers.flush();
        assert.deepEqual(rec.events, []);
    } finally {
        timers.restore();
    }
});

test('scroll hide cancels a pending tooltip', () => {
    const timers = installFakeTimers();
    try {
        const rec = makeRecorder();
        const dwell = createTooltipDwell({ onShow: rec.onShow, onHide: rec.onHide });
        dwell.pointerMove('a', 10, 10);
        dwell.hide();
        timers.flush();
        assert.deepEqual(rec.events, []);
    } finally {
        timers.restore();
    }
});

test('switching particles hides the shown card and waits again', () => {
    const timers = installFakeTimers();
    try {
        const rec = makeRecorder();
        const dwell = createTooltipDwell({ onShow: rec.onShow, onHide: rec.onHide });
        dwell.pointerMove('a', 10, 10);
        timers.flush();
        dwell.pointerMove('b', 50, 50);
        assert.deepEqual(rec.events, [['show', 'a', 10, 10], ['hide']]);
        assert.equal(dwell.isShowing(), false);
        timers.flush();
        assert.deepEqual(rec.events, [['show', 'a', 10, 10], ['hide'], ['show', 'b', 50, 50]]);
    } finally {
        timers.restore();
    }
});

test('staying on the shown particle does not re-show it', () => {
    const timers = installFakeTimers();
    try {
        const rec = makeRecorder();
        const dwell = createTooltipDwell({ onShow: rec.onShow, onHide: rec.onHide });
        dwell.pointerMove('a', 10, 10);
        timers.flush();
        dwell.pointerMove('a', 80, 80);
        timers.flush();
        assert.deepEqual(rec.events, [['show', 'a', 10, 10]]);
    } finally {
        timers.restore();
    }
});

test('hide after a shown tooltip reports exactly one hide', () => {
    const timers = installFakeTimers();
    try {
        const rec = makeRecorder();
        const dwell = createTooltipDwell({ onShow: rec.onShow, onHide: rec.onHide });
        dwell.pointerMove('a', 10, 10);
        timers.flush();
        dwell.hide();
        dwell.hide();
        assert.deepEqual(rec.events, [['show', 'a', 10, 10], ['hide']]);
    } finally {
        timers.restore();
    }
});

test('dwell constants match the documented reading delay', () => {
    assert.equal(TOOLTIP_DWELL_MS, 1000);
    assert.equal(TOOLTIP_MOVE_TOLERANCE_PX, 6);
});
