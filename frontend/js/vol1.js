document.addEventListener('DOMContentLoaded', async () => {
    await DataService.init({ slim: true });
    const data = DataService.dataset;
    if(data.length === 0) {
        renderLocalGallery([], '当前筛选下没有电影记录。');
        document.getElementById('gallery-subtitle').innerText = '暂无数据';
        return;
    }

    const chart = echarts.init(document.getElementById('bubbleChart'));
    
    // Group data
    const aggregated = {};
    data.forEach(d => {
        if(!aggregated[d.decade]) aggregated[d.decade] = { sum: 0, count: 0 };
        aggregated[d.decade].sum += d.rating;
        aggregated[d.decade].count++;
    });

    const sortedDecades = ["Pre-1990s", "1990s", "2000s", "2010s", "2020s"];
    const chartData = sortedDecades.map((d, i) => {
        if(!aggregated[d]) return null;
        return [i, aggregated[d].sum / aggregated[d].count, aggregated[d].count, d];
    }).filter(d => d);

    const maxCount = Math.max(1, ...chartData.map(item => item[2]));
    const overallMean = data.reduce((sum, movie) => sum + movie.rating, 0) / data.length;

    const option = {
        ...getBaseChartOption(),
        tooltip: {
            ...getBaseChartOption().tooltip,
            trigger: 'item',
            formatter: p => {
                const row = p.seriesType === 'line' ? chartData[p.dataIndex] : p.data;
                if (!row) return '';
                return `<div style="font-weight:bold;color:${TOKENS.primary};margin-bottom:8px">${row[3]}</div>
                        平均评分: <span style="color:${TOKENS.textMain}">${row[1].toFixed(2)}</span><br>
                        电影数 n: <span style="color:${TOKENS.textMain}">${row[2].toLocaleString('zh-CN')}</span>`;
            }
        },
        grid: { left: '8%', right: '8%', top: '10%', bottom: '10%' },
        xAxis: {
            type: 'category',
            data: sortedDecades,
            splitLine: { show: true, lineStyle: { color: TOKENS.gridLine, type: 'dashed' } },
            axisLine: { lineStyle: { color: TOKENS.gridLine } },
            axisLabel: { color: TOKENS.textMuted }
        },
        yAxis: {
            type: 'value',
            min: 5, max: 10,
            splitLine: { show: true, lineStyle: { color: TOKENS.gridLine, type: 'dashed' } },
            axisLine: { lineStyle: { color: TOKENS.gridLine } },
            axisLabel: { color: TOKENS.textMuted }
        },
        series: [
            {
                name: '年代电影',
                type: 'scatter',
                data: chartData,
                symbolSize: row => 18 + Math.sqrt(row[2] / maxCount) * 62,
                itemStyle: {
                    color: 'rgba(143, 178, 255, 0.42)',
                    borderColor: TOKENS.primary,
                    borderWidth: 1.5
                },
                markLine: {
                    silent: true,
                    symbol: ['none', 'none'],
                    lineStyle: { color: TOKENS.accent, type: 'dashed', width: 1.5 },
                    label: {
                        formatter: `全部电影均值 ${overallMean.toFixed(2)}`,
                        color: TOKENS.accent,
                        position: 'insideEndTop',
                        backgroundColor: 'rgba(9, 9, 11, 0.86)',
                        padding: [3, 5]
                    },
                    data: [{ yAxis: overallMean }]
                },
                z: 3
            },
            {
                name: '年代均值走势',
                type: 'line',
                data: chartData.map(row => row[1]),
                symbol: 'none',
                silent: true,
                lineStyle: { color: TOKENS.secondary, width: 2 },
                z: 2
            }
        ]
    };
    chart.setOption(option);
    window.addEventListener('resize', (window.StoryUI ? window.StoryUI.rafThrottle(() => chart.resize()) : () => chart.resize()));

    // Initial Empty State
    renderLocalGallery([], '点击年代点查看该组评分较高的电影');

    chart.on('click', params => {
        if(params.name) {
            const movies = DataService.getMoviesByDecade(params.name);
            renderLocalGallery(movies, `${params.name} 电影（n=${movies.length.toLocaleString('zh-CN')}，按评分展示前 12 部）`);
        }
    });
});
