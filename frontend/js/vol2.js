import { DataService, StoryUI, TOKENS, getBaseChartOption, renderLocalGallery } from './core.js';

document.addEventListener('DOMContentLoaded', async () => {
    await DataService.init({ slim: true });
    const data = DataService.dataset;
    if(data.length === 0) {
        renderLocalGallery([], '当前筛选下没有电影记录。');
        document.getElementById('gallery-subtitle').innerText = '暂无数据';
        return;
    }

    const chart = echarts.init(document.getElementById('boxplotChart'));
    
    function getQuantile(arr, q) {
        if(arr.length === 0) return 0;
        if(arr.length === 1) return arr[0];
        const pos = (arr.length - 1) * q;
        const base = Math.floor(pos);
        const rest = pos - base;
        if (arr[base + 1] !== undefined) return arr[base] + rest * (arr[base + 1] - arr[base]);
        return arr[base];
    }
    
    function calcBoxplotData(dataArray) {
        if(!dataArray || dataArray.length === 0) {
            return { box: [0, 0, 0, 0, 0], lowerFence: 0, upperFence: 0 };
        }
        const sorted = [...dataArray].sort((a,b) => a - b);
        const q1 = getQuantile(sorted, 0.25);
        const median = getQuantile(sorted, 0.5);
        const q3 = getQuantile(sorted, 0.75);
        const iqr = q3 - q1;
        const lowerFence = q1 - 1.5 * iqr;
        const upperFence = q3 + 1.5 * iqr;
        const lowerWhisker = sorted.find(value => value >= lowerFence);
        const upperWhisker = [...sorted].reverse().find(value => value <= upperFence);
        return {
            box: [lowerWhisker, q1, median, q3, upperWhisker],
            lowerFence,
            upperFence
        };
    }

    const regions = ["North_America", "Europe", "East_Asia", "China", "Other"];
    const regionLabels = {
        North_America: '北美',
        Europe: '欧洲',
        East_Asia: '东亚',
        China: '中国（含港澳台）',
        Other: '其他'
    };
    const grouped = {};
    regions.forEach(r => grouped[r] = []);
    data.forEach(d => { if(grouped[d.region]) grouped[d.region].push(d.rating); });

    const boxStats = regions.map(r => calcBoxplotData(grouped[r]));
    const boxData = boxStats.map(stats => stats.box);
    const sortedRatings = data.map(movie => movie.rating).sort((a, b) => a - b);
    const overallMedian = getQuantile(sortedRatings, 0.5);
    
    // Calculate Outliers
    const outliers = [];
    regions.forEach((r, i) => {
        const stats = boxStats[i];
        grouped[r].forEach(val => {
            if(val < stats.lowerFence || val > stats.upperFence) {
                outliers.push({ value: [i, val], region: r });
            }
        });
    });

    const option = {
        ...getBaseChartOption(),
        tooltip: {
            ...getBaseChartOption().tooltip,
            trigger: 'item',
            axisPointer: { type: 'shadow' },
            formatter: params => {
                const region = params.seriesType === 'scatter'
                    ? params.data.region
                    : regions[params.dataIndex];
                const label = regionLabels[region] || region;
                if (params.seriesType === 'scatter') {
                    return `<strong style="color:${TOKENS.primary}">${label}离群点</strong><br>
                            评分：${Number(params.value[1]).toFixed(1)}<br>
                            电影数 n=${grouped[region].length.toLocaleString('zh-CN')}`;
                }
                const values = boxStats[params.dataIndex].box;
                return `<strong style="color:${TOKENS.primary}">${label}</strong><br>
                        电影数 n=${grouped[region].length.toLocaleString('zh-CN')}<br>
                        下须线：${values[0].toFixed(2)}<br>
                        Q1：${values[1].toFixed(2)}<br>
                        中位数：${values[2].toFixed(2)}<br>
                        Q3：${values[3].toFixed(2)}<br>
                        上须线：${values[4].toFixed(2)}`;
            }
        },
        grid: { left: '8%', right: '8%', top: '10%', bottom: '15%' },
        xAxis: {
            type: 'category',
            data: regions,
            axisLine: { lineStyle: { color: TOKENS.gridLine } },
            axisLabel: {
                color: TOKENS.textMuted,
                lineHeight: 18,
                formatter: value => `${regionLabels[value]}\nn=${grouped[value].length.toLocaleString('zh-CN')}`
            }
        },
        yAxis: {
            type: 'value', min: 0, max: 10,
            splitLine: { lineStyle: { color: TOKENS.gridLine } },
            axisLabel: { color: TOKENS.textMuted }
        },
        series: [
            {
                name: 'Rating Distribution',
                type: 'boxplot',
                data: boxData,
                itemStyle: { color: 'rgba(143, 178, 255, 0.18)', borderColor: TOKENS.primary, borderWidth: 1.5 },
                boxWidth: [20, 50],
                markLine: {
                    silent: true,
                    symbol: ['none', 'none'],
                    lineStyle: { type: 'dashed', width: 1.25 },
                    label: {
                        position: 'insideEndTop',
                        backgroundColor: 'rgba(9, 9, 11, 0.86)',
                        padding: [3, 5]
                    },
                    data: [
                        {
                            yAxis: overallMedian,
                            name: `全部电影中位数 ${overallMedian.toFixed(2)}`,
                            lineStyle: { color: TOKENS.secondary },
                            label: { formatter: `全部电影中位数 ${overallMedian.toFixed(2)}`, color: TOKENS.secondary }
                        },
                        {
                            yAxis: 5,
                            name: '低分界线 5.0',
                            lineStyle: { color: TOKENS.accent },
                            label: { formatter: '低分界线 5.0', color: TOKENS.accent }
                        },
                        {
                            yAxis: 8.5,
                            name: '编辑高分阈值 8.5',
                            lineStyle: { color: '#FFD166' },
                            label: { formatter: '编辑高分阈值 8.5', color: '#FFD166' }
                        }
                    ]
                }
            },
            {
                name: 'Cultural Outliers',
                type: 'scatter',
                data: outliers,
                symbolSize: 6,
                itemStyle: { color: TOKENS.accent }
            }
        ]
    };
    chart.setOption(option);
    window.addEventListener('resize', (window.StoryUI ? window.StoryUI.rafThrottle(() => chart.resize()) : () => chart.resize()));

    renderLocalGallery([], '点击箱体或离群点查看对应地区的电影');

    chart.on('click', params => {
        const region = params.seriesType === 'scatter'
            ? params.data && params.data.region
            : regions[params.dataIndex];
        if(region) {
            const movies = DataService.getMoviesByRegion(region);
            renderLocalGallery(movies, `${regionLabels[region]}电影（n=${movies.length.toLocaleString('zh-CN')}，按评分展示前 12 部）`);
        }
    });
});
