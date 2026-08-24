import { SPARKLE_STAR_PATH, DIAMOND_STAR_PATH } from './star-shape.js';

export { DIAMOND_STAR_PATH, SPARKLE_STAR_PATH };

const STAR_TIERS = {
    // Province film markers. 7.8+ = primary glow (Douban-style highlight).
    // Dataset contains many dialect films ≥7.8 (esp. Cantonese), so primary is populated.
    primary: {
        minRating: 7.8,
        size: 17,
        shadowSize: 20,
        color: '#F0D7A8',
        borderColor: '#fff4d6',
        shadowColor: 'rgba(240,215,168,0.45)',
        glowColor: 'rgba(240,215,168,0.55)',
    },
    secondary: {
        minRating: 7.3,
        size: 13,
        shadowSize: 15,
        color: '#d4a574',
        borderColor: '#e8c896',
        shadowColor: 'rgba(212,165,116,0.35)',
        glowColor: 'rgba(212,165,116,0.4)',
    },
};

const PROVINCE_AREA_COLORS = {
    heilongjiang: '#1a2d3d',
    jilin: '#1c3040',
    liaoning: '#1e3238',
    inner_mongolia: '#2a2418',
    xinjiang: '#2e2818',
    tibet: '#252038',
    qinghai: '#282238',
    gansu: '#2a2618',
    ningxia: '#2a241c',
    shaanxi: '#2a2418',
    shanxi: '#1e2818',
    hebei: '#1e2c22',
    beijing: '#243028',
    tianjin: '#243228',
    shandong: '#1a3228',
    henan: '#1e3020',
    jiangsu: '#1a3438',
    anhui: '#1e3228',
    shanghai: '#1a3a48',
    zhejiang: '#1a3638',
    fujian: '#1a3830',
    jiangxi: '#1e3428',
    hubei: '#1e3224',
    hunan: '#1e3428',
    guangdong: '#1a3830',
    guangxi: '#1e3630',
    hainan: '#1a3838',
    chongqing: '#2c2a28',
    sichuan: '#283028',
    guizhou: '#243430',
    yunnan: '#2a2838',
    hongkong: '#1a3538',
    macau: '#1a3535',
    taiwan: '#1a3838',
};

const DEFAULT_AREA_COLOR = '#1a2f23';

const EMPHASIS_AREA_COLOR = '#2d4a3e';

export const PROVINCE_LABEL = {
    show: true,
    color: '#F0D7A8',
    fontFamily: '"Noto Serif SC", "Source Han Serif SC", serif',
    fontSize: 13,
    fontWeight: 500,
    textBorderColor: 'rgba(5,5,7,0.65)',
    textBorderWidth: 2,
    textShadowColor: 'rgba(240,215,168,0.35)',
    textShadowBlur: 6,
};

export const SAR_ALWAYS_LABEL = new Set(['hongkong', 'macau', 'taiwan']);

export function getProvinceAreaColor(provinceId) {
    return PROVINCE_AREA_COLORS[provinceId] || DEFAULT_AREA_COLOR;
}

function getProvinceHoverColor(provinceId) {
    const base = PROVINCE_AREA_COLORS[provinceId] || DEFAULT_AREA_COLOR;
    if (base === DEFAULT_AREA_COLOR) return lightenHex(EMPHASIS_AREA_COLOR, 0.08);
    return lightenHex(base, 0.22);
}

function getProvinceSelectedColor(provinceId) {
    const base = PROVINCE_AREA_COLORS[provinceId] || DEFAULT_AREA_COLOR;
    if (base === DEFAULT_AREA_COLOR) return lightenHex(EMPHASIS_AREA_COLOR, 0.16);
    return lightenHex(base, 0.30);
}

export function getProvinceEmphasisColor(provinceId) {
    return getProvinceHoverColor(provinceId);
}

export function buildBaseRegionItemStyle(provinceId) {
    const isSar = SAR_ALWAYS_LABEL.has(provinceId);
    return {
        areaColor: getProvinceAreaColor(provinceId),
        borderColor: 'rgba(240,215,168,0.28)',
        borderWidth: isSar ? 1.1 : 0.85,
    };
}

