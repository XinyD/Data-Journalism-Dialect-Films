const DATA_URL = './data/story_universe.json';
const GEO_URL = './data/china_provinces.json';

import {
    buildFeaturedMarkers,
    buildGeoRegions,
    buildBaseRegionItemStyle,
    buildProvinceActiveItemStyle,
    buildProvinceRegionLabel,
    SAR_ALWAYS_LABEL,
    SPARKLE_STAR_PATH,
} from './map-markers.js';
import { buildScreenLangStars } from './lang-star-layout.js';
import { createLangStarOverlay } from './lang-star-overlay.js';

const GEO_TO_ID = {
    '北京市': 'beijing',
    '天津市': 'tianjin',
    '河北省': 'hebei',
    '山西省': 'shanxi',
    '内蒙古自治区': 'inner_mongolia',
    '辽宁省': 'liaoning',
    '吉林省': 'jilin',
    '黑龙江省': 'heilongjiang',
    '上海市': 'shanghai',
    '江苏省': 'jiangsu',
    '浙江省': 'zhejiang',
    '安徽省': 'anhui',
    '福建省': 'fujian',
    '江西省': 'jiangxi',
    '山东省': 'shandong',
    '河南省': 'henan',
    '湖北省': 'hubei',
    '湖南省': 'hunan',
    '广东省': 'guangdong',
    '广西壮族自治区': 'guangxi',
    '海南省': 'hainan',
    '重庆市': 'chongqing',
    '四川省': 'sichuan',
    '贵州省': 'guizhou',
    '云南省': 'yunnan',
    '西藏自治区': 'tibet',
    '陕西省': 'shaanxi',
    '甘肃省': 'gansu',
    '青海省': 'qinghai',
    '宁夏回族自治区': 'ningxia',
    '新疆维吾尔自治区': 'xinjiang',
    '香港特别行政区': 'hongkong',
    '澳门特别行政区': 'macau',
    '台湾省': 'taiwan',
};

const ID_TO_GEO = Object.fromEntries(
    Object.entries(GEO_TO_ID).map(([geo, id]) => [id, geo]),
);

const SAR_PINS = [
    { label: '香港', geoName: '香港特别行政区', id: 'hongkong', value: [114.17, 22.32] },
    { label: '澳门', geoName: '澳门特别行政区', id: 'macau', value: [113.54, 22.19] },
    { label: '台湾', geoName: '台湾省', id: 'taiwan', value: [121.2, 23.9] },
];

const ASSET_TABS = [
    { key: 'languages', label: '语言' },
    { key: 'culture', label: '文化' },
    { key: 'folk', label: '风俗' },
    { key: 'food', label: '美食' },
    { key: 'history', label: '历史' },
    { key: 'myth', label: '神话' },
    { key: 'scenery', label: '风景' },
];

const DEFAULT_GEO_ZOOM = 1.28;
const CHINA_BOUNDING_COORDS = [[73, 16], [135, 54]];
const CHINA_BBOX_FALLBACK = { minLng: 73, maxLng: 135, minLat: 18, maxLat: 54 };
const FILM_HIT_PAD = 6;

let languageCatalog = [];

function walkCoords(coords, visitor) {
    if (!coords) return;
    if (typeof coords[0] === 'number') {
        visitor(coords[0], coords[1]);
        return;
    }
    coords.forEach((c) => walkCoords(c, visitor));
}

function computeChinaBBox(geo) {
    let minLng = Infinity;
    let maxLng = -Infinity;
    let minLat = Infinity;
    let maxLat = -Infinity;

    (geo?.features || []).forEach((feature) => {
        walkCoords(feature.geometry?.coordinates, (lng, lat) => {
            if (!Number.isFinite(lng) || !Number.isFinite(lat)) return;
            minLng = Math.min(minLng, lng);
            maxLng = Math.max(maxLng, lng);
            minLat = Math.min(minLat, lat);
            maxLat = Math.max(maxLat, lat);
        });
    });

    if (!Number.isFinite(minLng)) return { ...CHINA_BBOX_FALLBACK };
    return { minLng, maxLng, minLat, maxLat };
}

