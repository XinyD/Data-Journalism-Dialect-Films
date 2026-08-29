const MOTIF_IDS = [
    '1307914', '1303913', '900054', '1305690', '900089',
    '26337866', '26633257', '27110296', '900072', '26657126', '27668250',
    '1292434', '27059130', '3993559', '30292777', '34805873', '37116446'
];

function lerp(a, b, t) {
    return a + (b - a) * t;
}

function hash01(value, salt = 0) {
    let hash = (2166136261 ^ salt) >>> 0;
    const text = String(value);
    for (let i = 0; i < text.length; i += 1) {
        hash ^= text.charCodeAt(i);
        hash = Math.imul(hash, 16777619);
    }
    return (hash >>> 0) / 4294967295;
}

function line(x1, y1, x2, y2, count) {
    const points = [];
    const n = Math.max(1, count);
    for (let i = 0; i < n; i += 1) {
        const t = n === 1 ? 0 : i / (n - 1);
        points.push({ x: lerp(x1, x2, t), y: lerp(y1, y2, t) });
    }
    return points;
}

function ring(cx, cy, rx, ry, count) {
    const points = [];
    const n = Math.max(3, count);
    for (let i = 0; i < n; i += 1) {
        const a = (i / n) * Math.PI * 2;
        points.push({ x: cx + Math.cos(a) * rx, y: cy + Math.sin(a) * ry });
    }
    return points;
}

function disc(cx, cy, rx, ry, count, salt) {
    const points = [];
    const n = Math.max(1, count);
    for (let i = 0; i < n; i += 1) {
        const a = hash01(i, salt) * Math.PI * 2;
        const r = Math.sqrt(hash01(i, salt + 7));
        points.push({ x: cx + Math.cos(a) * rx * r, y: cy + Math.sin(a) * ry * r });
    }
    return points;
}

function poly(pts, count) {
    if (!pts.length) return [];
    if (pts.length === 1) return [{ x: pts[0][0], y: pts[0][1] }];
    let perimeter = 0;
    const segs = [];
    for (let i = 0; i < pts.length - 1; i += 1) {
        const dx = pts[i + 1][0] - pts[i][0];
        const dy = pts[i + 1][1] - pts[i][1];
        const len = Math.hypot(dx, dy);
        segs.push({ i, len });
        perimeter += len;
    }
    const n = Math.max(1, count);
    const points = [];
    for (let k = 0; k < n; k += 1) {
        let walk = (k / n) * perimeter;
        for (let s = 0; s < segs.length; s += 1) {
            if (walk > segs[s].len && s < segs.length - 1) {
                walk -= segs[s].len;
                continue;
            }
            const t = segs[s].len ? walk / segs[s].len : 0;
            const a = pts[segs[s].i];
            const b = pts[segs[s].i + 1];
            points.push({ x: lerp(a[0], b[0], t), y: lerp(a[1], b[1], t) });
            break;
        }
    }
    return points;
}

function figure(x, y, w, h, count) {
    const head = disc(x, y - h * 0.36, w * 0.17, h * 0.13, Math.floor(count * 0.22), 1);
    const body = disc(x, y + h * 0.06, w * 0.24, h * 0.4, Math.floor(count * 0.78), 2);
    return head.concat(body);
}

