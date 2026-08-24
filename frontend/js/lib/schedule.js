export function rafThrottle(fn) {
    let frame = 0;
    return (...args) => {
        if (frame) return;
        frame = requestAnimationFrame(() => {
            frame = 0;
            fn(...args);
        });
    };
}

export function debounce(fn, waitMs) {
    let timer = 0;
    return (...args) => {
        if (timer) clearTimeout(timer);
        timer = setTimeout(() => {
            timer = 0;
            fn(...args);
        }, waitMs);
    };
}

export function prefersReducedMotion() {
    return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
}
