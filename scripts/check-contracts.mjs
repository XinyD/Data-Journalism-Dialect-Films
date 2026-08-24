import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');

const LANGUAGE_DISPLAY_ORDER = [0, 1, 4, 2, 3, 5];
const LANGUAGE_LABELS = ['英语', '日语', '普通话', '方言', '韩语', '其他'];
const FLOP_CASE_IDS = ['26796665', '22557335', '6068516', '3874981'];
const DECADE_VALUES = ['2020s', '2010s', '2000s', '1990s', 'Pre-1990s'];
const REGION_VALUES = ['North_America', 'Europe', 'East_Asia', 'China', 'Other'];
const HTML_MANIFEST_KEYS = {
    'frontend/index.html': ['style', 'echartsMain', 'app'],
    'frontend/vol1_time.html': ['style', 'echartsVolume', 'vol1'],
    'frontend/vol2_geo.html': ['style', 'echartsVolume', 'vol2'],
    'frontend/vol3_lang.html': ['style', 'echartsVolume', 'vol3'],
    'frontend/vol4_memory.html': ['style', 'vol4']
};

function read(relPath) {
    return readFileSync(join(root, relPath), 'utf8');
}

function extractOptionValues(html, selectId) {
    const selectPattern = new RegExp(`<select[^>]*id="${selectId}"[\\s\\S]*?</select>`);
    const match = html.match(selectPattern);
    if (!match) throw new Error(`Missing <select id="${selectId}"> in HTML`);
    const values = [...match[0].matchAll(/<option value="([^"]+)"/g)].map(item => item[1]);
    return values.filter(value => value.toLowerCase() !== 'all');
}

function assertSame(label, actual, expected) {
    const same = actual.length === expected.length
        && actual.every((value, index) => value === expected[index]);
    if (!same) {
        throw new Error(
            `${label} option order mismatch.\nExpected: ${expected.join(', ')}\nActual: ${actual.join(', ')}`
        );
    }
}

function extractFlopCaseIds(html) {
    return [...html.matchAll(/data-movie-id="(\d+)"/g)]
        .map(item => item[1])
        .filter(id => FLOP_CASE_IDS.includes(id));
}

const indexHtml = read('frontend/index.html');
const vol4Html = read('frontend/vol4_memory.html');
const expectedLanguageValues = LANGUAGE_DISPLAY_ORDER.map(code => String(code));

for (const [label, html] of [
    ['index.html', indexHtml],
    ['vol4_memory.html', vol4Html]
]) {
    assertSame(`${label} filter-language`, extractOptionValues(html, 'filter-language'), expectedLanguageValues);
    assertSame(`${label} filter-decade`, extractOptionValues(html, 'filter-decade'), DECADE_VALUES);
    assertSame(`${label} filter-region`, extractOptionValues(html, 'filter-region'), REGION_VALUES);
}

const indexFlopIds = extractFlopCaseIds(indexHtml);
if (indexFlopIds.length !== FLOP_CASE_IDS.length
    || !FLOP_CASE_IDS.every(id => indexFlopIds.includes(id))) {
    throw new Error(`index.html flop case IDs mismatch: ${indexFlopIds.join(', ')}`);
}

const appJs = read('frontend/js/app.js');
for (const id of FLOP_CASE_IDS) {
    if (!appJs.includes(`movieId: '${id}'`)) {
        throw new Error(`app.js missing flop case movieId ${id}`);
    }
}

const manifest = JSON.parse(read('frontend/build/manifest.json'));
for (const [htmlPath, keys] of Object.entries(HTML_MANIFEST_KEYS)) {
    const html = read(htmlPath);
    for (const key of keys) {
        const href = manifest[key];
        if (!href) throw new Error(`manifest.json missing ${key}`);
        if (!html.includes(href)) {
            throw new Error(`${htmlPath} is missing hashed asset ${key} (${href})`);
        }
    }
}

console.log({
    languageOptions: expectedLanguageValues.map((value, index) => `${value} ${LANGUAGE_LABELS[LANGUAGE_DISPLAY_ORDER[index]]}`),
    decadeOptions: DECADE_VALUES,
    regionOptions: REGION_VALUES,
    flopCaseIds: FLOP_CASE_IDS,
    hashedAssets: Object.fromEntries(
        Object.entries(HTML_MANIFEST_KEYS).map(([page, keys]) => [page, keys.map(key => manifest[key])])
    )
});