function motifUnit(id) {
    if (id === '1307914') {
        return figure(0.3, 0.56, 0.28, 0.82, 160)
            .concat(figure(0.7, 0.54, 0.28, 0.84, 160))
            .concat(line(0.12, 0.08, 0.18, 0.9, 10))
            .concat(line(0.86, 0.06, 0.92, 0.88, 10));
    }
    if (id === '1303913') {
        return poly([[0.08, 0.86], [0.18, 0.28], [0.5, 0.12], [0.82, 0.28], [0.92, 0.86]], 90)
            .concat(line(0.18, 0.28, 0.82, 0.28, 24))
            .concat(ring(0.5, 0.22, 0.08, 0.07, 28))
            .concat(disc(0.5, 0.22, 0.05, 0.04, 16, 3));
    }
    if (id === '900054') {
        return ring(0.5, 0.62, 0.36, 0.16, 64)
            .concat(disc(0.5, 0.6, 0.3, 0.1, 40, 4))
            .concat(ring(0.32, 0.52, 0.08, 0.05, 20))
            .concat(ring(0.5, 0.48, 0.1, 0.06, 22))
            .concat(ring(0.68, 0.52, 0.08, 0.05, 20));
    }
    if (id === '1305690') {
        return poly([[0.22, 0.12], [0.78, 0.12], [0.78, 0.9], [0.22, 0.9], [0.22, 0.12]], 70)
            .concat(line(0.5, 0.12, 0.5, 0.9, 24))
            .concat(figure(0.62, 0.58, 0.2, 0.62, 80));
    }
    if (id === '900089') {
        return ring(0.32, 0.42, 0.28, 0.28, 80)
            .concat(disc(0.32, 0.42, 0.08, 0.08, 24, 8))
            .concat(line(0.32, 0.42, 0.32, 0.18, 18))
            .concat(line(0.32, 0.42, 0.52, 0.5, 18))
            .concat(disc(0.78, 0.62, 0.12, 0.18, 70, 12));
    }
    if (id === '26337866') {
        return poly([[0.04, 0.86], [0.18, 0.5], [0.34, 0.62], [0.52, 0.28], [0.7, 0.48], [0.96, 0.22]], 70)
            .concat(poly([[0.04, 0.92], [0.22, 0.7], [0.4, 0.78], [0.6, 0.52], [0.82, 0.68], [0.96, 0.44]], 70)
            .concat(poly([[0.02, 0.98], [0.3, 0.86], [0.58, 0.9], [0.98, 0.72]], 40)));
    }
    if (id === '26633257') {
        return line(0.62, 0.12, 0.62, 0.82, 36)
            .concat(disc(0.62, 0.18, 0.14, 0.1, 36, 9))
            .concat(ring(0.62, 0.18, 0.16, 0.12, 28))
            .concat(figure(0.38, 0.62, 0.18, 0.5, 70));
    }
    if (id === '27110296') {
        return poly([[0.12, 0.9], [0.12, 0.38], [0.5, 0.18], [0.88, 0.38], [0.88, 0.9]], 70)
            .concat(poly([[0.28, 0.46], [0.46, 0.46], [0.46, 0.7], [0.28, 0.7], [0.28, 0.46]], 36))
            .concat(disc(0.37, 0.56, 0.07, 0.08, 18, 11))
            .concat(line(0.12, 0.38, 0.88, 0.38, 20));
    }
    if (id === '900072') {
        return poly([[0.08, 0.42], [0.5, 0.12], [0.92, 0.42], [0.8, 0.42], [0.8, 0.88], [0.2, 0.88], [0.2, 0.42], [0.08, 0.42]], 110)
            .concat(poly([[0.18, 0.36], [0.78, 0.18], [0.9, 0.08]], 28));
    }
    if (id === '26657126') {
        return poly([[0.12, 0.82], [0.22, 0.28], [0.32, 0.82]], 36)
            .concat(poly([[0.4, 0.86], [0.52, 0.18], [0.64, 0.86]], 44)
            .concat(poly([[0.7, 0.82], [0.8, 0.32], [0.9, 0.82]], 32)))
            .concat(figure(0.5, 0.7, 0.16, 0.42, 50));
    }
    if (id === '27668250') {
        return poly([
            [0.3, 0.28], [0.42, 0.22], [0.4, 0.4], [0.7, 0.48],
            [0.52, 0.56], [0.58, 0.9], [0.42, 0.9], [0.4, 0.62],
            [0.18, 0.7], [0.26, 0.5], [0.3, 0.4], [0.3, 0.28]
        ], 90)
            .concat(line(0.08, 0.1, 0.2, 0.92, 16))
            .concat(line(0.5, 0.04, 0.62, 0.9, 16))
            .concat(line(0.82, 0.08, 0.94, 0.88, 16));
    }
    if (id === '1292434') {
        return poly([[0.12, 0.9], [0.12, 0.42], [0.5, 0.14], [0.88, 0.42], [0.88, 0.9], [0.12, 0.9]], 80)
            .concat(poly([[0.2, 0.5], [0.38, 0.5], [0.38, 0.72], [0.2, 0.72], [0.2, 0.5]], 28))
            .concat(poly([[0.42, 0.5], [0.58, 0.5], [0.58, 0.72], [0.42, 0.72], [0.42, 0.5]], 28))
            .concat(poly([[0.62, 0.5], [0.8, 0.5], [0.8, 0.72], [0.62, 0.72], [0.62, 0.5]], 28));
    }
    if (id === '27059130') {
        return ring(0.32, 0.72, 0.14, 0.14, 36)
            .concat(ring(0.68, 0.72, 0.14, 0.14, 36))
            .concat(poly([[0.32, 0.72], [0.42, 0.42], [0.58, 0.36], [0.68, 0.72]], 40))
            .concat(figure(0.5, 0.4, 0.16, 0.36, 40))
            .concat(ring(0.78, 0.18, 0.1, 0.08, 24));
    }
    if (id === '3993559') {
        return poly([[0.02, 0.86], [0.18, 0.52], [0.36, 0.64], [0.54, 0.28], [0.74, 0.5], [0.98, 0.36], [0.98, 0.9], [0.02, 0.9]], 90)
            .concat(line(0.72, 0.16, 0.72, 0.52, 22))
            .concat(poly([[0.72, 0.16], [0.92, 0.24], [0.72, 0.34]], 28));
    }
    if (id === '30292777') {
        return poly([[0.08, 0.06], [0.62, 0.06], [0.38, 0.94], [0.02, 0.94], [0.08, 0.06]], 70)
            .concat(figure(0.58, 0.62, 0.2, 0.46, 70));
    }
    if (id === '34805873') {
        return ring(0.5, 0.62, 0.28, 0.16, 48)
            .concat(disc(0.5, 0.6, 0.22, 0.1, 28, 21))
            .concat(poly([[0.42, 0.48], [0.38, 0.22], [0.46, 0.3], [0.5, 0.14], [0.54, 0.32], [0.62, 0.2], [0.58, 0.48]], 48));
    }
    if (id === '37116446') {
        return poly([[0.18, 0.28], [0.5, 0.1], [0.82, 0.28], [0.82, 0.86], [0.18, 0.86], [0.18, 0.28]], 70)
            .concat(line(0.18, 0.28, 0.5, 0.48, 24))
            .concat(line(0.82, 0.28, 0.5, 0.48, 24))
            .concat(line(0.3, 0.62, 0.7, 0.62, 16))
            .concat(line(0.3, 0.72, 0.62, 0.72, 14));
    }
    return [];
}