export function buildProvinceActiveItemStyle(provinceId, mode) {
    const isSelected = mode === 'selected';
    return {
        areaColor: isSelected ? getProvinceSelectedColor(provinceId) : getProvinceHoverColor(provinceId),
        borderColor: isSelected ? 'rgba(240,215,168,0.9)' : 'rgba(240,215,168,0.85)',
        borderWidth: isSelected ? 2.6 : 2,
        shadowBlur: isSelected ? 18 : 10,
        shadowColor: isSelected ? 'rgba(240,215,168,0.4)' : 'rgba(240,215,168,0.25)',
        shadowOffsetY: isSelected ? 4 : 2,
    };
}

export function buildProvinceRegionLabel(shortName, { show = true, fontSize = 13, fontWeight = 500 } = {}) {
    return {
        ...PROVINCE_LABEL,
        show,
        fontSize,
        fontWeight,
        formatter: () => shortName,
    };
}

function lightenHex(hex, amount) {
    const n = parseInt(hex.slice(1), 16);
    const r = Math.min(255, ((n >> 16) & 0xff) + Math.round(255 * amount));
    const g = Math.min(255, ((n >> 8) & 0xff) + Math.round(255 * amount));
    const b = Math.min(255, (n & 0xff) + Math.round(255 * amount));
    return `#${((r << 16) | (g << 8) | b).toString(16).padStart(6, '0')}`;
}

export function getStarTier(film) {
    const rating = film?.rating || 0;
    if (rating >= STAR_TIERS.primary.minRating) return 'primary';
    if (rating >= STAR_TIERS.secondary.minRating) return 'secondary';
    return null;
}

export function pickFeaturedFilm(prov) {
    const films = prov?.films || [];
    if (!films.length) return null;

    if (prov.featuredFilmId) {
        const picked = films.find((f) => String(f.id) === String(prov.featuredFilmId));
        if (picked) return picked;
    }

    const sorted = [...films].sort((a, b) => (b.rating || 0) - (a.rating || 0));
    const top = sorted[0];
    return getStarTier(top) ? top : null;
}

export function buildGeoRegions(provinces, geoNameById) {
    return Object.entries(provinces).map(([id, prov]) => {
        const geoName = geoNameById[id];
        if (!geoName) return null;
        const isSar = SAR_ALWAYS_LABEL.has(id);
        const shortName = prov?.name || '';
        return {
            name: geoName,
            label: isSar
                ? buildProvinceRegionLabel(shortName, { show: true, fontSize: 10, fontWeight: 600 })
                : { show: false },
            itemStyle: buildBaseRegionItemStyle(id),
        };
    }).filter(Boolean);
}

export function buildFeaturedMarkers(provinces, centers) {
    const body = [];
    const glow = [];

    Object.entries(provinces).forEach(([pid, prov]) => {
        const center = centers[pid];
        const film = pickFeaturedFilm(prov);
        if (!center || !film) return;

        const tier = getStarTier(film);
        if (!tier) return;

        const style = STAR_TIERS[tier];

        const base = {
            name: film.title,
            film,
            province: prov,
            tier,
            symbol: SPARKLE_STAR_PATH,
        };

        body.push({
            ...base,
            value: [center[0], center[1], film.rating || 0],
            symbolSize: style.size,
            baseSymbolSize: style.size,
            itemStyle: {
                color: style.color,
                borderColor: style.borderColor,
                borderWidth: 1,
                shadowBlur: tier === 'primary' ? 16 : 10,
                shadowColor: style.glowColor,
            },
            label: {
                show: false,
                formatter: () => `《${film.title}》 ${film.rating != null ? film.rating.toFixed(1) : ''}`,
                color: '#F0D7A8',
                fontSize: 11,
                fontWeight: 600,
                position: 'top',
                distance: 8,
                backgroundColor: 'rgba(5,5,7,0.72)',
                padding: [4, 8],
                borderRadius: 4,
            },
            emphasis: {
                scale: 1.2,
                label: { show: true },
                itemStyle: {
                    shadowBlur: 22,
                    shadowColor: style.glowColor,
                },
            },
        });

        if (tier === 'primary') {
            glow.push({
                ...base,
                value: [center[0], center[1], film.rating || 0],
                symbolSize: style.size + 2,
                baseSymbolSize: style.size + 2,
                itemStyle: {
                    color: style.glowColor,
                    borderColor: 'transparent',
                    opacity: 0.35,
                },
            });
        }
    });

    return { body, glow };
}