function getMapScreenRect(chart, container, overlayAnchor, geo) {
    const bbox = computeChinaBBox(geo);
    const corners = [
        [bbox.minLng, bbox.maxLat],
        [bbox.maxLng, bbox.maxLat],
        [bbox.maxLng, bbox.minLat],
        [bbox.minLng, bbox.minLat],
    ];

    let minX = Infinity;
    let maxX = -Infinity;
    let minY = Infinity;
    let maxY = -Infinity;

    corners.forEach((lngLat) => {
        const pixel = chart.convertToPixel({ geoIndex: 0 }, lngLat);
        if (!pixel || !Number.isFinite(pixel[0]) || !Number.isFinite(pixel[1])) return;
        minX = Math.min(minX, pixel[0]);
        maxX = Math.max(maxX, pixel[0]);
        minY = Math.min(minY, pixel[1]);
        maxY = Math.max(maxY, pixel[1]);
    });

    if (!Number.isFinite(minX)) {
        return { left: 0, top: 0, width: 0, height: 0, cx: 0, cy: 0 };
    }

    const wrapRect = container.getBoundingClientRect();
    const anchorRect = overlayAnchor.getBoundingClientRect();
    const left = wrapRect.left - anchorRect.left + minX;
    const top = wrapRect.top - anchorRect.top + minY;
    const width = maxX - minX;
    const height = maxY - minY;

    return {
        left,
        top,
        width,
        height,
        cx: left + width / 2,
        cy: top + height / 2,
    };
}

function getGeoZoom(chart) {
    const geo = chart.getOption()?.geo;
    const entry = Array.isArray(geo) ? geo[0] : geo;
    return entry?.zoom ?? DEFAULT_GEO_ZOOM;
}

export async function loadMapData() {
    const [storyRes, geoRes] = await Promise.all([
        fetch(DATA_URL),
        fetch(GEO_URL),
    ]);
    if (!storyRes.ok) throw new Error(`story_universe.json ${storyRes.status}`);
    if (!geoRes.ok) throw new Error(`china_provinces.json ${geoRes.status}`);
    const story = await storyRes.json();
    const geo = await geoRes.json();
    const centers = {};
    geo.features.forEach((f) => {
        const id = GEO_TO_ID[f.properties.name];
        if (id && f.properties.center) centers[id] = f.properties.center;
    });
    SAR_PINS.forEach((pin) => {
        centers[pin.id] = pin.value;
    });
    const provinces = Object.fromEntries((story.provinces || []).map(p => [p.id, p]));
    const languages = story.languages || [];
    languageCatalog = Array.isArray(languages) ? languages : [];
    return { geo, provinces, centers, languages };
}