function motifBox(width, height) {
    const mobile = width <= 768;
    return {
        x: width * (mobile ? 0.18 : 0.28),
        y: height * (mobile ? 0.2 : 0.16),
        w: width * (mobile ? 0.64 : 0.44),
        h: height * (mobile ? 0.3 : 0.38)
    };
}

function mapBox(point, box) {
    return {
        x: box.x + point.x * box.w,
        y: box.y + point.y * box.h
    };
}

export function waveFilmMotifIds() {
    return MOTIF_IDS.slice();
}

export function sampleFilmMotif(movieId, width, height, count) {
    const id = String(movieId || '');
    const unit = motifUnit(id);
    if (!unit.length || !count) return [];
    const box = motifBox(width, height);
    const mapped = unit.map(point => mapBox(point, box));
    if (mapped.length >= count) {
        const step = mapped.length / count;
        const out = [];
        for (let i = 0; i < count; i += 1) {
            out.push(mapped[Math.min(mapped.length - 1, Math.floor(i * step))]);
        }
        return out;
    }
    const out = mapped.slice();
    let extra = 0;
    while (out.length < count) {
        const src = mapped[out.length % mapped.length];
        const j = extra + id.length;
        out.push({
            x: src.x + (hash01(j, 3) - 0.5) * 5,
            y: src.y + (hash01(j, 4) - 0.5) * 5
        });
        extra += 1;
    }
    return out;
}

export function motifCentroid(points) {
    if (!points.length) return { x: 0, y: 0 };
    let x = 0;
    let y = 0;
    for (let i = 0; i < points.length; i += 1) {
        x += points[i].x;
        y += points[i].y;
    }
    return { x: x / points.length, y: y / points.length };
}

export function particleSparkle(seed01, time, phase, reduced) {
    const seed = Math.max(0, Math.min(1, Number(seed01) || 0));
    if (reduced) return { twinkle: false, flash: 0.82 };
    const twinkle = seed > 0.84;
    const rate = twinkle ? 5.4 + seed * 8.2 : 1.7 + seed * 1.8;
    const beat = 0.5 + 0.5 * Math.sin((Number(time) || 0) * rate + (Number(phase) || 0));
    const flash = twinkle ? beat * beat * beat : 0.58 + 0.42 * beat;
    return { twinkle, flash: Math.max(0, Math.min(1, flash)) };
}
