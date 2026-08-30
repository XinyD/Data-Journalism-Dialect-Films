document.addEventListener('DOMContentLoaded', async () => {
    await DataService.init({ slim: true });
    const data = DataService.dataset;
    if(data.length === 0) {
        renderLocalGallery([], '当前筛选下没有电影记录。');
        document.getElementById('gallery-subtitle').innerText = '暂无数据';
        return;
    }

    const chart = echarts.init(document.getElementById('languageChart'));
    
    const languageGroups = [
        { code: 0, label: '英语' },
        { code: 1, label: '日语' },
        { code: 4, label: '韩语' },
        { code: 2, label: '普通话' },
        { code: 3, label: '方言' },
        { code: 5, label: '其他' }
    ];
    const aggregated = Object.fromEntries(languageGroups.map(group => [group.code, { sum: 0, count: 0 }]));
    data.forEach(d => {
        if (!aggregated[d.langCode]) return;
        aggregated[d.langCode].sum += d.rating;
        aggregated[d.langCode].count++;
    });

    const total = data.length;
    const barData = languageGroups.map(group => ({
        value: aggregated[group.code].count,
        name: group.label,
        code: group.code,
        label: group.label,
        rating: aggregated[group.code].sum / aggregated[group.code].count,
        share: aggregated[group.code].count / total * 100
    })).sort((a,b) => b.value - a.value);
    const equalShareCount = total / barData.length;
    const colors = ['#8FB2FF', '#E85D4C', '#5CC8A1', '#62B0FF', '#FFD166', '#B5A6D8'];

    const option = {
        ...getBaseChartOption(),
        tooltip: {
            ...getBaseChartOption().tooltip,
            trigger: 'item',
            formatter: p => `<div style="font-weight:bold;color:${TOKENS.primary};margin-bottom:8px">${p.data.label}</div>
                             电影数 n: <span style="color:${TOKENS.textMain}">${Number(p.value).toLocaleString('zh-CN')}</span><br>
                             电影占比: <span style="color:${TOKENS.textMain}">${p.data.share.toFixed(1)}%</span><br>
                             组内均分: <span style="color:${TOKENS.textMain}">${p.data.rating.toFixed(2)}</span>`
        },
        grid: { left: 118, right: 90, top: 28, bottom: 48 },
        xAxis: {
            type: 'value',
            name: '电影数',
            nameLocation: 'middle',
            nameGap: 30,
            nameTextStyle: { color: TOKENS.textMuted },
            splitLine: { lineStyle: { color: TOKENS.gridLine, type: 'dashed' } },
            axisLine: { lineStyle: { color: TOKENS.gridLine } },
            axisLabel: { color: TOKENS.textMuted }
        },
        yAxis: {
            type: 'category',
            inverse: true,
            data: barData.map(item => item.label),
            axisLine: { lineStyle: { color: TOKENS.gridLine } },
            axisTick: { show: false },
            axisLabel: { color: TOKENS.textMuted }
        },
        series: [{
            name: 'Languages',
            type: 'bar',
            data: barData,
            barMaxWidth: 46,
            itemStyle: {
                color: params => colors[params.dataIndex % colors.length],
                borderRadius: [0, 3, 3, 0]
            },
            label: {
                show: true,
                position: 'right',
                color: TOKENS.textMain,
                formatter: params => `${Number(params.value).toLocaleString('zh-CN')} · ${params.data.share.toFixed(1)}%`
            },
            markLine: {
                silent: true,
                symbol: ['none', 'none'],
                lineStyle: { color: TOKENS.accent, type: 'dashed', width: 1.5 },
                label: {
                    formatter: `六组等额（${Math.round(equalShareCount).toLocaleString('zh-CN')} 部）`,
                    color: TOKENS.accent,
                    position: 'insideEndTop',
                    backgroundColor: 'rgba(9, 9, 11, 0.86)',
                    padding: [3, 5]
                },
                data: [{ xAxis: equalShareCount }]
            }
        }]
    };
    chart.setOption(option);
    window.addEventListener('resize', (window.StoryUI ? window.StoryUI.rafThrottle(() => chart.resize()) : () => chart.resize()));

    renderLocalGallery([], '点击条形查看该语言分类的电影');

    chart.on('click', params => {
        const code = params.data && params.data.code;
        if(Number.isInteger(code)) {
            const movies = data.filter(movie => movie.langCode === code);
            renderLocalGallery(movies, `${params.data.label}电影（n=${movies.length.toLocaleString('zh-CN')}，按评分展示前 12 部）`);
        }
    });
});