export function createChinaMap(container, data, hooks, options = {}) {
    if (!window.echarts) throw new Error('ECharts 未加载');
    const chart = window.echarts.init(container, null, { renderer: 'canvas' });
    if (typeof window.echarts.registerMap !== 'function') {
        throw new Error('ECharts 缺少地图组件（GeoComponent）');
    }
    window.echarts.registerMap('china_story', data.geo);

    const onMapWheel = (e) => {
        e.preventDefault();
    };
    container.addEventListener('wheel', onMapWheel, { passive: false });

    let selectedGeoName = null;
    let hoveredGeoName = null;
    let savedMapView = null;
    const reducedMotion = options.reducedMotion || false;

    const { body: filmBody, glow: filmGlow } = buildFeaturedMarkers(data.provinces, data.centers);
    const geoRegions = buildGeoRegions(data.provinces, ID_TO_GEO);
    const baseGeoRegions = geoRegions.map((region) => ({
        name: region.name,
        itemStyle: { ...region.itemStyle },
        label: { ...region.label },
    }));

    const langMarkers = buildScreenLangStars(data.languages || []);
    const langOverlay = options.overlayAnchor
        ? createLangStarOverlay(options.overlayAnchor, langMarkers, {
            onLangStar: hooks.onLangStar,
            onLangStarHover: hooks.onLangStarHover,
            onLangStarLeave: hooks.onLangStarLeave,
        }, { reducedMotion })
        : null;

    const option = {
        backgroundColor: 'transparent',
        geo: {
            map: 'china_story',
            roam: true,
            zoom: DEFAULT_GEO_ZOOM,
            scaleLimit: { min: 0.7, max: 6 },
            layoutCenter: ['50%', '52%'],
            layoutSize: '96%',
            boundingCoords: CHINA_BOUNDING_COORDS,
            selectedMode: 'single',
            label: { show: false },
            itemStyle: {
                areaColor: '#1a2f23',
                borderColor: 'rgba(240,215,168,0.28)',
                borderWidth: 0.85,
            },
            emphasis: {
                itemStyle: {
                    areaColor: '#2d4a3e',
                    borderColor: 'rgba(240,215,168,0.85)',
                    borderWidth: 2,
                },
                label: { show: true, color: '#F0D7A8', fontSize: 12, fontWeight: 600 },
            },
            select: {
                itemStyle: {
                    areaColor: '#2d4a3e',
                    borderColor: 'rgba(240,215,168,0.9)',
                    borderWidth: 2.4,
                },
                label: { show: true, color: '#F0D7A8', fontSize: 12, fontWeight: 600 },
            },
            regions: geoRegions,
        },
        series: [
            {
                id: 'stars-glow',
                type: 'effectScatter',
                coordinateSystem: 'geo',
                data: filmGlow,
                symbol: SPARKLE_STAR_PATH,
                symbolSize: (val, params) => params.data.symbolSize || 20,
                z: 5,
                rippleEffect: {
                    brushType: 'stroke',
                    scale: 1.2,
                    period: 5,
                    number: 2,
                },
                silent: true,
                emphasis: { disabled: true },
            },
            {
                id: 'stars-body',
                type: 'scatter',
                coordinateSystem: 'geo',
                data: filmBody,
                symbol: SPARKLE_STAR_PATH,
                symbolSize: (val, params) => params.data.symbolSize || 14,
                z: 6,
                cursor: 'pointer',
                animation: false,
            },
        ],
        tooltip: { show: false },
    };

    chart.setOption(option);

    function syncLangOverlay() {
        if (!langOverlay || !options.overlayAnchor) return;
        langOverlay.syncToMap(
            getMapScreenRect(chart, container, options.overlayAnchor, data.geo),
            getGeoZoom(chart),
        );
    }

    requestAnimationFrame(syncLangOverlay);

    function getGeoOption() {
        const geo = chart.getOption()?.geo;
        return Array.isArray(geo) ? geo[0] : geo;
    }

    function buildDefaultRegionStyle(geoName) {
        const id = GEO_TO_ID[geoName];
        if (!id) {
            return { itemStyle: {}, label: { show: false } };
        }
        const isSar = SAR_ALWAYS_LABEL.has(id);
        const shortName = data.provinces[id]?.name || '';
        return {
            itemStyle: buildBaseRegionItemStyle(id),
            label: isSar
                ? buildProvinceRegionLabel(shortName, { show: true, fontSize: 10, fontWeight: 600 })
                : { show: false },
        };
    }

    function buildActiveRegionStyle(provinceId, mode) {
        const shortName = data.provinces[provinceId]?.name || '';
        return {
            itemStyle: buildProvinceActiveItemStyle(provinceId, mode),
            label: buildProvinceRegionLabel(shortName, true),
        };
    }

    function syncProvinceRegionStyles() {
        chart.setOption({
            geo: {
                regions: baseGeoRegions.map((region) => {
                    const id = GEO_TO_ID[region.name];
                    if (region.name === selectedGeoName) {
                        return { name: region.name, ...buildActiveRegionStyle(id, 'selected') };
                    }
                    if (region.name === hoveredGeoName) {
                        return { name: region.name, ...buildActiveRegionStyle(id, 'hover') };
                    }
                    return { name: region.name, ...buildDefaultRegionStyle(region.name) };
                }),
            },
        }, { lazyUpdate: false });
    }

    function focusProvinceView(geoName) {
        const id = GEO_TO_ID[geoName];
        const center = data.centers[id];
        if (!center) return;

        const geo = getGeoOption();
        if (!savedMapView) {
            const currentCenter = geo?.center;
            savedMapView = {
                center: Array.isArray(currentCenter) ? [...currentCenter] : undefined,
                zoom: geo?.zoom ?? DEFAULT_GEO_ZOOM,
            };
        }

        const currentZoom = geo?.zoom ?? DEFAULT_GEO_ZOOM;
        chart.setOption({
            geo: {
                center: [...center],
                zoom: Math.min(currentZoom * 1.06, 6),
                animationDurationUpdate: 450,
                animationEasingUpdate: 'cubicOut',
            },
        });

        requestAnimationFrame(syncLangOverlay);
        window.setTimeout(syncLangOverlay, 500);
    }

    function restoreMapView() {
        if (!savedMapView) return;
        chart.setOption({
            geo: {
                ...savedMapView,
                animationDurationUpdate: 400,
                animationEasingUpdate: 'cubicOut',
            },
        });
        savedMapView = null;
        requestAnimationFrame(syncLangOverlay);
        window.setTimeout(syncLangOverlay, 450);
    }

    function setHoverProvince(geoName) {
        const next = geoName || null;
        if (next === hoveredGeoName) return;
        hoveredGeoName = next;
        syncProvinceRegionStyles();
    }

    function selectProvince(geoName, { focus = true } = {}) {
        if (!geoName) return;
        selectedGeoName = geoName;
        if (focus) focusProvinceView(geoName);
        syncProvinceRegionStyles();
    }

    function highlightProvince(geoName, options) {
        selectProvince(geoName, options);
    }

    function clearHighlight() {
        hoveredGeoName = null;
        if (selectedGeoName) {
            selectedGeoName = null;
            restoreMapView();
        }
        syncProvinceRegionStyles();
    }

    function geoToScreen(lngLat) {
        const pixel = chart.convertToPixel({ geoIndex: 0 }, lngLat);
        if (!pixel || !Number.isFinite(pixel[0]) || !Number.isFinite(pixel[1])) {
            return null;
        }
        const rect = container.getBoundingClientRect();
        return {
            x: rect.left + pixel[0],
            y: rect.top + pixel[1],
            visible: true,
        };
    }

    function flyToProvince(provinceId, { zoom = 1.75, duration = 700 } = {}) {
        const center = data.centers[provinceId];
        const geoName = ID_TO_GEO[provinceId];
        if (!center || !geoName) return;

        savedMapView = null;

        chart.setOption({
            geo: {
                center: [...center],
                zoom,
                animationDurationUpdate: duration,
                animationEasingUpdate: 'cubicOut',
            },
        });

        highlightProvince(geoName, { focus: false });

        const syncAfterFly = () => syncLangOverlay();
        requestAnimationFrame(syncAfterFly);
        window.setTimeout(syncAfterFly, duration + 50);
    }

    function pickGeoNameAt(x, y) {
        const lnglat = chart.convertFromPixel({ geoIndex: 0 }, [x, y]);
        if (!lnglat || !Number.isFinite(lnglat[0]) || !Number.isFinite(lnglat[1])) {
            return null;
        }

        const coordSys = chart.getModel()?.getComponent('geo', 0)?.coordinateSystem;
        if (coordSys) {
            const regions = coordSys.regions || [];
            for (let i = 0; i < regions.length; i += 1) {
                const region = regions[i];
                if (region.contain && region.contain(lnglat)) {
                    return region.name;
                }
            }
        }

        let bestName = null;
        let bestDist = Infinity;
        const threshold = 2.8;

        Object.entries(data.centers).forEach(([provinceId, center]) => {
            const geoName = ID_TO_GEO[provinceId];
            if (!geoName || !center || center.length < 2) return;
            const dist = Math.hypot(lnglat[0] - center[0], lnglat[1] - center[1]);
            if (dist < bestDist && dist < threshold) {
                bestDist = dist;
                bestName = geoName;
            }
        });

        return bestName;
    }

    function pickFilmAt(x, y) {
        let best = null;
        let bestDist = Infinity;

        for (const item of filmBody) {
            if (!item.film) continue;
            const lngLat = item.value;
            if (!lngLat || lngLat.length < 2) continue;

            const pixel = chart.convertToPixel({ geoIndex: 0 }, lngLat);
            if (!pixel || !Number.isFinite(pixel[0]) || !Number.isFinite(pixel[1])) continue;

            const size = item.baseSymbolSize || item.symbolSize || 14;
            const radius = size / 2 + FILM_HIT_PAD;
            const dist = Math.hypot(x - pixel[0], y - pixel[1]);

            if (dist <= radius && dist < bestDist) {
                bestDist = dist;
                best = item;
            }
        }

        return best;
    }

    function openProvinceByGeoName(geoName, params) {
        const id = GEO_TO_ID[geoName];
        if (!id || !data.provinces[id]) return false;
        selectProvince(geoName, { focus: false });
        hooks.onProvince(data.provinces[id], geoName, params);
        return true;
    }

    let hoverRaf = 0;
    let pendingHover = null;

    function routeMapHover(x, y) {
        if (!Number.isFinite(x) || !Number.isFinite(y)) {
            setHoverProvince(null);
            return;
        }
        if (pickFilmAt(x, y)) {
            setHoverProvince(null);
            return;
        }
        setHoverProvince(pickGeoNameAt(x, y));
    }

    const onContainerMouseMove = (event) => {
        const rect = container.getBoundingClientRect();
        pendingHover = {
            x: event.clientX - rect.left,
            y: event.clientY - rect.top,
        };
        if (hoverRaf) return;
        hoverRaf = requestAnimationFrame(() => {
            hoverRaf = 0;
            if (!pendingHover) return;
            routeMapHover(pendingHover.x, pendingHover.y);
            pendingHover = null;
        });
    };

    const onContainerMouseLeave = () => {
        pendingHover = null;
        if (hoverRaf) {
            cancelAnimationFrame(hoverRaf);
            hoverRaf = 0;
        }
        setHoverProvince(null);
    };

    let lastClickKey = '';
    let lastClickTs = 0;

    function shouldSkipDuplicateClick(x, y) {
        const key = `${Math.round(x)}:${Math.round(y)}`;
        const now = Date.now();
        if (key === lastClickKey && now - lastClickTs < 50) {
            return true;
        }
        lastClickKey = key;
        lastClickTs = now;
        return false;
    }

    function getChartOffsetFromEvent(rawEvent) {
        if (rawEvent?.offsetX != null && rawEvent?.offsetY != null) {
            return [rawEvent.offsetX, rawEvent.offsetY];
        }
        if (rawEvent?.clientX != null && rawEvent?.clientY != null) {
            const rect = container.getBoundingClientRect();
            return [rawEvent.clientX - rect.left, rawEvent.clientY - rect.top];
        }
        return null;
    }

    function routeMapClick(x, y, rawEvent, geoNameHint = null) {
        if (!Number.isFinite(x) || !Number.isFinite(y)) return;
        if (shouldSkipDuplicateClick(x, y)) return;

        const filmHit = pickFilmAt(x, y);
        if (filmHit) {
            hooks.onFilm(filmHit.film, filmHit.province);
            return;
        }

        const geoName = geoNameHint || pickGeoNameAt(x, y);
        if (geoName && openProvinceByGeoName(geoName, { event: rawEvent })) {
            return;
        }

        hooks.onMapBlankClick?.();
    }

    const onContainerClick = (event) => {
        const rect = container.getBoundingClientRect();
        routeMapClick(
            event.clientX - rect.left,
            event.clientY - rect.top,
            event,
        );
    };

    container.addEventListener('click', onContainerClick);
    container.addEventListener('mousemove', onContainerMouseMove);
    container.addEventListener('mouseleave', onContainerMouseLeave);

    chart.on('click', (params) => {
        const offset = getChartOffsetFromEvent(params?.event?.event || params?.event);
        if (!offset) return;

        if (params.componentType === 'series' && params.data?.film) {
            if (shouldSkipDuplicateClick(offset[0], offset[1])) return;
            hooks.onFilm(params.data.film, params.data.province);
            return;
        }

        const geoNameHint = params.componentType === 'geo' ? params.name : null;
        routeMapClick(offset[0], offset[1], params.event?.event || params.event, geoNameHint);
    });

    chart.getZr().on('click', (event) => {
        routeMapClick(event.offsetX, event.offsetY, event);
    });

    chart.on('georoam', () => {
        syncLangOverlay();
        hooks.onGeoRoam?.();
    });

    let filmRaf = 0;
    let filmMotionActive = false;

    function heartbeatScale(t, phase = 0) {
        const cycleMs = 1300;
        const u = ((t + phase * 180) % cycleMs) / cycleMs;
        let scale = 1;
        if (u < 0.14) {
            scale += 0.13 * Math.sin((u / 0.14) * Math.PI);
        } else if (u >= 0.2 && u < 0.32) {
            scale += 0.09 * Math.sin(((u - 0.2) / 0.12) * Math.PI);
        } else {
            scale += 0.015 * Math.sin(u * Math.PI * 4);
        }
        return scale;
    }

    function resetFilmStarMotion() {
        chart.setOption({
            series: [
                { id: 'stars-glow', data: filmGlow },
                { id: 'stars-body', data: filmBody },
            ],
        }, { lazyUpdate: true });
    }

    function animateFilmStarsHeartbeat(t) {
        if (!filmMotionActive) return;

        const bodyData = filmBody.map((item, index) => {
            const scale = heartbeatScale(t, index * 0.5);
            const base = item.baseSymbolSize || item.symbolSize;
            return {
                ...item,
                symbolSize: base * scale,
            };
        });

        const glowData = filmGlow.map((item) => {
            const bodyIndex = filmBody.findIndex((bodyItem) => bodyItem.province?.id === item.province?.id);
            const scale = heartbeatScale(t, (bodyIndex >= 0 ? bodyIndex : 0) * 0.5);
            const base = item.baseSymbolSize || item.symbolSize;
            return {
                ...item,
                symbolSize: base * scale,
            };
        });

        chart.setOption({
            series: [
                { id: 'stars-glow', data: glowData, animationDurationUpdate: 0 },
                { id: 'stars-body', data: bodyData, animationDurationUpdate: 0 },
            ],
        }, { lazyUpdate: true, silent: true });

        filmRaf = requestAnimationFrame(animateFilmStarsHeartbeat);
    }

    function startFilmMotion() {
        if (reducedMotion || filmMotionActive) return;
        filmMotionActive = true;
        cancelAnimationFrame(filmRaf);
        filmRaf = requestAnimationFrame(animateFilmStarsHeartbeat);
    }

    function stopFilmMotion() {
        filmMotionActive = false;
        cancelAnimationFrame(filmRaf);
        filmRaf = 0;
        resetFilmStarMotion();
    }

    if (!reducedMotion) {
        requestAnimationFrame(() => startFilmMotion());
    }

    return {
        resize() {
            chart.resize();
            syncLangOverlay();
            langOverlay?.resize();
        },
        dispose() {
            container.removeEventListener('wheel', onMapWheel);
            container.removeEventListener('click', onContainerClick);
            container.removeEventListener('mousemove', onContainerMouseMove);
            container.removeEventListener('mouseleave', onContainerMouseLeave);
            if (hoverRaf) {
                cancelAnimationFrame(hoverRaf);
                hoverRaf = 0;
            }
            stopFilmMotion();
            langOverlay?.dispose();
            chart.dispose();
        },
        startMotion() {
            langOverlay?.start();
            startFilmMotion();
        },
        stopMotion() {
            langOverlay?.stop();
            stopFilmMotion();
        },
        clearHighlight,
        flyToProvince,
        highlightByProvinceId(provinceId) {
            const geoName = ID_TO_GEO[provinceId];
            if (geoName) highlightProvince(geoName);
        },
        getProvince(provinceId) {
            return data.provinces[provinceId];
        },
        getProvinceScreenPos(provinceId) {
            const center = data.centers[provinceId];
            if (!center) return null;
            return geoToScreen(center);
        },
        getLangStarScreenPos(langId) {
            return langOverlay?.getScreenPos(langId) || null;
        },
        getLanguages() {
            return data.languages || [];
        },
    };
}

export function renderAssetTabs(province, activeKey, languages) {
    const assets = province && typeof province.assets === 'object' && province.assets
        ? province.assets
        : {};
    const provinceLangs = Array.isArray(province?.languages) ? province.languages : [];
    const catalog = Array.isArray(languages) ? languages : languageCatalog;
    const byName = new Map(catalog.map((item) => [item.name, item]));
    const tabs = ASSET_TABS.filter((tab) => {
        if (tab.key === 'languages') return provinceLangs.length;
        return Array.isArray(assets[tab.key]) && assets[tab.key].length;
    });
    const key = activeKey && tabs.some((t) => t.key === activeKey) ? activeKey : tabs[0]?.key;
    let items = [];
    if (key === 'languages') {
        items = provinceLangs.map((lang) => {
            const meta = byName.get(lang);
            const desc = (meta && (meta.stories || meta.language)) || '本地叙事常用口语。';
            return { title: lang, desc, langName: lang };
        });
    } else {
        items = Array.isArray(assets[key]) ? assets[key] : [];
    }
    return { tabs, key, items };
}

export { ASSET_TABS, GEO_TO_ID, SAR_PINS, ID_TO_GEO };
