import { escapeHtml } from '../lib/dom.js';

const SKIP_LAND_LINK = new Set(['方言', '手语', '普通话']);

export function buildLangLandIndex(provinces) {
    const index = new Map();
    Object.values(provinces || {}).forEach((prov) => {
        (prov.languages || []).forEach((name) => {
            if (!name || SKIP_LAND_LINK.has(name)) return;
            if (!index.has(name)) index.set(name, []);
            const list = index.get(name);
            if (!list.some((item) => item.id === prov.id)) {
                list.push({ id: prov.id, name: prov.name });
            }
        });
    });
    return index;
}

export function findLandsForLanguage(lang, index) {
    const name = typeof lang === 'string' ? lang : (lang?.name || lang?.id || '');
    const aliases = typeof lang === 'object' ? (lang.aliases || []) : [];
    if (!name || SKIP_LAND_LINK.has(name) || !index) return [];
    const seen = new Set();
    const lands = [];
    [name, ...aliases].forEach((key) => {
        if (!key || SKIP_LAND_LINK.has(key)) return;
        (index.get(key) || []).forEach((item) => {
            if (seen.has(item.id)) return;
            seen.add(item.id);
            lands.push(item);
        });
    });
    return lands;
}

export function landLinkMarkup(lands) {
    if (!lands || !lands.length) return '';
    const buttons = lands.map((item) => (
        `<button type="button" class="land-link" data-province-id="${escapeHtml(item.id)}">${escapeHtml(item.name)}</button>`
    )).join('');
    return `<div class="land-links">${buttons}</div>`;
}
